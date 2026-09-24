# services/tmbd_service.py
import requests
import time
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

def fetch_movie_metadata(title, year, api_key=None):
    """
    Search movie by title + year, then retrieve full metadata.
    """
    key = api_key or get_tmdb_api_key()
    if not key:
        return None
        
    search_url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": key,
        "query": title,
        "year": int(year) if year and str(year).isdigit() else None
    }
    
    try:
        res = requests.get(search_url, params=params, timeout=5)
        if res.status_code != 200:
            return None
        data = res.json()
        results = data.get("results", [])
        if not results:
            return None
            
        movie_id = results[0]["id"]
        return fetch_movie_details_by_id(movie_id, key)
    except Exception:
        return None