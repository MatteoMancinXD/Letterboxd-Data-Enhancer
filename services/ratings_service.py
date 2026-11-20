# services/ratings_service.py
import pandas as pd
import numpy as np


def rating_to_10(value):
    """Convert a stored Letterboxd 0.5–5.0 rating to the 1–10 scale."""
    num = pd.to_numeric(value, errors='coerce')
    if pd.isna(num):
        return np.nan
    return float(num) * 2.0


def series_to_10(series):
    """Convert a Series of stored Letterboxd 0.5–5.0 ratings to the 1–10 scale."""
    return pd.to_numeric(series, errors='coerce') * 2.0


def rating_from_10(value):
    """Convert a 1–10 UI rating back to canonical stored 0.5–5.0 Letterboxd scale."""
    num = pd.to_numeric(value, errors='coerce')
    if pd.isna(num) or float(num) <= 0:
        return np.nan
    return float(num) / 2.0


def format_rating_10(value, suffix=' / 10 ★', unrated='—'):
    """Format a 1–10 rating (clean integer for whole numbers, concise float otherwise)."""
    num = pd.to_numeric(value, errors='coerce')
    if pd.isna(num):
        return unrated
    num = float(num)
    if num.is_integer():
        return f"{int(num)}{suffix}"
    return f"{num:g}{suffix}"


def calculate_taste_affinity(df):
    """Compare personal ratings against scores available for each source."""
    data = df.copy()
    data['score_user'] = series_to_10(data.get('Rating', pd.Series(index=data.index, dtype=float)))
    correlations = {}
    coverage = {}
    for source, column, maximum in [('tmdb', 'tmdb_rating', 10),
                                     ('imdb', 'imdb_rating', 10), ('rt', 'rt_tomatometer', 100)]:
        scores = pd.to_numeric(data.get(column, pd.Series(index=data.index, dtype=float)), errors='coerce')
        minimum = 0 if source == 'rt' else 0.01
        data[f'score_{source}'] = scores.where(scores.between(minimum, maximum)) * (10 / maximum)
        pairs = data[['score_user', f'score_{source}']].dropna()
        coverage[source] = len(pairs)
        correlation = pairs.iloc[:, 0].corr(pairs.iloc[:, 1]) if len(pairs) >= 3 and pairs.nunique().min() > 1 else np.nan
        correlations[f'correlation_{source}'] = round(float(correlation), 2) if pd.notna(correlation) else None
    rated_df = data.dropna(subset=['score_user', 'score_tmdb']).copy()

    # Divergence
    rated_df = rated_df.copy()
    rated_df['delta_tmdb'] = (rated_df['score_user'] - rated_df['score_tmdb']).round(2)
    contrarian_score = round(float(rated_df['delta_tmdb'].abs().mean()), 2) if len(rated_df) >= 3 else None
    delta_mean = round(float(rated_df['delta_tmdb'].mean()), 2) if len(rated_df) >= 3 else 0.0

    # Hidden Gems: films rated significantly higher by user than TMDb (delta >= 1.5)
    hidden_gems = rated_df[rated_df['delta_tmdb'] >= 1.5].sort_values(by='delta_tmdb', ascending=False)
    
    # Overrated: films rated significantly lower by user than TMDb (delta <= -1.5)
    overrated = rated_df[rated_df['delta_tmdb'] <= -1.5].sort_values(by='delta_tmdb', ascending=True)

    # Persona
    if delta_mean > 0.4:
        persona = "Generous Cinephile (+)"
    elif delta_mean < -0.4:
        persona = "Tough Critic (-)"
    else:
        persona = "Balanced Enthusiast (=)"

    return {
        "has_user_rating": data['score_user'].notna().any(),
        "rated_count": len(rated_df),
        "total_count": len(data),
        **correlations,
        "coverage": coverage,
        "contrarian_score": contrarian_score,
        "hidden_gems": hidden_gems,
        "overrated": overrated,
        "critic_persona": persona,
        "delta_mean": delta_mean,
        "df_comparison": rated_df
    }
