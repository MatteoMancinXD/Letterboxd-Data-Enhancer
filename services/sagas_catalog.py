"""Additional curated series. Thematic groups do not imply shared continuity.

Film years refer to original releases. Catalogs are explicit scopes, not a
promise to include future sequels. TMDb refresh can expand franchise collections.
"""

def series(sid, name, films, thematic=False, description='', category=None, badge_color=None):
    cat = category or ('thematic' if thematic else 'saga')
    default_color = '#40BCF4' if cat == 'thematic' else ('#E52E71' if cat == 'universe' else '#FF9B38')
    tag = 'Cinematic Universe' if cat == 'universe' else ('Thematic trilogy' if cat == 'thematic' else 'Film saga')
    parsed_films = []
    for f in films:
        if isinstance(f, dict):
            entry = dict(f)
            entry.setdefault('aliases', [])
            entry.setdefault('phase', '')
            parsed_films.append(entry)
        else:
            parsed_films.append(dict(title=f[0], year=f[1], aliases=list(f[2:]), phase=''))
    return dict(
        id=sid,
        name=name,
        category=cat,
        tag=tag,
        badge_color=badge_color or default_color,
        description=description or (
            'Films linked by themes or authorship, not a single narrative continuity.'
            if cat == 'thematic'
            else 'Curated film series; alternate continuities and remakes are counted separately.'
        ),
        films=parsed_films,
    )

