# services/importer_service.py
"""
Secure Importer & Watched List Synchronization Service for Letterboxd Data.

Features:
- Secure ZIP validation (prevents zip bombs, zip slack, path traversal/zip slip, polyglots, dangerous extensions).
- In-memory CSV parsing and smart merging of watched.csv, ratings.csv, and diary.csv.
- Granular diff computation: identifies added, deleted, and retained films.
- Non-destructive synchronization: preserves existing TMDb metadata and physical copy status,
  fetches TMDb metadata only for newly added films, and removes deleted films.
"""

import io
import struct
import zipfile
import time
import os
import pandas as pd
import numpy as np
from services.tmbd_service import fetch_movie_metadata

# --- SECURITY LIMITS FOR ZIP ARCHIVES ---
MAX_ZIP_UPLOAD_SIZE = 50 * 1024 * 1024       # 50 MB compressed
MAX_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024   # 100 MB uncompressed
MAX_SINGLE_FILE_UNCOMPRESSED = 25 * 1024 * 1024 # 25 MB single file
MAX_COMPRESSION_RATIO = 100.0                # Max expansion ratio
MAX_ENTRIES_COUNT = 250                      # Max files in zip

DANGEROUS_EXTENSIONS = {
    '.exe', '.dll', '.bat', '.cmd', '.sh', '.vbs', '.js', '.py', '.scr',
    '.pif', '.lnk', '.jar', '.com', '.msi', '.ps1', '.hta', '.reg',
    '.zip', '.tar', '.gz', '.7z', '.rar', '.bz2', '.iso', '.bin', '.sys',
    '.app', '.dmg', '.action', '.command'
}

class ZipSecurityError(Exception):
    """Raised when an uploaded ZIP file fails security or structural verification."""
    pass


