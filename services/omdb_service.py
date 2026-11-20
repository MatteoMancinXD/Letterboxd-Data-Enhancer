"""Fetch published IMDb and Tomatometer scores through OMDb."""
import re

import pandas as pd
import requests


def fetch_scores(session, film, api_key):
    params = {'apikey': api_key, 'type': 'movie'}
    imdb_id = str(film.get('imdb_id', ''))
    if re.fullmatch(r'tt\d+', imdb_id):
        params['i'] = imdb_id
    else:
        title = film.get('Name') or film.get('Title')
        year = pd.to_numeric(film.get('Year'), errors='coerce')
        if not isinstance(title, str) or not title.strip() or pd.isna(year) or year < 1:
            return {}
        params.update(t=title.strip(), y=int(year))

    response = session.get('https://www.omdbapi.com/', params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if payload.get('Response') != 'True':
        if payload.get('Error', '').casefold().rstrip('.') in {'movie not found', 'series not found', 'incorrect imdb id'}:
            return {}
        raise ValueError('OMDb request rejected')
    if 'i' in params and payload.get('imdbID') != imdb_id:
        return {}
    if 'y' in params and (str(payload.get('Year')) != str(params['y']) or
                         str(payload.get('Title', '')).strip().casefold() != params['t'].casefold()):
        return {}
    result = {}
    imdb = pd.to_numeric(payload.get('imdbRating'), errors='coerce')
    if pd.notna(imdb) and 0 < imdb <= 10:
        result['imdb_rating'] = float(imdb)
    for rating in payload.get('Ratings', []):
        if rating.get('Source') == 'Rotten Tomatoes':
            value = re.fullmatch(r'(\d{1,3})%', rating.get('Value', ''))
            if value and int(value[1]) <= 100:
                result['rt_tomatometer'] = int(value[1])
    return result


def update_scores(library, api_key, batch_size=25):
    updated = library.copy()
    checked = updated.get('omdb_checked', pd.Series(False, index=updated.index)).eq(True)
    rated = updated.get('Rating', pd.Series(index=updated.index, dtype=float)).notna()
    pending = updated.loc[rated & ~checked].head(batch_size)
    processed = found = 0
    failed = False
    with requests.Session() as session:
        for index, film in pending.iterrows():
            try:
                scores = fetch_scores(session, film, api_key)
            except (requests.RequestException, ValueError):
                failed = True
                break
            for column, value in scores.items():
                updated.at[index, column] = value
            updated.at[index, 'omdb_checked'] = True
            processed += 1
            found += bool(scores)
    return updated, processed, found, failed
