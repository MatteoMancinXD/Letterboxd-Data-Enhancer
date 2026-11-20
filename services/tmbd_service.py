# services/tmbd_service.py
import requests
import re
import unicodedata
import os
import streamlit as st

BASE_URL = "https://api.themoviedb.org/3"

def get_tmdb_api_key():
    """
    Retrieves the TMDb API key with priority:
    1. Streamlit secrets (.streamlit/secrets.toml)
    2. Environment variables (TMDB_API_KEY)
    3. Session state (st.session_state['tmdb_api_key'])
    """
    try:
        if hasattr(st, "secrets") and "TMDB_API_KEY" in st.secrets and st.secrets["TMDB_API_KEY"]:
            val = str(st.secrets["TMDB_API_KEY"]).strip()
            if val:
                return val
    except Exception:
        pass
        
    env_key = os.environ.get("TMDB_API_KEY")
    if env_key:
        return env_key.strip()
        
    return st.session_state.get("tmdb_api_key", "").strip()

def search_movies(query, api_key=None, year=None):
    """
    Search TMDb for movies matching the query.
    Returns a list of dicts with basic metadata: id, title, release_date, poster_path, overview.
    """
    if not query:
        return []
    
    key = api_key or get_tmdb_api_key()
    if not key:
        return []
        
    search_url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": key,
        "query": query,
        "language": "en-US"
    }
    if year and str(year).isdigit():
        params["year"] = int(year)
        
    try:
        res = requests.get(search_url, params=params, timeout=6)
        if res.status_code != 200:
            return []
        data = res.json()
        results = data.get("results", [])
        formatted = []
        for r in results[:10]:
            rel_date = r.get("release_date", "")
            yr = rel_date.split("-")[0] if rel_date and "-" in rel_date else "N/A"
            poster = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get("poster_path") else None
            formatted.append({
                "id": r.get("id"),
                "title": r.get("title") or r.get("original_title"),
                "year": yr,
                "release_date": rel_date,
                "poster_url": poster,
                "poster_path": r.get("poster_path"),
                "overview": r.get("overview", ""),
                "tmdb_rating": r.get("vote_average"),
                "vote_count": r.get("vote_count", 0)
            })
        return formatted
    except Exception:
        return []

def fetch_movie_details_by_id(movie_id, api_key=None):
    """
    Retrieve full details, credits, and external_ids for a specific movie ID.
    """
    key = api_key or get_tmdb_api_key()
    if not key:
        return None
        
    details_url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": key,
        "append_to_response": "credits,external_ids"
    }
    
    try:
        res = requests.get(details_url, params=params, timeout=6)
        if res.status_code != 200:
            return None
        movie_details = res.json()
        
        genres = [g["name"] for g in movie_details.get("genres", [])]
        
        crew = movie_details.get("credits", {}).get("crew", [])
        directors = [m["name"] for m in crew if m.get("job") == "Director"]
        
        cast = movie_details.get("credits", {}).get("cast", [])
        top_actors = [actor["name"] for actor in cast[:5]]
        
        external_ids = movie_details.get("external_ids", {})
        imdb_id = external_ids.get("imdb_id")
        
        tmdb_vote = movie_details.get("vote_average", None)
        runtime = movie_details.get("runtime", None)
        poster_path = movie_details.get("poster_path", None)
        poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else None
        overview = movie_details.get("overview", "")
        countries = [c.get("name") for c in movie_details.get("production_countries", [])]
        rel_date = movie_details.get("release_date", "")
        yr = int(rel_date.split("-")[0]) if rel_date and "-" in rel_date and rel_date.split("-")[0].isdigit() else None
        
        return {
            "tmdb_id": movie_id,
            "release_date": rel_date,
            "vote_count": movie_details.get("vote_count"),
            "collection_id": (movie_details.get("belongs_to_collection") or {}).get("id"),
            "title": movie_details.get("title") or movie_details.get("original_title"),
            "year": yr,
            "genres": genres,
            "directors": directors,
            "actors": top_actors,
            "tmdb_rating": tmdb_vote,
            "runtime": runtime,
            "poster_path": poster_path,
            "poster_url": poster_url,
            "overview": overview,
            "imdb_id": imdb_id,
            "production_countries": countries
        }
    except Exception:
        return None

def _title_key(title):
    text = unicodedata.normalize('NFKC', str(title or '')).casefold()
    return ' '.join(re.findall(r'[^\W_]+', text))


def _release_year(value):
    match = re.fullmatch(r'([1-9]\d{3})(?:\.0+)?', str(value).strip())
    return int(match[1]) if match else None


def fetch_movie_metadata(title, year, api_key=None):
    """Enrich a title only when TMDb yields an unambiguous title/year match."""
    key = api_key or get_tmdb_api_key()
    title_key = _title_key(title)
    if not key or not title_key:
        return None

    expected_year = _release_year(year)
    params = {'api_key': key, 'query': title, 'year': expected_year}
    try:
        response = requests.get(f'{BASE_URL}/search/movie', params=params, timeout=5)
        if response.status_code != 200:
            return None
        matches = {}
        for candidate in response.json().get('results', []):
            titles = {_title_key(candidate.get('title')), _title_key(candidate.get('original_title'))}
            release_year = _release_year((candidate.get('release_date') or '')[:4])
            if (candidate.get('id') is not None and title_key in titles
                    and (expected_year is None or release_year == expected_year)):
                matches[candidate['id']] = release_year
        if len(matches) != 1:
            return None
        movie_id, release_year = next(iter(matches.items()))
        details = fetch_movie_details_by_id(movie_id, key)
        if details and (release_year is None or details.get('year') == release_year):
            return details
    except (requests.RequestException, ValueError):
        pass
    return None
