# pages/data_manager.py
import streamlit as st
import pandas as pd
import os
import time
from services.tmbd_service import fetch_movie_metadata, get_tmdb_api_key
from services.translations import t

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")
os.makedirs(DATA_DIR, exist_ok=True)

st.title(f"⚙️ {t('nav_data_manager')}")
st.markdown("<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>Upload, inspect, and enrich your Letterboxd dataset with TMDb metadata.</p>", unsafe_allow_html=True)

# Upload new CSV option
with st.expander("📤 Upload Letterboxd CSV(s)", expanded=('raw_data' not in st.session_state)):
    st.markdown(
        """
        💡 **Tip:** You can upload **both** `watched.csv` (all movies you watched) and `ratings.csv` (movies you rated) at the same time!
        The app will automatically merge them so that **all watched movies** are kept, and personal ratings are attached.
        """
    )
    uploaded_files = st.file_uploader(
        "Select watched.csv, ratings.csv, and/or diary.csv",
        type=['csv'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        dfs = []
        for uf in uploaded_files:
            try:
                temp_df = pd.read_csv(uf)
                fname = uf.name.lower()
                dfs.append((fname, temp_df))
            except Exception as e:
                st.error(f"Error reading {uf.name}: {e}")
                
        if dfs:
            if len(dfs) == 1:
                combined_df = dfs[0][1]
            else:
                # Identify watched vs ratings
                watched_df = None
                ratings_df = None
                for fname, d in dfs:
                    if 'watched' in fname or 'Rating' not in d.columns:
                        watched_df = d
                    elif 'rating' in fname or 'Rating' in d.columns:
                        ratings_df = d
                        
                if watched_df is not None and ratings_df is not None:
                    # Merge on Name and Year or URI
                    join_keys = [c for c in ['Name', 'Year'] if c in watched_df.columns and c in ratings_df.columns]
                    if not join_keys:
                        join_keys = ['Letterboxd URI'] if 'Letterboxd URI' in watched_df.columns else ['Name']
                        
                    rating_sub = ratings_df[join_keys + ['Rating']].drop_duplicates(subset=join_keys)
                    combined_df = pd.merge(watched_df, rating_sub, on=join_keys, how='left')
                    st.success(f"Merged `{len(watched_df)}` watched films with `{len(ratings_df)}` ratings: **{len(combined_df)}** total films retained!")
                else:
                    # Fallback concat
                    combined_df = pd.concat([d for _, d in dfs], ignore_index=True).drop_duplicates(subset=['Name', 'Year'] if 'Year' in dfs[0][1].columns else ['Name'])
                    
            st.session_state['raw_data'] = combined_df
            st.session_state['data_loaded'] = True
            st.info(f"Loaded dataset with **{len(combined_df)}** records ready for enrichment or exploration.")

# Determine working df
raw_df = st.session_state.get('raw_data', None)

if raw_df is not None:
    st.markdown(f"**Loaded Raw Records:** `{len(raw_df)}` rows")
    st.dataframe(raw_df.head(5), use_container_width=True)
else:
    st.info("No raw CSV loaded. If you already have an enriched parquet file, you can manage or reload it below.")

# API Key input
api_key = get_tmdb_api_key()

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

# Batch Enrichment
if raw_df is not None:
    if st.button("🚀 Start TMDb Enrichment", type="primary", use_container_width=True):
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
            st.success(f"Enriched {len(enriched_df)} movies successfully saved to `{ENRICHED_FILE}`!")

st.divider()

# Existing file loader
if os.path.exists(ENRICHED_FILE):
    st.info(f"An enriched dataset file exists on disk: `{ENRICHED_FILE}`")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        if st.button("🔄 Reload Local File into Memory", use_container_width=True):
            st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
            st.session_state['data_loaded'] = True
            st.success("Enriched data reloaded into session state!")
    with col_l2:
        if st.button("📊 Go to Overview", use_container_width=True):
            st.switch_page("pages/overview.py")