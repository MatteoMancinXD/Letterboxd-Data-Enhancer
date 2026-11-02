"""Saga rankings, transparent coverage and refreshable film catalogs."""
import pandas as pd
import streamlit as st
from services.tmbd_service import search_movies, get_tmdb_api_key
from services.translations import t, localized as tr
from services.sagas_service import compute_sagas_progress, scan_and_cache_tmdb_collections, refresh_curated_saga, add_film_to_curated_saga

def render_sagas():
    st.subheader(f"🪐 {t('sagas_title')}")
    st.caption(tr("Compare ratings, follow your progress and discover the next chapter.",
                  "Confronta i voti, segui i tuoi progressi e scopri il prossimo capitolo."))
    df = st.session_state.get('enriched_data', pd.DataFrame())
    if df.empty:
        st.info(t('no_data_warning'))
        st.page_link('pages/data_manager.py', label=t('nav_data_manager'), icon='⚙️')
        return
    if 'saga_refresh_result' in st.session_state:
        st.info(st.session_state.pop('saga_refresh_result'))
    data = compute_sagas_progress(df)
    all_sagas = data['started_sagas'] + data['completed_sagas'] + data['unstarted_sagas']
    kpis = data['kpis']
    cols = st.columns(4)
    for col, label, value in zip(cols,
            [t('sagas_kpi_tracked'), t('sagas_kpi_completed'), t('sagas_kpi_franchise_films'),
             tr('Physical films in sagas', 'Film delle saghe posseduti')],
            [len(all_sagas), kpis['completed_count'], kpis['total_franchise_films_watched'], kpis['total_physical_films']]):
        col.metric(label, value)
    st.caption(tr("Film totals count each film once, even when it belongs to several sagas.",
                  "I totali contano ogni film una sola volta, anche se appartiene a più saghe."))

    with st.expander(tr('Update saga information', 'Aggiorna informazioni sulle saghe')):
        st.write(tr("Scan the entire library to discover collections and refresh their films, ratings and release dates. Existing cached data remains available if requests fail.",
                    "Scansiona tutta la libreria per scoprire collezioni e aggiornarne film, voti e date di uscita. Se una richiesta fallisce, i dati già salvati restano disponibili."))
        if st.button(tr('Discover / refresh TMDb collections', 'Scopri / aggiorna collezioni TMDb')):
            progress = st.progress(0.0)
            try:
                report = scan_and_cache_tmdb_collections(df, progress_callback=lambda n, total: progress.progress(n / total))
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state['saga_refresh_result'] = tr(
                    "Scanned {scanned} films: {new} new collections, {refreshed} refreshed, {failed} failed requests, {unmatched} uncertain matches.",
                    "Esaminati {scanned} film: {new} nuove collezioni, {refreshed} aggiornate, {failed} richieste fallite, {unmatched} abbinamenti incerti.").format(**report)
                st.rerun()
        st.caption(tr("Universes use a curated film list. Their known films can be refreshed in the detail panel below; TMDb collections are not a complete universe catalog.",
                      "Gli universi usano una lista curata. Puoi aggiornare i dati dei film noti nel dettaglio qui sotto; le collezioni TMDb non sono un catalogo completo degli universi."))

    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input(tr('Search saga or film', 'Cerca saga o film'))
    category = c2.selectbox(tr('Type', 'Tipo'), ['all', 'universe', 'saga', 'thematic'],
        format_func=lambda v, labels={'all': tr('All', 'Tutti'), 'universe': tr('Universes', 'Universi'), 'saga': tr('Sagas', 'Saghe'), 'thematic': tr('Thematic cycles', 'Cicli tematici')}: labels[v])
    status = c3.selectbox(tr('Progress', 'Stato'), ['all', 'started', 'complete', 'unstarted'],
        format_func=lambda v, labels={'all': tr('All', 'Tutti'), 'started': tr('In progress', 'In corso'),
                               'complete': tr('Completed', 'Completate'), 'unstarted': tr('Not started', 'Non iniziate')}: labels[v])
    c1, c2, c3 = st.columns([2, 1, 1])
    order = c1.selectbox(tr('Sort by', 'Ordina per'), ['personal', 'tmdb', 'progress', 'remaining', 'gap', 'name'],
        format_func=lambda v, labels={'personal': tr('Your highest ratings', 'Meglio votate da te'),
            'tmdb': tr('Highest TMDb ratings', 'Meglio votate da TMDb'), 'progress': tr('Most complete', 'Più completate'),
            'remaining': tr('Fewest films remaining', 'Meno film mancanti'),
            'gap': tr('You rate higher than TMDb', 'Preferite da te rispetto a TMDb'), 'name': tr('Name A–Z', 'Nome A–Z')}: labels[v])
    min_personal = c2.number_input(tr('Minimum personal ratings', 'Minimo voti personali'), min_value=0, value=0, step=1)
    min_tmdb = c3.number_input(tr('Minimum TMDb-rated films', 'Minimo film con voto TMDb'), min_value=0, value=0, step=1)
    filtered = [s for s in all_sagas
        if (category == 'all' or s['category'] == category)
        and (not query.strip() or query.casefold() in s['name'].casefold() or any(query.casefold() in f['title'].casefold() for f in s['all_films']))
        and (status == 'all' or (status == 'complete' and s['is_complete'])
             or (status == 'started' and s['watched_count'] and not s['is_complete'])
             or (status == 'unstarted' and not s['watched_count']))
        and s['ratings_count'] >= min_personal and s['tmdb_ratings_count'] >= min_tmdb]
    def sort_key(s):
        if order == 'name':
            return s['name'].casefold(),
        if order == 'remaining':
            return s['remaining_count'], -s['progress_pct'], s['name']
        field = {'personal': 'avg_user_rating', 'tmdb': 'avg_tmdb_rating', 'progress': 'progress_pct', 'gap': 'taste_gap'}[order]
        value = s[field]
        return value is None, -(value or 0), -s['ratings_count'], s['name']
    filtered.sort(key=sort_key)
    st.caption(tr("Personal mean: rated watched films. TMDb mean: released films with available scores, including unwatched films. Both are simple film averages. The gap compares only films rated by both (your score × 2 − TMDb). Missing ratings are excluded.",
                  "Media personale: film visti e votati. Media TMDb: film usciti con voto disponibile, anche non visti. Sono medie semplici per film. Lo scarto confronta solo film votati da entrambi (tuo voto × 2 − TMDb). I voti mancanti sono esclusi."))
    if not filtered:
        st.info(tr('No sagas match these filters.', 'Nessuna saga corrisponde ai filtri.'))
        return
    rows = [{tr('Saga / universe', 'Saga / universo'): s['name'],
             tr('Your mean / 5', 'Media tua / 5'): s['avg_user_rating'],
             tr('Your rated films', 'Film votati da te'): s['ratings_count'],
             'TMDb / 10': s['avg_tmdb_rating'],
             tr('TMDb coverage', 'Copertura TMDb'): f"{s['tmdb_ratings_count']}/{s['released_films']}",
             tr('Progress %', 'Completamento %'): s['progress_pct'],
             tr('Released films remaining', 'Film usciti mancanti'): s['remaining_count'],
             tr('Rating gap / 10', 'Scarto voti / 10'): s['taste_gap']} for s in filtered]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    selected_id = st.selectbox(tr('Explore a saga', 'Esplora una saga'), [s['id'] for s in filtered],
                             format_func=lambda value: next(s['name'] for s in filtered if s['id'] == value))
    saga = next(s for s in filtered if s['id'] == selected_id)
    st.subheader(saga['name'])
    if saga.get('description'):
        st.write(saga['description'])
    st.progress(saga['progress_pct'] / 100)
    st.write(tr('{watched_count} watched · {remaining_count} released films remaining · {upcoming_count} upcoming · {unknown_release_count} release dates to verify',
                '{watched_count} visti · {remaining_count} film usciti mancanti · {upcoming_count} in arrivo · {unknown_release_count} uscite da verificare').format(**saga))
    source = tr('TMDb collection', 'Collezione TMDb') if saga.get('source') == 'tmdb' else tr('Curated list', 'Lista curata')
    st.caption(source + ' · ' + tr('Last metadata refresh: ', 'Ultimo aggiornamento metadati: ') + (saga.get('updated_at') or tr('not yet refreshed', 'non ancora aggiornati')))
    if saga['unknown_release_count']:
        st.warning(tr('Completion refers only to known released films. Verify unknown release dates by refreshing metadata.',
                      'Il completamento considera solo i film con uscita nota. Aggiorna i metadati per verificare le uscite incerte.'))
    if saga.get('source') == 'curated':
        if st.button(tr('Refresh known films in this saga', 'Aggiorna i film noti di questa saga')):
            progress = st.progress(0.0)
            try:
                report = refresh_curated_saga(saga['id'], lambda n, total: progress.progress(n / total))
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state['saga_refresh_result'] = tr('Updated {updated} films; {failed} could not be matched/refreshed.',
                    'Aggiornati {updated} film; {failed} non abbinati/aggiornati.').format(**report)
                st.rerun()
        with st.expander(tr('Add a missing film to this saga / universe', 'Aggiungi un film mancante a questa saga / universo')):
            st.caption(tr('Choose the film from TMDb. This updates the saga catalog; it does not mark the film as watched.',
                          'Scegli il film da TMDb. Questa azione aggiorna il catalogo della saga e non segna il film come visto.'))
            search = st.text_input(tr('Film title on TMDb', 'Titolo del film su TMDb'), key=f"saga_search_{saga['id']}")
            if st.button(tr('Search TMDb', 'Cerca su TMDb')):
                if not get_tmdb_api_key():
                    st.warning(tr('Configure your TMDb key in Settings.', 'Configura la chiave TMDb nelle Impostazioni.'))
                else:
                    st.session_state[f"saga_matches_{saga['id']}"] = search_movies(search)
            matches = st.session_state.get(f"saga_matches_{saga['id']}")
            if matches == []:
                st.info(tr('No results. Try another title.', 'Nessun risultato. Prova un altro titolo.'))
            if matches:
                movie_id = st.selectbox(tr('Select the film', 'Seleziona il film'), [m['id'] for m in matches],
                    format_func=lambda value: next(f"{m['title']} ({m['year']})" for m in matches if m['id'] == value))
                phase = st.text_input(tr('Phase / chapter (optional)', 'Fase / capitolo (facoltativo)'))
                if st.button(tr('Add to saga catalog', 'Aggiungi al catalogo della saga')):
                    try:
                        added = add_film_to_curated_saga(saga['id'], movie_id, phase)
                    except Exception as exc:
                        st.error(str(exc))
                    else:
                        st.session_state['saga_refresh_result'] = (tr('Film added to saga.', 'Film aggiunto alla saga.') if added
                            else tr('This film is already in the saga.', 'Il film è già presente nella saga.'))
                        st.rerun()
    film_rows = []
    for film in saga['all_films']:
        film_rows.append({tr('Film', 'Film'): film['title'], tr('Year', 'Anno'): film.get('year'),
            tr('Chapter / phase', 'Capitolo / fase'): film.get('phase', ''),
            tr('Watched', 'Visto'): film['watched'], tr('Your rating / 5', 'Tuo voto / 5'): film['user_rating'],
            'TMDb / 10': film.get('tmdb_rating'), tr('Release', 'Uscita'): film.get('release_date') or '—',
            tr('Status', 'Stato'): {'released': tr('Released', 'Uscito'), 'upcoming': tr('Upcoming', 'In arrivo'),
                                   'unknown': tr('To verify', 'Da verificare')}[film['release_state']],
            tr('Owned', 'Posseduto'): film['has_physical']})
    st.dataframe(pd.DataFrame(film_rows), hide_index=True, use_container_width=True)
    next_films = [f for f in saga['all_films'] if not f['watched'] and f['release_state'] == 'released'][:5]
    if next_films:
        st.write(tr('Next films in release order', 'Prossimi film in ordine di uscita'))
        for col, film in zip(st.columns(len(next_films)), next_films):
            if film.get('poster_path'):
                col.image('https://image.tmdb.org/t/p/w300' + film['poster_path'], use_container_width=True)
            col.caption(f"{film['title']} ({film.get('year') or '—'})")
