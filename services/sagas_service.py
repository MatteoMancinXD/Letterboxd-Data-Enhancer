# services/sagas_service.py
import re
import datetime
import tempfile
import unicodedata
import json
import os
import requests
import pandas as pd
import numpy as np
from services.tmbd_service import get_tmdb_api_key, fetch_movie_metadata, fetch_movie_details_by_id

DATA_DIR = "data"
CACHE_FILE = os.path.join(DATA_DIR, "tmdb_collections_cache.json")
CURATED_CACHE_FILE = os.path.join(DATA_DIR, "curated_sagas_cache.json")

def normalize_title(title):
    """
    Normalizes a movie title for robust cross-catalog matching.
    Removes accents, punctuation, special dash characters, and casing.
    """
    if not title or pd.isna(title):
        return ""
    s = unicodedata.normalize('NFKD', str(title)).lower()
    # Replace unicode dashes, weird quotes, and replacement chars
    s = re.sub(r'[\uFFFD\ufffd\?–—\:\,\.\'\!\-\&]', ' ', s)
    # Strip everything except letters and digits
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

# --- CURATED CINEMATIC UNIVERSES & MAJOR SAGAS REGISTRY ---
# Each entry defines canonical films with titles, release years, and common aliases.
CURATED_SAGAS = [
    {
        "id": "mcu",
        "name": "Marvel Cinematic Universe (MCU)",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#E52E71",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/yF1EbTN8gfLrmIX594LioRJko92.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/or06FN3Dka5tukK1e9sl16pB3iy.jpg",
        "description": "The monumental Marvel Cinematic Universe spanning Phase 1 to Phase 5. Only theatrical feature films.",
        "films": [
            # Phase 1
            {"title": "Iron Man", "year": 2008, "phase": "Phase 1: Assemble", "aliases": []},
            {"title": "The Incredible Hulk", "year": 2008, "phase": "Phase 1: Assemble", "aliases": ["Incredible Hulk"]},
            {"title": "Iron Man 2", "year": 2010, "phase": "Phase 1: Assemble", "aliases": []},
            {"title": "Thor", "year": 2011, "phase": "Phase 1: Assemble", "aliases": []},
            {"title": "Captain America: The First Avenger", "year": 2011, "phase": "Phase 1: Assemble", "aliases": ["The First Avenger"]},
            {"title": "The Avengers", "year": 2012, "phase": "Phase 1: Assemble", "aliases": ["Marvel's The Avengers", "Avengers Assemble"]},
            # Phase 2
            {"title": "Iron Man 3", "year": 2013, "phase": "Phase 2", "aliases": []},
            {"title": "Thor: The Dark World", "year": 2013, "phase": "Phase 2", "aliases": ["The Dark World"]},
            {"title": "Captain America: The Winter Soldier", "year": 2014, "phase": "Phase 2", "aliases": ["The Winter Soldier"]},
            {"title": "Guardians of the Galaxy", "year": 2014, "phase": "Phase 2", "aliases": ["Guardians of the Galaxy Vol. 1"]},
            {"title": "Avengers: Age of Ultron", "year": 2015, "phase": "Phase 2", "aliases": ["Age of Ultron"]},
            {"title": "Ant-Man", "year": 2015, "phase": "Phase 2", "aliases": []},
            # Phase 3
            {"title": "Captain America: Civil War", "year": 2016, "phase": "Phase 3: Infinity War", "aliases": ["Civil War"]},
            {"title": "Doctor Strange", "year": 2016, "phase": "Phase 3: Infinity War", "aliases": ["Dr. Strange"]},
            {"title": "Guardians of the Galaxy Vol. 2", "year": 2017, "phase": "Phase 3: Infinity War", "aliases": ["Guardians of the Galaxy 2"]},
            {"title": "Spider-Man: Homecoming", "year": 2017, "phase": "Phase 3: Infinity War", "aliases": ["Homecoming"]},
            {"title": "Thor: Ragnarok", "year": 2017, "phase": "Phase 3: Infinity War", "aliases": ["Ragnarok"]},
            {"title": "Black Panther", "year": 2018, "phase": "Phase 3: Infinity War", "aliases": []},
            {"title": "Avengers: Infinity War", "year": 2018, "phase": "Phase 3: Infinity War", "aliases": ["Infinity War"]},
            {"title": "Ant-Man and the Wasp", "year": 2018, "phase": "Phase 3: Infinity War", "aliases": ["Ant-Man 2"]},
            {"title": "Captain Marvel", "year": 2019, "phase": "Phase 3: Infinity War", "aliases": []},
            {"title": "Avengers: Endgame", "year": 2019, "phase": "Phase 3: Infinity War", "aliases": ["Endgame"]},
            {"title": "Spider-Man: Far From Home", "year": 2019, "phase": "Phase 3: Infinity War", "aliases": ["Far From Home"]},
            # Phase 4: Multiverse Saga
            {"title": "Black Widow", "year": 2021, "phase": "Phase 4: Multiverse", "aliases": []},
            {"title": "Shang-Chi and the Legend of the Ten Rings", "year": 2021, "phase": "Phase 4: Multiverse", "aliases": ["Shang-Chi"]},
            {"title": "Eternals", "year": 2021, "phase": "Phase 4: Multiverse", "aliases": ["The Eternals"]},
            {"title": "Spider-Man: No Way Home", "year": 2021, "phase": "Phase 4: Multiverse", "aliases": ["No Way Home"]},
            {"title": "Doctor Strange in the Multiverse of Madness", "year": 2022, "phase": "Phase 4: Multiverse", "aliases": ["Multiverse of Madness", "Doctor Strange 2"]},
            {"title": "Thor: Love and Thunder", "year": 2022, "phase": "Phase 4: Multiverse", "aliases": ["Love and Thunder", "Thor 4"]},
            {"title": "Black Panther: Wakanda Forever", "year": 2022, "phase": "Phase 4: Multiverse", "aliases": ["Wakanda Forever", "Black Panther 2"]},
            # Phase 5
            {"title": "Ant-Man and the Wasp: Quantumania", "year": 2023, "phase": "Phase 5", "aliases": ["Quantumania", "Ant-Man 3"]},
            {"title": "Guardians of the Galaxy Vol. 3", "year": 2023, "phase": "Phase 5", "aliases": ["Guardians of the Galaxy 3"]},
            {"title": "The Marvels", "year": 2023, "phase": "Phase 5", "aliases": ["Captain Marvel 2"]},
            {"title": "Deadpool & Wolverine", "year": 2024, "phase": "Phase 5", "aliases": ["Deadpool 3"]},
            {"title": "Captain America: Brave New World", "year": 2025, "phase": "Phase 5", "aliases": ["Brave New World"]},
            {"title": "Thunderbolts*", "year": 2025, "phase": "Phase 5", "aliases": ["Thunderbolts"]}
        ]
    },
    {
        "id": "star_wars_complete",
        "name": "Star Wars: Complete Film Canon",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#FFC107",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/5Iw7zQWebEMiISV6jh99flAh0f0.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg",
        "description": "The complete theatrical Star Wars film saga: the 9 Skywalker Saga chapters, Rogue One, Solo, and the upcoming Mandalorian feature film.",
        "films": [
            {"title": "Star Wars: Episode IV - A New Hope", "year": 1977, "phase": "Original Trilogy", "aliases": ["Star Wars", "A New Hope", "Star Wars: A New Hope"]},
            {"title": "Star Wars: Episode V - The Empire Strikes Back", "year": 1980, "phase": "Original Trilogy", "aliases": ["The Empire Strikes Back", "Empire Strikes Back"]},
            {"title": "Star Wars: Episode VI - Return of the Jedi", "year": 1983, "phase": "Original Trilogy", "aliases": ["Return of the Jedi"]},
            {"title": "Star Wars: Episode I - The Phantom Menace", "year": 1999, "phase": "Prequel Trilogy", "aliases": ["The Phantom Menace"]},
            {"title": "Star Wars: Episode II - Attack of the Clones", "year": 2002, "phase": "Prequel Trilogy", "aliases": ["Attack of the Clones"]},
            {"title": "Star Wars: Episode III - Revenge of the Sith", "year": 2005, "phase": "Prequel Trilogy", "aliases": ["Revenge of the Sith"]},
            {"title": "Star Wars: The Clone Wars", "year": 2008, "phase": "Animated Theatrical", "aliases": ["The Clone Wars"]},
            {"title": "Star Wars: The Force Awakens", "year": 2015, "phase": "Sequel Trilogy", "aliases": ["The Force Awakens", "Star Wars: Episode VII - The Force Awakens"]},
            {"title": "Rogue One: A Star Wars Story", "year": 2016, "phase": "Star Wars Stories", "aliases": ["Rogue One"]},
            {"title": "Star Wars: The Last Jedi", "year": 2017, "phase": "Sequel Trilogy", "aliases": ["The Last Jedi", "Star Wars: Episode VIII - The Last Jedi"]},
            {"title": "Solo: A Star Wars Story", "year": 2018, "phase": "Star Wars Stories", "aliases": ["Solo"]},
            {"title": "Star Wars: The Rise of Skywalker", "year": 2019, "phase": "Sequel Trilogy", "aliases": ["The Rise of Skywalker", "Star Wars: Episode IX - The Rise of Skywalker"]},
            {"title": "The Mandalorian & Grogu", "year": 2026, "phase": "New Era (2026)", "aliases": ["The Mandalorian and Grogu", "The Mandalorian", "Mandalorian"], "upcoming": True}
        ]
    },
    {
        "id": "star_wars_skywalker",
        "name": "Star Wars: The Skywalker Saga (Episodes I - IX)",
        "category": "saga",
        "tag": "The 9 Episodes",
        "badge_color": "#FFC107",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/zqkmTXzjkAgMfRdrwq6GegV0Nqf.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/db32LaOibwEliAmSL2jjDF6oDdj.jpg",
        "description": "The core nine-part Skywalker Saga chronicling the rise, fall, and redemption of the Jedi order.",
        "films": [
            {"title": "Star Wars: Episode IV - A New Hope", "year": 1977, "phase": "Original Trilogy", "aliases": ["Star Wars", "A New Hope", "Star Wars: A New Hope"]},
            {"title": "Star Wars: Episode V - The Empire Strikes Back", "year": 1980, "phase": "Original Trilogy", "aliases": ["The Empire Strikes Back", "Empire Strikes Back"]},
            {"title": "Star Wars: Episode VI - Return of the Jedi", "year": 1983, "phase": "Original Trilogy", "aliases": ["Return of the Jedi"]},
            {"title": "Star Wars: Episode I - The Phantom Menace", "year": 1999, "phase": "Prequel Trilogy", "aliases": ["The Phantom Menace"]},
            {"title": "Star Wars: Episode II - Attack of the Clones", "year": 2002, "phase": "Prequel Trilogy", "aliases": ["Attack of the Clones"]},
            {"title": "Star Wars: Episode III - Revenge of the Sith", "year": 2005, "phase": "Prequel Trilogy", "aliases": ["Revenge of the Sith"]},
            {"title": "Star Wars: The Force Awakens", "year": 2015, "phase": "Sequel Trilogy", "aliases": ["The Force Awakens", "Star Wars: Episode VII - The Force Awakens"]},
            {"title": "Star Wars: The Last Jedi", "year": 2017, "phase": "Sequel Trilogy", "aliases": ["The Last Jedi", "Star Wars: Episode VIII - The Last Jedi"]},
            {"title": "Star Wars: The Rise of Skywalker", "year": 2019, "phase": "Sequel Trilogy", "aliases": ["The Rise of Skywalker", "Star Wars: Episode IX - The Rise of Skywalker"]}
        ]
    },
    {
        "id": "dceu",
        "name": "DC Extended Universe (DCEU)",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#00A2FF",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/7k2B06VfE1VbJp2PauQyV19d00s.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/775HbbgczNq62uT2WkGj9aL2u36.jpg",
        "description": "DC's interconnected cinematic universe from Man of Steel to Aquaman and the Lost Kingdom.",
        "films": [
            {"title": "Man of Steel", "year": 2013, "phase": "Gods & Monsters", "aliases": []},
            {"title": "Batman v Superman: Dawn of Justice", "year": 2016, "phase": "Gods & Monsters", "aliases": ["Batman v Superman", "Dawn of Justice"]},
            {"title": "Suicide Squad", "year": 2016, "phase": "Gods & Monsters", "aliases": []},
            {"title": "Wonder Woman", "year": 2017, "phase": "Gods & Monsters", "aliases": []},
            {"title": "Justice League", "year": 2017, "phase": "Gods & Monsters", "aliases": ["Zack Snyder's Justice League"]},
            {"title": "Aquaman", "year": 2018, "phase": "Expanded World", "aliases": []},
            {"title": "Shazam!", "year": 2019, "phase": "Expanded World", "aliases": []},
            {"title": "Birds of Prey", "year": 2020, "phase": "Expanded World", "aliases": ["Birds of Prey (and the Fantabulous Emancipation of One Harley Quinn)"]},
            {"title": "Wonder Woman 1984", "year": 2020, "phase": "Expanded World", "aliases": ["WW84"]},
            {"title": "Zack Snyder's Justice League", "year": 2021, "phase": "Snyder Cut", "aliases": ["Justice League Snyder Cut"]},
            {"title": "The Suicide Squad", "year": 2021, "phase": "Expanded World", "aliases": ["Suicide Squad 2"]},
            {"title": "Black Adam", "year": 2022, "phase": "Expanded World", "aliases": []},
            {"title": "Shazam! Fury of the Gods", "year": 2023, "phase": "Climax Era", "aliases": ["Shazam 2"]},
            {"title": "The Flash", "year": 2023, "phase": "Climax Era", "aliases": []},
            {"title": "Blue Beetle", "year": 2023, "phase": "Climax Era", "aliases": []},
            {"title": "Aquaman and the Lost Kingdom", "year": 2023, "phase": "Climax Era", "aliases": ["Aquaman 2"]}
        ]
    },
    {
        "id": "x_men",
        "name": "X-Men Cinematic Universe",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/bql4H14FjL81kHwXvR7N8sM5w9E.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/2LqaLgk4Z226KkgPJuiOQ58wvrm.jpg",
        "description": "Fox's 24-year mutant saga from the revolutionary 2000 original to Logan, Deadpool, and New Mutants.",
        "films": [
            {"title": "X-Men", "year": 2000, "phase": "Original Trilogy", "aliases": []},
            {"title": "X2", "year": 2003, "phase": "Original Trilogy", "aliases": ["X2: X-Men United", "X-Men 2"]},
            {"title": "X-Men: The Last Stand", "year": 2006, "phase": "Original Trilogy", "aliases": ["The Last Stand", "X-Men 3"]},
            {"title": "X-Men Origins: Wolverine", "year": 2009, "phase": "Wolverine Trilogy", "aliases": ["Origins: Wolverine"]},
            {"title": "X-Men: First Class", "year": 2011, "phase": "Prequel Generation", "aliases": ["First Class"]},
            {"title": "The Wolverine", "year": 2013, "phase": "Wolverine Trilogy", "aliases": []},
            {"title": "X-Men: Days of Future Past", "year": 2014, "phase": "Prequel Generation", "aliases": ["Days of Future Past"]},
            {"title": "Deadpool", "year": 2016, "phase": "Deadpool Era", "aliases": []},
            {"title": "X-Men: Apocalypse", "year": 2016, "phase": "Prequel Generation", "aliases": ["Apocalypse"]},
            {"title": "Logan", "year": 2017, "phase": "Wolverine Trilogy", "aliases": []},
            {"title": "Deadpool 2", "year": 2018, "phase": "Deadpool Era", "aliases": []},
            {"title": "Dark Phoenix", "year": 2019, "phase": "Prequel Generation", "aliases": ["X-Men: Dark Phoenix"]},
            {"title": "The New Mutants", "year": 2020, "phase": "Spinoff", "aliases": ["New Mutants"]},
            {"title": "Deadpool & Wolverine", "year": 2024, "phase": "Multiverse Finale", "aliases": ["Deadpool 3"]}
        ]
    },
    {
        "id": "lotr_trilogy",
        "name": "The Lord of the Rings Trilogy",
        "category": "saga",
        "tag": "Masterpiece Trilogy",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/lXhgCODAbBXL5buk9yEmTFOo0FS.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/6oom5QYQ2yQTMJIbnvbkBL9cDK6.jpg",
        "description": "Peter Jackson's legendary three-part cinematic adaptation of J.R.R. Tolkien's high fantasy epic.",
        "films": [
            {"title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001, "phase": "Middle-earth", "aliases": ["The Fellowship of the Ring", "LOTR 1"]},
            {"title": "The Lord of the Rings: The Two Towers", "year": 2002, "phase": "Middle-earth", "aliases": ["The Two Towers", "LOTR 2"]},
            {"title": "The Lord of the Rings: The Return of the King", "year": 2003, "phase": "Middle-earth", "aliases": ["The Return of the King", "LOTR 3"]}
        ]
    },
    {
        "id": "middle_earth_complete",
        "name": "Middle-earth: Complete Film Saga",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/2cUsGKa2a4vtAeGQSYvup5GyHG0.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/2G0Z11m0D4aD2E2x2D0K0e3y9vL.jpg",
        "description": "The complete 6-film Jackson cinematic journey spanning The Hobbit and The Lord of the Rings.",
        "films": [
            {"title": "The Hobbit: An Unexpected Journey", "year": 2012, "phase": "The Hobbit", "aliases": ["An Unexpected Journey", "The Hobbit 1"]},
            {"title": "The Hobbit: The Desolation of Smaug", "year": 2013, "phase": "The Hobbit", "aliases": ["The Desolation of Smaug", "The Hobbit 2"]},
            {"title": "The Hobbit: The Battle of the Five Armies", "year": 2014, "phase": "The Hobbit", "aliases": ["The Battle of the Five Armies", "The Hobbit 3"]},
            {"title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001, "phase": "The Lord of the Rings", "aliases": ["The Fellowship of the Ring"]},
            {"title": "The Lord of the Rings: The Two Towers", "year": 2002, "phase": "The Lord of the Rings", "aliases": ["The Two Towers"]},
            {"title": "The Lord of the Rings: The Return of the King", "year": 2003, "phase": "The Lord of the Rings", "aliases": ["The Return of the King"]}
        ]
    },
    {
        "id": "dark_knight",
        "name": "The Dark Knight Trilogy",
        "category": "saga",
        "tag": "Masterpiece Trilogy",
        "badge_color": "#40BCF4",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "description": "Christopher Nolan's groundbreaking realistic reimagining of the Caped Crusader.",
        "films": [
            {"title": "Batman Begins", "year": 2005, "phase": "Nolan Trilogy", "aliases": []},
            {"title": "The Dark Knight", "year": 2008, "phase": "Nolan Trilogy", "aliases": []},
            {"title": "The Dark Knight Rises", "year": 2012, "phase": "Nolan Trilogy", "aliases": []}
        ]
    },
    {
        "id": "harry_potter",
        "name": "Harry Potter (The 8 Films)",
        "category": "saga",
        "tag": "Original 8 Films",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/hziiv14OpD73u9gAak4XDDfBKa2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/wuMc08IPKEatv9rnMNXvIDJJ04b.jpg",
        "description": "The definitive 8-chapter saga of the Boy Who Lived at Hogwarts School of Witchcraft and Wizardry.",
        "films": [
            {"title": "Harry Potter and the Philosopher's Stone", "year": 2001, "phase": "Hogwarts Era", "aliases": ["Harry Potter and the Sorcerer's Stone", "Harry Potter 1"]},
            {"title": "Harry Potter and the Chamber of Secrets", "year": 2002, "phase": "Hogwarts Era", "aliases": ["Harry Potter 2"]},
            {"title": "Harry Potter and the Prisoner of Azkaban", "year": 2004, "phase": "Hogwarts Era", "aliases": ["Harry Potter 3"]},
            {"title": "Harry Potter and the Goblet of Fire", "year": 2005, "phase": "Hogwarts Era", "aliases": ["Harry Potter 4"]},
            {"title": "Harry Potter and the Order of the Phoenix", "year": 2007, "phase": "Hogwarts Era", "aliases": ["Harry Potter 5"]},
            {"title": "Harry Potter and the Half-Blood Prince", "year": 2009, "phase": "Hogwarts Era", "aliases": ["Harry Potter 6"]},
            {"title": "Harry Potter and the Deathly Hallows: Part 1", "year": 2010, "phase": "The Final Battle", "aliases": ["Harry Potter and the Deathly Hallows – Part 1", "Deathly Hallows Part 1"]},
            {"title": "Harry Potter and the Deathly Hallows: Part 2", "year": 2011, "phase": "The Final Battle", "aliases": ["Harry Potter and the Deathly Hallows – Part 2", "Deathly Hallows Part 2"]}
        ]
    },
    {
        "id": "wizarding_world",
        "name": "Wizarding World Universe",
        "category": "universe",
        "tag": "Cinematic Universe",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/hziiv14OpD73u9gAak4XDDfBKa2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/wuMc08IPKEatv9rnMNXvIDJJ04b.jpg",
        "description": "The expanded Wizarding World universe, uniting the 8 Harry Potter films with the Fantastic Beasts prequel trilogy.",
        "films": [
            {"title": "Harry Potter and the Philosopher's Stone", "year": 2001, "phase": "Harry Potter Saga", "aliases": ["Harry Potter and the Sorcerer's Stone"]},
            {"title": "Harry Potter and the Chamber of Secrets", "year": 2002, "phase": "Harry Potter Saga", "aliases": []},
            {"title": "Harry Potter and the Prisoner of Azkaban", "year": 2004, "phase": "Harry Potter Saga", "aliases": []},
            {"title": "Harry Potter and the Goblet of Fire", "year": 2005, "phase": "Harry Potter Saga", "aliases": []},
            {"title": "Harry Potter and the Order of the Phoenix", "year": 2007, "phase": "Harry Potter Saga", "aliases": []},
            {"title": "Harry Potter and the Half-Blood Prince", "year": 2009, "phase": "Harry Potter Saga", "aliases": []},
            {"title": "Harry Potter and the Deathly Hallows: Part 1", "year": 2010, "phase": "Harry Potter Saga", "aliases": ["Harry Potter and the Deathly Hallows – Part 1"]},
            {"title": "Harry Potter and the Deathly Hallows: Part 2", "year": 2011, "phase": "Harry Potter Saga", "aliases": ["Harry Potter and the Deathly Hallows – Part 2"]},
            {"title": "Fantastic Beasts and Where to Find Them", "year": 2016, "phase": "Fantastic Beasts Prequels", "aliases": ["Fantastic Beasts 1"]},
            {"title": "Fantastic Beasts: The Crimes of Grindelwald", "year": 2018, "phase": "Fantastic Beasts Prequels", "aliases": ["The Crimes of Grindelwald", "Fantastic Beasts 2"]},
            {"title": "Fantastic Beasts: The Secrets of Dumbledore", "year": 2022, "phase": "Fantastic Beasts Prequels", "aliases": ["The Secrets of Dumbledore", "Fantastic Beasts 3"]}
        ]
    },
    {
        "id": "spider_man_raimi",
        "name": "Spider-Man: Sam Raimi Trilogy",
        "category": "saga",
        "tag": "Classic Trilogy",
        "badge_color": "#E52E71",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/6xKCYgH16UezIhkqA4gL7rN95Q2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/gh4c2bhLYQEZASJHvd29Sc6keRI.jpg",
        "description": "Sam Raimi and Tobey Maguire's genre-defining Spider-Man trilogy.",
        "films": [
            {"title": "Spider-Man", "year": 2002, "phase": "Raimi Trilogy", "aliases": []},
            {"title": "Spider-Man 2", "year": 2004, "phase": "Raimi Trilogy", "aliases": []},
            {"title": "Spider-Man 3", "year": 2007, "phase": "Raimi Trilogy", "aliases": []}
        ]
    },
    {
        "id": "spider_verse",
        "name": "Spider-Verse (Animated)",
        "category": "saga",
        "tag": "Animation Masterpiece",
        "badge_color": "#E52E71",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/4HodYYKEIsGOdinkGi2Ucz6X9i0.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "description": "Miles Morales' revolutionary multiverse animated odyssey.",
        "films": [
            {"title": "Spider-Man: Into the Spider-Verse", "year": 2018, "phase": "Multiverse", "aliases": ["Into the Spider-Verse"]},
            {"title": "Spider-Man: Across the Spider-Verse", "year": 2023, "phase": "Multiverse", "aliases": ["Across the Spider-Verse"]}
        ]
    },
    {
        "id": "back_to_the_future",
        "name": "Back to the Future Trilogy",
        "category": "saga",
        "tag": "Sci-Fi Classic",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/7lyKFbXjI16iE0Pq3Xo99R5eQJ.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/fNOH9f1aA7XRTzl1sAOx9iF553Q.jpg",
        "description": "Robert Zemeckis' timeless time-travel comedy adventures with Marty McFly and Doc Brown.",
        "films": [
            {"title": "Back to the Future", "year": 1985, "phase": "1985 Era", "aliases": []},
            {"title": "Back to the Future Part II", "year": 1989, "phase": "Future & Alternate", "aliases": ["Back to the Future 2"]},
            {"title": "Back to the Future Part III", "year": 1990, "phase": "Old West", "aliases": ["Back to the Future 3"]}
        ]
    },
    {
        "id": "the_godfather",
        "name": "The Godfather Trilogy",
        "category": "saga",
        "tag": "Cinema Royalty",
        "badge_color": "#FFC107",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/tmU7GeKVybMWF92vGZSDTMKhitY.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "description": "Francis Ford Coppola's monumental chronicle of the Corleone family dynasty.",
        "films": [
            {"title": "The Godfather", "year": 1972, "phase": "Vito & Michael", "aliases": []},
            {"title": "The Godfather Part II", "year": 1974, "phase": "Dynasty", "aliases": ["The Godfather 2"]},
            {"title": "The Godfather Part III", "year": 1990, "phase": "Redemption", "aliases": ["The Godfather 3", "The Godfather Coda: The Death of Michael Corleone"]}
        ]
    },
    {
        "id": "fast_and_furious",
        "name": "Fast & Furious Saga",
        "category": "universe",
        "tag": "Action Franchise",
        "badge_color": "#40BCF4",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/14GEzyA2oVdfd9q0j7x9Q8A4uF2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/fiVW06jE7z9YnO4trhaMEdclSiC.jpg",
        "description": "High-octane automotive heists, family loyalty, and global espionage across 11 films.",
        "films": [
            {"title": "The Fast and the Furious", "year": 2001, "phase": "Street Racing", "aliases": ["Fast and Furious 1"]},
            {"title": "2 Fast 2 Furious", "year": 2003, "phase": "Miami", "aliases": ["Fast and Furious 2"]},
            {"title": "The Fast and the Furious: Tokyo Drift", "year": 2006, "phase": "Tokyo", "aliases": ["Tokyo Drift"]},
            {"title": "Fast & Furious", "year": 2009, "phase": "Reunion", "aliases": ["Fast & Furious 4"]},
            {"title": "Fast Five", "year": 2011, "phase": "Rio Heist", "aliases": ["Fast & Furious 5"]},
            {"title": "Fast & Furious 6", "year": 2013, "phase": "Global Team", "aliases": []},
            {"title": "Furious 7", "year": 2015, "phase": "Global Team", "aliases": ["Fast & Furious 7"]},
            {"title": "The Fate of the Furious", "year": 2017, "phase": "Global Espionage", "aliases": ["Fast & Furious 8"]},
            {"title": "Fast & Furious Presents: Hobbs & Shaw", "year": 2019, "phase": "Spinoff", "aliases": ["Hobbs & Shaw"]},
            {"title": "F9", "year": 2021, "phase": "Global Espionage", "aliases": ["Fast & Furious 9", "F9: The Fast Saga"]},
            {"title": "Fast X", "year": 2023, "phase": "The End of the Road", "aliases": ["Fast & Furious 10"]}
        ]
    },
    {
        "id": "mission_impossible",
        "name": "Mission: Impossible Saga",
        "category": "saga",
        "tag": "Espionage Masterclass",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/628Dep6AxEtDxjZoGP78TsOxYbK.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/NNxYkU70HPurnNCSiCjYAmacwm.jpg",
        "description": "Tom Cruise's breathtaking stunts and Ethan Hunt's death-defying IMF missions across 7 films.",
        "films": [
            {"title": "Mission: Impossible", "year": 1996, "phase": "IMF Origins", "aliases": ["Mission Impossible 1"]},
            {"title": "Mission: Impossible II", "year": 2000, "phase": "John Woo Era", "aliases": ["Mission: Impossible 2", "M:I-2"]},
            {"title": "Mission: Impossible III", "year": 2006, "phase": "J.J. Abrams Era", "aliases": ["Mission: Impossible 3", "M:I:III"]},
            {"title": "Mission: Impossible - Ghost Protocol", "year": 2011, "phase": "Brad Bird Era", "aliases": ["Ghost Protocol", "Mission: Impossible 4"]},
            {"title": "Mission: Impossible - Rogue Nation", "year": 2015, "phase": "McQuarrie Era", "aliases": ["Rogue Nation", "Mission: Impossible 5"]},
            {"title": "Mission: Impossible - Fallout", "year": 2018, "phase": "McQuarrie Era", "aliases": ["Fallout", "Mission: Impossible 6"]},
            {"title": "Mission: Impossible - Dead Reckoning Part One", "year": 2023, "phase": "McQuarrie Era", "aliases": ["Dead Reckoning", "Mission: Impossible 7"]}
        ]
    },
    {
        "id": "james_bond_craig",
        "name": "James Bond (Daniel Craig Era)",
        "category": "saga",
        "tag": "007 Era",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/r2J02Z2OpNTctfOSN2Ydgii51I3.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/iItdtlO1m02D8e4r8c826G0d7Q.jpg",
        "description": "Daniel Craig's celebrated serialized 5-film arc as Agent 007 with a license to kill.",
        "films": [
            {"title": "Casino Royale", "year": 2006, "phase": "007 Origin", "aliases": []},
            {"title": "Quantum of Solace", "year": 2008, "phase": "Vengeance", "aliases": []},
            {"title": "Skyfall", "year": 2012, "phase": "Sam Mendes Era", "aliases": []},
            {"title": "Spectre", "year": 2015, "phase": "Sam Mendes Era", "aliases": []},
            {"title": "No Time to Die", "year": 2021, "phase": "Grand Finale", "aliases": []}
        ]
    },
    {
        "id": "monsterverse",
        "name": "MonsterVerse",
        "category": "universe",
        "tag": "Titan Battles",
        "badge_color": "#00A2FF",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/xOMo8BRK7PfcJv9JCnx7s520fff.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/tMefBSflR6PGQLv7WvFPpKLZkyk.jpg",
        "description": "Legendary's shared titan universe bringing Godzilla, Kong, and the Hollow Earth titans together.",
        "films": [
            {"title": "Godzilla", "year": 2014, "phase": "Titan Awakens", "aliases": []},
            {"title": "Kong: Skull Island", "year": 2017, "phase": "Origins", "aliases": ["Skull Island"]},
            {"title": "Godzilla: King of the Monsters", "year": 2019, "phase": "King of the Monsters", "aliases": ["Godzilla 2"]},
            {"title": "Godzilla vs. Kong", "year": 2021, "phase": "Clash of Titans", "aliases": []},
            {"title": "Godzilla x Kong: The New Empire", "year": 2024, "phase": "Hollow Earth", "aliases": ["The New Empire"]}
        ]
    },
    {
        "id": "jurassic_park",
        "name": "Jurassic Park & Jurassic World Saga",
        "category": "universe",
        "tag": "Dino Spectacle",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/9K4B6mGjV4oF8c1p64g0J521m8.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/c566q0z1v03oA4Y727h8W9845uV.jpg",
        "description": "65 million years in the making: Spielberg's classic trilogy and the modern Jurassic World trilogy.",
        "films": [
            {"title": "Jurassic Park", "year": 1993, "phase": "Isla Nublar Classic", "aliases": []},
            {"title": "The Lost World: Jurassic Park", "year": 1997, "phase": "Isla Sorna", "aliases": ["The Lost World", "Jurassic Park 2"]},
            {"title": "Jurassic Park III", "year": 2001, "phase": "Isla Sorna", "aliases": ["Jurassic Park 3"]},
            {"title": "Jurassic World", "year": 2015, "phase": "World Reborn", "aliases": []},
            {"title": "Jurassic World: Fallen Kingdom", "year": 2018, "phase": "World Reborn", "aliases": ["Fallen Kingdom"]},
            {"title": "Jurassic World Dominion", "year": 2022, "phase": "Global Coexistence", "aliases": ["Dominion"]}
        ]
    },
    {
        "id": "indiana_jones",
        "name": "Indiana Jones Saga",
        "category": "saga",
        "tag": "Adventure Classic",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/3G1Q5xF4Sp4xevU0pWf7457i8G.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/4cW294n4D71z1eU5s42h7905151.jpg",
        "description": "Harrison Ford's iconic archaeologist adventuring across archaeological wonders.",
        "films": [
            {"title": "Raiders of the Lost Ark", "year": 1981, "phase": "Classic Era", "aliases": ["Indiana Jones and the Raiders of the Lost Ark"]},
            {"title": "Indiana Jones and the Temple of Doom", "year": 1984, "phase": "Classic Era", "aliases": ["Temple of Doom"]},
            {"title": "Indiana Jones and the Last Crusade", "year": 1989, "phase": "Classic Era", "aliases": ["The Last Crusade"]},
            {"title": "Indiana Jones and the Kingdom of the Crystal Skull", "year": 2008, "phase": "Modern Era", "aliases": ["Kingdom of the Crystal Skull"]},
            {"title": "Indiana Jones and the Dial of Destiny", "year": 2023, "phase": "Final Farewell", "aliases": ["Dial of Destiny"]}
        ]
    },
    {
        "id": "the_matrix",
        "name": "The Matrix Saga",
        "category": "saga",
        "tag": "Cyberpunk Masterpiece",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/l4QHerTSbMI7qgDCwah5JhiUNY2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
        "description": "The Wachowskis' groundbreaking cyberpunk reality-bending philosopher-action saga.",
        "films": [
            {"title": "The Matrix", "year": 1999, "phase": "Awakening", "aliases": []},
            {"title": "The Matrix Reloaded", "year": 2003, "phase": "Zion At War", "aliases": ["Matrix Reloaded"]},
            {"title": "The Matrix Revolutions", "year": 2003, "phase": "Peace Achieved", "aliases": ["Matrix Revolutions"]},
            {"title": "The Matrix Resurrections", "year": 2021, "phase": "Reawakening", "aliases": ["Matrix Resurrections"]}
        ]
    },
    {
        "id": "john_wick",
        "name": "John Wick Saga",
        "category": "saga",
        "tag": "Neo-Noir Action",
        "badge_color": "#E52E71",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/h8gHn0OzToRIImCd4AG28GZuhR1.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/fZPSd91yGE9fCcCe6OoQr6E3Bev.jpg",
        "description": "Keanu Reeves' legendary Baba Yaga fighting the High Table through 4 chapters.",
        "films": [
            {"title": "John Wick", "year": 2014, "phase": "Baba Yaga", "aliases": []},
            {"title": "John Wick: Chapter 2", "year": 2017, "phase": "Blood Oath", "aliases": ["John Wick 2"]},
            {"title": "John Wick: Chapter 3 - Parabellum", "year": 2019, "phase": "Excommunicado", "aliases": ["John Wick 3", "Parabellum"]},
            {"title": "John Wick: Chapter 4", "year": 2023, "phase": "The High Table", "aliases": ["John Wick 4"]}
        ]
    },
    {
        "id": "toy_story",
        "name": "Toy Story Saga",
        "category": "saga",
        "tag": "Pixar Classic",
        "badge_color": "#40BCF4",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/lxD5ak7BOxob9zrIOganbh2RScD.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/uXDfjJbdP4ijW5hWSBrPrlKpxab.jpg",
        "description": "Woody, Buzz Lightyear, and the toys that defined modern computer animation.",
        "films": [
            {"title": "Toy Story", "year": 1995, "phase": "Andy's Room", "aliases": []},
            {"title": "Toy Story 2", "year": 1999, "phase": "Andy's Room", "aliases": []},
            {"title": "Toy Story 3", "year": 2010, "phase": "Sunnyside & College", "aliases": []},
            {"title": "Toy Story 4", "year": 2019, "phase": "Forky & Road Trip", "aliases": []},
            {"title": "Lightyear", "year": 2022, "phase": "Spinoff", "aliases": []}
        ]
    },
    {
        "id": "shrek_universe",
        "name": "Shrek Universe",
        "category": "universe",
        "tag": "Animation Royalty",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/jY9p6kG37v1b1iL4xK0eG7A1F2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/iB64vpL3dIObOtMZg3vUV5HmOD8.jpg",
        "description": "DreamWorks' fractured fairy tale kingdom: Shrek, Donkey, and Puss in Boots.",
        "films": [
            {"title": "Shrek", "year": 2001, "phase": "Far Far Away", "aliases": []},
            {"title": "Shrek 2", "year": 2004, "phase": "Far Far Away", "aliases": []},
            {"title": "Shrek the Third", "year": 2007, "phase": "Far Far Away", "aliases": ["Shrek 3"]},
            {"title": "Shrek Forever After", "year": 2010, "phase": "Far Far Away", "aliases": ["Shrek 4"]},
            {"title": "Puss in Boots", "year": 2011, "phase": "Puss in Boots", "aliases": []},
            {"title": "Puss in Boots: The Last Wish", "year": 2022, "phase": "Puss in Boots", "aliases": ["The Last Wish"]}
        ]
    },
    {
        "id": "planet_of_the_apes_reboot",
        "name": "Planet of the Apes (Reboot Saga)",
        "category": "saga",
        "tag": "Sci-Fi Masterpiece",
        "badge_color": "#FFC107",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/aL5vX7a1j6pX7L2QvK0n8A1F3.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/7I90zF1r0E2n4K1m9xK8qY7oW2.jpg",
        "description": "The extraordinary Caesar saga and its continuation into the Kingdom of the Apes.",
        "films": [
            {"title": "Rise of the Planet of the Apes", "year": 2011, "phase": "Caesar's Rise", "aliases": []},
            {"title": "Dawn of the Planet of the Apes", "year": 2014, "phase": "War Begins", "aliases": []},
            {"title": "War for the Planet of the Apes", "year": 2017, "phase": "Caesar's Legacy", "aliases": []},
            {"title": "Kingdom of the Planet of the Apes", "year": 2024, "phase": "New Era", "aliases": []}
        ]
    },
    {
        "id": "hunger_games",
        "name": "The Hunger Games Saga",
        "category": "saga",
        "tag": "Dystopian Epic",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/yvO1l92l5fHq0f42vL4m8x9A0.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/bv9p5n2bA1kL7Q0e9A1F3G4vH1.jpg",
        "description": "Katniss Everdeen's revolution across Panem and the origins of Coriolanus Snow.",
        "films": [
            {"title": "The Hunger Games", "year": 2012, "phase": "74th Games", "aliases": []},
            {"title": "The Hunger Games: Catching Fire", "year": 2013, "phase": "Quarter Quell", "aliases": ["Catching Fire"]},
            {"title": "The Hunger Games: Mockingjay - Part 1", "year": 2014, "phase": "Rebellion", "aliases": ["Mockingjay - Part 1", "Mockingjay Part 1"]},
            {"title": "The Hunger Games: Mockingjay - Part 2", "year": 2015, "phase": "Rebellion", "aliases": ["Mockingjay - Part 2", "Mockingjay Part 2"]},
            {"title": "The Hunger Games: The Ballad of Songbirds & Snakes", "year": 2023, "phase": "Prequel", "aliases": ["The Ballad of Songbirds & Snakes", "Songbirds & Snakes"]}
        ]
    },
    {
        "id": "pirates_caribbean",
        "name": "Pirates of the Caribbean Saga",
        "category": "saga",
        "tag": "High Seas Fantasy",
        "badge_color": "#40BCF4",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/jY9p6kG37v1b1iL4xK0eG7A1F2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/z8onk7LV9MPkNDFz5v0v8B3jY1.jpg",
        "description": "Captain Jack Sparrow's supernatural voyages across the Caribbean seas.",
        "films": [
            {"title": "Pirates of the Caribbean: The Curse of the Black Pearl", "year": 2003, "phase": "Original Trilogy", "aliases": ["The Curse of the Black Pearl", "Pirates of the Caribbean 1"]},
            {"title": "Pirates of the Caribbean: Dead Man's Chest", "year": 2006, "phase": "Original Trilogy", "aliases": ["Dead Man's Chest", "Pirates of the Caribbean 2"]},
            {"title": "Pirates of the Caribbean: At World's End", "year": 2007, "phase": "Original Trilogy", "aliases": ["At World's End", "Pirates of the Caribbean 3"]},
            {"title": "Pirates of the Caribbean: On Stranger Tides", "year": 2011, "phase": "Fountain of Youth", "aliases": ["On Stranger Tides", "Pirates of the Caribbean 4"]},
            {"title": "Pirates of the Caribbean: Dead Men Tell No Tales", "year": 2017, "phase": "Salazar's Revenge", "aliases": ["Dead Men Tell No Tales", "Salazar's Revenge", "Pirates of the Caribbean 5"]}
        ]
    },
    {
        "id": "alien_universe",
        "name": "Alien & Predator Universe",
        "category": "universe",
        "tag": "Sci-Fi Horror",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/AmR3JG1YrIh0vfJ5e9y1A7F0J3.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/vfrQk5IPloGg1v9FU42eFa0YFrg.jpg",
        "description": "The terrifying Xenomorph and Yautja mythology from Ridley Scott's 1979 masterpiece to Romulus.",
        "films": [
            {"title": "Alien", "year": 1979, "phase": "Xenomorph", "aliases": []},
            {"title": "Aliens", "year": 1986, "phase": "Xenomorph", "aliases": ["Alien 2"]},
            {"title": "Alien 3", "year": 1992, "phase": "Xenomorph", "aliases": ["Alien³"]},
            {"title": "Alien Resurrection", "year": 1997, "phase": "Xenomorph", "aliases": ["Alien 4"]},
            {"title": "Prometheus", "year": 2012, "phase": "Origins", "aliases": []},
            {"title": "Alien: Covenant", "year": 2017, "phase": "Origins", "aliases": ["Covenant"]},
            {"title": "Alien: Romulus", "year": 2024, "phase": "New Nightmare", "aliases": ["Romulus"]},
            {"title": "Predator", "year": 1987, "phase": "Predator", "aliases": []},
            {"title": "Predator 2", "year": 1990, "phase": "Predator", "aliases": []},
            {"title": "Predators", "year": 2010, "phase": "Predator", "aliases": []},
            {"title": "The Predator", "year": 2018, "phase": "Predator", "aliases": []},
            {"title": "Prey", "year": 2022, "phase": "Predator", "aliases": []}
        ]
    },
    {
        "id": "before_trilogy",
        "name": "Before Trilogy (Richard Linklater)",
        "category": "saga",
        "tag": "Romantic Cinema",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/tM9p6kG37v1b1iL4xK0eG7A1F2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/khSV4zXfIu6q53eY7h820L9f45B.jpg",
        "description": "Richard Linklater, Ethan Hawke, and Julie Delpy's 18-year real-time romantic masterwork.",
        "films": [
            {"title": "Before Sunrise", "year": 1995, "phase": "Vienna", "aliases": []},
            {"title": "Before Sunset", "year": 2004, "phase": "Paris", "aliases": []},
            {"title": "Before Midnight", "year": 2013, "phase": "Greece", "aliases": []}
        ]
    },
    {
        "id": "cornetto_trilogy",
        "name": "Three Flavours Cornetto Trilogy (Edgar Wright)",
        "category": "saga",
        "tag": "Comedy Perfection",
        "badge_color": "#00E054",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/6xKCYgH16UezIhkqA4gL7rN95Q2.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/1Xdd32Kj3n44uL3nK1e8A1F3G4v.jpg",
        "description": "Edgar Wright, Simon Pegg, and Nick Frost's legendary genre-parody blood-and-ice-cream trilogy.",
        "films": [
            {"title": "Shaun of the Dead", "year": 2004, "phase": "Red Strawberry", "aliases": []},
            {"title": "Hot Fuzz", "year": 2007, "phase": "Blue Class", "aliases": []},
            {"title": "The World's End", "year": 2013, "phase": "Green Mint", "aliases": []}
        ]
    },
    {
        "id": "dune_saga",
        "name": "Dune Saga (Denis Villeneuve)",
        "category": "saga",
        "tag": "Modern Sci-Fi",
        "badge_color": "#FFC107",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/xOMo8BRK7PfcJv9JCnx7s520fff.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/d5NXSklXo0qyIYkgV94XAgMIckC.jpg",
        "description": "Denis Villeneuve's visionary cinematic realization of Frank Herbert's Arrakis epic.",
        "films": [
            {"title": "Dune", "year": 2021, "phase": "Arrakis Awakening", "aliases": ["Dune: Part One", "Dune: Part 1"]},
            {"title": "Dune: Part Two", "year": 2024, "phase": "Holy War", "aliases": ["Dune 2", "Dune: Part 2"]}
        ]
    },
    {
        "id": "avatar_saga",
        "name": "Avatar Saga (James Cameron)",
        "category": "saga",
        "tag": "Visual Revolution",
        "badge_color": "#00A2FF",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/o07FWaqU4LdYrI12Pt4vW5B34.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/kyeqWdyUXW608qlYkRqosgxmukK.jpg",
        "description": "James Cameron's record-shattering Pandora expeditions.",
        "films": [
            {"title": "Avatar", "year": 2009, "phase": "Pandora Rainforest", "aliases": []},
            {"title": "Avatar: The Way of Water", "year": 2022, "phase": "Pandora Oceans", "aliases": ["Avatar 2"]}
        ]
    },
    {
        "id": "mad_max",
        "name": "Mad Max Saga (George Miller)",
        "category": "saga",
        "tag": "Wasteland Fury",
        "badge_color": "#FF8000",
        "backdrop_url": "https://image.tmdb.org/t/p/w780/nlCHUWjY9XbGAqR92x421p8.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w300/hA2ple9q4qnwxp3hKVNhroipsir.jpg",
        "description": "George Miller's post-apocalyptic kinetic motor-mayhem from 1979 to Furiosa.",
        "films": [
            {"title": "Mad Max", "year": 1979, "phase": "The Fall", "aliases": []},
            {"title": "Mad Max 2", "year": 1981, "phase": "The Road Warrior", "aliases": ["The Road Warrior", "Mad Max 2: The Road Warrior"]},
            {"title": "Mad Max Beyond Thunderdome", "year": 1985, "phase": "Bartertown", "aliases": ["Mad Max 3"]},
            {"title": "Mad Max: Fury Road", "year": 2015, "phase": "Fury Road", "aliases": ["Fury Road"]},
            {"title": "Furiosa: A Mad Max Saga", "year": 2024, "phase": "Furiosa Prequel", "aliases": ["Furiosa"]}
        ]
    }
]

from services.sagas_catalog import EXTRA_SAGAS
CURATED_SAGAS.extend(EXTRA_SAGAS)


def build_user_library_lookup(df):
    """
    Creates a pre-indexed fast lookup structure of user's watched movies
    for title, normalized title, aliases, year, rating, poster, and physical copy status.
    """
    lookup = []
    if df is None or df.empty:
        return lookup
        
    for idx, row in df.iterrows():
        title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "")
        year = None
        if pd.notna(row.get('Year')):
            yr_str = str(row.get('Year')).replace('.0', '').strip()
            if yr_str.isdigit():
                year = int(yr_str)
                
        user_rating = row.get('Rating') if ('Rating' in row and pd.notna(row.get('Rating'))) else None
        has_physical = bool(row.get('physical_copy')) if ('physical_copy' in row and pd.notna(row.get('physical_copy'))) else False
        poster = row.get('poster_path') if ('poster_path' in row and pd.notna(row.get('poster_path'))) else None
        tmdb_score = row.get('tmdb_rating') if ('tmdb_rating' in row and pd.notna(row.get('tmdb_rating'))) else None
        runtime = row.get('runtime') if ('runtime' in row and pd.notna(row.get('runtime'))) else None
        
        lookup.append({
            "idx": idx,
            "tmdb_id": int(row["tmdb_id"]) if pd.notna(row.get("tmdb_id")) else None,
            "title": str(title),
            "norm": normalize_title(title),
            "year": year,
            "user_rating": user_rating,
            "has_physical": has_physical,
            "poster_path": poster,
            "tmdb_rating": tmdb_score,
            "runtime": runtime
        })
        
    return lookup

def match_film(film_def, user_lookup):
    """ID first, then exact title/alias and year (never match a different remake)."""
    movie_id = film_def.get('tmdb_id')
    if movie_id:
        for item in user_lookup:
            if item.get('tmdb_id') == movie_id:
                return item
    names = {normalize_title(film_def['title'])}
    names.update(normalize_title(a) for a in film_def.get('aliases', []) if a)
    candidates = [item for item in user_lookup if item['norm'] in names]
    year = film_def.get('year')
    exact = [item for item in candidates if item['year'] == year]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1 and (year is None or candidates[0]['year'] is None):
        return candidates[0]
    return None


def read_cache(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return []


def write_cache(path, entries):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=directory, suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(entries, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def film_key(film):
    return normalize_title(film['title']), film.get('year')


def saga_catalog(include_tmdb_collections=True):
    """Merge fresh TMDb metadata and suppress duplicate standalone sagas.

    Universes retain their editorial membership: a TMDb collection describes a
    series, not necessarily an entire cinematic universe.
    """
    overrides = {s['id']: s for s in read_cache(CURATED_CACHE_FILE)}
    curated = []
    for original in CURATED_SAGAS:
        saga = dict(original)
        cached = overrides.get(saga['id'], {})
        details = {film_key(f): f for f in cached.get('films', [])}
        saga['films'] = [{**f, **details.get(film_key(f), {})} for f in saga['films']]
        known = {film_key(f) for f in saga['films']}
        saga['films'].extend(dict(f) for f in cached.get('films', []) if film_key(f) not in known)
        saga['updated_at'] = cached.get('updated_at')
        saga['source'] = 'curated'
        curated.append(saga)
    if not include_tmdb_collections:
        return curated
    collections = read_cache(CACHE_FILE)
    # Transfer available film details even when the containing universe stays curated.
    movie_details = {film_key(f): f for c in collections for f in c.get('films', [])}
    for saga in curated:
        for film in saga['films']:
            details = movie_details.get(film_key(film), {})
            for field in ('tmdb_id', 'poster_path', 'tmdb_rating', 'vote_count', 'release_date'):
                if details.get(field) is not None:
                    film[field] = details[field]
    result = list(curated)
    for collection in collections:
        collection = dict(collection, source='tmdb')
        keys = {film_key(f) for f in collection.get('films', [])}
        if not keys:
            continue
        duplicate = None
        for saga in curated:
            curated_keys = {film_key(f) for f in saga['films']}
            # Equal catalogs, or TMDb adds sequels to an existing standalone saga.
            if saga.get('category') == 'saga' and len(curated_keys) >= 2 and curated_keys <= keys:
                duplicate = saga
                break
        if duplicate is not None and duplicate in result:
            replacement = dict(collection, id=duplicate['id'], name=duplicate['name'])
            result[result.index(duplicate)] = replacement
        else:
            result.append(collection)
    return result


def release_state(film, today):
    release = film.get('release_date')
    if release:
        try:
            return 'released' if datetime.date.fromisoformat(release) <= today else 'upcoming'
        except ValueError:
            pass
    if 'release_date' in film:
        return 'unknown'
    if film.get('upcoming'):
        return 'unknown' if (film.get('year') or today.year) <= today.year else 'upcoming'
    if film.get('year') and film['year'] > today.year:
        return 'upcoming'
    return 'released'


def compute_sagas_progress(df, include_tmdb_collections=True, today=None):
    today = today or datetime.date.today()
    lookup = build_user_library_lookup(df)
    all_sagas = saga_catalog(include_tmdb_collections)
    groups = {'started_sagas': [], 'completed_sagas': [], 'unstarted_sagas': []}
    unique_watched, unique_physical = set(), set()
    for saga in all_sagas:
        films = []
        seen = set()
        for film in saga.get('films', []):
            identity = ('id', film['tmdb_id']) if film.get('tmdb_id') else film_key(film)
            if identity in seen:
                continue
            seen.add(identity)
            item = dict(film)
            item['release_state'] = release_state(item, today)
            item['upcoming'] = item['release_state'] != 'released'
            match = match_film(item, lookup)
            item.update(watched=match is not None, user_rating=None, has_physical=False)
            if match:
                item['user_rating'] = match['user_rating']
                item['has_physical'] = match['has_physical']
                item['poster_path'] = item.get('poster_path') or match['poster_path']
                item['tmdb_rating'] = item.get('tmdb_rating') or match['tmdb_rating']
                item['runtime'] = match['runtime']
                item['diary_title'] = match['title']
                identity = match.get('tmdb_id') or (match['norm'], match['year'])
                unique_watched.add(identity)
                if item['has_physical']:
                    unique_physical.add(identity)
            films.append(item)
        if not films:
            continue
        released = [f for f in films if f['release_state'] == 'released']
        watched = [f for f in films if f['watched']]
        released_watched = [f for f in released if f['watched']]
        ratings = [float(f['user_rating']) for f in watched if pd.notna(f['user_rating'])]
        scores = [float(f['tmdb_rating']) for f in released
                  if pd.notna(f.get('tmdb_rating')) and float(f['tmdb_rating']) > 0
                  and (f.get('vote_count') is None or f['vote_count'] > 0)]
        # Taste gap uses the same films on both scales (personal rating × 2).
        pairs = [float(f['user_rating']) * 2 - float(f['tmdb_rating']) for f in released_watched
                 if pd.notna(f['user_rating']) and pd.notna(f.get('tmdb_rating')) and f['tmdb_rating'] > 0]
        pct = len(released_watched) / len(released) * 100 if released else 0.0
        summary = dict(saga, total_films=len(films), released_films=len(released),
            watched_count=len(watched), remaining_count=len(released) - len(released_watched),
            upcoming_count=sum(f['release_state'] == 'upcoming' for f in films),
            unknown_release_count=sum(f['release_state'] == 'unknown' for f in films),
            progress_pct=round(pct, 1), is_complete=bool(released) and len(released_watched) == len(released),
            matched_films=watched, unmatched_films=[f for f in films if not f['watched']],
            all_films=sorted(films, key=lambda f: (f.get('release_date') or str(f.get('year') or 9999), f['title'])),
            avg_user_rating=round(float(np.mean(ratings)), 2) if ratings else None,
            avg_tmdb_rating=round(float(np.mean(scores)), 2) if scores else None,
            taste_gap=round(float(np.mean(pairs)), 2) if pairs else None,
            comparison_count=len(pairs), ratings_count=len(ratings), tmdb_ratings_count=len(scores),
            physical_count=sum(f['has_physical'] for f in watched))
        group = 'completed_sagas' if summary['is_complete'] else 'started_sagas' if watched else 'unstarted_sagas'
        groups[group].append(summary)
    groups['started_sagas'].sort(key=by_progress_desc)
    groups['completed_sagas'].sort(key=by_films_desc)
    groups['kpis'] = dict(total_sagas_tracked=sum(len(v) for v in groups.values()),
        started_count=len(groups['started_sagas']), completed_count=len(groups['completed_sagas']),
        unstarted_count=len(groups['unstarted_sagas']), total_franchise_films_watched=len(unique_watched),
        total_physical_films=len(unique_physical))
    return groups


def by_progress_desc(s):
    return -s['progress_pct'], -s['watched_count']

def by_films_desc(s):
    return -s['total_films'], s['name']

def scan_and_cache_tmdb_collections(df, max_movies=None, progress_callback=None):
    """Discover AND refresh collections, once each per scan, across the library."""
    key = get_tmdb_api_key()
    if not key:
        raise ValueError('Configure a TMDb API key in Settings / Impostazioni.')
    existing = {c['id']: c for c in read_cache(CACHE_FILE)}
    visited = set()
    report = dict(scanned=0, new=0, refreshed=0, failed=0, unmatched=0)
    rows = df if max_movies is None else df.head(max_movies)
    def request(path, **params):
        response = requests.get(f'https://api.themoviedb.org/3/{path}',
                                params=dict(api_key=key, **params), timeout=10)
        response.raise_for_status()
        return response.json()
    for _, row in rows.iterrows():
        try:
            collection_id = row.get('collection_id')
            if pd.isna(collection_id):
                movie_id = row.get('tmdb_id')
                if pd.isna(movie_id):
                    title = row.get('Name') if pd.notna(row.get('Name')) else row.get('Title')
                    year = row.get('Year')
                    params = {'query': title}
                    if pd.notna(year) and str(year).replace('.0', '').isdigit():
                        params['year'] = int(float(year))
                    candidates = request('search/movie', **params).get('results', [])
                    names = {normalize_title(title)}
                    candidates = [m for m in candidates if names & {normalize_title(m.get('title')), normalize_title(m.get('original_title'))}
                                  and ('year' not in params or (m.get('release_date') or '').startswith(str(params['year'])))]
                    if len(candidates) != 1:
                        report['unmatched'] += 1
                        continue
                    movie_id = candidates[0]['id']
                details = request(f'movie/{int(movie_id)}')
                collection_id = (details.get('belongs_to_collection') or {}).get('id')
            if not collection_id or pd.isna(collection_id):
                continue
            collection_id = int(collection_id)
            if collection_id in visited:
                continue
            visited.add(collection_id)
            details = request(f'collection/{collection_id}')
            films = []
            for part in details.get('parts', []):
                release = part.get('release_date') or ''
                films.append(dict(title=part.get('title') or part.get('original_title'),
                    year=int(release[:4]) if release[:4].isdigit() else None,
                    tmdb_id=part['id'], release_date=release, phase='Part',
                    aliases=[part['original_title']] if part.get('original_title') else [],
                    poster_path=part.get('poster_path'), tmdb_rating=part.get('vote_average'),
                    vote_count=part.get('vote_count')))
            cache_id = f'tmdb_col_{collection_id}'
            report['refreshed' if cache_id in existing else 'new'] += 1
            existing[cache_id] = dict(id=cache_id, name=details.get('name', 'TMDb Collection'),
                category='saga', tag='TMDb Collection', badge_color='#00A2FF',
                description=details.get('overview', ''), films=films,
                updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        except (requests.RequestException, ValueError, TypeError, KeyError):
            report['failed'] += 1
        finally:
            report['scanned'] += 1
            if progress_callback:
                progress_callback(report['scanned'], len(rows))
    if report['new'] or report['refreshed']:
        write_cache(CACHE_FILE, list(existing.values()))
    return report


def refresh_curated_saga(saga_id, progress_callback=None):
    """Refresh known universe members without claiming TMDb defines its canon."""
    key = get_tmdb_api_key()
    if not key:
        raise ValueError('Configure a TMDb API key in Settings / Impostazioni.')
    saga = next(s for s in saga_catalog(False) if s['id'] == saga_id)
    films, failed = [], 0
    for index, film in enumerate(saga['films']):
        movie_id = film.get('tmdb_id')
        meta = (fetch_movie_details_by_id(movie_id, key) if movie_id
                else fetch_movie_metadata(film['title'], film.get('year'), key))
        exact_title = meta and normalize_title(meta['title']) in {normalize_title(film['title']), *(normalize_title(a) for a in film.get('aliases', []))}
        if meta and (movie_id == meta.get('tmdb_id') or (exact_title and meta.get('year') == film.get('year'))):
            film = dict(film, **{k: meta.get(k) for k in ('tmdb_id', 'tmdb_rating', 'vote_count', 'release_date', 'poster_path')})
        else:
            failed += 1
        films.append(film)
        if progress_callback:
            progress_callback(index + 1, len(saga['films']))
    if failed < len(films):
        entries = {s['id']: s for s in read_cache(CURATED_CACHE_FILE)}
        entries[saga_id] = dict(id=saga_id, films=films, updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write_cache(CURATED_CACHE_FILE, list(entries.values()))
    return dict(updated=len(films) - failed, failed=failed)


def add_film_to_curated_saga(saga_id, movie_id, phase=''):
    """User-selected membership supplements the curated universe catalog."""
    meta = fetch_movie_details_by_id(movie_id, get_tmdb_api_key())
    if not meta:
        raise ValueError('TMDb: movie details unavailable / dettagli film non disponibili.')
    saga = next(s for s in saga_catalog(False) if s['id'] == saga_id)
    film = dict(title=meta['title'], year=meta.get('year'), phase=phase,
                aliases=[], **{k: meta.get(k) for k in
                ('tmdb_id', 'tmdb_rating', 'vote_count', 'release_date', 'poster_path')})
    if any(f.get('tmdb_id') == movie_id or film_key(f) == film_key(film) for f in saga['films']):
        return False
    entries = {s['id']: s for s in read_cache(CURATED_CACHE_FILE)}
    entries[saga_id] = dict(id=saga_id, films=saga['films'] + [film],
                           updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_cache(CURATED_CACHE_FILE, list(entries.values()))
    return True
