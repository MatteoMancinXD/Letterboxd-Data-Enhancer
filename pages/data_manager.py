# pages/data_manager.py
import streamlit as st
import pandas as pd
import os
import time
import datetime
from services.tmbd_service import fetch_movie_metadata, get_tmdb_api_key
from services.translations import t
from services.importer_service import (
    load_uploaded_files,
    compute_dataset_diff,
    apply_dataset_update,
    ZipSecurityError
)

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")
os.makedirs(DATA_DIR, exist_ok=True)

# Load existing enriched data into session state if on disk
if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

has_enriched_data = ('enriched_data' in st.session_state and not st.session_state['enriched_data'].empty)

st.title(f"⚙️ {t('nav_data_manager')}")
st.markdown("<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>Upload, synchronize, inspect, and enrich your Letterboxd dataset with TMDb metadata.</p>", unsafe_allow_html=True)

# --- SECTION 1: UPLOAD LETTERBOXD EXPORT (ZIP OR CSV) ---
upload_label = "🔄 Update Watched List (Upload New Letterboxd ZIP or CSV)" if has_enriched_data else "📤 Upload Letterboxd ZIP or CSV(s)"
with st.expander(upload_label, expanded=True):
    st.markdown(
        """
        💡 **Direct ZIP Support:** You can drag & drop the **`.zip` file downloaded directly from Letterboxd** (e.g. `letterboxd-username-...zip`)!
        The application securely verifies the archive (checking against zip bombs, zip slack, and path traversals) and automatically merges `watched.csv`, `ratings.csv`, and `diary.csv`.
        
        *You can also still upload individual `.csv` files.*
        """
    )
    
    uploaded_files = st.file_uploader(
        t("importer_upload_label"),
        type=['zip', 'csv'],
        accept_multiple_files=True,
        help=t("importer_upload_help")
    )
    
    if uploaded_files:
        try:
            parsed_df, parse_info = load_uploaded_files(uploaded_files)
            if not parsed_df.empty:
                st.session_state['new_imported_data'] = parsed_df
                st.session_state['parse_info'] = parse_info
                
                detected_files_str = ", ".join([f"`{f}`" for f in parse_info.get("files_found", [])])
                st.success(
                    f"✅ **{parse_info.get('source', 'files').upper()} Parsed Successfully!** "
                    f"Found {detected_files_str} containing **{len(parsed_df)}** unique films "
                    f"({parse_info.get('has_ratings', 0)} with personal ratings)."
                )
            else:
                st.warning("No valid film entries could be parsed from the uploaded file(s).")
        except ZipSecurityError as zse:
            st.error(f"🛡️ **{t('importer_zip_security_error')}**: {zse}")
        except Exception as e:
            st.error(f"Error parsing upload: {e}")

# Working dataframes
existing_df = st.session_state.get('enriched_data', None)
new_imported_df = st.session_state.get('new_imported_data', None)

# If no new import yet but raw_data was stored from landing page
if new_imported_df is None and 'raw_data' in st.session_state:
    new_imported_df = st.session_state['raw_data']

# TMDb API Key state
api_key = get_tmdb_api_key()

st.divider()

