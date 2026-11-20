# pages/personal_space.py
import streamlit as st
import pandas as pd
import numpy as np
import os
from services.translations import t, localized as tr
from services.importer_service import save_dataset
from services.awards_service import match_awards_for_film
from services.ratings_service import rating_to_10, series_to_10, rating_from_10, format_rating_10
from services.ui_components import styled_rating_slider



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

st.title(f"{t('ps_title')}")
st.markdown(f"<p class='sub-title' style='text-align: left; margin-bottom: 1.5rem;'>{t('ps_subtitle')}</p>", unsafe_allow_html=True)

# 1. Summary KPIs with Physical Collection
total_count = len(df)
rated_count = int(df['Rating'].notna().sum())
unrated_count = total_count - rated_count
avg_user_rating = float(series_to_10(df['Rating']).dropna().mean()) if rated_count > 0 else 0.0

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
    st.metric(t("ps_kpi_avg"), f"{avg_user_rating:.2f} / 10 ★" if rated_count > 0 else "N/A")
with col5:
    st.metric(f"💿 {t('ps_kpi_physical')}", f"{physical_count} films", f"{physical_pct:.1f}%")

# Percentage Progress Bar Banner for Physical Collection
phys_banner_html = (
    f"<div class='physical-kpi-card'>"
    f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>"
    f"<span style='color: #C79AFF; font-weight: 700; font-size: 0.95rem;'>💿 {t('ps_kpi_physical')}: <b>{physical_count}</b> of <b>{total_count}</b> films</span>"
    f"<b style='color: #00E676; font-size: 1.05rem;'>{physical_pct:.1f}% in Physical Media</b>"
    f"</div>"
    f"<div class='saga-progress-track'>"
    f"<div style='height: 100%; border-radius: 6px; width: {physical_pct}%; background: linear-gradient(90deg, #A855F7 0%, #00E676 100%);'></div>"
    f"</div>"
    f"</div>"
)
st.markdown(phys_banner_html, unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

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

# 2. Interactive Film Rater & Modifier
st.subheader(tr("Film details", "Scheda del film"))

# Selectbox to search and pick any movie from the entire library
film_labels = {}

for idx, row in filtered_table.iterrows():
    name = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
    year = int(row['Year']) if pd.notna(row.get('Year')) and str(row.get('Year')).replace('.0','').isdigit() else "N/A"
    display_label = f"{name} ({year})"
    film_labels[idx] = display_label

FILM_PICKER_KEY = 'personal_space_film'
if 'film' in st.query_params:
    requested_film = st.query_params.pop('film')
    for index in film_labels:
        if str(index) == requested_film:
            st.session_state[FILM_PICKER_KEY] = index
            break
if st.session_state.get(FILM_PICKER_KEY) not in film_labels:
    st.session_state.pop(FILM_PICKER_KEY, None)

col_pick, col_sort = st.columns([3, 1])
with col_pick:
    target_idx = st.selectbox(
        t("ps_select_movie"),
        options=list(film_labels),
        format_func=film_labels.__getitem__,
        index=None,
        key=FILM_PICKER_KEY,
        placeholder=tr("Select a film", "Seleziona un film"),
        help="Search or select a film from the filtered collection"
    )

if target_idx is not None:
    target_row = df.loc[target_idx]

    col_card1, col_card2 = st.columns([1, 2])

    with col_card1:
        poster_path = target_row.get('poster_path')
        if poster_path and pd.notna(poster_path):
            st.image(f"https://image.tmdb.org/t/p/w200{poster_path}", width=180)
        else:
            st.markdown(
                """
                <div style="width: 180px; height: 260px; background: #192231; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: #9AB; font-size: 0.9rem;">No Poster</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_card2:
        m_name = target_row.get('Name') if pd.notna(target_row.get('Name')) else (target_row.get('Title') if pd.notna(target_row.get('Title')) else "Untitled")
        m_year = int(target_row['Year']) if pd.notna(target_row.get('Year')) and str(target_row.get('Year')).replace('.0','').isdigit() else "N/A"
        st.markdown(f"#### {m_name} ({m_year})")

        unavailable = tr('Unavailable', 'Non disponibile')
        for field, label in [('directors', tr('Directed by', 'Regia')), ('actors', tr('Cast', 'Cast'))]:
            credits = target_row.get(field)
            if isinstance(credits, str):
                credits = [credits]
            names = [name.strip() for name in credits if isinstance(name, str) and name.strip()] if isinstance(credits, (list, tuple, np.ndarray)) else []
            st.write(f"**{label}** · {', '.join(names) or unavailable}")

        runtime = pd.to_numeric(target_row.get('runtime'), errors='coerce')
        duration = f'{int(runtime)} min' if pd.notna(runtime) and 0 < runtime < np.inf else unavailable
        st.write(f"**{tr('Runtime', 'Durata')}** · {duration}")

        awards = match_awards_for_film(m_name, m_year, exact_year=True)
        if awards:
            with st.expander(tr('Awards and nominations', 'Premi e candidature')):
                for category, label in [('oscars', 'Oscar'), ('cannes', 'Cannes'), ('venice', tr('Venice', 'Venezia'))]:
                    if awards[category]:
                        st.write(f"**{label}** · {' · '.join(awards[category])}")
                if awards['source_url']:
                    st.markdown(f"[{tr('Official results', 'Risultati ufficiali')}]({awards['source_url']})")
        else:
            st.caption(tr('No awards or nominations recorded for this film in the local catalog.',
                          'Il catalogo locale non riporta premi o candidature per questo film.'))

        # Current status badges
        curr_val = target_row.get('Rating')
        curr_val_10 = rating_to_10(curr_val)
        curr_phys = bool(target_row.get('physical_copy', False))

        status_badges = []
        if pd.notna(curr_val_10):
            status_badges.append(f"<span class='rating-badge'>{format_rating_10(curr_val_10, suffix=' / 10 ★')}</span>")
        else:
            status_badges.append("<span style='color: #FF9B38; font-weight: bold;'>⚠️ Unrated</span>")

        if curr_phys:
            status_badges.append("<span class='physical-badge'>💿 Physical Copy in Collection</span>")

        st.markdown(" ".join(status_badges), unsafe_allow_html=True)
        st.markdown(f"**TMDb Consensus:** ⭐ {target_row.get('tmdb_rating') or 'N/A'} / 10")

        review = target_row.get('Review')
        review = review if isinstance(review, str) else ''
        st.markdown(tr('**Your review**', '**La tua recensione**'))
        if review:
            st.text(review)
        else:
            st.caption(tr('No review yet.', 'Nessuna recensione.'))
        new_review = st.text_area(tr('Write or edit your review', 'Scrivi o modifica la recensione'),
                                  value=review, key=f'review_{target_idx}', height=140)

        # Rating options (integer 1-10 scale)
        rating_slider_options = ["Unrated"] + [f"{i} ★" for i in range(1, 11)]
        curr_int_10 = int(round(curr_val_10)) if pd.notna(curr_val_10) else None
        default_slider_val = f"{curr_int_10} ★" if curr_int_10 in range(1, 11) else "Unrated"

        new_rating_choice = styled_rating_slider(
            tr("Set Your Personal Rating (1–10):", "Imposta il tuo voto personale (1–10):"),
            options=rating_slider_options,
            value=default_slider_val,
            key=f"slider_rate_{target_idx}",
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
            if st.button(tr('Save film details', 'Salva la scheda'), type="primary", use_container_width=True):
                if new_rating_choice == "Unrated":
                    df.at[target_idx, 'Rating'] = np.nan
                else:
                    df.at[target_idx, 'Rating'] = rating_from_10(int(new_rating_choice.replace(" ★", "")))

                df.at[target_idx, 'Review'] = new_review.strip()
                df.at[target_idx, 'physical_copy'] = bool(new_physical_choice)

                # Save to disk and session
                save_dataset(df, ENRICHED_FILE)
                st.session_state['enriched_data'] = df
                st.toast(tr('Film details saved.', 'Scheda salvata.'), icon='🎬')
                st.rerun()

        with col_btn2:
            if pd.notna(curr_val):
                if st.button(f"🗑️ {t('ps_clear_rating_btn')}", use_container_width=True):
                    df.at[target_idx, 'Rating'] = np.nan
                    save_dataset(df, ENRICHED_FILE)
                    st.session_state['enriched_data'] = df
                    st.info(f"{t('ps_rating_cleared')} **{m_name}**.")
                    st.rerun()

st.divider()

# Prepare editable grid
editor_data = pd.DataFrame(index=filtered_table.index)
title_series = filtered_table['Name'] if 'Name' in filtered_table.columns else pd.Series(index=filtered_table.index, dtype=object)
if 'Title' in filtered_table.columns:
    title_series = title_series.fillna(filtered_table['Title'])

editor_data['Title'] = title_series.fillna("Untitled")
editor_data['Year'] = filtered_table['Year'].fillna(0).astype(int) if 'Year' in filtered_table.columns else 0
editor_data['Physical Copy'] = filtered_table['physical_copy'].fillna(False).astype(bool)
editor_data['Your Rating'] = (
    filtered_table['Rating'].apply(lambda r: format_rating_10(rating_to_10(r), suffix=' / 10 ★', unrated='Unrated'))
    if 'Rating' in filtered_table.columns else "Unrated"
)
editor_data['TMDb Score'] = filtered_table['tmdb_rating'] if 'tmdb_rating' in filtered_table.columns else "N/A"
editor_data['Watch Date'] = filtered_table['Date'] if 'Date' in filtered_table.columns else "N/A"
editor_data['Directors'] = filtered_table['directors'].apply(lambda l: ", ".join(l) if hasattr(l, '__iter__') and not isinstance(l, (str, bytes)) else "N/A") if 'directors' in filtered_table.columns else "N/A"

st.caption(tr(f'{len(editor_data)} films. Select a row to open its details above.',
              f'{len(editor_data)} film. Seleziona una riga per aprire la scheda qui sopra.'))
edit_copies = st.toggle(tr('Edit physical copies in the table', 'Modifica le copie fisiche nella tabella'))
column_config = {
    'Physical Copy': st.column_config.CheckboxColumn('💿 Physical', default=False),
    'Year': st.column_config.NumberColumn('Year', format='%d'),
    'TMDb Score': st.column_config.NumberColumn('TMDb', format='%.1f'),
}

if edit_copies:
    edited_result = st.data_editor(
        editor_data, column_config=column_config,
        disabled=[column for column in editor_data if column != 'Physical Copy'],
        use_container_width=True, height=450, key='data_editor_personal_space',
    )
    changed = edited_result['Physical Copy'].ne(df.loc[edited_result.index, 'physical_copy'])
    if changed.any():
        values = edited_result.loc[changed, 'Physical Copy']
        df.loc[values.index, 'physical_copy'] = values
        save_dataset(df, ENRICHED_FILE)
        st.session_state['enriched_data'] = df
        st.toast(tr('Physical copies updated.', 'Copie fisiche aggiornate.'), icon='💿')
        st.rerun()
else:
    table_key = 'personal_space_results'

    def select_film_from_table():
        rows = st.session_state[table_key].selection.rows
        if rows:
            st.session_state[FILM_PICKER_KEY] = editor_data.index[rows[0]]

    st.dataframe(editor_data, column_config=column_config, hide_index=True,
                 use_container_width=True, height=450, key=table_key,
                 selection_mode='single-row', on_select=select_film_from_table)

# CSV Export
csv_data = filtered_table.to_csv(index=False).encode('utf-8')
st.download_button(
    label="💾 Download Current View as CSV",
    data=csv_data,
    file_name="my_personal_letterboxd_ratings.csv",
    mime="text/csv"
)
