"""An editorial opening page for the personal cinema journal."""
import html
import pandas as pd
import streamlit as st
from services.translations import t, localized as tr


def safe(value):
    return html.escape(str(value), quote=True)


df = st.session_state.get('enriched_data', pd.DataFrame())
posters = []
if not df.empty and 'poster_path' in df:
    selection = df.sort_values('Rating', ascending=False) if 'Rating' in df else df
    posters = selection['poster_path'].dropna().drop_duplicates().head(3).tolist()
poster_html = ''.join(f'<img src="https://image.tmdb.org/t/p/w500{safe(path)}" alt="{tr("A film from your library", "Un film della tua libreria")}">' for path in posters if str(path).startswith('/'))
headline = tr('Your films.<br>Your <em>universe.</em>', 'I tuoi film.<br>Il tuo <em>universo.</em>')
intro = tr('Every film leaves something behind. Rediscover your favourites, follow your curiosity, and see the shape of your cinematic world.',
           'Ogni film lascia qualcosa. Ritrova i tuoi preferiti, segui la curiosità e scopri il filo che unisce le tue visioni.')
st.markdown(f'<section class="editorial-hero"><div><div class="eyebrow">Letterboxd Enhancer · {tr("Your cinema dashboard", "La tua dashboard di cinema")}</div><h1>{headline}</h1><p>{intro}</p></div><div class="poster-triptych">{poster_html}</div></section>', unsafe_allow_html=True)
if df.empty:
    st.page_link('pages/data_manager.py', label=tr('Begin your journal →', 'Inizia il tuo diario →'))
    st.stop()
ratings = pd.to_numeric(df.get('Rating', pd.Series(dtype=float)), errors='coerce')
owned = int(df['physical_copy'].fillna(False).sum()) if 'physical_copy' in df else 0
runtime = pd.to_numeric(df.get('runtime', pd.Series(dtype=float)), errors='coerce').sum()
cols = st.columns(4)
for col, label, value in zip(cols,
        [tr('FILMS IN YOUR JOURNAL', 'FILM NEL TUO DIARIO'), tr('YOUR AVERAGE RATING', 'IL TUO VOTO MEDIO'),
         tr('HOURS OF CINEMA', 'ORE DI CINEMA'), tr('ON YOUR SHELF', 'NELLA TUA COLLEZIONE')],
        [f'{len(df):,}', f'{ratings.mean():.2f} / 5' if ratings.notna().any() else '—', f'{runtime / 60:,.0f}', owned]):
    col.metric(label, value)
st.markdown(f'<div class="section-heading"><h2>{tr("Your next discovery", "Il prossimo sguardo")}</h2><span>{tr("EXPLORE YOUR CINEMA", "ESPLORA IL TUO CINEMA")}</span></div>', unsafe_allow_html=True)
left, right = st.columns(2, gap='large')
with left:
    st.markdown(f'<div class="feature-story"><span class="number">01 / {tr("THE COLLECTION", "LA COLLEZIONE")}</span><h3>{tr("Films worth keeping.", "Storie da tenere con sé.")}</h3><p>{tr("Your films, your ratings, your shelf. Revisit the collection you have built, one screening at a time.", "I tuoi film, i tuoi voti, la tua collezione. Ritrova le storie che hai raccolto, una visione alla volta.")}</p></div>', unsafe_allow_html=True)
    st.page_link('pages/personal_space.py', label=tr('Explore your collection →', 'Esplora la collezione →'))
with right:
    st.markdown(f'<div class="feature-story"><span class="number">02 / {tr("THE BIGGER PICTURE", "OLTRE LO SCHERMO")}</span><h3>{tr("Find your cinematic signature.", "Scopri la tua firma cinematografica.")}</h3><p>{tr("Directors, genres, places and entire universes. Discover what connects the films you love.", "Registi, generi, luoghi e interi universi. Scopri cosa lega i film che ami, dalle prime visioni alle saghe completate.")}</p></div>', unsafe_allow_html=True)
    st.page_link('pages/more_statistics.py', label=tr('Open Deep Statistics →', 'Apri Deep Statistics →'))
st.markdown(f'<div class="section-heading"><h2>{tr("Recently in your diary", "Di recente nel tuo diario")}</h2><span>{tr("THE LATEST ENTRIES", "LE ULTIME VISIONI")}</span></div>', unsafe_allow_html=True)
recent = df.copy()
if 'Date' in recent:
    recent['_date'] = pd.to_datetime(recent['Date'], errors='coerce')
    recent = recent.sort_values('_date', ascending=False, na_position='last')
recent = recent.head(6)
for col, (_, movie) in zip(st.columns(len(recent)), recent.iterrows()):
    with col:
        path = movie.get('poster_path')
        if pd.notna(path) and str(path).startswith('/'):
            st.image('https://image.tmdb.org/t/p/w300' + str(path), use_container_width=True)
        title = movie.get('Name', movie.get('Title', ''))
        year = movie.get('Year', '')
        rating = movie.get('Rating')
        score = f' · {rating:g} / 5' if pd.notna(rating) else ''
        st.markdown(f'<div class="film-caption">{safe(title)}</div><div class="film-meta">{safe(year)}{safe(score)}</div>', unsafe_allow_html=True)
st.divider()
st.page_link('pages/data_manager.py', label=tr('Keep your journal up to date →', 'Aggiorna il tuo diario →'))