EXTRA_SAGAS = [
series('halloween', 'Halloween', [
 ('Halloween',1978),('Halloween II',1981),('Halloween III: Season of the Witch',1982),
 ('Halloween 4: The Return of Michael Myers',1988),('Halloween 5: The Revenge of Michael Myers',1989,'Halloween 5'),
 ('Halloween: The Curse of Michael Myers',1995,'Halloween 6: The Curse of Michael Myers'),
 ('Halloween H20: 20 Years Later',1998,'Halloween H20: Twenty Years Later'),('Halloween: Resurrection',2002),
 ('Halloween',2007),('Halloween II',2009),('Halloween',2018),('Halloween Kills',2021),('Halloween Ends',2022)],
 description='The 13 theatrical films from 1978–2022, including the anthology entry and separate reboot timelines.'),
series('dollars', 'Dollars Trilogy / Trilogia del dollaro', [
 ('A Fistful of Dollars',1964,'Per un pugno di dollari'),('For a Few Dollars More',1965,'Per qualche dollaro in più'),
 ('The Good, the Bad and the Ugly',1966,'Il buono, il brutto, il cattivo')],True),
series('vengeance', 'Vengeance Trilogy / Trilogia della vendetta', [
 ('Sympathy for Mr. Vengeance',2002,'Mr. Vendetta'),('Oldboy',2003,'Old Boy'),
 ('Lady Vengeance',2005,'Sympathy for Lady Vengeance')],True),
series('three_colors', 'Three Colours / Tre colori', [
 ('Three Colours: Blue',1993,'Three Colors: Blue','Film blu'),('Three Colours: White',1994,'Three Colors: White','Film bianco'),
 ('Three Colours: Red',1994,'Three Colors: Red','Film rosso')],True),
series('carpenter_apocalypse', 'John Carpenter: Apocalypse Trilogy', [
 ('The Thing',1982,'La cosa'),('Prince of Darkness',1987,'Il signore del male'),('In the Mouth of Madness',1994,'Il seme della follia')],True),
series('depression_trilogy', 'Lars von Trier: Depression Trilogy', [
 ('Antichrist',2009),('Melancholia',2011),('Nymphomaniac: Vol. I',2013,'Nymphomaniac: Volume I'),
 ('Nymphomaniac: Vol. II',2013,'Nymphomaniac: Volume II')],True,
 'Three works linked by theme; Nymphomaniac is represented by its two separately logged volumes.'),
series('nightmare_elm_street', 'A Nightmare on Elm Street', [
 ('A Nightmare on Elm Street',1984),('A Nightmare on Elm Street Part 2: Freddy\'s Revenge',1985),
 ('A Nightmare on Elm Street 3: Dream Warriors',1987),('A Nightmare on Elm Street 4: The Dream Master',1988),
 ('A Nightmare on Elm Street: The Dream Child',1989,'A Nightmare on Elm Street 5: The Dream Child'),
 ('Freddy\'s Dead: The Final Nightmare',1991),('New Nightmare',1994,'Wes Craven\'s New Nightmare'),
 ('Freddy vs. Jason',2003),('A Nightmare on Elm Street',2010)]),
series('friday_13', 'Friday the 13th', [
 ('Friday the 13th',1980),('Friday the 13th Part 2',1981),('Friday the 13th Part III',1982,'Friday the 13th Part 3'),
 ('Friday the 13th: The Final Chapter',1984),('Friday the 13th: A New Beginning',1985),
 ('Friday the 13th Part VI: Jason Lives',1986),('Friday the 13th Part VII: The New Blood',1988),
 ('Friday the 13th Part VIII: Jason Takes Manhattan',1989),('Jason Goes to Hell: The Final Friday',1993),
 ('Jason X',2001),('Freddy vs. Jason',2003),('Friday the 13th',2009)]),
series('evil_dead', 'Evil Dead — 1981–2023', [
 ('The Evil Dead',1981,'La casa'),('Evil Dead II',1987,'Evil Dead 2','La casa 2'),
 ('Army of Darkness',1992,'L\'armata delle tenebre'),('Evil Dead',2013),('Evil Dead Rise',2023)]),
series('saw', 'Saw — 2004–2023', [
 ('Saw',2004),('Saw II',2005),('Saw III',2006),('Saw IV',2007),('Saw V',2008),('Saw VI',2009),
 ('Saw 3D',2010,'Saw: The Final Chapter'),('Jigsaw',2017),('Spiral: From the Book of Saw',2021,'Spiral'),('Saw X',2023)]),
series('rocky', 'Rocky', [('Rocky',1976),('Rocky II',1979),('Rocky III',1982),('Rocky IV',1985),('Rocky V',1990),('Rocky Balboa',2006)]),
series('creed', 'Creed — I–III', [('Creed',2015),('Creed II',2018),('Creed III',2023)]),
series('terminator', 'Terminator', [('The Terminator',1984,'Terminator'),('Terminator 2: Judgment Day',1991),
 ('Terminator 3: Rise of the Machines',2003),('Terminator Salvation',2009),('Terminator Genisys',2015),('Terminator: Dark Fate',2019)]),
series('underworld', 'Underworld', [('Underworld',2003),('Underworld: Evolution',2006),
 ('Underworld: Rise of the Lycans',2009),('Underworld: Awakening',2012),('Underworld: Blood Wars',2016)]),
series('resident_evil', 'Resident Evil — live action 2002–2021', [('Resident Evil',2002),('Resident Evil: Apocalypse',2004),
 ('Resident Evil: Extinction',2007),('Resident Evil: Afterlife',2010),('Resident Evil: Retribution',2012),
 ('Resident Evil: The Final Chapter',2016),('Resident Evil: Welcome to Raccoon City',2021)]),
series('blade', 'Blade Trilogy', [('Blade',1998),('Blade II',2002),('Blade: Trinity',2004)]),
series('rush_hour', 'Rush Hour Trilogy', [('Rush Hour',1998),('Rush Hour 2',2001),('Rush Hour 3',2007)]),
series('oceans', 'Ocean\'s Trilogy', [('Ocean\'s Eleven',2001),('Ocean\'s Twelve',2004),('Ocean\'s Thirteen',2007)]),
series('die_hard', 'Die Hard', [('Die Hard',1988,'Trappola di cristallo'),('Die Hard 2',1990),
 ('Die Hard with a Vengeance',1995),('Live Free or Die Hard',2007,'Die Hard 4.0'),('A Good Day to Die Hard',2013)]),
series('bourne', 'Jason Bourne', [('The Bourne Identity',2002),('The Bourne Supremacy',2004),
 ('The Bourne Ultimatum',2007),('The Bourne Legacy',2012),('Jason Bourne',2016)]),

# --- KAIJU & GIANT MONSTERS ---
series('godzilla_toho', 'Godzilla (Toho Live-Action Saga)', [
 ('Godzilla', 1954, 'Gojira'),
 ('Godzilla Raids Again', 1955),
 ('King Kong vs. Godzilla', 1962),
 ('Mothra vs. Godzilla', 1964),
 ('Ghidorah, the Three-Headed Monster', 1964),
 ('Invasion of Astro-Monster', 1965),
 ('Ebirah, Horror of the Deep', 1966),
 ('Son of Godzilla', 1967),
 ('Destroy All Monsters', 1968),
 ('All Monsters Attack', 1969),
 ('Godzilla vs. Hedorah', 1971),
 ('Godzilla vs. Gigan', 1972),
 ('Godzilla vs. Megalon', 1973),
 ('Godzilla vs. Mechagodzilla', 1974),
 ('Terror of Mechagodzilla', 1975),
 ('The Return of Godzilla', 1984, 'Godzilla 1985'),
 ('Godzilla vs. Biollante', 1989),
 ('Godzilla vs. King Ghidorah', 1991),
 ('Godzilla vs. Mothra', 1992),
 ('Godzilla vs. Mechagodzilla II', 1993),
 ('Godzilla vs. SpaceGodzilla', 1994),
 ('Godzilla vs. Destoroyah', 1995),
 ('Godzilla 2000: Millennium', 1999, 'Godzilla 2000'),
 ('Godzilla vs. Megaguirus', 2000),
 ('Godzilla, Mothra and King Ghidorah: Giant Monsters All-Out Attack', 2001),
 ('Godzilla Against Mechagodzilla', 2002),
 ('Godzilla: Tokyo S.O.S.', 2003),
 ('Godzilla: Final Wars', 2004),
 ('Shin Godzilla', 2016),
 ('Godzilla Minus One', 2023),
 dict(title='Godzilla Minus Zero', year=2026, release_date='2026-11-06'),
], category='universe', badge_color='#00E054',
 description='All 31 Toho live-action Godzilla theatrical features spanning Showa, Heisei, Millennium, and Reiwa eras.'),
series('godzilla_minus', 'Godzilla Minus Saga (Takashi Yamazaki)', [
 ('Godzilla Minus One', 2023),
 dict(title='Godzilla Minus Zero', year=2026, release_date='2026-11-06'),
]),
series('king_kong', 'King Kong', [
 ('King Kong', 1933),
 ('The Son of Kong', 1933, 'Son of Kong'),
 ('King Kong vs. Godzilla', 1962),
 ('King Kong Escapes', 1967),
 ('King Kong', 1976),
 ('King Kong Lives', 1986),
 ('King Kong', 2005),
 ('Kong: Skull Island', 2017, 'Skull Island'),
 ('Godzilla vs. Kong', 2021),
 ('Godzilla x Kong: The New Empire', 2024, 'The New Empire'),
], category='universe', badge_color='#FFC107',
 description='All 10 theatrical King Kong feature appearances from the 1933 classic through the MonsterVerse.'),

# --- ICONIC ACTION, SCI-FI & ADVENTURE ---
series('robocop', 'RoboCop', [
 ('RoboCop', 1987), ('RoboCop 2', 1990), ('RoboCop 3', 1993), ('RoboCop', 2014),
]),
series('men_in_black', 'Men in Black', [
 ('Men in Black', 1997, 'MIB'),
 ('Men in Black II', 2002, 'Men in Black 2', 'MIB 2'),
 ('Men in Black 3', 2012, 'Men in Black III', 'MIB 3'),
 ('Men in Black: International', 2019),
]),
series('bad_boys', 'Bad Boys', [
 ('Bad Boys', 1995),
 ('Bad Boys II', 2003, 'Bad Boys 2'),
 ('Bad Boys for Life', 2020, 'Bad Boys 3'),
 ('Bad Boys: Ride or Die', 2024, 'Bad Boys 4'),
]),
series('rambo', 'Rambo', [
 ('First Blood', 1982, 'Rambo'),
 ('Rambo: First Blood Part II', 1985, 'Rambo 2'),
 ('Rambo III', 1988, 'Rambo 3'),
 ('Rambo', 2008, 'John Rambo'),
 ('Rambo: Last Blood', 2019, 'Rambo 5'),
]),
series('lethal_weapon', 'Lethal Weapon / Arma letale', [
 ('Lethal Weapon', 1987, 'Arma letale'),
 ('Lethal Weapon 2', 1989),
 ('Lethal Weapon 3', 1992),
 ('Lethal Weapon 4', 1998),
]),
series('beverly_hills_cop', 'Beverly Hills Cop', [
 ('Beverly Hills Cop', 1984),
 ('Beverly Hills Cop II', 1987, 'Beverly Hills Cop 2'),
 ('Beverly Hills Cop III', 1994, 'Beverly Hills Cop 3'),
 ('Beverly Hills Cop: Axel F', 2024),
]),
series('ghostbusters', 'Ghostbusters', [
 ('Ghostbusters', 1984),
 ('Ghostbusters II', 1989, 'Ghostbusters 2'),
 ('Ghostbusters', 2016, 'Ghostbusters: Answer the Call'),
 ('Ghostbusters: Afterlife', 2021),
 ('Ghostbusters: Frozen Empire', 2024),
]),
series('james_bond_complete', 'James Bond 007 (Complete Eon Saga)', [
 ('Dr. No', 1962),
 ('From Russia with Love', 1963),
 ('Goldfinger', 1964),
 ('Thunderball', 1965),
 ('You Only Live Twice', 1967),
 ('On Her Majesty\'s Secret Service', 1969),
 ('Diamonds Are Forever', 1971),
 ('Live and Let Die', 1973),
 ('The Man with the Golden Gun', 1974),
 ('The Spy Who Loved Me', 1977),
 ('Moonraker', 1979),
 ('For Your Eyes Only', 1981),
 ('Octopussy', 1983),
 ('A View to a Kill', 1985),
 ('The Living Daylights', 1987),
 ('Licence to Kill', 1989),
 ('GoldenEye', 1995),
 ('Tomorrow Never Dies', 1997),
 ('The World Is Not Enough', 1999),
 ('Die Another Day', 2002),
 ('Casino Royale', 2006),
 ('Quantum of Solace', 2008),
 ('Skyfall', 2012),
 ('Spectre', 2015),
 ('No Time to Die', 2021),
], category='universe', badge_color='#00E054',
 description='All 25 official Eon Productions James Bond 007 theatrical films from Dr. No (1962) to No Time to Die (2021).'),
series('star_trek', 'Star Trek (Complete Film Saga)', [
 ('Star Trek: The Motion Picture', 1979),
 ('Star Trek II: The Wrath of Khan', 1982),
 ('Star Trek III: The Search for Spock', 1984),
 ('Star Trek IV: The Voyage Home', 1986),
 ('Star Trek V: The Final Frontier', 1989),
 ('Star Trek VI: The Undiscovered Country', 1991),
 ('Star Trek Generations', 1994, 'Star Trek: Generations'),
 ('Star Trek: First Contact', 1996),
 ('Star Trek: Insurrection', 1998),
 ('Star Trek: Nemesis', 2002),
 ('Star Trek', 2009),
 ('Star Trek Into Darkness', 2013),
 ('Star Trek Beyond', 2016),
], category='universe', badge_color='#40BCF4',
 description='All 13 theatrical Star Trek feature films across the Original Crew, Next Generation, and Kelvin timelines.'),
series('transformers', 'Transformers', [
 ('Transformers', 2007),
 ('Transformers: Revenge of the Fallen', 2009),
 ('Transformers: Dark of the Moon', 2011),
 ('Transformers: Age of Extinction', 2014),
 ('Transformers: The Last Knight', 2017),
 ('Bumblebee', 2018),
 ('Transformers: Rise of the Beasts', 2023),
 ('Transformers One', 2024),
], category='universe', badge_color='#40BCF4'),
series('the_mummy', 'The Mummy', [
 ('The Mummy', 1999, 'La mummia'),
 ('The Mummy Returns', 2001),
 ('The Mummy: Tomb of the Dragon Emperor', 2008),
 ('The Mummy', 2017),
]),
series('planet_of_the_apes_classic', 'Planet of the Apes (Classic 1968–1973)', [
 ('Planet of the Apes', 1968),
 ('Beneath the Planet of the Apes', 1970),
 ('Escape from the Planet of the Apes', 1971),
 ('Conquest of the Planet of the Apes', 1972),
 ('Battle for the Planet of the Apes', 1973),
]),
series('blade_runner', 'Blade Runner', [
 ('Blade Runner', 1982), ('Blade Runner 2049', 2017),
]),
series('tron', 'Tron', [
 ('Tron', 1982),
 ('Tron: Legacy', 2010),
 dict(title='Tron: Ares', year=2025, release_date='2025-10-10'),
]),
series('kill_bill', 'Kill Bill', [
 ('Kill Bill: Vol. 1', 2003, 'Kill Bill: Volume 1', 'Kill Bill Vol. 1'),
 ('Kill Bill: Vol. 2', 2004, 'Kill Bill: Volume 2', 'Kill Bill Vol. 2'),
]),
series('top_gun', 'Top Gun', [
 ('Top Gun', 1986), ('Top Gun: Maverick', 2022),
]),
series('gladiator', 'Gladiator', [
 ('Gladiator', 2000, 'Il gladiatore'), ('Gladiator II', 2024, 'Gladiator 2'),
]),
series('jumanji', 'Jumanji', [
 ('Jumanji', 1995), ('Jumanji: Welcome to the Jungle', 2017), ('Jumanji: The Next Level', 2019),
]),
series('karate_kid', 'The Karate Kid', [
 ('The Karate Kid', 1984),
 ('The Karate Kid Part II', 1986, 'The Karate Kid 2'),
 ('The Karate Kid Part III', 1989, 'The Karate Kid 3'),
 ('The Next Karate Kid', 1994),
 ('The Karate Kid', 2010),
 dict(title='Karate Kid: Legends', year=2025, release_date='2025-05-30'),
]),
series('kingsman', 'Kingsman', [
 ('Kingsman: The Secret Service', 2014),
 ('Kingsman: The Golden Circle', 2017),
 ('The King\'s Man', 2021),
]),
series('taken', 'Taken', [
 ('Taken', 2008, 'Io vi troverò'), ('Taken 2', 2012), ('Taken 3', 2014, 'Tak3n'),
]),
series('equalizer', 'The Equalizer', [
 ('The Equalizer', 2014), ('The Equalizer 2', 2018), ('The Equalizer 3', 2023),
]),
series('expendables', 'The Expendables / I mercenari', [
 ('The Expendables', 2010), ('The Expendables 2', 2012), ('The Expendables 3', 2014),
 ('Expend4bles', 2023, 'The Expendables 4'),
]),
series('knives_out', 'Knives Out (Benoit Blanc Mysteries)', [
 ('Knives Out', 2019, 'Cena con delitto'),
 ('Glass Onion', 2022, 'Glass Onion: A Knives Out Mystery'),
 dict(title='Wake Up Dead Man', year=2025, release_date='2025-11-26', aliases=['Wake Up Dead Man: A Knives Out Mystery']),
]),
series('now_you_see_me', 'Now You See Me', [
 ('Now You See Me', 2013),
 ('Now You See Me 2', 2016),
 dict(title='Now You See Me: Now You Don\'t', year=2025, release_date='2025-11-14', aliases=['Now You See Me 3']),
]),
series('national_treasure', 'National Treasure', [
 ('National Treasure', 2004, 'Il mistero dei Templari'),
 ('National Treasure: Book of Secrets', 2007),
]),
series('night_at_the_museum', 'Night at the Museum', [
 ('Night at the Museum', 2006),
 ('Night at the Museum: Battle of the Smithsonian', 2009),
 ('Night at the Museum: Secret of the Tomb', 2014),
]),
series('sherlock_holmes', 'Sherlock Holmes (Guy Ritchie)', [
 ('Sherlock Holmes', 2009), ('Sherlock Holmes: A Game of Shadows', 2011),
]),
series('tmnt', 'Teenage Mutant Ninja Turtles', [
 ('Teenage Mutant Ninja Turtles', 1990),
 ('Teenage Mutant Ninja Turtles II: The Secret of the Ooze', 1991),
 ('Teenage Mutant Ninja Turtles III', 1993),
 ('TMNT', 2007),
 ('Teenage Mutant Ninja Turtles', 2014),
 ('Teenage Mutant Ninja Turtles: Out of the Shadows', 2016),
 ('Teenage Mutant Ninja Turtles: Mutant Mayhem', 2023),
]),
series('narnia', 'The Chronicles of Narnia', [
 ('The Chronicles of Narnia: The Lion, the Witch and the Wardrobe', 2005),
 ('The Chronicles of Narnia: Prince Caspian', 2008),
 ('The Chronicles of Narnia: The Voyage of the Dawn Treader', 2010),
]),
series('maze_runner', 'The Maze Runner Trilogy', [
 ('The Maze Runner', 2014),
 ('Maze Runner: The Scorch Trials', 2015, 'The Maze Runner: The Scorch Trials'),
 ('Maze Runner: The Death Cure', 2018, 'The Maze Runner: The Death Cure'),
]),
series('twilight', 'The Twilight Saga', [
 ('Twilight', 2008),
 ('The Twilight Saga: New Moon', 2009, 'New Moon'),
 ('The Twilight Saga: Eclipse', 2010, 'Eclipse'),
 ('The Twilight Saga: Breaking Dawn - Part 1', 2011, 'Breaking Dawn - Part 1'),
 ('The Twilight Saga: Breaking Dawn - Part 2', 2012, 'Breaking Dawn - Part 2'),
]),
series('trainspotting', 'Trainspotting', [
 ('Trainspotting', 1996), ('T2 Trainspotting', 2017, 'Trainspotting 2'),
]),
series('sicario', 'Sicario', [
 ('Sicario', 2015), ('Sicario: Day of the Soldado', 2018, 'Soldado'),
]),

# --- SUPERHEROES ---
series('dcu', 'DC Universe (DCU — James Gunn Era)', [
 dict(title='Superman', year=2025, release_date='2025-07-11'),
 dict(title='Supergirl', year=2026, release_date='2026-06-26', aliases=['Supergirl: Woman of Tomorrow']),
 dict(title='Clayface', year=2026, release_date='2026-10-23'),
], category='universe', badge_color='#00A2FF',
 description='James Gunn and Peter Safran\'s rebooted DC Universe (Chapter One: Gods and Monsters) theatrical slate.'),
series('batman_classic', 'Batman (Burton & Schumacher Era)', [
 ('Batman', 1989), ('Batman Returns', 1992), ('Batman Forever', 1995), ('Batman & Robin', 1997),
]),
series('superman_classic', 'Superman (Christopher Reeve / Classic Era)', [
 ('Superman', 1978, 'Superman: The Movie'),
 ('Superman II', 1980),
 ('Superman III', 1983),
 ('Superman IV: The Quest for Peace', 1987),
 ('Superman Returns', 2006),
]),
series('amazing_spider_man', 'The Amazing Spider-Man', [
 ('The Amazing Spider-Man', 2012), ('The Amazing Spider-Man 2', 2014),
]),
series('spider_man_mcu', 'Spider-Man (MCU — Tom Holland)', [
 ('Spider-Man: Homecoming', 2017),
 ('Spider-Man: Far From Home', 2019),
 ('Spider-Man: No Way Home', 2021),
 dict(title='Spider-Man: Brand New Day', year=2026, release_date='2026-07-31', aliases=['Spider-Man 4']),
]),
series('venom', 'Venom Trilogy', [
 ('Venom', 2018),
 ('Venom: Let There Be Carnage', 2021, 'Venom 2'),
 ('Venom: The Last Dance', 2024, 'Venom 3'),
]),
series('deadpool', 'Deadpool Trilogy', [
 ('Deadpool', 2016), ('Deadpool 2', 2018), ('Deadpool & Wolverine', 2024, 'Deadpool 3'),
]),
series('fantastic_four', 'Fantastic Four (Theatrical Films)', [
 ('Fantastic Four', 2005, 'Fantastic 4'),
 ('Fantastic Four: Rise of the Silver Surfer', 2007, 'Fantastic 4: Rise of the Silver Surfer'),
 ('Fantastic Four', 2015, 'Fant4stic'),
 dict(title='The Fantastic Four: First Steps', year=2025, release_date='2025-07-25', aliases=['The Fantastic 4: First Steps', 'Fantastic Four: First Steps', 'Fantastic 4: First Steps']),
]),

# --- HORROR & THRILLER ---
series('conjuring_universe', 'The Conjuring Universe', [
 ('The Conjuring', 2013),
 ('Annabelle', 2014),
 ('The Conjuring 2', 2016),
 ('Annabelle: Creation', 2017),
 ('The Nun', 2018),
 ('The Curse of La Llorona', 2019),
 ('Annabelle Comes Home', 2019),
 ('The Conjuring: The Devil Made Me Do It', 2021),
 ('The Nun II', 2023, 'The Nun 2'),
 dict(title='The Conjuring: Last Rites', year=2025, release_date='2025-09-05'),
], category='universe', badge_color='#E52E71',
 description='James Wan\'s interconnected supernatural horror universe: The Conjuring, Annabelle, The Nun, and La Llorona.'),
series('scream', 'Scream', [
 ('Scream', 1996),
 ('Scream 2', 1997),
 ('Scream 3', 2000),
 ('Scream 4', 2011, 'Scream IV'),
 ('Scream', 2022, 'Scream 5'),
 ('Scream VI', 2023, 'Scream 6'),
 dict(title='Scream 7', year=2026, release_date='2026-02-27', aliases=['Scream VII']),
]),
series('final_destination', 'Final Destination', [
 ('Final Destination', 2000),
 ('Final Destination 2', 2003),
 ('Final Destination 3', 2006),
 ('The Final Destination', 2009, 'Final Destination 4'),
 ('Final Destination 5', 2011),
 dict(title='Final Destination Bloodlines', year=2025, release_date='2025-05-16', aliases=['Final Destination: Bloodlines']),
]),
series('28_days_later', '28 Days Later Saga', [
 ('28 Days Later', 2002),
 ('28 Weeks Later', 2007),
 dict(title='28 Years Later', year=2025, release_date='2025-06-20'),
 dict(title='28 Years Later: The Bone Temple', year=2026, release_date='2026-01-16'),
]),
series('insidious', 'Insidious', [
 ('Insidious', 2010),
 ('Insidious: Chapter 2', 2013),
 ('Insidious: Chapter 3', 2015),
 ('Insidious: The Last Key', 2018),
 ('Insidious: The Red Door', 2023),
 dict(title='Insidious: Out of the Further', year=2026, release_date='2026-08-21', aliases=['Insidious: The Bleeding World']),
]),
series('childs_play', 'Child\'s Play / Chucky', [
 ('Child\'s Play', 1988, 'La bambola assassina'),
 ('Child\'s Play 2', 1990),
 ('Child\'s Play 3', 1991),
 ('Bride of Chucky', 1998),
 ('Seed of Chucky', 2004),
 ('Curse of Chucky', 2013),
 ('Cult of Chucky', 2017),
 ('Child\'s Play', 2019),
]),
series('texas_chainsaw', 'The Texas Chainsaw Massacre', [
 ('The Texas Chain Saw Massacre', 1974, 'The Texas Chainsaw Massacre'),
 ('The Texas Chainsaw Massacre 2', 1986),
 ('Leatherface: The Texas Chainsaw Massacre III', 1990, 'Leatherface: Texas Chainsaw Massacre III'),
 ('Texas Chainsaw Massacre: The Next Generation', 1994, 'The Return of the Texas Chainsaw Massacre'),
 ('The Texas Chainsaw Massacre', 2003),
 ('The Texas Chainsaw Massacre: The Beginning', 2006),
 ('Texas Chainsaw 3D', 2013, 'Texas Chainsaw'),
 ('Leatherface', 2017),
 ('Texas Chainsaw Massacre', 2022),
]),
series('hellraiser', 'Hellraiser', [
 ('Hellraiser', 1987),
 ('Hellbound: Hellraiser II', 1988, 'Hellraiser II'),
 ('Hellraiser III: Hell on Earth', 1992),
 ('Hellraiser: Bloodline', 1996),
 ('Hellraiser: Inferno', 2000),
 ('Hellraiser: Hellseeker', 2002),
 ('Hellraiser: Deader', 2005),
 ('Hellraiser: Hellworld', 2005),
 ('Hellraiser: Revelations', 2011),
 ('Hellraiser: Judgment', 2018),
 ('Hellraiser', 2022),
]),
series('the_exorcist', 'The Exorcist', [
 ('The Exorcist', 1973, 'L\'esorcista'),
 ('Exorcist II: The Heretic', 1977),
 ('The Exorcist III', 1990),
 ('Exorcist: The Beginning', 2004),
 ('Dominion: Prequel to the Exorcist', 2005),
 ('The Exorcist: Believer', 2023),
]),
series('a_quiet_place', 'A Quiet Place', [
 ('A Quiet Place', 2018),
 ('A Quiet Place Part II', 2020, 'A Quiet Place 2'),
 ('A Quiet Place: Day One', 2024),
]),
series('cloverfield', 'Cloverfield', [
 ('Cloverfield', 2008), ('10 Cloverfield Lane', 2016), ('The Cloverfield Paradox', 2018),
]),
series('the_purge', 'The Purge', [
 ('The Purge', 2013),
 ('The Purge: Anarchy', 2014),
 ('The Purge: Election Year', 2016),
 ('The First Purge', 2018),
 ('The Forever Purge', 2021),
]),
series('hannibal_lecter', 'Hannibal Lecter', [
 ('Manhunter', 1986),
 ('The Silence of the Lambs', 1991, 'Il silenzio degli innocenti'),
 ('Hannibal', 2001),
 ('Red Dragon', 2002),
 ('Hannibal Rising', 2007),
]),
series('jaws', 'Jaws / Lo squalo', [
 ('Jaws', 1975, 'Lo squalo'),
 ('Jaws 2', 1978),
 ('Jaws 3-D', 1983, 'Jaws 3'),
 ('Jaws: The Revenge', 1987),
]),
series('psycho', 'Psycho', [
 ('Psycho', 1960),
 ('Psycho II', 1983),
 ('Psycho III', 1986),
 ('Psycho IV: The Beginning', 1990),
 ('Psycho', 1998),
]),
series('the_shining', 'The Shining', [
 ('The Shining', 1980, 'Shining'), ('Doctor Sleep', 2019),
]),
series('rec_saga', '[REC]', [
 ('[REC]', 2007, 'REC', '[•REC]'),
 ('[REC]²', 2009, 'REC 2', '[REC] 2', '[•REC]²'),
 ('[REC]³: Genesis', 2012, 'REC 3: Genesis', '[REC] 3: Genesis'),
 ('[REC] 4: Apocalypse', 2014, 'REC 4: Apocalypse', '[REC]⁴: Apocalypse'),
]),
series('romero_dead', 'George A. Romero: Dead Trilogy', [
 ('Night of the Living Dead', 1968),
 ('Dawn of the Dead', 1978, 'Zombi'),
 ('Day of the Dead', 1985),
]),
series('terrifier', 'Terrifier', [
 ('Terrifier', 2016), ('Terrifier 2', 2022), ('Terrifier 3', 2024),
]),
series('smile_saga', 'Smile', [
 ('Smile', 2022), ('Smile 2', 2024),
]),
series('black_phone', 'The Black Phone', [
 ('The Black Phone', 2021),
 dict(title='Black Phone 2', year=2025, release_date='2025-10-17', aliases=['The Black Phone 2']),
]),

# --- ANIMATION & FAMILY ---
series('kung_fu_panda', 'Kung Fu Panda', [
 ('Kung Fu Panda', 2008), ('Kung Fu Panda 2', 2011), ('Kung Fu Panda 3', 2016), ('Kung Fu Panda 4', 2024),
]),
series('how_to_train_your_dragon', 'How to Train Your Dragon', [
 ('How to Train Your Dragon', 2010, 'Dragon Trainer'),
 ('How to Train Your Dragon 2', 2014),
 ('How to Train Your Dragon: The Hidden World', 2019),
 dict(title='How to Train Your Dragon', year=2025, release_date='2025-06-13'),
]),
series('despicable_me', 'Despicable Me & Minions', [
 ('Despicable Me', 2010, 'Cattivissimo me'),
 ('Despicable Me 2', 2013),
 ('Minions', 2015),
 ('Despicable Me 3', 2017),
 ('Minions: The Rise of Gru', 2022),
 ('Despicable Me 4', 2024),
 dict(title='Minions & Monsters', year=2026, release_date='2026-07-01', aliases=['Minions 3']),
], category='universe', badge_color='#FFC107'),
series('ice_age', 'Ice Age / L\'era glaciale', [
 ('Ice Age', 2002, 'L\'era glaciale'),
 ('Ice Age: The Meltdown', 2006, 'Ice Age 2'),
 ('Ice Age: Dawn of the Dinosaurs', 2009, 'Ice Age 3'),
 ('Ice Age: Continental Drift', 2012, 'Ice Age 4'),
 ('Ice Age: Collision Course', 2016, 'Ice Age 5'),
 ('The Ice Age Adventures of Buck Wild', 2022),
]),
series('madagascar', 'Madagascar', [
 ('Madagascar', 2005),
 ('Madagascar: Escape 2 Africa', 2008, 'Madagascar 2'),
 ('Madagascar 3: Europe\'s Most Wanted', 2012, 'Madagascar 3'),
 ('Penguins of Madagascar', 2014),
]),
series('cars_pixar', 'Cars (Pixar)', [
 ('Cars', 2006), ('Cars 2', 2011), ('Cars 3', 2017),
]),
series('incredibles', 'The Incredibles', [
 ('The Incredibles', 2004, 'Gli Incredibili'), ('Incredibles 2', 2018),
]),
series('finding_nemo', 'Finding Nemo', [
 ('Finding Nemo', 2003, 'Alla ricerca di Nemo'), ('Finding Dory', 2016),
]),
series('monsters_inc', 'Monsters, Inc.', [
 ('Monsters, Inc.', 2001, 'Monsters & Co.'), ('Monsters University', 2013),
]),
series('inside_out', 'Inside Out', [
 ('Inside Out', 2015), ('Inside Out 2', 2024),
]),
series('frozen', 'Frozen', [
 ('Frozen', 2013), ('Frozen II', 2019, 'Frozen 2'),
]),
series('zootopia', 'Zootopia', [
 ('Zootopia', 2016, 'Zootropolis'),
 dict(title='Zootopia 2', year=2025, release_date='2025-11-26', aliases=['Zootropolis 2']),
]),
series('moana', 'Moana / Oceania', [
 ('Moana', 2016, 'Oceania'), ('Moana 2', 2024, 'Oceania 2'),
]),
series('sonic', 'Sonic the Hedgehog', [
 ('Sonic the Hedgehog', 2020), ('Sonic the Hedgehog 2', 2022), ('Sonic the Hedgehog 3', 2024),
]),
series('paddington', 'Paddington', [
 ('Paddington', 2014), ('Paddington 2', 2017), ('Paddington in Peru', 2024),
]),

# --- COMEDY & CULT CLASSICS ---
series('the_hangover', 'The Hangover Trilogy / Una notte da leoni', [
 ('The Hangover', 2009, 'Una notte da leoni'),
 ('The Hangover Part II', 2011, 'The Hangover 2'),
 ('The Hangover Part III', 2013, 'The Hangover 3'),
]),
series('home_alone', 'Home Alone / Mamma, ho perso l\'aereo', [
 ('Home Alone', 1990),
 ('Home Alone 2: Lost in New York', 1992),
 ('Home Alone 3', 1997),
 ('Home Alone 4', 2002),
 ('Home Alone: The Holiday Heist', 2012),
 ('Home Sweet Home Alone', 2021),
]),
series('scary_movie', 'Scary Movie', [
 ('Scary Movie', 2000),
 ('Scary Movie 2', 2001),
 ('Scary Movie 3', 2003),
 ('Scary Movie 4', 2006),
 ('Scary Movie 5', 2013, 'Scary Movie V'),
 dict(title='Scary Movie', year=2026, release_date='2026-06-05', aliases=['Scary Movie 6']),
]),
series('american_pie', 'American Pie (Original Quartet)', [
 ('American Pie', 1999),
 ('American Pie 2', 2001),
 ('American Wedding', 2003, 'American Pie: The Wedding'),
 ('American Reunion', 2012, 'American Pie: Reunion'),
]),
series('austin_powers', 'Austin Powers Trilogy', [
 ('Austin Powers: International Man of Mystery', 1997),
 ('Austin Powers: The Spy Who Shagged Me', 1999),
 ('Austin Powers in Goldmember', 2002),
]),
series('naked_gun', 'The Naked Gun / Una pallottola spuntata', [
 ('The Naked Gun: From the Files of Police Squad!', 1988, 'The Naked Gun'),
 ('The Naked Gun 2½: The Smell of Fear', 1991),
 ('Naked Gun 33⅓: The Final Insult', 1994, 'The Naked Gun 33 1/3: The Final Insult'),
 dict(title='The Naked Gun', year=2025, release_date='2025-08-01'),
]),
series('gremlins', 'Gremlins', [
 ('Gremlins', 1984), ('Gremlins 2: The New Batch', 1990),
]),
series('beetlejuice', 'Beetlejuice', [
 ('Beetlejuice', 1988), ('Beetlejuice Beetlejuice', 2024),
]),
]
