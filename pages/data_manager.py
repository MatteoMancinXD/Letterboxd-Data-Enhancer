"""Single entry point for imports, synchronization, inspection and backups."""
import io
import os
import pandas as pd
import streamlit as st
from services.translations import t, localized as tr
from services.tmbd_service import get_tmdb_api_key
from services.importer_service import load_uploaded_files, compute_dataset_diff, apply_dataset_update

ENRICHED_FILE = "data/letterboxd_enriched.parquet"
st.title(f"{t('nav_data_manager')}")
st.caption(tr("Import, synchronize and back up your Letterboxd library.",
              "Importa, sincronizza e salva una copia della tua libreria Letterboxd."))
if 'sync_result' in st.session_state:
    summary = st.session_state.pop('sync_result')
    st.success(tr("Saved: {added} added, {deleted} removed, {ratings_updated} ratings changed.",
                  "Salvato: {added} aggiunti, {deleted} rimossi, {ratings_updated} voti modificati.").format(**summary))
existing = st.session_state.get('enriched_data', pd.DataFrame())
upload_tab, inspect_tab, backup_tab = st.tabs([
    tr("Import & update", "Importa e aggiorna"), tr("Inspect data", "Esplora dati"),
    tr("Export & backup", "Esporta e backup")])

with upload_tab:
    st.write(tr("Upload your Letterboxd ZIP or watched.csv, ratings.csv and diary.csv.",
                "Carica lo ZIP di Letterboxd oppure watched.csv, ratings.csv e diary.csv."))
    generation = st.session_state.get('upload_generation', 0)
    uploads = st.file_uploader(t('importer_upload_label'), type=['zip', 'csv'],
                              accept_multiple_files=True, key=f'library_upload_{generation}')
    incoming = None
    if uploads:
        try:
            incoming, info = load_uploaded_files(uploads)
            mode = info.get('sync_mode', 'partial')
            if mode == 'full':
                st.info(tr("Full watched list: films absent from watched.csv will be removed. ratings.csv defines current ratings, including removed ratings.",
                           "Lista completa: i film assenti da watched.csv saranno rimossi. ratings.csv definisce i voti attuali, inclusi quelli eliminati."))
            else:
                st.info(tr("Partial update: only supplied films and ratings will change. Other films stay in your library.",
                           "Aggiornamento parziale: vengono aggiornati solo i film e i voti forniti. Gli altri film restano nella libreria."))
            st.caption(', '.join(info.get('files_found', [])))
        except Exception as exc:
            st.error(str(exc))
            incoming = None
    if incoming is not None:
        added, deleted, retained = compute_dataset_diff(existing, incoming)
        changes = retained.attrs.get('rating_changes', [])
        cols = st.columns(4)
        for col, label, count in zip(cols,
                [tr("New films", "Nuovi film"), tr("Removed films", "Film rimossi"),
                 tr("Retained films", "Film mantenuti"), tr("Changed ratings", "Voti modificati")],
                [len(added), len(deleted), len(retained), len(changes)]):
            col.metric(label, count)
        if changes:
            with st.expander(tr("Rating changes: before → after", "Voti modificati: prima → dopo"), expanded=True):
                preview = pd.DataFrame(changes).rename(columns={
                    'Name': tr('Film', 'Film'), 'Year': tr('Year', 'Anno'),
                    'Previous rating': tr('Previous rating / 5', 'Voto precedente / 5'),
                    'New rating': tr('New rating / 5', 'Voto attuale / 5')})
                st.dataframe(preview, hide_index=True, use_container_width=True)
                st.caption(tr("An empty value means unrated.", "Un valore vuoto indica un voto assente."))
        for label, frame in [(tr("Films to add", "Film da aggiungere"), added),
                             (tr("Films to remove", "Film da rimuovere"), deleted)]:
            if not frame.empty:
                with st.expander(label):
                    st.dataframe(frame[[c for c in ['Name', 'Year', 'Rating'] if c in frame]], hide_index=True)
        if not len(added) and not len(deleted) and not changes:
            st.info(tr("No film or rating changes. Synchronizing still applies supplied dates.",
                       "Nessuna modifica a film o voti. La sincronizzazione applica comunque le date fornite."))
        api_key = get_tmdb_api_key()
        if len(added) and not api_key:
            st.warning(tr("Configure your TMDb key in Settings to enrich new films.",
                          "Configura la chiave TMDb nelle Impostazioni per arricchire i nuovi film."))
            st.page_link('pages/settings.py', label=t('nav_settings'), icon='🔧')
        if st.button(t('sync_btn_start'), type='primary', disabled=bool(len(added) and not api_key)):
            progress = st.progress(0.0)
            status = st.empty()
            try:
                updated, summary = apply_dataset_update(existing, incoming, api_key,
                    parquet_path=ENRICHED_FILE, progress_callback=progress.progress,
                    status_callback=status.text)
            except Exception as exc:
                st.error(tr("Could not save the update: ", "Impossibile salvare l’aggiornamento: ") + str(exc))
            else:
                st.session_state['enriched_data'] = updated
                st.session_state['data_loaded'] = True
                st.session_state['sync_result'] = summary
                st.session_state['upload_generation'] = generation + 1
                st.rerun()
    elif not uploads:
        st.info(tr("Your library is ready for a new export.", "La libreria è pronta per un nuovo export."))

with inspect_tab:
    if existing.empty:
        st.info(t('no_data_warning'))
    else:
        st.caption(tr("Technical view of the saved dataset. Browse films in Personal Movie Space.",
                      "Vista tecnica dei dati salvati. Per consultare i film usa lo Spazio personale."))
        st.dataframe(existing, hide_index=True, use_container_width=True)

with backup_tab:
    if not existing.empty:
        buffer = io.BytesIO()
        export = existing.copy()
        export.attrs = {}
        export.to_parquet(buffer, index=False)
        st.download_button(t('db_download_parquet'), buffer.getvalue(),
                           file_name='letterboxd_enriched_backup.parquet', mime='application/octet-stream')
        st.download_button(t('db_download_csv'), export.to_csv(index=False).encode('utf-8'),
                           file_name='letterboxd_enriched_backup.csv', mime='text/csv')
    if os.path.exists(ENRICHED_FILE):
        st.caption(tr("Saved database size: ", "Dimensione archivio salvato: ") +
                   f"{os.path.getsize(ENRICHED_FILE) / 1024:.1f} KB")
        if st.button(tr("Reload saved data", "Ricarica dati salvati")):
            st.session_state['enriched_data'] = pd.read_parquet(ENRICHED_FILE)
            st.session_state['data_loaded'] = True
            st.rerun()
