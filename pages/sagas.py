# pages/sagas.py
import streamlit as st
import pandas as pd
import numpy as np
import os
from services.translations import t
from services.sagas_service import compute_sagas_progress, scan_and_cache_tmdb_collections

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

# --- DATA AUTO-LOADER ---
DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

if 'enriched_data' not in st.session_state or st.session_state['enriched_data'].empty:
    st.warning(t("no_data_warning"))
    st.stop()

df = st.session_state['enriched_data'].copy()

# Ensure required columns
if 'Rating' not in df.columns:
    df['Rating'] = np.nan
if 'physical_copy' not in df.columns:
    df['physical_copy'] = False

# Compute sagas data
with st.spinner("Analyzing film sagas and cinematic universes..."):
    sagas_data = compute_sagas_progress(df, include_tmdb_collections=True)

started_sagas = sagas_data["started_sagas"]
completed_sagas = sagas_data["completed_sagas"]
unstarted_sagas = sagas_data["unstarted_sagas"]
kpis = sagas_data["kpis"]

# --- HEADER ---
st.title(f"🪐 {t('sagas_title')}")
st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>{t('sagas_subtitle')}</p>", unsafe_allow_html=True)

# --- KPI METRICS ROW ---
col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
with col_k1:
    st.metric(t("sagas_kpi_tracked"), f"{kpis['total_sagas_tracked']} sagas")
with col_k2:
    st.metric(t("sagas_kpi_started"), f"{kpis['started_count']} in progress")
with col_k3:
    st.metric(t("sagas_kpi_completed"), f"{kpis['completed_count']} completed", "100% 🏆")
with col_k4:
    st.metric(t("sagas_kpi_franchise_films"), f"{kpis['total_franchise_films_watched']} films")
with col_k5:
    total_physical_in_sagas = sum(s['physical_count'] for s in started_sagas + completed_sagas)
    st.metric("💿 Physical in Sagas", f"{total_physical_in_sagas} discs")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- FILTERS & SEARCH ROW ---
col_search, col_type, col_sort = st.columns([2, 1.5, 1.5])

with col_search:
    search_q = st.text_input("🔍 " + t("sagas_search_placeholder"), placeholder="Filter by saga name (e.g. Star Wars, Marvel, Batman)...")

with col_type:
    type_filter = st.selectbox(
        t("sagas_filter_type"),
        options=["All", "Universes", "Sagas"],
        format_func=lambda x: {
            "All": t("sagas_filter_all"),
            "Universes": t("sagas_filter_universes"),
            "Sagas": t("sagas_filter_sagas")
        }.get(x, x)
    )

with col_sort:
    sort_option = st.selectbox(
        t("sagas_sort_label"),
        options=["Progress % (Highest)", "Progress % (Lowest)", "Films Remaining", "Total Films", "Name (A-Z)", "Your Rating (Highest)"]
    )

def filter_and_sort_sagas(sagas_list):
    res = list(sagas_list)
    # Search filter
    if search_q.strip():
        q = search_q.strip().lower()
        res = [s for s in res if q in s['name'].lower() or any(q in f['title'].lower() for f in s['all_films'])]
        
    # Type filter
    if type_filter == "Universes":
        res = [s for s in res if s['category'] == 'universe']
    elif type_filter == "Sagas":
        res = [s for s in res if s['category'] == 'saga']
        
    # Sort
    if sort_option == "Progress % (Highest)":
        res.sort(key=lambda s: (-s['progress_pct'], -s['watched_count']))
    elif sort_option == "Progress % (Lowest)":
        res.sort(key=lambda s: (s['progress_pct'], s['watched_count']))
    elif sort_option == "Films Remaining":
        res.sort(key=lambda s: (s['remaining_count'], -s['progress_pct']))
    elif sort_option == "Total Films":
        res.sort(key=lambda s: (-s['total_films'], s['name']))
    elif sort_option == "Name (A-Z)":
        res.sort(key=lambda s: s['name'].lower())
    elif sort_option == "Your Rating (Highest)":
        res.sort(key=lambda s: (-(s['avg_user_rating'] or 0), -s['progress_pct']))
        
    return res

filtered_started = filter_and_sort_sagas(started_sagas)
filtered_completed = filter_and_sort_sagas(completed_sagas)
all_combined = filter_and_sort_sagas(started_sagas + completed_sagas + unstarted_sagas)

