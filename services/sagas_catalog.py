"""Additional curated series. Thematic groups do not imply shared continuity.

Film years refer to original releases. Catalogs are explicit scopes, not a
promise to include future sequels. TMDb refresh can expand franchise collections.
"""

def series(sid, name, films, thematic=False, description=''):
    return dict(id=sid, name=name, category='thematic' if thematic else 'saga',
        tag='Thematic trilogy' if thematic else 'Film saga', badge_color='#40BCF4' if thematic else '#FF9B38',
        description=description or ('Films linked by themes or authorship, not a single narrative continuity.' if thematic else 'Curated film series; alternate continuities and remakes are counted separately.'),
        films=[dict(title=f[0], year=f[1], aliases=list(f[2:]), phase='') for f in films])

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
]
