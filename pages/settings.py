# pages/settings.py
import streamlit as st
import pandas as pd
import os
import datetime
from services.translations import t, localized as tr
from services.tmbd_service import get_tmdb_api_key

# Custom CSS


DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

st.title(f"{t('settings_title')}")
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

st.page_link("pages/data_manager.py", label=tr("Import, inspect and export your data", "Importa, esplora ed esporta i dati"), icon="⚙️")
st.divider()

# 4. Danger Zone: Reset Movie History
st.subheader(f"🚨 {t('danger_zone_title')}")
st.markdown(
    f"""
    <div class="lb-card" style="border-left: 4px solid #E52E71; background: rgba(229, 46, 113, 0.08);">
        <p style="color: #F4F7FC; margin: 0; font-size: 0.95rem;">
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
        st.session_state.pop('sync_result', None)
        st.session_state['upload_generation'] = st.session_state.get('upload_generation', 0) + 1
        st.session_state['data_loaded'] = False
        
        st.success(t("reset_success"))
        st.info("Redirecting to Home...")
        st.rerun()