# --- HELPER: RENDER SAGA CARD ---
def render_saga_card(saga, is_completed_view=False):
    pct = saga['progress_pct']
    watched_c = saga['watched_count']
    total_c = saga['total_films']
    avg_r = saga['avg_user_rating']
    phys_c = saga['physical_count']
    is_complete = saga['is_complete']
    
    # Progress color & styling
    bar_color = "#00E054" if is_complete else "#FF8000"
    
    with st.container(border=True):
        col_hdr_left, col_hdr_right = st.columns([3, 1])
        
        with col_hdr_left:
            tag_color = saga.get('badge_color', '#FF8000')
            tag_name = saga.get('tag', 'Saga')
            header_html = (
                f"<span style='font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.6px; color: {tag_color}; font-weight: 700;'>"
                f"{tag_name}</span>"
                f"<h3 style='margin: 4px 0 4px 0; color: #EEF2F6; font-size: 1.35rem; font-weight: 700;'>{saga['name']}</h3>"
            )
            if saga.get('description'):
                header_html += f"<p style='color: #9AB; font-size: 0.88rem; margin: 0 0 4px 0;'>{saga['description']}</p>"
            st.markdown(header_html, unsafe_allow_html=True)
            
        with col_hdr_right:
            if is_complete:
                badge_html = f"<div style='text-align: right; padding-top: 4px;'><span class='saga-badge saga-badge-complete'>🏆 {t('sagas_complete_badge')}</span></div>"
            else:
                badge_html = f"<div style='text-align: right; padding-top: 4px;'><span class='saga-badge saga-badge-progress'>🚀 {pct:.1f}% {t('sagas_progress')}</span></div>"
            st.markdown(badge_html, unsafe_allow_html=True)

        # Native Streamlit progress bar (safe from any Markdown escaping bugs)
        progress_val = min(1.0, max(0.0, float(pct) / 100.0))
        st.progress(progress_val)
        
        # Bottom statistics bar
        col_stat_left, col_stat_right = st.columns([2, 1])
        with col_stat_left:
            stat_left_html = (
                f"<span style='color: #EEF2F6; font-size: 0.95rem; font-weight: 600;'>"
                f"🎬 <b>{watched_c}</b> of <b>{total_c}</b> films watched "
                f"<span style='color: {bar_color}; font-weight: 700;'>({pct:.1f}%)</span></span>"
            )
            st.markdown(stat_left_html, unsafe_allow_html=True)
            
        with col_stat_right:
            rating_text = f"⭐ <b>{avg_r:.2f} ★</b>" if avg_r is not None else "<span style='color: #9AB;'>Unrated</span>"
            phys_text = f"<span class='physical-badge'>💿 {phys_c}/{watched_c} Owned</span>" if phys_c > 0 else "<span style='color: #8C98A4; font-size: 0.82rem;'>💿 0 Owned</span>"
            stat_right_html = (
                f"<div style='text-align: right; display: flex; justify-content: flex-end; align-items: center; gap: 10px; font-size: 0.88rem;'>"
                f"{rating_text} &nbsp; {phys_text}</div>"
            )
            st.markdown(stat_right_html, unsafe_allow_html=True)
        
        # Interactive film list accordion
        expander_label = f"📋 View Film Details & Progress ({watched_c}/{total_c})"
        with st.expander(expander_label, expanded=False):
            col_list1, col_list2 = st.columns([1, 1])
            
            with col_list1:
                st.markdown(f"##### ✅ {t('sagas_watched_films')} ({len(saga['matched_films'])})")
                if saga['matched_films']:
                    for mf in saga['matched_films']:
                        yr_str = f"({mf['year']})" if mf.get('year') else ""
                        phase_str = f" • <span style='color: #8C98A4; font-size: 0.8rem;'>{mf.get('phase', '')}</span>" if mf.get('phase') else ""
                        star_str = f"<span style='color: #FF8000; font-weight: bold;'>{mf['user_rating']} ★</span>" if mf.get('user_rating') is not None else "<span style='color: #9AB;'>Unrated</span>"
                        phys_icon = " <span class='physical-badge' style='font-size: 0.7rem; padding: 2px 6px;'>💿 Disc</span>" if mf.get('has_physical') else ""
                        
                        item_html = (
                            f"<div style='padding: 8px 12px; background: rgba(0, 224, 84, 0.08); border-left: 4px solid #00E054; border-radius: 6px; margin-bottom: 8px; font-size: 0.88rem;'>"
                            f"<b>{mf['title']}</b> {yr_str}{phase_str}<br>"
                            f"Your Rating: {star_str} &nbsp;|&nbsp; TMDb: ⭐ {mf.get('tmdb_rating') or 'N/A'}{phys_icon}"
                            f"</div>"
                        )
                        st.markdown(item_html, unsafe_allow_html=True)
                else:
                    st.info("No films watched yet.")
                    
            with col_list2:
                st.markdown(f"##### ⏳ {t('sagas_remaining_films')} ({len(saga['unmatched_films'])})")
                if saga['unmatched_films']:
                    for uf in saga['unmatched_films']:
                        yr_str = f"({uf['year']})" if uf.get('year') else ""
                        upcoming_badge = f" <span style='color: #FFC107; font-size: 0.72rem; font-weight: bold; background: rgba(255,193,7,0.15); padding: 2px 6px; border-radius: 4px;'>{t('sagas_upcoming_notice')}</span>" if uf.get('upcoming') else ""
                        phase_str = f" • <span style='color: #8C98A4; font-size: 0.8rem;'>{uf.get('phase', '')}</span>" if uf.get('phase') else ""
                        
                        item_html = (
                            f"<div style='padding: 8px 12px; background: rgba(255, 255, 255, 0.03); border-left: 4px solid #8C98A4; border-radius: 6px; margin-bottom: 8px; font-size: 0.88rem;'>"
                            f"<span style='color: #EEF2F6; font-weight: 500;'>{uf['title']}</span> {yr_str}{upcoming_badge}{phase_str}"
                            f"</div>"
                        )
                        st.markdown(item_html, unsafe_allow_html=True)
                else:
                    st.success("🎉 You've watched every single film in this saga! Outstanding dedication!")

