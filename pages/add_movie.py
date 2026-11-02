"""Search TMDb and add a film through an immediately visible dialog."""
import datetime
import inspect
import re
import pandas as pd
import streamlit as st
from services.tmbd_service import search_movies, fetch_movie_details_by_id, get_tmdb_api_key
from services.importer_service import save_dataset
from services.translations import t, localized as tr

ENRICHED_FILE = 'data/letterboxd_enriched.parquet'
st.title(t('add_movie_title'))
st.caption(tr('Search for a film, then click its cover to add it to your diary.',
              'Cerca un film, poi clicca sulla copertina per aggiungerlo al diario.'))
if 'movie_saved_notice' in st.session_state:
    st.success(st.session_state.pop('movie_saved_notice'), icon='🎬')

def close_movie_dialog():
    st.session_state.pop('movie_dialog_selection', None)


dialog_options = {'on_dismiss': close_movie_dialog} if 'on_dismiss' in inspect.signature(st.dialog).parameters else {}


@st.dialog(tr('Add to your diary', 'Aggiungi al diario'), width='large', **dialog_options)
def movie_dialog(selected):
    st.subheader(f"{selected['title']} ({selected.get('year') or '—'})")
    with st.form(f"movie_entry_{selected['tmdb_id']}"):
        left, right = st.columns([1, 2])
        with left:
            if selected.get('poster_url'):
                st.image(selected['poster_url'], width=160)
            st.caption(', '.join(selected.get('directors', [])))
        with right:
            rating = st.select_slider(t('add_user_rating_label'), options=[0.0] + [i / 2 for i in range(1, 11)],
                value=4.0, format_func=lambda v: '—' if v == 0 else f'{v:g} ★')
            watched = st.date_input(t('add_watch_date_label'), value=datetime.date.today())
            physical = st.checkbox(t('add_physical_checkbox'), value=False)
            submitted = st.form_submit_button(t('add_save_button'), type='primary', use_container_width=True)
        if submitted:
            record = {key: selected.get(key) for key in ('tmdb_id', 'collection_id', 'genres', 'directors',
                'actors', 'tmdb_rating', 'runtime', 'poster_path', 'overview', 'production_countries')}
            record.update(Name=selected['title'], Year=selected.get('year'), Rating=rating or None,
                Date=watched.isoformat(), physical_copy=physical,
                **{'Letterboxd URI': f"https://boxd.it/tmdb-{selected['tmdb_id']}"})
            current = st.session_state.get('enriched_data', pd.DataFrame()).copy()
            # Repeated submissions update the film, preserving its official URI and ownership.
            ids = pd.to_numeric(current.get('tmdb_id', pd.Series(index=current.index, dtype=float)), errors='coerce')
            names = current.get('Name', pd.Series(index=current.index, dtype=str)).fillna('').str.casefold()
            years = pd.to_numeric(current.get('Year', pd.Series(index=current.index, dtype=float)), errors='coerce')
            match = (ids == selected['tmdb_id']) | ((names == selected['title'].casefold()) & (years == selected.get('year')))
            if match.any():
                index = current.index[match][0]
                old = current.loc[index].to_dict()
                record['Letterboxd URI'] = old.get('Letterboxd URI') or record['Letterboxd URI']
                record['physical_copy'] = physical or (pd.notna(old.get('physical_copy')) and bool(old.get('physical_copy')))
                old.update(record)
                records = current.to_dict('records')
                records[current.index.get_loc(index)] = old
                updated = pd.DataFrame(records)
            else:
                updated = pd.concat([current, pd.DataFrame([record])], ignore_index=True)
            try:
                save_dataset(updated, ENRICHED_FILE)
            except Exception as exc:
                st.error(tr('Could not save: ', 'Salvataggio non riuscito: ') + str(exc))
            else:
                st.session_state['enriched_data'] = updated
                st.session_state['data_loaded'] = True
                st.session_state['movie_saved_notice'] = tr('In your diary: ', 'Nel tuo diario: ') + selected['title'] + (f' · {rating:g} ★' if rating else '')
                close_movie_dialog()
                st.rerun()

if not get_tmdb_api_key():
    st.info(tr('Configure a TMDb API key in Settings to search.', 'Configura una chiave TMDb nelle Impostazioni per cercare.'))
    st.page_link('pages/settings.py', label=t('nav_settings'))
with st.form('movie_search'):
    left, right = st.columns([3, 1])
    query = left.text_input(t('add_search_label'), placeholder=t('add_search_placeholder'))
    year = right.text_input(t('add_year_label'), placeholder='2024')
    search = st.form_submit_button(t('add_search_button'), type='primary')
if search:
    if not query.strip():
        st.warning(tr('Enter a film title.', 'Inserisci il titolo di un film.'))
    elif not get_tmdb_api_key():
        st.warning(tr('A TMDb key is required.', 'È necessaria una chiave TMDb.'))
    else:
        with st.spinner(t('add_searching')):
            st.session_state['search_results'] = search_movies(query.strip(), year=year.strip() or None)
        if not st.session_state['search_results']:
            st.info(t('add_no_results'))
results = st.session_state.get('search_results', [])
if results:
    cols = st.columns(4)
    for index, movie in enumerate(results):
        with cols[index % 4]:
            title = re.sub(r'[\\\[\]!*_`<>]', '', movie['title'])
            label = f"![{title}]({movie['poster_url']})" if movie.get('poster_url') else title
            if st.button(label, key=f"movie_cover_{movie['id']}", help=f"{movie['title']} ({movie['year']})", use_container_width=True):
                with st.spinner(tr('Loading film…', 'Caricamento film…')):
                    details = fetch_movie_details_by_id(movie['id'])
                if details:
                    st.session_state['movie_dialog_selection'] = details
                else:
                    st.error(tr('Film details unavailable. Please retry.', 'Dettagli non disponibili. Riprova.'))
            st.write(movie['title'])
            st.caption(f"{movie['year']} · TMDb {movie.get('tmdb_rating') or '—'} / 10")

if st.session_state.get('movie_dialog_selection'):
    movie_dialog(st.session_state['movie_dialog_selection'])
    if not dialog_options:
        close_movie_dialog()