# --- SCENARIO A: ENRICHED DATABASE EXISTS -> SYNCHRONIZATION / UPDATE FLOW ---
if existing_df is not None and not existing_df.empty:
    if new_imported_df is not None and not new_imported_df.empty:
        st.subheader(f"🔄 {t('sync_section_title')}")
        st.markdown(f"<p style='color: #8C98A4; margin-bottom: 1.25rem;'>{t('sync_section_subtitle')}</p>", unsafe_allow_html=True)
        
        # Calculate granular diff
        added_df, deleted_df, retained_df = compute_dataset_diff(existing_df, new_imported_df)
        
        # 3 KPI Cards
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #00E054;">
                    <div class="lb-stat-number" style="color: #00E054;">+{len(added_df)}</div>
                    <div class="lb-stat-label">{t('sync_kpi_added')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_s2:
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #FF4444;">
                    <div class="lb-stat-number" style="color: #FF4444;">-{len(deleted_df)}</div>
                    <div class="lb-stat-label">{t('sync_kpi_deleted')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_s3:
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #40BCF4;">
                    <div class="lb-stat-number" style="color: #40BCF4;">{len(retained_df)}</div>
                    <div class="lb-stat-label">{t('sync_kpi_retained')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # Detailed Expanders for Added / Deleted films
        if len(added_df) > 0:
            with st.expander(f"➕ {t('sync_list_added_title')} ({len(added_df)})", expanded=True):
                preview_cols = [c for c in ['Name', 'Year', 'Rating', 'Date'] if c in added_df.columns]
                st.dataframe(added_df[preview_cols], use_container_width=True)
                
        if len(deleted_df) > 0:
            with st.expander(f"➖ {t('sync_list_deleted_title')} ({len(deleted_df)})", expanded=False):
                del_cols = [c for c in ['Name', 'Year', 'Rating', 'Date'] if c in deleted_df.columns]
                st.dataframe(deleted_df[del_cols], use_container_width=True)
                
        if len(added_df) == 0 and len(deleted_df) == 0:
            st.info(f"✨ {t('sync_up_to_date')}")

        # API Key management for added movies
        if len(added_df) > 0:
            if api_key:
                masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "****"
                st.markdown(
                    f"""
                    <div style="background: rgba(0, 224, 84, 0.08); border: 1px solid rgba(0, 224, 84, 0.25); border-radius: 8px; padding: 6px 12px; margin-bottom: 12px;">
                        <span style="color: #00E054; font-size: 0.85rem; font-weight: 600;">🔑 TMDb API Key Active: <code>{masked}</code> (ready to enrich new films)</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                with st.expander("🔑 TMDb API Key Required for New Films", expanded=True):
                    new_key = st.text_input(
                        "TMDb API Key (v3 auth):",
                        value=st.session_state.get('tmdb_api_key', ''),
                        type="password",
                        help="Required to enrich newly added movies via TMDb."
                    )
                    if new_key:
                        st.session_state['tmdb_api_key'] = new_key.strip()
                        api_key = new_key.strip()
                        
        # Synchronize Button
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button(f"🚀 {t('sync_btn_start')}", type="primary", use_container_width=True):
                if len(added_df) > 0 and not api_key:
                    st.error("Please enter a valid TMDb API key to fetch information for new films.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    final_updated_df, summary = apply_dataset_update(
                        existing_df=existing_df,
                        new_raw_df=new_imported_df,
                        api_key=api_key,
                        parquet_path=ENRICHED_FILE,
                        progress_callback=lambda p: progress_bar.progress(p),
                        status_callback=lambda s: status_text.text(s)
                    )
                    
                    st.session_state['enriched_data'] = final_updated_df
                    st.session_state['data_loaded'] = True
                    st.session_state.pop('new_imported_data', None)
                    st.session_state.pop('raw_data', None)
                    
                    status_text.text("✅ Synchronization complete!")
                    st.success(t("sync_success_msg").format(
                        added=summary['added'],
                        deleted=summary['deleted'],
                        retained=summary['retained']
                    ))
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        with col_btn2:
            if st.button("❌ Cancel / Clear Upload", use_container_width=True):
                st.session_state.pop('new_imported_data', None)
                st.session_state.pop('raw_data', None)
                st.rerun()

        # Alternative: Full Fresh Re-Enrichment Option
        with st.expander(f"⚠️ {t('sync_full_import_expander')}", expanded=False):
            st.warning("Starting from scratch will overwrite your entire current database and re-download all movies from TMDb.")
            if st.button("Re-Enrich ALL Movies from Scratch", type="secondary"):
                if not api_key:
                    st.error("Please provide a TMDb API key first.")
                else:
                    st.session_state['raw_data'] = new_imported_df
                    st.session_state['force_full_enrich'] = True
                    st.rerun()

    else:
        # No new upload pending: Show active library status
        st.subheader("📚 Active Collection Status")
        st.info(f"Your enriched library currently contains **{len(existing_df)}** films. Upload a new Letterboxd export (`.zip` or `.csv`) above whenever you want to synchronize changes!")
        
        preview_cols = [c for c in ['Name', 'Year', 'Rating', 'Date', 'directors', 'physical_copy'] if c in existing_df.columns]
        st.dataframe(existing_df[preview_cols].head(8), use_container_width=True)

# --- SCENARIO B: NO ENRICHED DATABASE YET (INITIAL ENRICHMENT) ---
else:
    raw_df = new_imported_df or st.session_state.get('raw_data', None)
    if raw_df is not None and not raw_df.empty:
        st.subheader("📥 Initial Dataset Ready for Enrichment")
        st.markdown(f"**Loaded Films from Export:** `{len(raw_df)}` rows")
        preview_cols = [c for c in ['Name', 'Year', 'Rating', 'Date'] if c in raw_df.columns]
        st.dataframe(raw_df[preview_cols].head(5), use_container_width=True)

        # TMDb API Key input
        if api_key:
            masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "****"
            st.markdown(
                f"""
                <div style="background: rgba(0, 224, 84, 0.08); border: 1px solid rgba(0, 224, 84, 0.25); border-radius: 8px; padding: 6px 12px; margin-bottom: 12px;">
                    <span style="color: #00E054; font-size: 0.85rem; font-weight: 600;">🔑 TMDb API Key Active: <code>{masked}</code></span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            with st.expander("🔑 TMDb API Key Required", expanded=True):
                new_key = st.text_input(
                    "TMDb API Key (v3 auth):",
                    value=st.session_state.get('tmdb_api_key', ''),
                    type="password",
                    help="Required to enrich movies via TMDb API. You can also paste it in .streamlit/secrets.toml"
                )
                if new_key:
                    st.session_state['tmdb_api_key'] = new_key.strip()
                    api_key = new_key.strip()

        # Batch Enrichment Button
        if st.button("🚀 Start Initial TMDb Enrichment", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please enter a valid TMDb API key before starting enrichment.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                title_col = "Name" if "Name" in raw_df.columns else ("Title" if "Title" in raw_df.columns else None)
                year_col = "Year" if "Year" in raw_df.columns else None

                if not title_col:
                    st.error(f"Title column not found. Available columns: {list(raw_df.columns)}")
                    st.stop()

                enriched_records = []
                total = len(raw_df)

                for idx, row in raw_df.iterrows():
                    title = row[title_col]
                    year = row[year_col] if year_col else None

                    status_text.text(f"Fetching ({idx + 1}/{total}): {title}...")

                    meta = fetch_movie_metadata(title, year, api_key)

                    record = row.to_dict()
                    record["physical_copy"] = bool(row.get("physical_copy", False))
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

                    enriched_records.append(record)
                    progress_bar.progress((idx + 1) / total)
                    time.sleep(0.04)

                status_text.text("Enrichment complete. Saving database...")
                enriched_df = pd.DataFrame(enriched_records)
                enriched_df.to_parquet(ENRICHED_FILE, index=False)
                st.session_state['enriched_data'] = enriched_df
                st.session_state['data_loaded'] = True
                st.session_state.pop('new_imported_data', None)
                st.session_state.pop('raw_data', None)
                st.success(f"Enriched {len(enriched_df)} movies successfully saved to `{ENRICHED_FILE}`!")
                st.rerun()
    else:
        st.info("No Letterboxd export loaded yet. Upload your Letterboxd `.zip` export or `.csv` files above to get started!")

# --- FOOTER: LOCAL FILE RELOADER & NAVIGATION ---
st.divider()
if os.path.exists(ENRICHED_FILE):
    file_stat = os.stat(ENRICHED_FILE)
    file_size_kb = round(file_stat.st_size / 1024, 2)
    last_mod = datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"📁 Local database file: `{ENRICHED_FILE}` ({file_size_kb} KB, Last Modified: {last_mod})")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        if st.button("🔄 Reload Local File into Memory", use_container_width=True):
            st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
            st.session_state['data_loaded'] = True
            st.success("Enriched data reloaded into session state!")
            st.rerun()
    with col_l2:
        if st.button("📊 Go to Overview", use_container_width=True):
            st.switch_page("pages/overview.py")