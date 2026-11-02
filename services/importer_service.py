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
from __future__ import annotations

import io
import struct
import zipfile
import time
import os
import tempfile
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

    entries = zf.infolist()
    if len(entries) > MAX_ENTRIES_COUNT:
        raise ZipSecurityError(f"ZIP archive contains too many entries ({len(entries)} > {MAX_ENTRIES_COUNT}). Potential zip bomb.")

    total_uncompressed = 0
    extracted_csvs = {}
    candidates = []

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
            # Only account exports: lists/reviews may contain unrelated CSVs.
            if base_name in {'watched.csv', 'ratings.csv', 'diary.csv'}:
                if not any(part.startswith('.') or part == '__macosx' for part in lower_name.split('/')[:-1]):
                    candidates.append((lower_name, info))

    # Letterboxd may include nested exports (e.g. tv/diary.csv). Only the
    # top-level account CSVs belong to the film library. Allow a wrapper folder.
    if candidates:
        depth = min(name.count('/') for name, _ in candidates)
        roots = {name.rsplit('/', 1)[0] if '/' in name else ''
                 for name, _ in candidates if name.count('/') == depth}
        if len(roots) != 1:
            raise ZipSecurityError("Multiple account export folders found; upload one Letterboxd export at a time.")
        for name, info in candidates:
            if name.count('/') == depth:
                base_name = name.rsplit('/', 1)[-1]
                if base_name in extracted_csvs:
                    raise ZipSecurityError(f"Duplicate account file at the same path: {name}")
                extracted_csvs[base_name] = info

    # Decompress only after ALL size checks. Reading verifies each CSV's CRC.
    extracted_csvs = {name: zf.read(info) for name, info in extracted_csvs.items()}
    zf.close()

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
    return pd.read_csv(io.BytesIO(data_bytes), encoding='utf-8', encoding_errors='replace')


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
                if csv_name in raw_csv_dict:
                    raise ValueError(f"Duplicate export file: {csv_name}")
                raw_csv_dict[csv_name] = read_csv_safe(csv_bytes)
        elif fname.endswith('.csv'):
            if fname not in {'watched.csv', 'ratings.csv', 'diary.csv'}:
                raise ValueError("Use watched.csv, ratings.csv or diary.csv from Letterboxd.")
            if fname in raw_csv_dict:
                raise ValueError(f"Duplicate export file: {fname}")
            raw_csv_dict[fname] = read_csv_safe(content)

    if not raw_csv_dict:
        return pd.DataFrame(), {}

    # Merge watched, ratings, and diary CSVs
    combined_df = merge_letterboxd_dfs(raw_csv_dict)
    
    info = {
        "source": source_type,
        "sync_mode": combined_df.attrs.get('sync_mode', 'partial'),
        "files_found": list(raw_csv_dict.keys()),
        "total_records": len(combined_df),
        "has_ratings": int(combined_df['Rating'].notna().sum()) if 'Rating' in combined_df.columns else 0
    }
    return combined_df, info


def _find_match(row, records):
    """Prefer URI, then exact title/year; unknown years must be unambiguous."""
    uri = normalize_uri(row.get('Letterboxd URI'))
    if uri:
        matches = [i for i, other in enumerate(records)
                   if normalize_uri(other.get('Letterboxd URI')) == uri]
        if len(matches) == 1:
            return matches[0]
    name = normalize_title(row.get('Name', row.get('Title')))
    year = normalize_year(row.get('Year'))
    candidates = [i for i, other in enumerate(records)
                  if name and normalize_title(other.get('Name', other.get('Title'))) == name]
    exact = [i for i in candidates if normalize_year(records[i].get('Year')) == year]
    if len(exact) == 1:
        return exact[0]
    if not year and len(candidates) == 1:
        return candidates[0]
    return None


