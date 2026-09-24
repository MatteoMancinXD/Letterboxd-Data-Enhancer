# pages/personal_space.py
import streamlit as st
import pandas as pd
import numpy as np
import os
from services.translations import t

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

if 'enriched_data' not in st.session_state or st.session_state['enriched_data'].empty:
    st.warning(t("no_data_warning"))
    st.stop()

df = st.session_state['enriched_data'].copy()

# Ensure 'Rating' and 'physical_copy' columns exist
if 'Rating' not in df.columns:
    df['Rating'] = np.nan
if 'physical_copy' not in df.columns:
    df['physical_copy'] = False
df['physical_copy'] = df['physical_copy'].fillna(False).astype(bool)

st.title(f"🎬 {t('ps_title')}")
st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>{t('ps_subtitle')}</p>", unsafe_allow_html=True)

# 1. Summary KPIs with Physical Collection
total_count = len(df)
rated_count = int(df['Rating'].notna().sum())
unrated_count = total_count - rated_count
avg_user_rating = float(df['Rating'].dropna().mean()) if rated_count > 0 else 0.0

physical_count = int(df['physical_copy'].sum())
physical_pct = (physical_count / total_count * 100) if total_count > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(t("ps_kpi_total"), f"{total_count} films")
with col2:
    st.metric(t("ps_kpi_rated"), f"{rated_count} films", f"{(rated_count / total_count * 100):.1f}%")
with col3:
    st.metric(t("ps_kpi_unrated"), f"{unrated_count} films", f"{(unrated_count / total_count * 100):.1f}%")
with col4:
    st.metric(t("ps_kpi_avg"), f"{avg_user_rating:.2f} ★" if rated_count > 0 else "N/A")
with col5:
    st.metric(f"💿 {t('ps_kpi_physical')}", f"{physical_count} films", f"{physical_pct:.1f}%")