def validate_and_extract_zip(zip_bytes: bytes) -> dict:
    """
    Performs comprehensive security and integrity checks on raw ZIP bytes,
    then extracts CSV files in-memory into a dict of {filename: bytes}.
    
    Protections:
    1. Magic Bytes & Polyglot check (must begin with PK\x03\x04 or PK\x05\x06 at offset 0).
    2. Zip Slack detection (checks End of Central Directory offset against total file size).
    3. Structural integrity verification (CRC32 checksums via testzip).
    4. Zip Bomb prevention (file count, single file size, total uncompressed size, compression ratio).
    5. Path traversal / Zip Slip prevention (checks relative path components and drive letters).
    6. Dangerous extension rejection (.exe, .bat, scripts, binaries, nested archives).
    7. Encryption rejection (Letterboxd archives are never encrypted).
    """
    total_size = len(zip_bytes)
    if total_size < 22:
        raise ZipSecurityError("Uploaded file is too small to be a valid ZIP archive.")
        
    if total_size > MAX_ZIP_UPLOAD_SIZE:
        raise ZipSecurityError(f"ZIP archive size ({total_size // (1024*1024)} MB) exceeds maximum allowed size ({MAX_ZIP_UPLOAD_SIZE // (1024*1024)} MB).")

    # 1. Polyglot / Prepend check
    if not (zip_bytes.startswith(b"PK\x03\x04") or zip_bytes.startswith(b"PK\x05\x06")):
        raise ZipSecurityError("Invalid ZIP header signature. File may be a polyglot archive, disguised executable, or corrupted.")

    # 2. Zip Slack / Appended Trailing Payload check
    max_search = min(total_size, 65557)
    search_buf = zip_bytes[-max_search:]
    eocd_pos_in_buf = search_buf.rfind(b"PK\x05\x06")
    if eocd_pos_in_buf == -1:
        raise ZipSecurityError("Could not locate End of Central Directory (EOCD) record. Archive is corrupted or invalid.")

    eocd_pos = total_size - max_search + eocd_pos_in_buf
    if total_size - eocd_pos < 22:
        raise ZipSecurityError("Truncated End of Central Directory record in archive.")

    comment_len = struct.unpack("<H", zip_bytes[eocd_pos + 20:eocd_pos + 22])[0]
    expected_end = eocd_pos + 22 + comment_len

    if total_size > expected_end:
        slack_bytes = total_size - expected_end
        if slack_bytes > 4:  # allow minimal 4-byte boundary padding
            raise ZipSecurityError(f"Zip Slack detected: {slack_bytes} bytes of unauthorized trailing data found appended to archive.")
    elif total_size < expected_end:
        raise ZipSecurityError("Archive is truncated: expected comment length exceeds file size.")

    # 3. Structural validation via zipfile module
    bio = io.BytesIO(zip_bytes)
    try:
        zf = zipfile.ZipFile(bio, 'r')
    except Exception as e:
        raise ZipSecurityError(f"Failed to parse ZIP archive: {e}")

    # Check CRC32 integrity
    bad_file = zf.testzip()
    if bad_file:
        raise ZipSecurityError(f"Archive integrity check failed: file '{bad_file}' is corrupted.")

    entries = zf.infolist()
    if len(entries) > MAX_ENTRIES_COUNT:
        raise ZipSecurityError(f"ZIP archive contains too many entries ({len(entries)} > {MAX_ENTRIES_COUNT}). Potential zip bomb.")

    total_uncompressed = 0
    extracted_csvs = {}

    for info in entries:
        # Check encryption
        if info.flag_bits & 0x1:
            raise ZipSecurityError(f"Encrypted entries are prohibited in Letterboxd exports: {info.filename}")

        # Path traversal / Zip Slip check
        norm_name = info.filename.replace('\\', '/')
        if '..' in norm_name or norm_name.startswith('/') or norm_name.startswith('\\') or (len(norm_name) > 1 and norm_name[1] == ':'):
            raise ZipSecurityError(f"Path traversal detected in archive entry: {info.filename}")

        if info.is_dir() or norm_name.endswith('/'):
            continue

        lower_name = norm_name.lower()
        ext = '.' + lower_name.rsplit('.', 1)[-1] if '.' in lower_name else ''

        if ext in DANGEROUS_EXTENSIONS:
            raise ZipSecurityError(f"Potentially dangerous or nested archive file '{ext}' detected: {info.filename}")

        # Zip bomb / ratio checks
        comp_size = max(info.compress_size, 1)
        uncomp_size = info.file_size

        if uncomp_size > MAX_SINGLE_FILE_UNCOMPRESSED:
            raise ZipSecurityError(f"Uncompressed entry exceeds maximum size ({uncomp_size // (1024*1024)} MB): {info.filename}")

        ratio = uncomp_size / comp_size
        if ratio > MAX_COMPRESSION_RATIO and comp_size > 100:
            raise ZipSecurityError(f"Abnormal compression ratio ({ratio:.1f}x) detected for {info.filename}. Potential zip bomb.")

        total_uncompressed += uncomp_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise ZipSecurityError(f"Total uncompressed content ({total_uncompressed // (1024*1024)} MB) exceeds security threshold.")

        if lower_name.endswith('.csv'):
            base_name = lower_name.rsplit('/', 1)[-1]
            extracted_csvs[base_name] = zf.read(info)

    if not extracted_csvs:
        raise ZipSecurityError("No valid Letterboxd CSV files found in the ZIP archive.")

    return extracted_csvs


