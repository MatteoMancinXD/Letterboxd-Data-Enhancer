# Letterboxd Data Enhancer

A local Streamlit application for exploring a Letterboxd film history. It combines Letterboxd exports with TMDb metadata to provide viewing statistics, saga progress, personal ratings and physical collection tracking.

## Requirements

- Python 3.9 or later
- A TMDb API key for film searches and metadata enrichment
- A Letterboxd export, or individual `watched.csv`, `ratings.csv` and `diary.csv` files

## Installation

```powershell
git clone https://github.com/MatteoMancinXD/Letterboxd-Data-Enhancer.git
cd Letterboxd-Data-Enhancer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Create `.streamlit/secrets.toml`:

```toml
TMDB_API_KEY = "your-api-key"
```

Alternatively, set the `TMDB_API_KEY` environment variable or enter a session key in Settings. The lookup order is secrets file, environment variable, then session key. Keep credentials out of version control.

Start the application:

```sh
python -m streamlit run app.py
```

Open the local address printed in the terminal, normally `http://localhost:8501`.

## Using the application

| Section | Purpose |
| --- | --- |
| Overview | Summary statistics, recent entries and navigation |
| Personal Movie Space | Browse films, edit personal ratings and track physical copies |
| Deep Statistics | Directors, cast, genres, countries, awards, decades, viewing habits, ratings and sagas |
| Add Movie | Search TMDb and click a cover to open the rating and ownership dialog |
| Data Manager | Import, synchronize, inspect and export the dataset |
| Settings | Configure TMDb access or reset the local library |

The interface supports English and Italian. Analysis controls appear in the relevant sections rather than applying a global sidebar filter.

### Importing and updating Letterboxd data

1. Export your data from Letterboxd.
2. Open **Data Manager → Import & update** and upload the ZIP or supported CSV files.
3. Review films to add/remove and the before/after rating changes.
4. Synchronize to save the updated library.

The presence of `watched.csv` makes the upload a complete watched-list snapshot: films absent from that file are removed. Without it, the update is partial and other films remain in the library. CSVs inside nested sections of the ZIP, such as television exports, are excluded from the film import.

`ratings.csv` takes precedence over diary ratings. For a complete watched-list snapshot, absence from `ratings.csv` clears the rating. In partial uploads, only supplied films are updated; an explicitly blank rating clears that film's score. If a CSV has no Rating column, existing ratings are preserved. Diary rewatches use the most recent watched date rather than file order.

Existing TMDb metadata and physical ownership are preserved for retained films. Only new films require enrichment; rating-only synchronization does not need a TMDb key. Saving writes a complete temporary Parquet before replacing the existing file.

### Adding a film manually

Search by title and optional year, then click the film cover. A dialog opens with rating, viewing date and physical ownership controls. Saving closes the dialog and shows a confirmation with the film title. An existing matching film is updated rather than duplicated; its official Letterboxd URI and existing physical ownership are preserved.

The library stores one current record per film. It is not a complete event-level archive of every rewatch.

### Sagas and thematic cycles

Open **Deep Statistics → Sagas & Universes**. The built-in catalog includes franchises, cinematic universes and thematic cycles such as the Dollars Trilogy, Park Chan-wook's Vengeance Trilogy and Three Colours. Thematic cycles have a separate type filter and do not imply shared narrative continuity.

Rank by personal rating, TMDb rating, completion, remaining films or rating difference. Personal averages use rated watched films on a five-point scale. TMDb averages use released films with available scores on a ten-point scale, including unwatched films. Coverage is displayed; missing ratings are excluded. The rating difference compares only films rated by both sources after multiplying the personal rating by two.

The collection scan discovers and refreshes TMDb collections across the library. Curated groups can refresh their known film metadata or accept a missing film selected through TMDb search. Matching uses TMDb identifiers when available, then exact normalized titles/aliases and release years to distinguish remakes.

Curated lists have explicit membership and may need maintenance as new films appear. Some series are intentionally scoped to a date range. Completion includes known released films only; uncertain release dates are identified separately. TMDb collections do not provide a definitive canon for every cinematic universe or thematic cycle.

Catalog references include the [official Halloween film list](https://halloweenmovies.com/films/), the [BFI discussion of Park Chan-wook's vengeance trilogy](https://www.bfi.org.uk/lists/10-great-films-about-revenge), and the [Cinémathèque de Luxembourg programme on the Dollars Trilogy](https://www.vdl.lu/sites/default/files/media/document/08815_CINEMATHEQUE_PROGRAMME_OCTOBRE_NOVEMBRE_2025_web2_0.pdf).

## Storage and backups

Local data is stored under `data/`:

- `letterboxd_enriched.parquet`: the film library, ratings and physical ownership.
- `tmdb_collections_cache.json`: discovered TMDb collections.
- `curated_sagas_cache.json`: refreshed metadata and custom additions to curated groups.

Use **Data Manager → Export & backup** to download CSV or Parquet copies of the library. Copy the two JSON files separately if you want to preserve saga customizations. These files and API credentials are excluded from Git. Resetting the library is destructive; export a backup first.

TMDb requests and poster loading require network access. Cached library analysis remains available without an API key. The application uses local storage and is intended for a trusted personal environment, not as a multi-user hosted service.

## Development

```sh
python -m unittest discover -s tests -v
python -m compileall -q app.py pages services tests
```

Tests cover import reconciliation, persistence, saga matching and statistics, and Streamlit page flows. External TMDb calls are mocked; tests do not modify the personal library.

`app.py` defines navigation and shared styling. `pages/` contains the application views; `services/` contains import, metadata, analytics and saga catalog logic. `assets/style.css` and `.streamlit/config.toml` define the visual theme.

## Data sources

Film metadata and images are provided by [TMDb](https://www.themoviedb.org/). This product uses the TMDb API but is not endorsed or certified by TMDb. Letterboxd exports remain the source for personal ratings and watched-film membership.