def merge_letterboxd_dfs(csv_dict: dict) -> pd.DataFrame:
    """watched defines membership; ratings is authoritative; diary uses latest date.

    Partial uploads update only supplied films/fields. A missing Rating column
    means 'no information', while an explicitly blank rating means 'unrated'.
    """
    sources = {}
    for filename, frame in csv_dict.items():
        if filename not in {'watched.csv', 'ratings.csv', 'diary.csv'}:
            continue
        frame = frame.copy()
        frame.columns = [str(c).strip() for c in frame.columns]
        if 'Name' not in frame and 'Title' in frame:
            frame['Name'] = frame['Title']
        if 'Name' not in frame or frame['Name'].isna().any():
            raise ValueError(f"{filename}: missing film names")
        if filename == 'ratings.csv' and 'Rating' not in frame:
            raise ValueError('ratings.csv: missing Rating column')
        if 'Rating' in frame:
            values = pd.to_numeric(frame['Rating'], errors='coerce')
            invalid = frame['Rating'].notna() & (
                values.isna() | ~values.between(0.5, 5) | (values * 2 % 1 != 0))
            if invalid.any():
                raise ValueError(f"{filename}: ratings must be between 0.5 and 5 in half-star steps")
            frame['Rating'] = values
        date_col = 'Watched Date' if 'Watched Date' in frame else 'Date'
        if date_col in frame:
            frame['_sort_date'] = pd.to_datetime(frame[date_col], errors='coerce')
            frame = frame.sort_values('_sort_date', kind='stable', na_position='first').drop(columns='_sort_date')
        records = []
        for row in frame.to_dict('records'):
            row['_rating_present'] = 'Rating' in frame
            if filename == 'diary.csv' and pd.notna(row.get('Watched Date')):
                row['Date'] = row['Watched Date']
            match = _find_match(row, records)
            if match is None:
                records.append(row)
            else:
                records[match] = row
        sources[filename] = records

    full = 'watched.csv' in sources
    base = [dict(row) for row in sources.get('watched.csv', [])]
    if not full:
        for filename in ('diary.csv', 'ratings.csv'):
            for row in sources.get(filename, []):
                if _find_match(row, base) is None:
                    base.append(dict(row))
    for row in base:
        diary = sources.get('diary.csv', [])
        match = _find_match(row, diary)
        if match is not None:
            entry = diary[match]
            if pd.notna(entry.get('Date')):
                row['Date'] = entry['Date']
            if entry['_rating_present']:
                row['Rating'] = entry.get('Rating', np.nan)
                row['_rating_present'] = True
        if 'ratings.csv' in sources:
            ratings = sources['ratings.csv']
            match = _find_match(row, ratings)
            # Full snapshot: absence from ratings.csv means rating removed.
            # With ratings.csv present, do not resurrect historical diary ratings.
            if match is not None or full or 'diary.csv' in sources:
                row['Rating'] = ratings[match].get('Rating', np.nan) if match is not None else np.nan
                row['_rating_present'] = True
        row.setdefault('Rating', np.nan)
    result = pd.DataFrame(base)
    result.attrs['sync_mode'] = 'full' if full else 'partial'
    return result.reset_index(drop=True)


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


def compute_dataset_diff(existing_df: pd.DataFrame, new_df: pd.DataFrame,
                         sync_mode=None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return additions, removals and updated retained films without mutating inputs.

    Deletions require watched.csv (or an explicitly selected full snapshot).
    The retained frame carries a rating_changes list for preview and reporting.
    """
    if new_df is None:
        new_df = pd.DataFrame()
    mode = sync_mode or new_df.attrs.get('sync_mode', 'partial')
    if mode not in {'full', 'partial'}:
        raise ValueError('Invalid synchronization mode')
    if existing_df is None:
        existing_df = pd.DataFrame()
    records = existing_df.to_dict('records')
    retained = [dict(row) for row in records]
    matched = set()
    additions, changes = [], []
    for incoming in new_df.to_dict('records'):
        idx = _find_match(incoming, records)
        if idx is None:
            additions.append({k: v for k, v in incoming.items() if not k.startswith('_')})
            continue
        matched.add(idx)
        row = retained[idx]
        if incoming.get('_rating_present', 'Rating' in incoming):
            old = pd.to_numeric(row.get('Rating'), errors='coerce')
            new = pd.to_numeric(incoming.get('Rating'), errors='coerce')
            if not ((pd.isna(old) and pd.isna(new)) or old == new):
                changes.append({'Name': row.get('Name', row.get('Title')), 'Year': row.get('Year'),
                                'Previous rating': old, 'New rating': new})
            row['Rating'] = new
        for col in ('Date', 'Watched Date', 'Letterboxd URI'):
            if pd.notna(incoming.get(col)) and str(incoming[col]).strip():
                row[col] = str(incoming[col])
    deleted = [row for i, row in enumerate(records) if mode == 'full' and i not in matched]
    kept = [row for i, row in enumerate(retained) if mode == 'partial' or i in matched]
    retained_df = pd.DataFrame(kept, columns=sorted(set(existing_df.columns) | {k for r in kept for k in r}))
    retained_df.attrs['rating_changes'] = changes
    return (pd.DataFrame(additions, columns=[c for c in new_df.columns if not c.startswith('_')]),
            pd.DataFrame(deleted, columns=existing_df.columns), retained_df)


def save_dataset(df, parquet_path):
    """Replace the database only after the complete new parquet was written."""
    directory = os.path.dirname(os.path.abspath(parquet_path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix='.parquet', dir=directory)
    os.close(fd)
    try:
        clean = df.copy()
        clean.attrs = {}
        clean.to_parquet(temporary, index=False)
        os.replace(temporary, parquet_path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def apply_dataset_update(existing_df: pd.DataFrame, new_raw_df: pd.DataFrame, api_key: str,
                         parquet_path: str = "data/letterboxd_enriched.parquet",
                         progress_callback=None, status_callback=None, sync_mode=None) -> tuple[pd.DataFrame, dict]:
    """
    Executes the watched list synchronization:
    1. Identifies added, deleted, and retained films.
    2. Fetches TMDb metadata only for the newly added films.
    3. Combines retained films with newly enriched films.
    4. Writes the updated dataset to the parquet file.
    5. Returns (updated_enriched_df, diff_summary).
    """
    added_df, deleted_df, retained_df = compute_dataset_diff(existing_df, new_raw_df, sync_mode)

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
            record["tmdb_id"] = meta.get("tmdb_id")
            record["collection_id"] = meta.get("collection_id")
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
    final_df.attrs = {}
    save_dataset(final_df, parquet_path)

    summary = {
        "ratings_updated": len(retained_df.attrs.get("rating_changes", [])),
        "added": len(added_df),
        "deleted": len(deleted_df),
        "retained": len(retained_df),
        "total": len(final_df)
    }
    return final_df, summary
