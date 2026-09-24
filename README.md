# 🎬 Letterboxd Enhancer & Cinema Analytics

An advanced, interactive analytics dashboard and companion app for **Letterboxd** users, powered by **Streamlit**, **Pandas**, and **The Movie Database (TMDb) API**.


Transform your Letterboxd diary and watchlist into rich visual insights, track completed film sagas, and manage your physical media collection.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🚀 **Try the Live App:** [Open Letterboxd Enhancer on Streamlit Cloud](https://share.streamlit.io) *(no local installation required)*

---

## ✨ Features

- 📊 **Rich Overview & Deep Analytics**: Visual breakdowns of your viewing history, top directors, actor networks, favorite genres, decades, and release year trends.
- 🌌 **Film Sagas & Cinematic Universes**:
  - Live progress tracking for over 33+ iconic movie sagas and mega-franchises (Marvel Cinematic Universe, Star Wars Canon, Middle-earth, Harry Potter & Wizarding World, DC Extended Universe, Batman, James Bond, Fast & Furious, Alien, etc.).
  - Automatic completed saga detection with badges, progress bars, and poster gallery.
  - Integration with TMDb Collections API to scan and discover custom collections directly from your logged movies.
- 📀 **Physical Media Collection Tracker**:
  - Track whether you own physical copies (4K UHD, Blu-ray, DVD, VHS, Steelbook) for every logged movie.
  - Interactive ownership toggles that persist directly into your database.
  - Live physical ownership counter and percentage tracker with dedicated filters.
- ➕ **Add & Search Movies via TMDb**: Quick search interface to enrich and log new films directly with automatic metadata fetching (directors, runtime, cast, release date, poster art, overview).
- 🌐 **Bilingual Support**: Instant toggle between **English** and **Italian**.
- 🎨 **Sleek Cinephile Theme**: Bespoke dark aesthetic inspired by Letterboxd's visual identity.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/letterboxd-enhancer.git
cd letterboxd-enhancer
```

### 2. Install Dependencies
Make sure you have Python 3.9+ installed:
```bash
pip install -r requirements.txt
```

### 3. Configure Your TMDb API Key
Create a `.streamlit/secrets.toml` file (or copy the example):
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
Open `.streamlit/secrets.toml` and add your free TMDb API key:
```toml
TMDB_API_KEY = "your_tmdb_api_key_here"
```
*(You can get a free API key at [themoviedb.org](https://www.themoviedb.org/settings/api)).*

### 4. Run the Application
```bash
streamlit run app.py
```
The app will open automatically in your browser at `http://localhost:8501`.

---

## 📁 Project Structure

```text
├── app.py                     # Main application entry point & navigation
├── pages/
│   ├── overview.py            # Overview statistics & quick filters
│   ├── personal_space.py      # Physical collection & personal diary
│   ├── sagas.py               # Sagas & Cinematic Universes tracker
│   ├── more_statistics.py     # In-depth director, genre, decade analytics
│   ├── add_movie.py           # Add new movies via TMDb live search
│   ├── data_manager.py        # Dataset inspection & CSV/Parquet export
│   └── settings.py            # Language, API key & physical collection preferences
├── services/
│   ├── sagas_service.py       # Universes, sagas definitions & TMDb scanner
│   ├── tmbd_service.py        # TMDb API client & caching
│   ├── ratings_service.py     # Ratings distribution & taste metrics
│   ├── nationality_service.py # World cinema & nationality statistics
│   ├── awards_service.py      # Oscar & festival awards intelligence
│   └── translations.py        # English / Italian localization strings
├── data/                      # Letterboxd parquet storage
└── .streamlit/                # App theme & configuration
```

---

## ☁️ Deploying to Streamlit Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and link your GitHub account.
3. Select your repository, branch (`main`), and main file path (`app.py`).
4. In **Advanced Settings**, add your `TMDB_API_KEY` under **Secrets**:
   ```toml
   TMDB_API_KEY = "your_actual_tmdb_api_key"
   ```
5. Click **Deploy**! 🚀

---

## 📜 TMDb Terms & Attribution

This project is an open-source, non-commercial portfolio and hobby tool built for cinema enthusiasts. 

- This product uses the [TMDB API](https://www.themoviedb.org/documentation/api) but is not endorsed or certified by [TMDB](https://www.themoviedb.org/).
- Film metadata, poster artwork, and collection details are provided courtesy of TMDb.
- Users can run the application with their own free personal TMDb API key via `.streamlit/secrets.toml` or directly in the app's **Settings** interface.