# --- MAIN TABS ---
tab_started, tab_completed, tab_all = st.tabs([
    f"🚀 {t('sagas_tab_started')} ({len(filtered_started)})",
    f"🏆 {t('sagas_tab_completed')} ({len(filtered_completed)})",
    f"🌌 {t('sagas_tab_all')} ({len(all_combined)})"
])

# TAB 1: STARTED SAGAS (IN PROGRESS)
with tab_started:
    if filtered_started:
        tab1_msg = (
            f"<div style='margin-bottom: 15px; color: #9AB; font-size: 0.95rem;'>"
            f"Showing <b>{len(filtered_started)}</b> sagas and universes currently in progress. Complete remaining films to unlock 100% status!"
            f"</div>"
        )
        st.markdown(tab1_msg, unsafe_allow_html=True)
        for saga in filtered_started:
            render_saga_card(saga, is_completed_view=False)
    else:
        st.info(f"ℹ️ {t('sagas_no_started')}")

# TAB 2: COMPLETED SAGAS (100%)
with tab_completed:
    if filtered_completed:
        tab2_msg = (
            f"<div style='background: linear-gradient(135deg, rgba(0, 224, 84, 0.12) 0%, rgba(31, 37, 44, 0.9) 100%); border: 1px solid rgba(0, 224, 84, 0.35); border-radius: 12px; padding: 14px 20px; margin-bottom: 20px;'>"
            f"<span style='color: #00E054; font-weight: 800; font-size: 1.1rem;'>🏆 Hall of Completed Franchises</span><br>"
            f"<span style='color: #EEF2F6; font-size: 0.92rem;'>"
            f"You have watched <b>100% of all released films</b> across these <b>{len(filtered_completed)}</b> legendary sagas and cinematic universes!"
            f"</span></div>"
        )
        st.markdown(tab2_msg, unsafe_allow_html=True)
        for saga in filtered_completed:
            render_saga_card(saga, is_completed_view=True)
    else:
        st.info(f"ℹ️ {t('sagas_no_completed')}")

# TAB 3: ALL SAGAS & UNIVERSES
with tab_all:
    tab3_msg = (
        f"<div style='margin-bottom: 15px; color: #9AB; font-size: 0.95rem;'>"
        f"Full directory of <b>{len(all_combined)}</b> tracked sagas, trilogies, and cinematic universes."
        f"</div>"
    )
    st.markdown(tab3_msg, unsafe_allow_html=True)
    for saga in all_combined:
        render_saga_card(saga, is_completed_view=saga['is_complete'])

st.divider()

# --- TMDB DYNAMIC SCANNER SECTION ---
st.subheader("🔍 Scan Library for TMDb Collections")
scan_desc_html = (
    "<p style='color: #9AB; font-size: 0.92rem;'>"
    "Want to track additional film series (such as <i>Ice Age, Kung Fu Panda, Knives Out, Despicable Me</i>)? "
    "Click below to scan your watched movies against TMDb's collection database and auto-discover new sagas!"
    "</p>"
)
st.markdown(scan_desc_html, unsafe_allow_html=True)

col_scan1, col_scan2 = st.columns([1, 2])
with col_scan1:
    if st.button(t("sagas_scan_btn"), type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_box = st.empty()
        
        def update_scan_progress(curr, total):
            progress_bar.progress(curr / total)
            status_box.text(f"Scanning movie ({curr}/{total})...")
            
        with st.spinner(t("sagas_scan_scanning")):
            new_found = scan_and_cache_tmdb_collections(df, max_movies=80, progress_callback=update_scan_progress)
            
        progress_bar.progress(1.0)
        status_box.empty()
        st.success(f"🎉 {t('sagas_scan_success').format(count=new_found)}")
        st.rerun()

with col_scan2:
    if st.button("🎬 View in Personal Movie Space", use_container_width=True):
        st.switch_page("pages/personal_space.py")