def read_csv_safe(data_bytes: bytes) -> pd.DataFrame:
    """Safely decodes and parses raw CSV bytes with multiple encodings."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            return pd.read_csv(io.BytesIO(data_bytes), encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError(f"Could not parse CSV: {e}")
    return pd.read_csv(io.BytesIO(data_bytes), encoding='utf-8', errors='replace')


def load_uploaded_files(uploaded_files_list) -> tuple[pd.DataFrame, dict]:
    """
    Processes uploaded files (list of UploadedFile objects, which may include
    .zip archives, or individual .csv files like watched.csv, ratings.csv, diary.csv).
    
    Returns:
        (combined_df, info_dict)
    """
    if not uploaded_files_list:
        return pd.DataFrame(), {}

    raw_csv_dict = {}  # {filename_lower: DataFrame}
    source_type = "csv"

    for uf in uploaded_files_list:
        fname = uf.name.lower()
        content = uf.getvalue() if hasattr(uf, 'getvalue') else uf.read()

        if fname.endswith('.zip'):
            source_type = "zip"
            # Validates security and extracts in-memory CSVs
            csv_bytes_map = validate_and_extract_zip(content)
            for csv_name, csv_bytes in csv_bytes_map.items():
                try:
                    df = read_csv_safe(csv_bytes)
                    raw_csv_dict[csv_name] = df
                except Exception as e:
                    pass
        elif fname.endswith('.csv'):
            try:
                df = read_csv_safe(content)
                raw_csv_dict[fname] = df
            except Exception as e:
                pass

    if not raw_csv_dict:
        return pd.DataFrame(), {}

    # Merge watched, ratings, and diary CSVs
    combined_df = merge_letterboxd_dfs(raw_csv_dict)
    
    info = {
        "source": source_type,
        "files_found": list(raw_csv_dict.keys()),
        "total_records": len(combined_df),
        "has_ratings": int(combined_df['Rating'].notna().sum()) if 'Rating' in combined_df.columns else 0
    }
    return combined_df, info


def merge_letterboxd_dfs(csv_dict: dict) -> pd.DataFrame:
    """
    Intelligently merges watched.csv, ratings.csv, and diary.csv from Letterboxd.
    Prioritizes:
    - watched.csv for complete history of watched films.
    - ratings.csv for official star ratings.
    - diary.csv for diary dates and ratings if missing.
    """
    watched_df = next((df for name, df in csv_dict.items() if 'watched' in name), None)
    ratings_df = next((df for name, df in csv_dict.items() if 'rating' in name), None)
    diary_df = next((df for name, df in csv_dict.items() if 'diary' in name), None)

    # Standardize column names
    def clean_cols(d):
        if d is None:
            return None
        res = d.copy()
        res.columns = [str(c).strip() for c in res.columns]
        if 'Title' in res.columns and 'Name' not in res.columns:
            res['Name'] = res['Title']
        return res

    watched_df = clean_cols(watched_df)
    ratings_df = clean_cols(ratings_df)
    diary_df = clean_cols(diary_df)

    # Base DataFrame
    if watched_df is not None and not watched_df.empty:
        base_df = watched_df.copy()
    elif diary_df is not None and not diary_df.empty:
        # Deduplicate diary entries to create base watched list
        diary_clean = diary_df.copy()
        if 'Watched Date' in diary_clean.columns and 'Date' not in diary_clean.columns:
            diary_clean['Date'] = diary_clean['Watched Date']
        dedup_keys = [c for c in ['Letterboxd URI', 'Name', 'Year'] if c in diary_clean.columns] or ['Name']
        base_df = diary_clean.drop_duplicates(subset=dedup_keys, keep='last').copy()
    elif ratings_df is not None and not ratings_df.empty:
        base_df = ratings_df.copy()
    else:
        # Fallback to the first available dataframe
        base_df = clean_cols(next(iter(csv_dict.values())))

    # Ensure required columns
    for col in ['Name', 'Year', 'Letterboxd URI']:
        if col not in base_df.columns:
            base_df[col] = ""

    # Attach or merge Ratings
    if ratings_df is not None and 'Rating' in ratings_df.columns:
        join_keys = [c for c in ['Letterboxd URI', 'Name', 'Year'] if c in base_df.columns and c in ratings_df.columns]
        if 'Letterboxd URI' in join_keys and (base_df['Letterboxd URI'].astype(str).str.contains('boxd.it').sum() > 0):
            keys_to_use = ['Letterboxd URI']
        elif 'Name' in join_keys and 'Year' in join_keys:
            keys_to_use = ['Name', 'Year']
        else:
            keys_to_use = ['Name'] if 'Name' in join_keys else []

        if keys_to_use:
            rating_sub = ratings_df[keys_to_use + ['Rating']].dropna(subset=['Rating']).drop_duplicates(subset=keys_to_use, keep='last')
            if 'Rating' in base_df.columns:
                base_df = base_df.drop(columns=['Rating'])
            base_df = pd.merge(base_df, rating_sub, on=keys_to_use, how='left')

    # If Rating is still missing or unrated, try pulling from diary.csv
    if diary_df is not None and 'Rating' in diary_df.columns:
        if 'Rating' not in base_df.columns:
            base_df['Rating'] = np.nan
        
        diary_keys = [c for c in ['Letterboxd URI', 'Name', 'Year'] if c in base_df.columns and c in diary_df.columns]
        if 'Letterboxd URI' in diary_keys:
            d_keys = ['Letterboxd URI']
        elif 'Name' in diary_keys and 'Year' in diary_keys:
            d_keys = ['Name', 'Year']
        else:
            d_keys = ['Name'] if 'Name' in diary_keys else []
            
        if d_keys:
            diary_ratings = diary_df[d_keys + ['Rating']].dropna(subset=['Rating']).drop_duplicates(subset=d_keys, keep='last')
            diary_map = dict(zip(diary_ratings[d_keys[0]], diary_ratings['Rating'])) if len(d_keys) == 1 else None
            if diary_map:
                base_df['Rating'] = base_df['Rating'].fillna(base_df[d_keys[0]].map(diary_map))

    # Also add any films from diary that weren't in watched.csv
    if diary_df is not None and watched_df is not None:
        diary_names = set(diary_df['Name'].dropna().astype(str).str.strip().str.lower())
        watched_names = set(base_df['Name'].dropna().astype(str).str.strip().str.lower())
        missing_names = diary_names - watched_names
        if missing_names:
            missing_diary = diary_df[diary_df['Name'].astype(str).str.strip().str.lower().isin(missing_names)].copy()
            if 'Watched Date' in missing_diary.columns and 'Date' not in missing_diary.columns:
                missing_diary['Date'] = missing_diary['Watched Date']
            dedup_keys = [c for c in ['Name', 'Year'] if c in missing_diary.columns] or ['Name']
            missing_clean = missing_diary.drop_duplicates(subset=dedup_keys)
            base_df = pd.concat([base_df, missing_clean], ignore_index=True)

    # Clean up types and deduplicate
    dedup_cols = ['Letterboxd URI'] if ('Letterboxd URI' in base_df.columns and base_df['Letterboxd URI'].astype(str).str.contains('boxd.it').sum() > 0) else [c for c in ['Name', 'Year'] if c in base_df.columns]
    if dedup_cols:
        base_df = base_df.drop_duplicates(subset=dedup_cols, keep='last')

    if 'Rating' in base_df.columns:
        base_df['Rating'] = pd.to_numeric(base_df['Rating'], errors='coerce')
    else:
        base_df['Rating'] = np.nan

    return base_df.reset_index(drop=True)


# --- CANONICAL FILM IDENTIFIER & DIFF ENGINE ---

def normalize_title(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip().lower()

def normalize_year(val):
    if pd.isna(val) or val is None:
        return 0
    try:
        s = str(val).split(".")[0].strip()
        return int(s) if s.isdigit() else 0
    except Exception:
        return 0

def normalize_uri(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip().lower().rstrip('/')
    return s if ('boxd.it' in s or 'letterboxd.com' in s) else ""


def compute_dataset_diff(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Compares the existing enriched dataset with a newly uploaded Letterboxd export.
    
    Returns:
        (added_df, deleted_df, retained_df)
        - added_df: new films in new_df not in existing_df (to be enriched with TMDb metadata).
        - deleted_df: films in existing_df not in new_df (to be removed from the database).
        - retained_df: films in existing_df that are preserved, with updated ratings/dates
          applied from new_df while strictly preserving all existing TMDb enrichment metadata
          and physical_copy toggles.
    """
    if existing_df is None or existing_df.empty:
        return new_df.copy() if new_df is not None else pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    if new_df is None or new_df.empty:
        return pd.DataFrame(), existing_df.copy(), pd.DataFrame()

    existing_by_uri = {}
    existing_by_title_year = {}

    for idx, row in existing_df.iterrows():
        uri = normalize_uri(row.get('Letterboxd URI'))
        if uri:
            existing_by_uri[uri] = idx
        name = normalize_title(row.get('Name') if pd.notna(row.get('Name')) else row.get('Title'))
        year = normalize_year(row.get('Year'))
        if name:
            existing_by_title_year[(name, year)] = idx
            if year != 0 and (name, 0) not in existing_by_title_year:
                existing_by_title_year[(name, 0)] = idx

    matched_existing_indices = set()
    added_new_indices = []
    new_to_existing_map = {}

    for new_idx, new_row in new_df.iterrows():
        new_uri = normalize_uri(new_row.get('Letterboxd URI'))
        new_name = normalize_title(new_row.get('Name') if pd.notna(new_row.get('Name')) else new_row.get('Title'))
        new_year = normalize_year(new_row.get('Year'))

        matched_idx = None
        if new_uri and new_uri in existing_by_uri:
            matched_idx = existing_by_uri[new_uri]
        elif (new_name, new_year) in existing_by_title_year:
            matched_idx = existing_by_title_year[(new_name, new_year)]
        elif (new_name, 0) in existing_by_title_year:
            matched_idx = existing_by_title_year[(new_name, 0)]

        if matched_idx is not None and matched_idx not in matched_existing_indices:
            matched_existing_indices.add(matched_idx)
            new_to_existing_map[new_idx] = matched_idx
        else:
            added_new_indices.append(new_idx)

    # 1. Added movies
    added_df = new_df.loc[added_new_indices].copy().reset_index(drop=True) if added_new_indices else pd.DataFrame(columns=new_df.columns)

    # 2. Deleted movies
    deleted_indices = [idx for idx in existing_df.index if idx not in matched_existing_indices]
    deleted_df = existing_df.loc[deleted_indices].copy().reset_index(drop=True) if deleted_indices else pd.DataFrame(columns=existing_df.columns)

    # 3. Retained movies (preserves TMDb columns and physical_copy, updates rating & date)
    retained_records = []
    for new_idx, ex_idx in new_to_existing_map.items():
        ex_row = existing_df.loc[ex_idx].to_dict()
        new_row = new_df.loc[new_idx]

        # Update Rating from new export
        if 'Rating' in new_df.columns:
            new_rating = new_row.get('Rating')
            if pd.notna(new_rating):
                try:
                    ex_row['Rating'] = float(new_rating)
                except Exception:
                    ex_row['Rating'] = new_rating
            else:
                ex_row['Rating'] = np.nan

        # Update Date from new export
        if 'Date' in new_df.columns and pd.notna(new_row.get('Date')):
            ex_row['Date'] = str(new_row.get('Date'))

        # Update Letterboxd URI if new_df has official URI and existing was tmdb placeholder
        if 'Letterboxd URI' in new_df.columns and pd.notna(new_row.get('Letterboxd URI')):
            uri_val = str(new_row.get('Letterboxd URI')).strip()
            if uri_val and ('tmdb-' not in uri_val or not ex_row.get('Letterboxd URI')):
                ex_row['Letterboxd URI'] = uri_val

        # Ensure physical_copy is preserved
        ex_row['physical_copy'] = bool(ex_row.get('physical_copy', False))

        retained_records.append(ex_row)

    retained_df = pd.DataFrame(retained_records) if retained_records else pd.DataFrame(columns=existing_df.columns)
    return added_df, deleted_df, retained_df


