# pages/more_statistics.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
from collections import Counter
from itertools import combinations
from services.translations import t
from services.ratings_service import calculate_taste_affinity
from services.nationality_service import compute_nationality_statistics
from services.awards_service import compute_awards_analytics

# Custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("assets/style.css")

# --- DATA RECOVERY ---
DATA_DIR = "data"
ENRICHED_FILE = os.path.join(DATA_DIR, "letterboxd_enriched.parquet")

if 'enriched_data' not in st.session_state and os.path.exists(ENRICHED_FILE):
    st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
    st.session_state['data_loaded'] = True

if 'enriched_data' in st.session_state and not st.session_state['enriched_data'].empty:
    df_raw = st.session_state['enriched_data']
elif 'raw_data' in st.session_state and not st.session_state['raw_data'].empty:
    df_raw = st.session_state['raw_data']
else:
    st.warning(t("no_data_warning"))
    st.stop()

# --- PREPARATION & USER RATING PRIORITIZATION ---
@st.cache_data
def prepare_dataset(df):
    data = df.copy()
    
    def clean_list(val):
        if isinstance(val, (list, np.ndarray)):
            return [str(item).strip() for item in val if pd.notna(item) and str(item).strip()]
        return []

    data['clean_directors'] = data['directors'].apply(clean_list) if 'directors' in data.columns else [[] for _ in range(len(data))]
    data['clean_actors'] = data['actors'].apply(clean_list) if 'actors' in data.columns else [[] for _ in range(len(data))]
    data['clean_genres'] = data['genres'].apply(clean_list) if 'genres' in data.columns else [[] for _ in range(len(data))]

    # Physical collection
    if 'physical_copy' not in data.columns:
        data['physical_copy'] = False
    data['physical_copy'] = data['physical_copy'].fillna(False).astype(bool)

    # Release Years & Decades
    if 'Year' in data.columns:
        data['Year'] = pd.to_numeric(data['Year'], errors='coerce')
        data['decade'] = (data['Year'] // 10) * 10
        data['decade_str'] = data['decade'].apply(lambda d: f"{int(d)}s" if pd.notna(d) else "Unknown")
    else:
        data['Year'] = np.nan
        data['decade_str'] = "Unknown"

    # Ratings
    if 'tmdb_rating' in data.columns:
        data['tmdb_rating'] = pd.to_numeric(data['tmdb_rating'], errors='coerce')
    else:
        data['tmdb_rating'] = np.nan

    if 'Rating' in data.columns:
        data['Rating'] = pd.to_numeric(data['Rating'], errors='coerce')
        # Normalized 10-point scale for user rating (0.5-5.0 stars -> 1.0-10.0)
        data['user_rating_10'] = data['Rating'] * 2.0
    else:
        data['Rating'] = np.nan
        data['user_rating_10'] = np.nan

    # Unified primary rating (User rating prioritized, then TMDb fallback)
    data['primary_rating_10'] = data['user_rating_10'].fillna(data['tmdb_rating'])
    data['rating_is_personal'] = data['Rating'].notna()

    # Watch Dates
    if 'Date' in data.columns:
        data['parsed_date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['watch_year'] = data['parsed_date'].dt.year
        data['watch_year_month'] = data['parsed_date'].dt.to_period('M').astype(str)
        data['watch_month_name'] = data['parsed_date'].dt.strftime('%B')
        data['watch_month_num'] = data['parsed_date'].dt.month
        data['watch_weekday'] = data['parsed_date'].dt.day_name()
    else:
        data['parsed_date'] = pd.NaT

    return data

df = prepare_dataset(df_raw)
has_user_ratings = df['Rating'].notna().any()

# --- SIDEBAR: ANALYTICAL FILTERS ---
st.sidebar.markdown(f"<h3 style='color: #FF8000;'>⚙️ {t('stats_filter_title')}</h3>", unsafe_allow_html=True)

# Release Year Filter
valid_years = df['Year'].dropna().astype(int)
if not valid_years.empty:
    min_year, max_year = int(valid_years.min()), int(valid_years.max())
    selected_year_range = st.sidebar.slider(
        t("stats_filter_year"),
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )
else:
    selected_year_range = (1900, 2030)

# Genre Filter
all_available_genres = sorted(list(set([g for sublist in df['clean_genres'] for g in sublist])))
selected_genres = st.sidebar.multiselect(
    t("stats_filter_genre"),
    options=all_available_genres,
    default=[]
)

# Rating Filter
rating_filter_label = t("stats_filter_min_score")
min_rating_filter = st.sidebar.slider(
    rating_filter_label,
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.5
)
include_unrated = st.sidebar.checkbox("Include unrated films when filtering by score", value=True)

# Reset Button
if st.sidebar.button(f"🔄 {t('stats_filter_reset')}", use_container_width=True):
    st.rerun()

# Apply Filters
filtered_df = df.copy()

if not valid_years.empty:
    filtered_df = filtered_df[
        (filtered_df['Year'] >= selected_year_range[0]) &
        (filtered_df['Year'] <= selected_year_range[1])
    ]

if selected_genres:
    filtered_df = filtered_df[
        filtered_df['clean_genres'].apply(lambda gl: any(g in gl for g in selected_genres))
    ]

if min_rating_filter > 0:
    if include_unrated:
        filtered_df = filtered_df[
            (filtered_df['primary_rating_10'] >= min_rating_filter) |
            (filtered_df['Rating'].isna())
        ]
    else:
        filtered_df = filtered_df[filtered_df['primary_rating_10'] >= min_rating_filter]

pct_shown = (len(filtered_df) / len(df) * 100) if len(df) > 0 else 0
st.sidebar.markdown(
    f"""
    <div style="background: #1F252C; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,128,0,0.3); margin-top: 15px;">
        <span style="color: #9AB; font-size: 0.85rem;">{t('stats_filter_active')}</span><br>
        <b style="color: #FF8000; font-size: 1.1rem;">{len(filtered_df)}</b> {t('stats_of')} {len(df)} {t('stats_films')}
        <span style="color: #00E054;">({pct_shown:.1f}%)</span>
    </div>
    """,
    unsafe_allow_html=True
)

# --- HEADER & KPI BAR ---
st.title(f"📈 {t('stats_title')}")
st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 1rem;'>{t('stats_subtitle')}</p>", unsafe_allow_html=True)

if filtered_df.empty:
    st.warning("No films match your selected filter criteria. Please reset filters.")
    st.stop()

# Total Watch History & Banners
rated_in_slice = filtered_df['Rating'].notna().sum()
unrated_in_slice = len(filtered_df) - rated_in_slice
phys_in_slice = int(filtered_df['physical_copy'].sum()) if 'physical_copy' in filtered_df.columns else 0
phys_in_slice_pct = (phys_in_slice / len(filtered_df) * 100) if len(filtered_df) > 0 else 0

col_ban_txt, col_ban_b1, col_ban_b2 = st.columns([2.5, 1, 1])
with col_ban_txt:
    ban_stats_html = (
        f"<div style='background: rgba(64, 188, 244, 0.08); border: 1px solid rgba(64, 188, 244, 0.25); border-radius: 10px; padding: 10px 16px;'>"
        f"<span style='color: #40BCF4; font-weight: bold; font-size: 0.95rem;'>🎬 Complete Watch History Active:</span> "
        f"<span style='color: #EEF2F6; font-size: 0.9rem;'>"
        f"Showing all <b>{len(filtered_df)}</b> watched films (<b>{rated_in_slice}</b> rated, <b>{unrated_in_slice}</b> unrated, <b style='color: #C084FC;'>{phys_in_slice}</b> physical copies [<b>{phys_in_slice_pct:.1f}%</b>])."
        f"</span></div>"
    )
    st.markdown(ban_stats_html, unsafe_allow_html=True)
with col_ban_b1:
    if st.button("🪐 Sagas & Universes", use_container_width=True, type="secondary", key="btn_stats_sagas"):
        st.switch_page("pages/sagas.py")
with col_ban_b2:
    if st.button("🎬 Personal Space", use_container_width=True, type="secondary", key="btn_stats_ps"):
        st.switch_page("pages/personal_space.py")

# Top KPI Summary Row
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

with col_kpi1:
    st.metric(t("stats_showing"), f"{len(filtered_df)} {t('stats_films')}")

with col_kpi2:
    if filtered_df['Year'].notna().any():
        st.metric(t("stats_range_years"), f"{int(filtered_df['Year'].min())} - {int(filtered_df['Year'].max())}")
    else:
        st.metric(t("stats_range_years"), "N/A")

with col_kpi3:
    if has_user_ratings and filtered_df['Rating'].notna().any():
        avg_u = filtered_df['Rating'].dropna().mean()
        st.metric(t("stats_avg_user"), f"{avg_u:.2f} ★")
    elif filtered_df['tmdb_rating'].notna().any():
        st.metric(t("stats_avg_tmdb"), f"{filtered_df['tmdb_rating'].dropna().mean():.2f} / 10")
    else:
        st.metric("Avg Rating", "N/A")

with col_kpi4:
    unique_dirs = len(set([d for sub in filtered_df['clean_directors'] for d in sub]))
    st.metric(t("stats_unique_dirs"), f"{unique_dirs}")

with col_kpi5:
    unique_actors = len(set([a for sub in filtered_df['clean_actors'] for a in sub]))
    st.metric(t("stats_unique_actors"), f"{unique_actors}")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- TABS ---
tab_dirs, tab_genres, tab_countries, tab_awards, tab_decades, tab_habits, tab_ratings, tab_search = st.tabs([
    f"🎬 {t('tab_directors')}",
    f"🧬 {t('tab_genres')}",
    f"🌍 {t('tab_nationalities')}",
    f"🏆 {t('tab_awards')}",
    f"⏳ {t('tab_decades')}",
    f"📅 {t('tab_habits')}",
    f"⭐ {t('tab_ratings')}",
    f"🔎 {t('tab_search')}"
])

# ==============================================================================
# TAB 1: DIRECTORS & CAST
# ==============================================================================
with tab_dirs:
    st.subheader(f"🎥 {t('tab_directors')}")
    
    dir_records = []
    for _, row in filtered_df.iterrows():
        title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
        year = row.get('Year')
        score = row['primary_rating_10']
        for d in row['clean_directors']:
            dir_records.append({'Director': d, 'Title': title, 'Year': year, 'Score': score})
            
    df_dir_exploded = pd.DataFrame(dir_records)
    
    if not df_dir_exploded.empty:
        dir_summary = df_dir_exploded.groupby('Director').agg(
            Film_Count=('Title', 'count'),
            Avg_Rating=('Score', 'mean')
        ).reset_index()
        dir_summary['Avg_Rating'] = dir_summary['Avg_Rating'].round(2)
        
        col_dir1, col_dir2 = st.columns([3, 2])
        
        with col_dir1:
            st.markdown(f"##### 🏆 {t('tab1_top_dirs')}")
            top_15_dirs = dir_summary.sort_values(by='Film_Count', ascending=False).head(15)
            
            chart_top_dirs = alt.Chart(top_15_dirs).mark_bar(
                cornerRadiusTopRight=6,
                cornerRadiusBottomRight=6,
                color='#FF8000'
            ).encode(
                x=alt.X('Film_Count:Q', title="Films Logged"),
                y=alt.Y('Director:N', sort=top_15_dirs['Director'].tolist(), title=None),
                tooltip=[
                    alt.Tooltip('Director:N', title='Director'),
                    alt.Tooltip('Film_Count:Q', title='Films Watched'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Rating (1-10)')
                ]
            ).properties(height=420)
            
            st.altair_chart(chart_top_dirs, use_container_width=True)
            
        with col_dir2:
            st.markdown(f"##### ⭐ {t('tab1_top_rated_dirs')}")
            
            # Pool of directors with valid ratings
            rated_dirs_pool = dir_summary[dir_summary['Avg_Rating'].notna() & (dir_summary['Avg_Rating'] > 0)]
            max_films_dir = int(rated_dirs_pool['Film_Count'].max()) if not rated_dirs_pool.empty else 5
            slider_max = max(5, max_films_dir)
            # Default to 2 if there are enough multi-film directors, otherwise 1 so the chart is never empty
            default_min = 2 if (rated_dirs_pool['Film_Count'] >= 2).sum() >= 5 else 1
            min_films_dir = st.slider(t("tab1_min_films_slider"), min_value=1, max_value=slider_max, value=default_min, key="slider_dir_min_films")
            
            qualified_dirs = rated_dirs_pool[rated_dirs_pool['Film_Count'] >= min_films_dir]
            top_rated_dirs = qualified_dirs.sort_values(by=['Avg_Rating', 'Film_Count'], ascending=[False, False]).head(10).copy()
            
            if not top_rated_dirs.empty:
                top_rated_dirs['label'] = top_rated_dirs.apply(
                    lambda r: f"{r['Avg_Rating']:.1f} ★ ({int(r['Film_Count'])}m)", axis=1
                )
                
                bars_rated = alt.Chart(top_rated_dirs).mark_bar(
                    cornerRadiusTopRight=6,
                    cornerRadiusBottomRight=6,
                    color='#00E054'
                ).encode(
                    x=alt.X('Avg_Rating:Q', title="Avg Rating (0-10 Scale)", scale=alt.Scale(domain=[0, 10.5])),
                    y=alt.Y('Director:N', sort=top_rated_dirs['Director'].tolist(), title=None),
                    tooltip=[
                        alt.Tooltip('Director:N', title='Director'),
                        alt.Tooltip('Avg_Rating:Q', title='Avg Rating (1-10)'),
                        alt.Tooltip('Film_Count:Q', title='Films Watched')
                    ]
                )
                
                text_rated = alt.Chart(top_rated_dirs).mark_text(
                    align='left',
                    baseline='middle',
                    dx=5,
                    color='#EEF2F6',
                    fontSize=11,
                    fontWeight=600
                ).encode(
                    x=alt.X('Avg_Rating:Q'),
                    y=alt.Y('Director:N', sort=top_rated_dirs['Director'].tolist()),
                    text=alt.Text('label:N')
                )
                
                chart_rated_dirs = (bars_rated + text_rated).properties(height=max(220, len(top_rated_dirs) * 38))
                st.altair_chart(chart_rated_dirs, use_container_width=True)
            else:
                st.info(f"ℹ️ No directors found with at least {min_films_dir} film(s) and a valid rating. Try lowering the minimum films slider.")

        st.divider()
        
        # Director Deep Dive
        st.subheader(f"🔍 {t('tab1_dir_deep_dive')}")
        all_dirs_sorted = sorted(dir_summary['Director'].unique())
        selected_director = st.selectbox(t("tab1_select_dir"), all_dirs_sorted, index=0)
        
        if selected_director:
            dir_movies = filtered_df[filtered_df['clean_directors'].apply(lambda dl: selected_director in dl)]
            d_count = len(dir_movies)
            d_avg = dir_movies['primary_rating_10'].mean() if dir_movies['primary_rating_10'].notna().any() else "N/A"
            d_genres = list(set([g for sub in dir_movies['clean_genres'] for g in sub]))
            
            col_dd1, col_dd2, col_dd3 = st.columns(3)
            with col_dd1:
                st.metric(t("tab1_films_in_diary"), f"{d_count}")
            with col_dd2:
                st.metric("Avg Rating (1-10)", f"{d_avg:.2f}" if isinstance(d_avg, float) else d_avg)
            with col_dd3:
                st.metric(t("tab1_genres_explored"), f"{len(d_genres)}")
                
            st.markdown(f"**Genres:** " + " ".join([f"<span class='genre-badge'>{g}</span>" for g in d_genres]), unsafe_allow_html=True)
            
            show_cols = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'Letterboxd URI'] if c in dir_movies.columns]
            st.dataframe(dir_movies[show_cols].sort_values(by='Year', ascending=True), use_container_width=True)

        st.divider()

        # Actors & Cast Stardom
        st.subheader(f"🎭 {t('tab1_top_actors')}")
        
        act_records = []
        for _, row in filtered_df.iterrows():
            title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
            year = row.get('Year')
            score = row['primary_rating_10']
            for a in row['clean_actors']:
                act_records.append({'Actor': a, 'Title': title, 'Year': year, 'Score': score})
                
        df_act_exploded = pd.DataFrame(act_records)
        
        if not df_act_exploded.empty:
            act_summary = df_act_exploded.groupby('Actor').agg(
                Film_Count=('Title', 'count'),
                Avg_Rating=('Score', 'mean')
            ).reset_index()
            act_summary['Avg_Rating'] = act_summary['Avg_Rating'].round(2)
            
            col_act1, col_act2 = st.columns([3, 2])
            
            with col_act1:
                top_20_acts = act_summary.sort_values(by='Film_Count', ascending=False).head(20)
                
                chart_top_acts = alt.Chart(top_20_acts).mark_bar(
                    cornerRadiusTopRight=6,
                    cornerRadiusBottomRight=6,
                    color='#40BCF4'
                ).encode(
                    x=alt.X('Film_Count:Q', title="Film Appearances"),
                    y=alt.Y('Actor:N', sort='-x', title=None),
                    tooltip=[
                        alt.Tooltip('Actor:N', title='Actor'),
                        alt.Tooltip('Film_Count:Q', title='Films'),
                        alt.Tooltip('Avg_Rating:Q', title='Avg Score')
                    ]
                ).properties(height=520)
                
                st.altair_chart(chart_top_acts, use_container_width=True)
                
            with col_act2:
                st.markdown(f"##### 🤝 {t('tab1_collabs')}")
                collab_counter = Counter()
                for _, row in filtered_df.iterrows():
                    for d in row['clean_directors']:
                        for a in row['clean_actors']:
                            collab_counter[(d, a)] += 1
                            
                top_collabs = pd.DataFrame(
                    [{'Director': pair[0], 'Actor': pair[1], 'Together': count} for pair, count in collab_counter.most_common(10)]
                )
                if not top_collabs.empty:
                    st.dataframe(top_collabs, use_container_width=True, height=240)
                
                st.markdown(f"##### 👥 {t('tab1_actor_duos')}")
                duo_counter = Counter()
                for _, row in filtered_df.iterrows():
                    acts = sorted(list(set(row['clean_actors'])))
                    for duo in combinations(acts, 2):
                        duo_counter[duo] += 1
                        
                top_duos = pd.DataFrame(
                    [{'Actor 1': duo[0], 'Actor 2': duo[1], 'Together': count} for duo, count in duo_counter.most_common(10)]
                )
                if not top_duos.empty:
                    st.dataframe(top_duos, use_container_width=True, height=240)

# ==============================================================================
# TAB 2: GENRES & STYLES
# ==============================================================================
with tab_genres:
    st.subheader(f"🧬 {t('tab_genres')}")
    
    genre_records = []
    for _, row in filtered_df.iterrows():
        title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
        year = row.get('Year')
        score = row['primary_rating_10']
        decade = row.get('decade_str')
        for g in row['clean_genres']:
            genre_records.append({'Genre': g, 'Title': title, 'Year': year, 'Score': score, 'Decade': decade})
            
    df_genre_exploded = pd.DataFrame(genre_records)
    
    if not df_genre_exploded.empty:
        genre_summary = df_genre_exploded.groupby('Genre').agg(
            Count=('Title', 'count'),
            Avg_Rating=('Score', 'mean')
        ).reset_index()
        
        genre_summary['Percent'] = (genre_summary['Count'] / len(filtered_df) * 100).round(1)
        genre_summary['Avg_Rating'] = genre_summary['Avg_Rating'].round(2)
        genre_summary = genre_summary.sort_values(by='Count', ascending=False)
        
        col_gen1, col_gen2 = st.columns([3, 2])
        
        with col_gen1:
            st.markdown(f"##### 📊 {t('tab2_genre_freq')}")
            chart_genres = alt.Chart(genre_summary).mark_bar(
                cornerRadiusTopRight=6,
                cornerRadiusBottomRight=6,
                color='#FF8000'
            ).encode(
                x=alt.X('Count:Q', title="Films Watched"),
                y=alt.Y('Genre:N', sort='-x', title=None),
                tooltip=[
                    alt.Tooltip('Genre:N', title='Genre'),
                    alt.Tooltip('Count:Q', title='Films'),
                    alt.Tooltip('Percent:Q', title='Share %'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Score')
                ]
            ).properties(height=480)
            
            st.altair_chart(chart_genres, use_container_width=True)
            
        with col_gen2:
            st.markdown(f"##### ⚖️ {t('tab2_matrix_title')}")
            st.caption(t("tab2_matrix_caption"))
            
            chart_scatter = alt.Chart(genre_summary).mark_circle(size=180).encode(
                x=alt.X('Count:Q', title="Volume (Films Watched)"),
                y=alt.Y('Avg_Rating:Q', title="Quality (Avg Rating)", scale=alt.Scale(zero=False)),
                color=alt.Color('Genre:N', legend=None),
                tooltip=[
                    alt.Tooltip('Genre:N', title='Genre'),
                    alt.Tooltip('Count:Q', title='Films'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Score')
                ]
            ).properties(height=350)
            
            chart_text = chart_scatter.mark_text(
                align='left',
                baseline='middle',
                dx=10,
                fontSize=11,
                color='#EEF2F6'
            ).encode(
                text='Genre:N'
            )
            
            st.altair_chart(chart_scatter + chart_text, use_container_width=True)

        st.divider()

        # Combinations & Evolution
        col_pair1, col_pair2 = st.columns([1, 1])
        
        with col_pair1:
            st.markdown(f"##### 🎭 {t('tab2_top_pairs')}")
            pair_counter = Counter()
            for _, row in filtered_df.iterrows():
                g_list = sorted(list(set(row['clean_genres'])))
                for pair in combinations(g_list, 2):
                    pair_counter[pair] += 1
                    
            top_pairs = pd.DataFrame(
                [{'Pair': f"{p[0]} + {p[1]}", 'Films': count} for p, count in pair_counter.most_common(12)]
            )
            if not top_pairs.empty:
                st.dataframe(top_pairs, use_container_width=True)
                
        with col_pair2:
            st.markdown(f"##### ⏳ {t('tab2_genre_evolution')}")
            top_5_genres = genre_summary.head(5)['Genre'].tolist()
            df_g_dec = df_genre_exploded[df_genre_exploded['Genre'].isin(top_5_genres)]
            
            if not df_g_dec.empty:
                g_dec_summary = df_g_dec.groupby(['Decade', 'Genre']).size().reset_index(name='Count')
                g_dec_summary = g_dec_summary[g_dec_summary['Decade'] != 'Unknown']
                
                chart_g_dec = alt.Chart(g_dec_summary).mark_line(point=True).encode(
                    x=alt.X('Decade:N', title="Decade"),
                    y=alt.Y('Count:Q', title="Films"),
                    color=alt.Color('Genre:N', title="Genre"),
                    tooltip=['Decade:N', 'Genre:N', 'Count:Q']
                ).properties(height=300)
                
                st.altair_chart(chart_g_dec, use_container_width=True)

# ==============================================================================
# TAB 3: WORLD CINEMA & NATIONALITIES
# ==============================================================================
with tab_countries:
    st.subheader(f"🌍 {t('tab_nat_title')}")
    st.markdown(f"<p style='color: #9AB;'>{t('tab_nat_subtitle')}</p>", unsafe_allow_html=True)
    
    col_opt1, col_opt2 = st.columns([2, 1])
    with col_opt1:
        nat_mode = st.radio(
            t("tab_nat_mode_label"),
            options=["director", "production"],
            format_func=lambda x: t("tab_nat_mode_dir") if x == "director" else t("tab_nat_mode_prod"),
            horizontal=True,
            key="radio_nat_analysis_mode"
        )
        
    nat_summary, nat_kpis, enriched_nat_df = compute_nationality_statistics(filtered_df, mode=nat_mode)
    
    if not nat_summary.empty:
        # KPIs
        col_nk1, col_nk2, col_nk3, col_nk4 = st.columns(4)
        with col_nk1:
            st.metric(t("tab_nat_kpi_countries"), f"{nat_kpis['unique_countries']}")
        with col_nk2:
            st.metric(t("tab_nat_kpi_top"), nat_kpis['top_country'])
        with col_nk3:
            st.metric(t("tab_nat_kpi_intl"), f"{nat_kpis['intl_percent']}%")
        with col_nk4:
            st.metric(t("tab_nat_kpi_highest"), nat_kpis['highest_rated_country'])
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Charts Row
        col_nc1, col_nc2 = st.columns([3, 2])
        
        with col_nc1:
            st.markdown(f"##### 🏆 {t('tab_nat_top_chart')}")
            top_15_nat = nat_summary.head(15).copy()
            top_15_nat['label'] = top_15_nat.apply(lambda r: f"{int(r['Film_Count'])} films ({r['Percent']}%)", axis=1)
            
            bars_nat = alt.Chart(top_15_nat).mark_bar(
                cornerRadiusTopRight=6,
                cornerRadiusBottomRight=6,
                color='#40BCF4'
            ).encode(
                x=alt.X('Film_Count:Q', title="Films Logged"),
                y=alt.Y('Display:N', sort=top_15_nat['Display'].tolist(), title=None),
                tooltip=[
                    alt.Tooltip('Display:N', title='Country'),
                    alt.Tooltip('Film_Count:Q', title='Films'),
                    alt.Tooltip('Percent:Q', title='Share %'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Rating (1-10)'),
                    alt.Tooltip('Top_Directors:N', title='Top Directors')
                ]
            )
            
            text_nat = alt.Chart(top_15_nat).mark_text(
                align='left',
                baseline='middle',
                dx=5,
                color='#EEF2F6',
                fontSize=11,
                fontWeight=600
            ).encode(
                x=alt.X('Film_Count:Q'),
                y=alt.Y('Display:N', sort=top_15_nat['Display'].tolist()),
                text=alt.Text('label:N')
            )
            
            chart_top_nat = (bars_nat + text_nat).properties(height=max(240, len(top_15_nat) * 32))
            st.altair_chart(chart_top_nat, use_container_width=True)
            
        with col_nc2:
            st.markdown(f"##### ⭐ {t('tab_nat_rated_chart')}")
            rated_nat = nat_summary[(nat_summary['Film_Count'] >= 2) & nat_summary['Avg_Rating'].notna()].sort_values(
                by=['Avg_Rating', 'Film_Count'], ascending=[False, False]
            ).head(10).copy()
            
            if not rated_nat.empty:
                rated_nat['label'] = rated_nat.apply(lambda r: f"{r['Avg_Rating']:.1f} ★ ({int(r['Film_Count'])}m)", axis=1)
                
                bars_r_nat = alt.Chart(rated_nat).mark_bar(
                    cornerRadiusTopRight=6,
                    cornerRadiusBottomRight=6,
                    color='#00E054'
                ).encode(
                    x=alt.X('Avg_Rating:Q', title="Avg Rating (0-10 Scale)", scale=alt.Scale(domain=[0, 10.5])),
                    y=alt.Y('Display:N', sort=rated_nat['Display'].tolist(), title=None),
                    tooltip=[
                        alt.Tooltip('Display:N', title='Country'),
                        alt.Tooltip('Avg_Rating:Q', title='Avg Rating (1-10)'),
                        alt.Tooltip('Film_Count:Q', title='Films Watched')
                    ]
                )
                
                text_r_nat = alt.Chart(rated_nat).mark_text(
                    align='left',
                    baseline='middle',
                    dx=5,
                    color='#EEF2F6',
                    fontSize=11,
                    fontWeight=600
                ).encode(
                    x=alt.X('Avg_Rating:Q'),
                    y=alt.Y('Display:N', sort=rated_nat['Display'].tolist()),
                    text=alt.Text('label:N')
                )
                
                chart_rated_nat = (bars_r_nat + text_r_nat).properties(height=max(220, len(rated_nat) * 36))
                st.altair_chart(chart_rated_nat, use_container_width=True)
            else:
                st.info("No countries with at least 2 films and valid ratings found in current filter.")
                
        st.divider()
        
        # Country Deep-Dive
        st.subheader(f"🔍 {t('tab_nat_explorer')}")
        all_countries_list = sorted(nat_summary['Display'].unique())
        selected_nat = st.selectbox(t("tab_nat_select_country"), all_countries_list, index=0, key="select_nat_deep_dive")
        
        if selected_nat:
            nat_row = nat_summary[nat_summary['Display'] == selected_nat].iloc[0]
            nat_films = enriched_nat_df[enriched_nat_df['film_country_display'] == selected_nat]
            
            col_nd1, col_nd2, col_nd3 = st.columns(3)
            with col_nd1:
                st.metric(t("tab_nat_total_logged"), f"{nat_row['Film_Count']}")
            with col_nd2:
                avg_display = f"{nat_row['Avg_Rating']:.2f}" if pd.notna(nat_row['Avg_Rating']) else "N/A"
                st.metric(t("tab_nat_avg_score"), avg_display)
            with col_nd3:
                st.metric(t("tab_nat_directors_list"), str(nat_row['Top_Directors']))
                
            cols_show = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'Letterboxd URI'] if c in nat_films.columns]
            st.dataframe(nat_films[cols_show].sort_values(by='Year', ascending=False), use_container_width=True)
    else:
        st.info("No nationality records found for current filter.")

# ==============================================================================
# TAB 4: OSCARS & PRESTIGIOUS FESTIVALS
# ==============================================================================
with tab_awards:
    st.subheader(f"🏆 {t('tab_aw_title')}")
    st.markdown(f"<p style='color: #9AB;'>{t('tab_aw_subtitle')}</p>", unsafe_allow_html=True)
    
    awards_results = compute_awards_analytics(filtered_df)
    aw_kpis = awards_results['kpis']
    aw_df = awards_results['award_films']
    
    if aw_kpis.get('total_awarded', 0) > 0:
        # KPI row
        col_aw1, col_aw2, col_aw3, col_aw4, col_aw5 = st.columns(5)
        with col_aw1:
            st.metric(t("tab_aw_kpi_total"), f"{aw_kpis['total_awarded']} ({aw_kpis['pct_of_library']}%)")
        with col_aw2:
            st.metric(t("tab_aw_kpi_oscars"), f"{aw_kpis['oscar_count']}")
        with col_aw3:
            st.metric(t("tab_aw_kpi_cannes"), f"{aw_kpis['cannes_count']}")
        with col_aw4:
            st.metric(t("tab_aw_kpi_venice"), f"{aw_kpis['venice_count']}")
        with col_aw5:
            st.metric(t("tab_aw_kpi_agreement"), f"{aw_kpis['agreement_rate']}%")
            
        # Festival comparison banner
        st.markdown(
            f"""
            <div style="background: rgba(255, 128, 0, 0.08); border: 1px solid rgba(255, 128, 0, 0.3); border-radius: 10px; padding: 12px 18px; margin: 12px 0 20px 0; display: flex; justify-content: space-around; flex-wrap: wrap;">
                <div><span style="color: #9AB;">🏆 Oscars Personal Avg:</span> <b style="color: #FF8000; font-size: 1.1rem;">{aw_kpis['avg_oscar_rating']} / 10</b></div>
                <div><span style="color: #9AB;">🌴 Cannes Personal Avg:</span> <b style="color: #00E054; font-size: 1.1rem;">{aw_kpis['avg_cannes_rating']} / 10</b></div>
                <div><span style="color: #9AB;">🦁 Venice Personal Avg:</span> <b style="color: #40BCF4; font-size: 1.1rem;">{aw_kpis['avg_venice_rating']} / 10</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Agreement Matrix: Liked vs Disliked
        st.markdown(f"#### ⚖️ {t('tab_aw_matrix_title')}")
        col_lov, col_dis = st.columns(2)
        
        with col_lov:
            st.markdown(f"##### {t('tab_aw_loved_title')}")
            st.caption(t("tab_aw_loved_desc"))
            agreed_df = awards_results['agreed_films']
            if not agreed_df.empty:
                st.dataframe(agreed_df[['Title', 'Year', 'Your Rating', 'Major Award', 'Festivals']].head(12), use_container_width=True)
            else:
                st.info(t("tab_aw_no_loved"))
                
        with col_dis:
            st.markdown(f"##### {t('tab_aw_overrated_title')}")
            st.caption(t("tab_aw_overrated_desc"))
            disagreed_df = awards_results['disagreed_films']
            if not disagreed_df.empty:
                st.dataframe(disagreed_df[['Title', 'Year', 'Your Rating', 'Major Award', 'Festivals']].head(12), use_container_width=True)
            else:
                st.info(t("tab_aw_no_disliked"))
                
        st.divider()
        
        # Full Awards Catalog with Filter
        st.subheader(f"📋 {t('tab_aw_catalog_title')}")
        fest_filter = st.selectbox(
            t("tab_aw_filter_festival"),
            options=["All", "Oscar", "Cannes", "Venice", "Loved", "Disliked"],
            format_func=lambda x: {
                "All": t("tab_aw_all_festivals"),
                "Oscar": t("tab_aw_only_oscars"),
                "Cannes": t("tab_aw_only_cannes"),
                "Venice": t("tab_aw_only_venice"),
                "Loved": "💚 " + t("tab_aw_loved_title").split(":")[0],
                "Disliked": "💔 " + t("tab_aw_overrated_title").split(":")[0]
            }.get(x, x),
            key="select_awards_festival_filter"
        )
        
        display_aw_df = aw_df.copy()
        if fest_filter == "Oscar":
            display_aw_df = display_aw_df[display_aw_df['Has_Oscar']]
        elif fest_filter == "Cannes":
            display_aw_df = display_aw_df[display_aw_df['Has_Cannes']]
        elif fest_filter == "Venice":
            display_aw_df = display_aw_df[display_aw_df['Has_Venice']]
        elif fest_filter == "Loved":
            display_aw_df = display_aw_df[display_aw_df['Stance'] == "Agreed (Loved) 💚"]
        elif fest_filter == "Disliked":
            display_aw_df = display_aw_df[display_aw_df['Stance'] == "Disagreed (Overrated) 💔"]
            
        catalog_cols = [c for c in ['Title', 'Year', 'Your Rating', 'TMDb Score', 'Directors', 'Major Award', 'Stance'] if c in display_aw_df.columns]
        st.dataframe(display_aw_df[catalog_cols], use_container_width=True, height=420)
    else:
        st.info("No major award winners (Oscar, Cannes, Venice) found in the current filter criteria.")

# ==============================================================================
# TAB 5: DECADES & HISTORY
# ==============================================================================
with tab_decades:
    st.subheader(f"⏳ {t('tab_decades')}")
    
    valid_decades_df = filtered_df[filtered_df['decade_str'] != 'Unknown']
    
    if not valid_decades_df.empty:
        decade_stats = valid_decades_df.groupby('decade_str').agg(
            Count=('Name', 'count'),
            Avg_Rating=('primary_rating_10', 'mean')
        ).reset_index()
        
        decade_stats['decade_num'] = decade_stats['decade_str'].str.replace('s', '').astype(int)
        decade_stats = decade_stats.sort_values(by='decade_num')
        decade_stats['Avg_Rating'] = decade_stats['Avg_Rating'].round(2)
        
        col_dec1, col_dec2 = st.columns([3, 2])
        
        with col_dec1:
            st.markdown(f"##### 🏛️ {t('tab3_decade_dist')}")
            chart_decades = alt.Chart(decade_stats).mark_bar(
                cornerRadiusTopLeft=6,
                cornerRadiusTopRight=6,
                color='#40BCF4'
            ).encode(
                x=alt.X('decade_str:N', sort=None, title="Decade"),
                y=alt.Y('Count:Q', title="Films"),
                tooltip=[
                    alt.Tooltip('decade_str:N', title='Decade'),
                    alt.Tooltip('Count:Q', title='Films'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Rating')
                ]
            ).properties(height=360)
            
            st.altair_chart(chart_decades, use_container_width=True)
            
        with col_dec2:
            st.markdown(f"##### 🌟 {t('tab3_golden_era')}")
            chart_dec_rating = alt.Chart(decade_stats).mark_line(
                point=alt.OverlayMarkDef(color='#00E054', size=80),
                color='#00E054',
                strokeWidth=3
            ).encode(
                x=alt.X('decade_str:N', sort=None, title="Decade"),
                y=alt.Y('Avg_Rating:Q', title="Avg Rating", scale=alt.Scale(domain=[6, 9])),
                tooltip=[
                    alt.Tooltip('decade_str:N', title='Decade'),
                    alt.Tooltip('Avg_Rating:Q', title='Avg Score'),
                    alt.Tooltip('Count:Q', title='Films')
                ]
            ).properties(height=360)
            
            st.altair_chart(chart_dec_rating, use_container_width=True)

        st.divider()

        # Vintage vs Contemporary
        st.subheader(f"🎞️ {t('tab3_vintage_title')}")
        classic_count = len(valid_decades_df[valid_decades_df['Year'] < 1980])
        modern_count = len(valid_decades_df[valid_decades_df['Year'] >= 1980])
        total_valid = classic_count + modern_count
        
        col_ratio1, col_ratio2, col_ratio3 = st.columns(3)
        with col_ratio1:
            pct_classic = (classic_count / total_valid * 100) if total_valid > 0 else 0
            st.metric(t("tab3_vintage_label"), f"{classic_count} films", f"{pct_classic:.1f}%")
        with col_ratio2:
            pct_modern = (modern_count / total_valid * 100) if total_valid > 0 else 0
            st.metric(t("tab3_modern_label"), f"{modern_count} films", f"{pct_modern:.1f}%")
        with col_ratio3:
            gold_decade = decade_stats.sort_values(by='Avg_Rating', ascending=False).iloc[0]
            st.metric("Top Rated Decade", f"{gold_decade['decade_str']}", f"Avg: {gold_decade['Avg_Rating']}")

        st.divider()

        # Extreme Milestones
        st.subheader(f"📍 {t('tab3_milestones')}")
        oldest_movie = valid_decades_df.sort_values(by='Year', ascending=True).iloc[0]
        newest_movie = valid_decades_df.sort_values(by='Year', ascending=False).iloc[0]
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #40BCF4;">
                    <span style="color: #40BCF4; font-size: 0.85rem; font-weight: bold;">{t('tab3_oldest')}</span>
                    <h3 style="margin: 6px 0 2px 0; color: #EEF2F6;">{oldest_movie.get('Name', oldest_movie.get('Title'))} ({int(oldest_movie['Year'])})</h3>
                    <p style="color: #9AB; margin: 0;">
                        Director: <b>{', '.join(oldest_movie['clean_directors']) if oldest_movie['clean_directors'] else 'N/A'}</b><br>
                        Score: <b style="color: #FF8000;">{oldest_movie.get('primary_rating_10', 'N/A')}</b>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with col_m2:
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #00E054;">
                    <span style="color: #00E054; font-size: 0.85rem; font-weight: bold;">{t('tab3_newest')}</span>
                    <h3 style="margin: 6px 0 2px 0; color: #EEF2F6;">{newest_movie.get('Name', newest_movie.get('Title'))} ({int(newest_movie['Year'])})</h3>
                    <p style="color: #9AB; margin: 0;">
                        Director: <b>{', '.join(newest_movie['clean_directors']) if newest_movie['clean_directors'] else 'N/A'}</b><br>
                        Score: <b style="color: #FF8000;">{newest_movie.get('primary_rating_10', 'N/A')}</b>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==============================================================================
# TAB 4: VIEWING HABITS & DIARY
# ==============================================================================
with tab_habits:
    st.subheader(f"📅 {t('tab_habits')}")
    
    valid_dates_df = filtered_df[filtered_df['parsed_date'].notna()]
    
    if not valid_dates_df.empty:
        col_hab1, col_hab2 = st.columns(2)
        
        with col_hab1:
            st.markdown(f"##### 🚀 {t('tab4_yearly_velocity')}")
            yearly_watches = valid_dates_df['watch_year'].value_counts().reset_index()
            yearly_watches.columns = ['Year', 'Films']
            yearly_watches['Year'] = yearly_watches['Year'].astype(str)
            yearly_watches = yearly_watches.sort_values(by='Year')
            
            chart_yearly = alt.Chart(yearly_watches).mark_bar(
                cornerRadiusTopLeft=6,
                cornerRadiusTopRight=6,
                color='#00E054'
            ).encode(
                x=alt.X('Year:N', title="Watch Year"),
                y=alt.Y('Films:Q', title="Films Watched"),
                tooltip=['Year:N', 'Films:Q']
            ).properties(height=300)
            
            st.altair_chart(chart_yearly, use_container_width=True)
            
        with col_hab2:
            st.markdown(f"##### 🍿 {t('tab4_favorite_day')}")
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_counts = valid_dates_df['watch_weekday'].value_counts().reindex(weekday_order).fillna(0).reset_index()
            weekday_counts.columns = ['Day', 'Count']
            
            chart_weekday = alt.Chart(weekday_counts).mark_bar(
                cornerRadiusTopLeft=6,
                cornerRadiusTopRight=6,
                color='#FF8000'
            ).encode(
                x=alt.X('Day:N', sort=None, title="Day of Week"),
                y=alt.Y('Count:Q', title="Films"),
                tooltip=['Day:N', 'Count:Q']
            ).properties(height=300)
            
            st.altair_chart(chart_weekday, use_container_width=True)

        st.divider()

        # Monthly timeline
        st.markdown(f"##### 📈 {t('tab4_monthly_timeline')}")
        monthly_series = valid_dates_df['watch_year_month'].value_counts().reset_index()
        monthly_series.columns = ['Year_Month', 'Films']
        monthly_series = monthly_series.sort_values(by='Year_Month')
        
        chart_timeline = alt.Chart(monthly_series).mark_area(
            color='#40BCF4',
            opacity=0.3,
            line={'color': '#40BCF4', 'strokeWidth': 2}
        ).encode(
            x=alt.X('Year_Month:N', title="Month"),
            y=alt.Y('Films:Q', title="Films"),
            tooltip=['Year_Month:N', 'Films:Q']
        ).properties(height=280)
        
        st.altair_chart(chart_timeline, use_container_width=True)

        # Binge records
        st.markdown(f"##### 🏆 {t('tab4_binge_records')}")
        top_dates = valid_dates_df['Date'].value_counts().head(5).reset_index()
        top_dates.columns = ['Date', 'Films Logged']
        st.dataframe(top_dates, use_container_width=True)

# ==============================================================================
# TAB 5: RATINGS & TASTE AFFINITY (MODEL COMPARISON)
# ==============================================================================
with tab_ratings:
    st.subheader(f"⭐ {t('tab_ratings')}")
    
    valid_scores_df = filtered_df[filtered_df['primary_rating_10'].notna()]
    
    if not valid_scores_df.empty:
        col_r_stat1, col_r_stat2, col_r_stat3, col_r_stat4 = st.columns(4)
        
        with col_r_stat1:
            st.metric("Global Mean (1-10)", f"{valid_scores_df['primary_rating_10'].mean():.2f}")
        with col_r_stat2:
            st.metric("Median Score", f"{valid_scores_df['primary_rating_10'].median():.2f}")
        with col_r_stat3:
            st.metric("Max Score", f"{valid_scores_df['primary_rating_10'].max():.2f}")
        with col_r_stat4:
            st.metric("Std Deviation", f"{valid_scores_df['primary_rating_10'].std():.2f}")
            
        st.divider()
        
        col_hist, col_scatter = st.columns(2)
        
        with col_hist:
            st.markdown(f"##### 📊 {t('tab5_distribution_title')}")
            chart_rating_hist = alt.Chart(valid_scores_df).mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                color='#00E054'
            ).encode(
                x=alt.X('primary_rating_10:Q', bin=alt.Bin(step=0.5), title="Rating (0.5 Bins)"),
                y=alt.Y('count():Q', title="Number of Films"),
                tooltip=[
                    alt.Tooltip('primary_rating_10:Q', bin=alt.Bin(step=0.5), title='Bin'),
                    alt.Tooltip('count():Q', title='Films')
                ]
            ).properties(height=340)
            
            st.altair_chart(chart_rating_hist, use_container_width=True)
            
        with col_scatter:
            st.markdown(f"##### 📉 Release Year vs. Score")
            chart_yr_rating = alt.Chart(valid_scores_df).mark_circle(
                size=60,
                color='#FF8000',
                opacity=0.6
            ).encode(
                x=alt.X('Year:Q', title="Release Year", scale=alt.Scale(zero=False)),
                y=alt.Y('primary_rating_10:Q', title="Score (1-10)", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip('Name:N', title='Film'),
                    alt.Tooltip('Year:Q', title='Year'),
                    alt.Tooltip('primary_rating_10:Q', title='Score')
                ]
            ).properties(height=340)
            
            st.altair_chart(chart_yr_rating, use_container_width=True)

        st.divider()

        # Hall of Fame vs Guilty Pleasures
        col_fame, col_guilty = st.columns(2)
        
        with col_fame:
            st.markdown(f"##### 👑 {t('tab5_hall_of_fame')}")
            top_10_movies = valid_scores_df.sort_values(by='primary_rating_10', ascending=False).head(10)
            top_cols = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'clean_directors'] if c in top_10_movies.columns]
            st.dataframe(top_10_movies[top_cols], use_container_width=True)
            
        with col_guilty:
            st.markdown(f"##### 🍿 {t('tab5_guilty_pleasures')}")
            guilty_movies = valid_scores_df[valid_scores_df['primary_rating_10'] < 6.0].sort_values(by='primary_rating_10', ascending=True).head(10)
            if not guilty_movies.empty:
                g_cols = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'clean_directors'] if c in guilty_movies.columns]
                st.dataframe(guilty_movies[g_cols], use_container_width=True)
            else:
                st.info("No films under 6.0 found in current filter.")

        st.divider()

        # --- TASTE AFFINITY & MODEL COMPARISON SECTION ---
        st.subheader(f"{t('tab5_affinity_title')}")
        st.markdown(f"<p style='color: #9AB;'>{t('tab5_affinity_desc')}</p>", unsafe_allow_html=True)
        
        affinity_results = calculate_taste_affinity(filtered_df)
        
        if affinity_results['has_user_rating']:
            col_af1, col_af2, col_af3, col_af4 = st.columns(4)
            with col_af1:
                st.metric(t("tab5_affinity_tmdb"), f"{affinity_results['correlation_tmdb']}%")
            with col_af2:
                st.metric(t("tab5_affinity_imdb"), f"{affinity_results['correlation_imdb']}%")
            with col_af3:
                st.metric(t("tab5_affinity_rt"), f"{affinity_results['correlation_rt']}%")
            with col_af4:
                st.metric("Contrarian Divergence", f"±{affinity_results['contrarian_score']} pts")
                
            st.markdown(
                f"""
                <div class="lb-card" style="border-left: 4px solid #FF8000; margin: 15px 0;">
                    <b style="color: #FF8000;">{t('tab5_critic_bias')}</b> 
                    <span style="color: #EEF2F6; font-size: 1.05rem; font-weight: 600;">{affinity_results['critic_persona']}</span> 
                    (Average Delta vs Consensus: <b>{affinity_results['delta_mean']:+.2f} pts</b>).
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Contrarian Meter: Hidden Gems & Overrated
            col_gem, col_over = st.columns(2)
            with col_gem:
                st.markdown(f"##### {t('tab5_hidden_gems')}")
                gems = affinity_results['hidden_gems']
                if not gems.empty:
                    gem_cols = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'delta_tmdb'] if c in gems.columns]
                    st.dataframe(gems[gem_cols].head(8), use_container_width=True)
                else:
                    st.info("No extreme hidden gems (films where your score was +1.5 pts above consensus).")
                    
            with col_over:
                st.markdown(f"##### {t('tab5_overrated')}")
                over = affinity_results['overrated']
                if not over.empty:
                    over_cols = [c for c in ['Name', 'Title', 'Year', 'Rating', 'tmdb_rating', 'delta_tmdb'] if c in over.columns]
                    st.dataframe(over[over_cols].head(8), use_container_width=True)
                else:
                    st.info("No extreme overrated films (films where your score was -1.5 pts below consensus).")
                    
        else:
            st.info(
                "💡 **Taste Affinity unlocks when you have rated films.**\n\n"
                "Currently, your dataset doesn't contain enough personal user ratings (e.g. from `ratings.csv` or added via 'Add Movie'). "
                "Add your ratings using the **Add Movie** page to view your live Taste Affinity profile against TMDb, IMDb, and Rotten Tomatoes!"
            )

# ==============================================================================
# TAB 6: EXPLORER & LIVE SEARCH
# ==============================================================================
with tab_search:
    st.subheader(f"🔎 {t('tab_search')}")
    
    search_query = st.text_input(f"🔍 {t('tab6_search_label')}", placeholder=t("tab6_search_placeholder"))
    
    result_df = filtered_df.copy()
    
    if search_query:
        q = search_query.strip().lower()
        def match_row(row):
            title = str(row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "")).lower()
            if q in title:
                return True
            if any(q in d.lower() for d in row['clean_directors']):
                return True
            if any(q in a.lower() for a in row['clean_actors']):
                return True
            if any(q in g.lower() for g in row['clean_genres']):
                return True
            return False

        result_df = result_df[result_df.apply(match_row, axis=1)]
        st.info(f"Found **{len(result_df)}** films matching: *'{search_query}'*")
    
    display_df = pd.DataFrame()
    title_series = result_df['Name'] if 'Name' in result_df.columns else pd.Series(index=result_df.index, dtype=object)
    if 'Title' in result_df.columns:
        title_series = title_series.fillna(result_df['Title'])
    display_df['Title'] = title_series.fillna("Untitled")
    display_df['Year'] = result_df['Year'].fillna(0).astype(int) if 'Year' in result_df.columns else 0
    if has_user_ratings and 'Rating' in result_df.columns:
        display_df['Your Rating'] = result_df['Rating'].apply(lambda r: f"{r} ★" if pd.notna(r) else "-")
    display_df['Physical'] = result_df['physical_copy'].apply(lambda p: "💿 Owned" if p else "—") if 'physical_copy' in result_df.columns else "—"
    display_df['TMDb Score'] = result_df['tmdb_rating'] if 'tmdb_rating' in result_df.columns else "N/A"
    display_df['Director'] = result_df['clean_directors'].apply(lambda l: ", ".join(l) if l else "N/A") if 'clean_directors' in result_df.columns else "N/A"
    display_df['Genres'] = result_df['clean_genres'].apply(lambda l: ", ".join(l) if l else "N/A") if 'clean_genres' in result_df.columns else "N/A"
    display_df['Main Cast'] = result_df['clean_actors'].apply(lambda l: ", ".join(l[:3]) if l else "N/A") if 'clean_actors' in result_df.columns else "N/A"
    if 'Letterboxd URI' in result_df.columns:
        display_df['Letterboxd Link'] = result_df['Letterboxd URI']
        
    st.dataframe(display_df, use_container_width=True, height=450)
    
    csv_data = result_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"💾 {t('tab6_download_btn')}",
        data=csv_data,
        file_name="letterboxd_filtered_statistics.csv",
        mime="text/csv"
    )
