# app.py
import streamlit as st
import pandas as pd
import os
from services.translations import t, render_language_selector

# Initialize page config (note: must be first Streamlit command)
st.set_page_config(
    page_title="Letterboxd Data Enhancer",
    layout="wide",
    page_icon="🎬"
)

# Custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

# --- DATA AUTO-LOADER ---
DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

if 'data_loaded' not in st.session_state:
    if os.path.exists(ENRICHED_FILE):
        st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
        st.session_state['data_loaded'] = True
    else:
        st.session_state['data_loaded'] = False

# --- MULTI-PAGE NAVIGATION (RENAMED SIDEBAR PAGES) ---
overview_page = st.Page("pages/overview.py", title=t("nav_overview"), icon="📊", default=True)
personal_space_page = st.Page("pages/personal_space.py", title=t("nav_personal_space"), icon="🎬")
sagas_page = st.Page("pages/sagas.py", title=t("nav_sagas"), icon="🪐")
stats_page = st.Page("pages/more_statistics.py", title=t("nav_statistics"), icon="📈")
add_page = st.Page("pages/add_movie.py", title=t("nav_add_movie"), icon="➕")
data_page = st.Page("pages/data_manager.py", title=t("nav_data_manager"), icon="⚙️")
settings_page = st.Page("pages/settings.py", title=t("nav_settings"), icon="🔧")

lang = st.session_state.get('lang', 'en')
analytics_section = "Analytics & Diary" if lang == "en" else "Analitica & Diario"
manage_section = "Manage & Settings" if lang == "en" else "Gestione & Impostazioni"

pg = st.navigation({
    analytics_section: [overview_page, personal_space_page, sagas_page, stats_page],
    manage_section: [add_page, data_page, settings_page]
})

# Sidebar branding & language toggle
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;">
            <span style="font-size: 1.25rem; font-weight: 800; color: #FF8000;">Letterboxd</span>
            <span style="font-size: 1.25rem; font-weight: 300; color: #EEF2F6;">Enhancer</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    render_language_selector(sidebar=False)
    
    st.markdown(
        """
        <div style="font-size: 0.70rem; color: #8F9CA7; text-align: center; margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; line-height: 1.3;">
            Data & images from <a href="https://www.themoviedb.org/" target="_blank" style="color: #01b4e4; text-decoration: none;">TMDb</a>.<br>
            <span style="opacity: 0.8; font-style: italic;">This product uses the TMDB API but is not endorsed or certified by TMDB.</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# Execute the selected page
pg.run()