# Percentage Progress Bar Banner for Physical Collection
phys_banner_html = (
    f"<div class='physical-kpi-card'>"
    f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>"
    f"<span style='color: #C084FC; font-weight: 700; font-size: 0.95rem;'>💿 {t('ps_kpi_physical')}: <b>{physical_count}</b> of <b>{total_count}</b> films</span>"
    f"<b style='color: #00E054; font-size: 1.05rem;'>{physical_pct:.1f}% in Physical Media</b>"
    f"</div>"
    f"<div class='saga-progress-track'>"
    f"<div style='height: 100%; border-radius: 6px; width: {physical_pct}%; background: linear-gradient(90deg, #A855F7 0%, #00E054 100%);'></div>"
    f"</div>"
    f"</div>"
)
st.markdown(phys_banner_html, unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# 2. Interactive Film Rater & Modifier
st.markdown(f"### ⭐ {t('ps_rate_box_title')}")

# Selectbox to search and pick any movie from the entire library
film_titles_options = []
film_index_map = {}

for idx, row in df.iterrows():
    name = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
    year = int(row['Year']) if pd.notna(row.get('Year')) and str(row.get('Year')).replace('.0','').isdigit() else "N/A"
    curr_r = f"{row['Rating']}★" if pd.notna(row.get('Rating')) else "Unrated"
    phys_tag = " [💿 Disc]" if row.get('physical_copy') else ""
    display_label = f"{name} ({year}) — [{curr_r}]{phys_tag}"
    film_titles_options.append(display_label)
    film_index_map[display_label] = idx

col_pick, col_sort = st.columns([3, 1])
with col_pick:
    selected_option = st.selectbox(
        t("ps_select_movie"),
        options=film_titles_options,
        index=0,
        help="Type to search through all movies in your library"
    )

if selected_option and selected_option in film_index_map:
    target_idx = film_index_map[selected_option]
    target_row = df.loc[target_idx]
    
    col_card1, col_card2 = st.columns([1, 2])
    
    with col_card1:
        poster_path = target_row.get('poster_path')
        if poster_path and pd.notna(poster_path):
            st.image(f"https://image.tmdb.org/t/p/w200{poster_path}", width=180)
        else:
            st.markdown(
                """
                <div style="width: 180px; height: 260px; background: #1F252C; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: #9AB; font-size: 0.9rem;">No Poster</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    with col_card2:
        m_name = target_row.get('Name') if pd.notna(target_row.get('Name')) else (target_row.get('Title') if pd.notna(target_row.get('Title')) else "Untitled")
        m_year = int(target_row['Year']) if pd.notna(target_row.get('Year')) and str(target_row.get('Year')).replace('.0','').isdigit() else "N/A"
        st.markdown(f"#### {m_name} ({m_year})")
        
        # Current status badges
        curr_val = target_row.get('Rating')
        curr_phys = bool(target_row.get('physical_copy', False))
        
        status_badges = []
        if pd.notna(curr_val):
            status_badges.append(f"<span class='rating-badge'>{curr_val} ★</span>")
        else:
            status_badges.append("<span style='color: #FF8000; font-weight: bold;'>⚠️ Unrated</span>")
            
        if curr_phys:
            status_badges.append("<span class='physical-badge'>💿 Physical Copy in Collection</span>")
            
        st.markdown(" ".join(status_badges), unsafe_allow_html=True)
        st.markdown(f"**TMDb Consensus:** ⭐ {target_row.get('tmdb_rating') or 'N/A'} / 10")
        
        # Rating options
        rating_slider_options = [
            "Unrated", "0.5 ★", "1.0 ★", "1.5 ★", "2.0 ★", "2.5 ★",
            "3.0 ★", "3.5 ★", "4.0 ★", "4.5 ★", "5.0 ★"
        ]
        
        default_slider_val = f"{curr_val} ★" if pd.notna(curr_val) and f"{curr_val} ★" in rating_slider_options else "Unrated"
        
        new_rating_choice = st.select_slider(
            "Set Your Personal Star Rating:",
            options=rating_slider_options,
            value=default_slider_val,
            key=f"slider_rate_{target_idx}"
        )
        
        # Physical copy checkbox
        new_physical_choice = st.checkbox(
            f"💿 {t('ps_physical_checkbox')}",
            value=curr_phys,
            key=f"chk_phys_edit_{target_idx}",
            help="Check if you own a 4K UHD, Blu-ray, or DVD physical disc copy of this movie"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(f"💾 {t('ps_save_rating_btn')}", type="primary", use_container_width=True):
                if new_rating_choice == "Unrated":
                    df.at[target_idx, 'Rating'] = np.nan
                else:
                    df.at[target_idx, 'Rating'] = float(new_rating_choice.replace(" ★", ""))
                    
                df.at[target_idx, 'physical_copy'] = bool(new_physical_choice)
                    
                # Save to disk and session
                df.to_parquet(ENRICHED_FILE, index=False)
                st.session_state['enriched_data'] = df
                st.success(f"{t('ps_rating_saved')} **{m_name}**!")
                st.rerun()
                
        with col_btn2:
            if pd.notna(curr_val):
                if st.button(f"🗑️ {t('ps_clear_rating_btn')}", use_container_width=True):
                    df.at[target_idx, 'Rating'] = np.nan
                    df.to_parquet(ENRICHED_FILE, index=False)
                    st.session_state['enriched_data'] = df
                    st.info(f"{t('ps_rating_cleared')} **{m_name}**.")
                    st.rerun()

st.divider()

# 3. Catalog Explorer with Quick Views (All, Rated, Unrated, Physical Copies)
st.subheader("📋 Film Collection & Diary")

col_filter1, col_filter2, col_filter3 = st.columns([2.5, 1.5, 1])

with col_filter1:
    view_filter = st.radio(
        "Filter View:",
        options=[
            f"{t('ps_filter_all')} ({total_count})",
            f"{t('ps_filter_rated')} ({rated_count})",
            f"{t('ps_filter_unrated')} ({unrated_count})",
            f"💿 {t('ps_filter_physical')} ({physical_count})"
        ],
        horizontal=True
    )

with col_filter2:
    search_text = st.text_input("🔍 Search films in collection:", placeholder="Filter by title or director...")

with col_filter3:
    sort_by = st.selectbox(
        "Sort By:",
        options=["Watch Date (Newest)", "Watch Date (Oldest)", "Your Rating (Highest)", "Your Rating (Lowest)", "Title (A-Z)", "Release Year"]
    )

# Apply View Filter
filtered_table = df.copy()

if "Rated Only" in view_filter or "Solo con Voto" in view_filter:
    filtered_table = filtered_table[filtered_table['Rating'].notna()]
elif "Unrated" in view_filter or "Senza Voto" in view_filter:
    filtered_table = filtered_table[filtered_table['Rating'].isna()]
elif "Physical" in view_filter or "Fisiche" in view_filter:
    filtered_table = filtered_table[filtered_table['physical_copy'] == True]

# Apply Search
if search_text.strip():
    q = search_text.strip().lower()
    def row_match(r):
        t_name = str(r.get('Name') if pd.notna(r.get('Name')) else (r.get('Title') if pd.notna(r.get('Title')) else "")).lower()
        if q in t_name:
            return True
        dirs = r.get('directors')
        if hasattr(dirs, '__iter__') and not isinstance(dirs, (str, bytes)):
            if any(q in str(d).lower() for d in dirs):
                return True
        return False
    filtered_table = filtered_table[filtered_table.apply(row_match, axis=1)]

# Apply Sort
if sort_by == "Watch Date (Newest)":
    if 'Date' in filtered_table.columns:
        filtered_table = filtered_table.sort_values(by='Date', ascending=False)
elif sort_by == "Watch Date (Oldest)":
    if 'Date' in filtered_table.columns:
        filtered_table = filtered_table.sort_values(by='Date', ascending=True)
elif sort_by == "Your Rating (Highest)":
    if 'Rating' in filtered_table.columns:
        filtered_table = filtered_table.sort_values(by='Rating', ascending=False)
elif sort_by == "Your Rating (Lowest)":
    if 'Rating' in filtered_table.columns:
        filtered_table = filtered_table.sort_values(by='Rating', ascending=True)
elif sort_by == "Title (A-Z)":
    sort_c = 'Name' if 'Name' in filtered_table.columns else ('Title' if 'Title' in filtered_table.columns else None)
    if sort_c:
        filtered_table = filtered_table.sort_values(by=sort_c, ascending=True)
elif sort_by == "Release Year":
    if 'Year' in filtered_table.columns:
        filtered_table = filtered_table.sort_values(by='Year', ascending=False)

# Prepare editable grid
editor_data = pd.DataFrame(index=filtered_table.index)
title_series = filtered_table['Name'] if 'Name' in filtered_table.columns else pd.Series(index=filtered_table.index, dtype=object)
if 'Title' in filtered_table.columns:
    title_series = title_series.fillna(filtered_table['Title'])

editor_data['Title'] = title_series.fillna("Untitled")
editor_data['Year'] = filtered_table['Year'].fillna(0).astype(int) if 'Year' in filtered_table.columns else 0
editor_data['Physical Copy'] = filtered_table['physical_copy'].fillna(False).astype(bool)
editor_data['Your Rating'] = filtered_table['Rating'].apply(lambda r: f"{r} ★" if pd.notna(r) else "Unrated") if 'Rating' in filtered_table.columns else "Unrated"
editor_data['TMDb Score'] = filtered_table['tmdb_rating'] if 'tmdb_rating' in filtered_table.columns else "N/A"
editor_data['Watch Date'] = filtered_table['Date'] if 'Date' in filtered_table.columns else "N/A"
editor_data['Directors'] = filtered_table['directors'].apply(lambda l: ", ".join(l) if hasattr(l, '__iter__') and not isinstance(l, (str, bytes)) else "N/A") if 'directors' in filtered_table.columns else "N/A"

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="color: #EEF2F6; font-size: 0.95rem;">
            Showing <b>{len(editor_data)}</b> films — <i>💡 You can toggle the <b>Physical Copy</b> checkbox directly in the table below!</i>
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

edited_result = st.data_editor(
    editor_data,
    column_config={
        "Physical Copy": st.column_config.CheckboxColumn(
            "💿 Physical",
            help="Check if you own this film on 4K UHD, Blu-ray, or DVD",
            default=False
        ),
        "Title": st.column_config.TextColumn("Title", disabled=True),
        "Year": st.column_config.NumberColumn("Year", format="%d", disabled=True),
        "Your Rating": st.column_config.TextColumn("Your Rating", disabled=True),
        "TMDb Score": st.column_config.NumberColumn("TMDb", format="%.1f", disabled=True),
        "Watch Date": st.column_config.TextColumn("Watch Date", disabled=True),
        "Directors": st.column_config.TextColumn("Directors", disabled=True),
    },
    disabled=["Title", "Year", "Your Rating", "TMDb Score", "Watch Date", "Directors"],
    use_container_width=True,
    height=450,
    key="data_editor_personal_space"
)

# Detect if physical copy changes were made in the interactive data editor
if edited_result is not None:
    changed_indices = []
    for row_idx in edited_result.index:
        old_val = bool(df.loc[row_idx, 'physical_copy'])
        new_val = bool(edited_result.loc[row_idx, 'Physical Copy'])
        if old_val != new_val:
            df.loc[row_idx, 'physical_copy'] = new_val
            changed_indices.append(row_idx)
            
    if changed_indices:
        df.to_parquet(ENRICHED_FILE, index=False)
        st.session_state['enriched_data'] = df
        st.toast(f"💾 Updated physical copy status for {len(changed_indices)} film(s)!", icon="💿")
        st.rerun()

# CSV Export
csv_data = filtered_table.to_csv(index=False).encode('utf-8')
st.download_button(
    label="💾 Download Current View as CSV",
    data=csv_data,
    file_name="my_personal_letterboxd_ratings.csv",
    mime="text/csv"
)
