# pages/settings.py
import streamlit as st
import pandas as pd
import os
import datetime
from services.translations import t
from services.tmbd_service import get_tmdb_api_key

# Custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

st.title(f"🔧 {t('settings_title')}")
st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 2rem;'>{t('settings_subtitle')}</p>", unsafe_allow_html=True)

# 1. API Key Status & Secrets info
st.subheader("🔑 TMDb API Configuration")
current_key = get_tmdb_api_key()
if current_key:
    masked_key = current_key[:4] + "..." + current_key[-4:] if len(current_key) > 8 else "****"
    st.success(f"✅ TMDb API Key active: `{masked_key}` (automatically loaded from secrets / session)")
else:
    st.info("ℹ️ No TMDb API Key detected. You can paste your key in `.streamlit/secrets.toml` as `TMDB_API_KEY = \"...\"` or enter it below.")

with st.expander("Override / Enter Session API Key", expanded=not bool(current_key)):
    new_key = st.text_input("TMDb API Key (v3 auth):", value=st.session_state.get('tmdb_api_key', ''), type="password")
    if new_key:
        st.session_state['tmdb_api_key'] = new_key.strip()
        st.success("Session API Key updated!")

st.divider()

# 2. Database Health & Telemetry
st.subheader(f"📊 {t('db_health_title')}")

file_exists = os.path.exists(ENRICHED_FILE)
if file_exists:
    file_stat = os.stat(ENRICHED_FILE)
    file_size_kb = round(file_stat.st_size / 1024, 2)
    last_modified = datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    
    # Load dataset to get exact row count
    if 'enriched_data' in st.session_state:
        df = st.session_state['enriched_data']
    else:
        df = pd.read_parquet(ENRICHED_FILE)
        st.session_state['enriched_data'] = df
        
    row_count = len(df)
    rated_count = df['Rating'].notna().sum() if 'Rating' in df.columns else 0
    physical_count = int(df['physical_copy'].fillna(False).sum()) if 'physical_copy' in df.columns else 0
    physical_pct = (physical_count / row_count * 100) if row_count > 0 else 0.0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(t("db_records"), f"{row_count} films")
    with col2:
        st.metric("Personal Ratings", f"{rated_count} films")
    with col3:
        st.metric("💿 Physical Copies", f"{physical_count} discs", f"{physical_pct:.1f}%")
    with col4:
        st.metric(t("db_file_size"), f"{file_size_kb} KB")
    with col5:
        st.metric(t("db_last_modified"), f"{last_modified}")
        
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    # 3. Export & Backup
    st.subheader(f"💾 {t('db_backup_title')}")
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        with open(ENRICHED_FILE, "rb") as f:
            st.download_button(
                label=f"📦 {t('db_download_parquet')}",
                data=f.read(),
                file_name="letterboxd_enriched_backup.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )
            
    with col_dl2:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📄 {t('db_download_csv')}",
            data=csv_data,
            file_name="letterboxd_enriched_backup.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.info("No enriched database file found yet. Upload a CSV or add movies to create one.")

st.divider()

# 4. Danger Zone: Reset Movie History
st.subheader(f"🚨 {t('danger_zone_title')}")
st.markdown(
    f"""
    <div class="lb-card" style="border-left: 4px solid #E52E71; background: rgba(229, 46, 113, 0.08);">
        <p style="color: #EEF2F6; margin: 0; font-size: 0.95rem;">
            {t('danger_zone_desc')}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

confirm_reset = st.checkbox("I confirm that I want to delete my movie history and start from scratch.")

if confirm_reset:
    if st.button(f"🗑️ {t('reset_button')}", type="primary"):
        # Delete file if exists
        if os.path.exists(ENRICHED_FILE):
            try:
                os.remove(ENRICHED_FILE)
            except Exception as e:
                st.error(f"Error removing file: {e}")
                
        # Clear session state
        st.session_state.pop('enriched_data', None)
        st.session_state.pop('raw_data', None)
        st.session_state['data_loaded'] = False
        
        st.success(t("reset_success"))
        st.info("Redirecting to Home...")
        st.rerun()