def apply_dataset_update(existing_df: pd.DataFrame, new_raw_df: pd.DataFrame, api_key: str,
                         parquet_path: str = "data/letterboxd_enriched.parquet",
                         progress_callback=None, status_callback=None) -> tuple[pd.DataFrame, dict]:
    """
    Executes the watched list synchronization:
    1. Identifies added, deleted, and retained films.
    2. Fetches TMDb metadata only for the newly added films.
    3. Combines retained films with newly enriched films.
    4. Writes the updated dataset to the parquet file.
    5. Returns (updated_enriched_df, diff_summary).
    """
    added_df, deleted_df, retained_df = compute_dataset_diff(existing_df, new_raw_df)

    title_col = "Name" if "Name" in added_df.columns else ("Title" if "Title" in added_df.columns else None)
    year_col = "Year" if "Year" in added_df.columns else None

    enriched_new_records = []
    total_to_enrich = len(added_df)

    for idx, row in added_df.iterrows():
        title = row[title_col] if title_col else ""
        year = row[year_col] if year_col else None

        if status_callback:
            status_callback(f"({idx + 1}/{total_to_enrich}) Enriching: {title} ({year or 'N/A'})...")

        meta = fetch_movie_metadata(title, year, api_key) if (api_key and title) else None

        record = row.to_dict()
        record["physical_copy"] = False  # Default for newly imported films

        if meta:
            record["genres"] = meta.get("genres", [])
            record["directors"] = meta.get("directors", [])
            record["actors"] = meta.get("actors", [])
            record["tmdb_rating"] = meta.get("tmdb_rating")
            record["runtime"] = meta.get("runtime")
            record["poster_path"] = meta.get("poster_path")
            record["overview"] = meta.get("overview", "")
            record["production_countries"] = meta.get("production_countries", [])
        else:
            record["genres"] = []
            record["directors"] = []
            record["actors"] = []
            record["tmdb_rating"] = None
            record["runtime"] = None
            record["poster_path"] = None
            record["overview"] = ""
            record["production_countries"] = []

        enriched_new_records.append(record)

        if progress_callback:
            progress_callback((idx + 1) / total_to_enrich if total_to_enrich > 0 else 1.0)

        # Gentle throttling for TMDb API rate limits
        time.sleep(0.04)

    # Combine retained films + newly enriched films
    if enriched_new_records:
        new_enriched_df = pd.DataFrame(enriched_new_records)
        final_df = pd.concat([retained_df, new_enriched_df], ignore_index=True)
    else:
        final_df = retained_df.copy()

    # Save to parquet
    os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
    final_df.to_parquet(parquet_path, index=False)

    summary = {
        "added": len(added_df),
        "deleted": len(deleted_df),
        "retained": len(retained_df),
        "total": len(final_df)
    }
    return final_df, summary
