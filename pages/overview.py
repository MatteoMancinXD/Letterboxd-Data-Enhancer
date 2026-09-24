# pages/overview.py
import streamlit as st
import pandas as pd
import os
from services.translations import t

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

# Data paths
DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

# Check data status
if 'enriched_data' in st.session_state and not st.session_state['enriched_data'].empty:
    df = st.session_state['enriched_data']
    data_type = t("dataset_status_enriched")
elif 'raw_data' in st.session_state and not st.session_state['raw_data'].empty:
    df = st.session_state['raw_data']
    data_type = t("dataset_status_raw")
else:
    # Landing / Empty state
    st.markdown('<p class="main-title">Letterboxd Enhancer</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">{t("landing_subtitle")}</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_files = st.file_uploader(t("landing_upload_label"), type=['csv'], accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            dfs = []
            for uf in uploaded_files:
                try:
                    temp_df = pd.read_csv(uf)
                    dfs.append((uf.name.lower(), temp_df))
                except Exception:
                    pass
            if dfs:
                if len(dfs) == 1:
                    df_up = dfs[0][1]
                else:
                    w_df = next((d for n, d in dfs if 'watched' in n or 'Rating' not in d.columns), None)
                    r_df = next((d for n, d in dfs if 'rating' in n or 'Rating' in d.columns), None)
                    if w_df is not None and r_df is not None:
                        keys = [c for c in ['Name', 'Year'] if c in w_df.columns and c in r_df.columns] or ['Name']
                        r_sub = r_df[keys + ['Rating']].drop_duplicates(subset=keys)
                        df_up = pd.merge(w_df, r_sub, on=keys, how='left')
                    else:
                        df_up = pd.concat([d for _, d in dfs], ignore_index=True)
                st.session_state['raw_data'] = df_up
                st.session_state['data_loaded'] = True
                st.success(t("landing_uploaded_success"))
                st.switch_page("pages/data_manager.py")
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        if st.button(f"➕ {t('nav_add_movie')} Manually", use_container_width=True):
            st.switch_page("pages/add_movie.py")
            
    st.stop()

# Header
st.title(f"📊 {t('overview_title')}")
st.markdown(
    f"<p style='color: #9AB; font-size: 1.05rem; margin-bottom: 1.5rem;'>"
    f"{t('overview_subtitle')} — "
    f"<span style='color: #00E054; font-weight: 600;'>{data_type}</span>"
    f"</p>",
    unsafe_allow_html=True
)

# Calcolo metriche per KPI Cards
total_films = len(df)

# Anno più frequente
year_col = "Year" if "Year" in df.columns else None
if year_col and not df[year_col].isnull().all():
    mode_year = int(df[year_col].mode()[0])
else:
    mode_year = "N/A"

# Ratings calculation: prioritize personal Rating, then fallback to TMDb
has_user_rating = 'Rating' in df.columns and df['Rating'].notna().any()
if has_user_rating:
    avg_score = round(float(df['Rating'].dropna().mean()), 2)
    rating_label = f"⭐ {t('kpi_avg_user_rating')}"
    rating_display = f"{avg_score} / 5.0 ★"
elif 'tmdb_rating' in df.columns and df['tmdb_rating'].notna().any():
    avg_score = round(float(df['tmdb_rating'].dropna().mean()), 2)
    rating_label = f"⭐ {t('kpi_avg_tmdb_rating')}"
    rating_display = f"{avg_score} / 10"
else:
    rating_label = "⭐ Rating"
    rating_display = "N/A"

# Physical collection calculation
physical_count = int(df['physical_copy'].fillna(False).sum()) if 'physical_copy' in df.columns else 0
physical_pct = (physical_count / total_films * 100) if total_films > 0 else 0.0

# Top Director
top_director = "N/A"
if 'directors' in df.columns:
    try:
        all_dirs = df['directors'].explode().dropna()
        if not all_dirs.empty:
            top_director = all_dirs.value_counts().index[0]
    except Exception:
        pass

# Top Genre
top_genre = "N/A"
if 'genres' in df.columns:
    try:
        all_genres = df['genres'].explode().dropna()
        if not all_genres.empty:
            top_genre = all_genres.value_counts().index[0]
    except Exception:
        pass

# Layout a 5 colonne per KPI
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label=t("kpi_total_films"), value=total_films)

with col2:
    st.metric(label=t("kpi_most_frequent_year"), value=mode_year)

with col3:
    st.metric(label=rating_label, value=rating_display)

with col4:
    st.metric(label=t("kpi_top_director"), value=top_director)

with col5:
    st.metric(label=f"💿 {t('kpi_physical_collection')}", value=f"{physical_count} films", delta=f"{physical_pct:.1f}%")

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

# Banners Callout per "Sagas & Universes" and "Deep Statistics"
col_ban_sagas, col_ban_stats = st.columns(2)

with col_ban_sagas:
    sagas_ban_html = (
        f"<div class='lb-card' style='border-left: 4px solid #00E054; height: 100%;'>"
        f"<h4 style='margin: 0 0 6px 0; color: #00E054;'>🪐 {t('cta_sagas_title')}</h4>"
        f"<p style='margin: 0 0 12px 0; color: #9AB; font-size: 0.92rem;'>{t('cta_sagas_desc')}</p>"
        f"</div>"
    )
    st.markdown(sagas_ban_html, unsafe_allow_html=True)
    if st.button(f"🪐 {t('cta_sagas_button')}", use_container_width=True, type="primary", key="btn_ov_sagas"):
        st.switch_page("pages/sagas.py")

with col_ban_stats:
    stats_ban_html = (
        f"<div class='lb-card' style='border-left: 4px solid #FF8000; height: 100%;'>"
        f"<h4 style='margin: 0 0 6px 0; color: #FF8000;'>🔥 {t('cta_stats_title')}</h4>"
        f"<p style='margin: 0 0 12px 0; color: #9AB; font-size: 0.92rem;'>{t('cta_stats_desc')}</p>"
        f"</div>"
    )
    st.markdown(stats_ban_html, unsafe_allow_html=True)
    if st.button(f"📈 {t('cta_stats_button')}", use_container_width=True, key="btn_ov_stats"):
        st.switch_page("pages/more_statistics.py")

st.divider()

# Esplorazione Tabella
st.subheader(f"📋 {t('explore_catalog_title')}")

cols_to_show = [c for c in ['Name', 'Title', 'Year', 'Rating', 'physical_copy', 'tmdb_rating', 'directors', 'genres'] if c in df.columns]
if not cols_to_show:
    cols_to_show = df.columns

st.dataframe(df[cols_to_show], use_container_width=True, height=450)