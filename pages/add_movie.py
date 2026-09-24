# pages/add_movie.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import datetime
from services.tmbd_service import search_movies, fetch_movie_details_by_id, get_tmdb_api_key
from services.translations import t

# Custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

# Dataset paths
DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")
os.makedirs(DATA_DIR, exist_ok=True)

# Auto-load existing enriched data
if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

col_am_title, col_am_link = st.columns([3, 1])
with col_am_title:
    st.title(f"➕ {t('add_movie_title')}")
    st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>{t('add_movie_subtitle')}</p>", unsafe_allow_html=True)
with col_am_link:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.button("🎬 Personal Movie Space", use_container_width=True):
        st.switch_page("pages/personal_space.py")

# TMDb API Key management (Check secrets.toml, env, or session)
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
        key_input = st.text_input(
            "TMDb API Key (v3 auth):",
            value=st.session_state.get('tmdb_api_key', ''),
            type="password",
            help="Required to query TMDb API directly. You can also paste it in .streamlit/secrets.toml"
        )
        if key_input:
            st.session_state['tmdb_api_key'] = key_input.strip()
            api_key = key_input.strip()
            st.success("API Key saved for current session!")

# Search inputs
col_s1, col_s2, col_s3 = st.columns([3, 1, 1])

with col_s1:
    search_query = st.text_input(t("add_search_label"), placeholder=t("add_search_placeholder"))

with col_s2:
    search_year = st.text_input(t("add_year_label"), placeholder="e.g. 2023")

with col_s3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    search_clicked = st.button(f"🔍 {t('add_search_button')}", use_container_width=True, type="primary")

# Maintain search results in session state
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []
if 'selected_movie_details' not in st.session_state:
    st.session_state['selected_movie_details'] = None

if search_clicked:
    current_key = get_tmdb_api_key()
    if not current_key:
        st.error("Please enter a valid TMDb API Key or add it to .streamlit/secrets.toml before searching.")
    elif not search_query.strip():
        st.warning("Please enter a movie title to search.")
    else:
        with st.spinner(t("add_searching")):
            results = search_movies(search_query.strip(), api_key=current_key, year=search_year.strip() if search_year else None)
            st.session_state['search_results'] = results
            st.session_state['selected_movie_details'] = None
            if not results:
                st.info(t("add_no_results"))

# Display search results
results = st.session_state.get('search_results', [])
if results:
    st.markdown(f"#### 🎬 {t('add_select_prompt')}")
    
    cols = st.columns(min(len(results), 4))
    for idx, movie in enumerate(results[:8]):
        col = cols[idx % len(cols)]
        with col:
            st.markdown(
                f"""
                <div class="lb-card" style="height: 380px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <img src="{movie['poster_url'] or 'https://via.placeholder.com/200x300?text=No+Poster'}" 
                             style="width: 100%; height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 8px;">
                        <h4 style="margin: 0; font-size: 1rem; color: #EEF2F6; line-height: 1.2;">{movie['title']}</h4>
                        <span style="color: #FF8000; font-size: 0.85rem; font-weight: bold;">📅 {movie['year']}</span> &nbsp;
                        <span style="color: #00E054; font-size: 0.85rem;">⭐ {movie['tmdb_rating'] or 'N/A'}</span>
                        <p style="color: #9AB; font-size: 0.78rem; margin-top: 6px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                            {movie['overview']}
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(f"👉 Select: {movie['title'][:18]}...", key=f"btn_select_{movie['id']}", use_container_width=True):
                with st.spinner("Fetching full details..."):
                    details = fetch_movie_details_by_id(movie['id'], get_tmdb_api_key())
                    st.session_state['selected_movie_details'] = details

st.divider()

# Rating and saving form for selected movie
selected = st.session_state.get('selected_movie_details')
if selected:
    st.subheader(f"✨ Configure Diary Entry: {selected['title']} ({selected.get('year') or 'N/A'})")
    
    col_d1, col_d2 = st.columns([1, 2])
    
    with col_d1:
        if selected.get('poster_url'):
            st.image(selected['poster_url'], use_container_width=True)
        st.markdown(f"**Directors:** {', '.join(selected.get('directors', [])) or 'N/A'}")
        st.markdown(f"**Cast:** {', '.join(selected.get('actors', [])) or 'N/A'}")
        st.markdown(f"**Genres:** {', '.join(selected.get('genres', [])) or 'N/A'}")
        if selected.get('runtime'):
            st.markdown(f"**Runtime:** {selected['runtime']} min")
            
    with col_d2:
        st.markdown(f"<p style='color: #9AB;'>{selected.get('overview', '')}</p>", unsafe_allow_html=True)
        
        rating_options = ["No Rating", "0.5 ★", "1.0 ★", "1.5 ★", "2.0 ★", "2.5 ★", "3.0 ★", "3.5 ★", "4.0 ★", "4.5 ★", "5.0 ★"]
        chosen_rating_str = st.select_slider(
            t("add_user_rating_label"),
            options=rating_options,
            value="4.0 ★",
            help=t("add_user_rating_help")
        )
        
        watch_date = st.date_input(
            t("add_watch_date_label"),
            value=datetime.date.today()
        )
        
        own_physical = st.checkbox(
            f"💿 {t('add_physical_checkbox')}",
            value=False,
            help="Check if you own a physical disc copy (4K UHD, Blu-ray, DVD)"
        )
        
        save_button = st.button(f"💾 {t('add_save_button')}", type="primary", use_container_width=True)
        
        if save_button:
            if chosen_rating_str == "No Rating":
                user_rating = np.nan
            else:
                user_rating = float(chosen_rating_str.replace(" ★", ""))
                
            new_record = {
                "Date": watch_date.strftime("%Y-%m-%d"),
                "Name": selected['title'],
                "Year": selected.get('year') or 0,
                "Letterboxd URI": f"https://boxd.it/tmdb-{selected['tmdb_id']}",
                "genres": selected.get('genres', []),
                "directors": selected.get('directors', []),
                "actors": selected.get('actors', []),
                "tmdb_rating": selected.get('tmdb_rating'),
                "Rating": user_rating,
                "physical_copy": bool(own_physical),
                "runtime": selected.get('runtime'),
                "poster_path": selected.get('poster_path'),
                "overview": selected.get('overview', ""),
                "production_countries": selected.get('production_countries', [])
            }
            
            if 'enriched_data' in st.session_state:
                current_df = st.session_state['enriched_data'].copy()
            elif os.path.exists(ENRICHED_FILE):
                current_df = pd.read_parquet(ENRICHED_FILE)
            else:
                current_df = pd.DataFrame()
                
            new_df_row = pd.DataFrame([new_record])
            updated_df = pd.concat([current_df, new_df_row], ignore_index=True)
            
            updated_df.to_parquet(ENRICHED_FILE, index=False)
            st.session_state['enriched_data'] = updated_df
            st.session_state['data_loaded'] = True
            
            st.success(f"🎉 {t('add_success')}")
            st.balloons()
