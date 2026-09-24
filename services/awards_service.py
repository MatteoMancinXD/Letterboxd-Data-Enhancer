# services/awards_service.py
import re
import pandas as pd
import numpy as np

# Comprehensive registry of iconic Oscar, Cannes, and Venice winners
# Keyed by standardized lower-case title
AWARDS_REGISTRY = {
    # --- 2020s ---
    "anora": {"year": 2024, "cannes": ["Palme d'Or (2024)"]},
    "the room next door": {"year": 2024, "venice": ["Golden Lion (2024)"]},
    "oppenheimer": {"year": 2023, "oscars": ["Best Picture (2024)", "Best Director", "Best Actor", "Best Supp. Actor"]},
    "anatomy of a fall": {"year": 2023, "cannes": ["Palme d'Or (2023)"], "oscars": ["Best Original Screenplay"]},
    "poor things": {"year": 2023, "venice": ["Golden Lion (2023)"], "oscars": ["Best Actress", "Best Production Design"]},
    "the zone of interest": {"year": 2023, "cannes": ["Grand Prix (2023)"], "oscars": ["Best International Feature", "Best Sound"]},
    "everything everywhere all at once": {"year": 2022, "oscars": ["Best Picture (2023)", "Best Director", "Best Actress", "Best Supp. Actor", "Best Supp. Actress"]},
    "triangle of sadness": {"year": 2022, "cannes": ["Palme d'Or (2022)"]},
    "all the beauty and the bloodshed": {"year": 2022, "venice": ["Golden Lion (2022)"]},
    "the banshees of inisherin": {"year": 2022, "venice": ["Volpi Cup (Best Actor)", "Best Screenplay"]},
    "coda": {"year": 2021, "oscars": ["Best Picture (2022)", "Best Supp. Actor", "Best Adapted Screenplay"]},
    "titane": {"year": 2021, "cannes": ["Palme d'Or (2021)"]},
    "happening": {"year": 2021, "venice": ["Golden Lion (2021)"]},
    "drive my car": {"year": 2021, "cannes": ["Best Screenplay"], "oscars": ["Best International Feature"]},
    "dune": {"year": 2021, "oscars": ["6 Academy Awards (Visual Effects, Score, Sound, Editing, Cinematography, Production)"]},
    "nomadland": {"year": 2020, "venice": ["Golden Lion (2020)"], "oscars": ["Best Picture (2021)", "Best Director", "Best Actress"]},
    "another round": {"year": 2020, "oscars": ["Best International Feature (2021)"]},
    "the father": {"year": 2020, "oscars": ["Best Actor", "Best Adapted Screenplay"]},

    # --- 2010s ---
    "parasite": {"year": 2019, "cannes": ["Palme d'Or (2019)"], "oscars": ["Best Picture (2020)", "Best Director", "Best Original Screenplay", "Best International Feature"]},
    "joker": {"year": 2019, "venice": ["Golden Lion (2019)"], "oscars": ["Best Actor", "Best Original Score"]},
    "green book": {"year": 2018, "oscars": ["Best Picture (2019)", "Best Supp. Actor", "Best Original Screenplay"]},
    "roma": {"year": 2018, "venice": ["Golden Lion (2018)"], "oscars": ["Best Director", "Best Foreign Language Film", "Best Cinematography"]},
    "shoplifters": {"year": 2018, "cannes": ["Palme d'Or (2018)"]},
    "the shape of water": {"year": 2017, "venice": ["Golden Lion (2017)"], "oscars": ["Best Picture (2018)", "Best Director", "Best Original Score", "Best Production Design"]},
    "the square": {"year": 2017, "cannes": ["Palme d'Or (2017)"]},
    "three billboards outside ebbing, missouri": {"year": 2017, "venice": ["Best Screenplay"], "oscars": ["Best Actress", "Best Supp. Actor"]},
    "moonlight": {"year": 2016, "oscars": ["Best Picture (2017)", "Best Supp. Actor", "Best Adapted Screenplay"]},
    "la la land": {"year": 2016, "oscars": ["Best Director (2017)", "Best Actress", "Best Original Score", "Best Cinematography"]},
    "i, daniel blake": {"year": 2016, "cannes": ["Palme d'Or (2016)"]},
    "the woman who left": {"year": 2016, "venice": ["Golden Lion (2016)"]},
    "spotlight": {"year": 2015, "oscars": ["Best Picture (2016)", "Best Original Screenplay"]},
    "dheepan": {"year": 2015, "cannes": ["Palme d'Or (2015)"]},
    "from afar": {"year": 2015, "venice": ["Golden Lion (2015)"]},
    "mad max: fury road": {"year": 2015, "oscars": ["6 Academy Awards (Editing, Sound, Production, Costumes, Makeup)"]},
    "the revenant": {"year": 2015, "oscars": ["Best Director", "Best Actor", "Best Cinematography"]},
    "birdman or (the unexpected virtue of ignorance)": {"year": 2014, "oscars": ["Best Picture (2015)", "Best Director", "Best Original Screenplay", "Best Cinematography"]},
    "birdman": {"year": 2014, "oscars": ["Best Picture (2015)", "Best Director", "Best Original Screenplay", "Best Cinematography"]},
    "winter sleep": {"year": 2014, "cannes": ["Palme d'Or (2014)"]},
    "a pigeon sat on a branch reflecting on existence": {"year": 2014, "venice": ["Golden Lion (2014)"]},
    "whiplash": {"year": 2014, "oscars": ["Best Supp. Actor", "Best Editing", "Best Sound"]},
    "interstellar": {"year": 2014, "oscars": ["Best Visual Effects"]},
    "the grand budapest hotel": {"year": 2014, "oscars": ["4 Academy Awards (Score, Production, Costumes, Makeup)"]},
    "12 years a slave": {"year": 2013, "oscars": ["Best Picture (2014)", "Best Supp. Actress", "Best Adapted Screenplay"]},
    "blue is the warmest colour": {"year": 2013, "cannes": ["Palme d'Or (2013)"]},
    "sacro gra": {"year": 2013, "venice": ["Golden Lion (2013)"]},
    "gravity": {"year": 2013, "oscars": ["Best Director", "6 Academy Awards"]},
    "the great beauty": {"year": 2013, "oscars": ["Best Foreign Language Film (2014)"]},
    "argo": {"year": 2012, "oscars": ["Best Picture (2013)", "Best Adapted Screenplay", "Best Editing"]},
    "amour": {"year": 2012, "cannes": ["Palme d'Or (2012)"], "oscars": ["Best Foreign Language Film"]},
    "pieta": {"year": 2012, "venice": ["Golden Lion (2012)"]},
    "life of pi": {"year": 2012, "oscars": ["Best Director", "Best Cinematography", "Best Visual Effects", "Best Score"]},
    "the artist": {"year": 2011, "cannes": ["Best Actor"], "oscars": ["Best Picture (2012)", "Best Director", "Best Actor"]},
    "the tree of life": {"year": 2011, "cannes": ["Palme d'Or (2011)"]},
    "faust": {"year": 2011, "venice": ["Golden Lion (2011)"]},
    "the king's speech": {"year": 2010, "oscars": ["Best Picture (2011)", "Best Director", "Best Actor", "Best Original Screenplay"]},
    "uncle boonmee who can recall his past lives": {"year": 2010, "cannes": ["Palme d'Or (2010)"]},
    "somewhere": {"year": 2010, "venice": ["Golden Lion (2010)"]},
    "inception": {"year": 2010, "oscars": ["4 Academy Awards (Cinematography, Sound, Visual Effects)"]},
    "the social network": {"year": 2010, "oscars": ["Best Adapted Screenplay", "Best Original Score", "Best Editing"]},

    # --- 2000s ---
    "the hurt locker": {"year": 2008, "oscars": ["Best Picture (2010)", "Best Director", "Best Original Screenplay"]},
    "the white ribbon": {"year": 2009, "cannes": ["Palme d'Or (2009)"]},
    "lebanon": {"year": 2009, "venice": ["Golden Lion (2009)"]},
    "slumdog millionaire": {"year": 2008, "oscars": ["Best Picture (2009)", "Best Director", "8 Academy Awards"]},
    "the class": {"year": 2008, "cannes": ["Palme d'Or (2008)"]},
    "the wrestler": {"year": 2008, "venice": ["Golden Lion (2008)"]},
    "the dark knight": {"year": 2008, "oscars": ["Best Supp. Actor (Heath Ledger)", "Best Sound Editing"]},
    "no country for old men": {"year": 2007, "oscars": ["Best Picture (2008)", "Best Director", "Best Supp. Actor", "Best Adapted Screenplay"]},
    "4 months, 3 weeks and 2 days": {"year": 2007, "cannes": ["Palme d'Or (2007)"]},
    "lust, caution": {"year": 2007, "venice": ["Golden Lion (2007)"]},
    "there will be blood": {"year": 2007, "oscars": ["Best Actor (Daniel Day-Lewis)", "Best Cinematography"]},
    "the departed": {"year": 2006, "oscars": ["Best Picture (2007)", "Best Director (Martin Scorsese)", "Best Adapted Screenplay", "Best Editing"]},
    "the wind that shakes the barley": {"year": 2006, "cannes": ["Palme d'Or (2006)"]},
    "still life": {"year": 2006, "venice": ["Golden Lion (2006)"]},
    "pan's labyrinth": {"year": 2006, "oscars": ["3 Academy Awards (Cinematography, Art Direction, Makeup)"]},
    "the lives of others": {"year": 2006, "oscars": ["Best Foreign Language Film"]},
    "crash": {"year": 2004, "oscars": ["Best Picture (2006)", "Best Original Screenplay", "Best Editing"]},
    "l'enfant": {"year": 2005, "cannes": ["Palme d'Or (2005)"]},
    "brokeback mountain": {"year": 2005, "venice": ["Golden Lion (2005)"], "oscars": ["Best Director", "Best Adapted Screenplay", "Best Score"]},
    "million dollar baby": {"year": 2004, "oscars": ["Best Picture (2005)", "Best Director (Clint Eastwood)", "Best Actress", "Best Supp. Actor"]},
    "fahrenheit 9/11": {"year": 2004, "cannes": ["Palme d'Or (2004)"]},
    "vera drake": {"year": 2004, "venice": ["Golden Lion (2004)"]},
    "eternal sunshine of the spotless mind": {"year": 2004, "oscars": ["Best Original Screenplay"]},
    "the lord of the rings: the return of the king": {"year": 2003, "oscars": ["Best Picture (2004)", "Best Director", "11 Academy Awards (Clean Sweep)"]},
    "elephant": {"year": 2003, "cannes": ["Palme d'Or (2003)"]},
    "the return": {"year": 2003, "venice": ["Golden Lion (2003)"]},
    "lost in translation": {"year": 2003, "oscars": ["Best Original Screenplay"]},
    "chicago": {"year": 2002, "oscars": ["Best Picture (2003)", "6 Academy Awards"]},
    "the pianist": {"year": 2002, "cannes": ["Palme d'Or (2002)"], "oscars": ["Best Director", "Best Actor", "Best Adapted Screenplay"]},
    "the magdalene sisters": {"year": 2002, "venice": ["Golden Lion (2002)"]},
    "spirited away": {"year": 2001, "oscars": ["Best Animated Feature"]},
    "a beautiful mind": {"year": 2001, "oscars": ["Best Picture (2002)", "Best Director", "Best Supp. Actress", "Best Adapted Screenplay"]},
    "the son's room": {"year": 2001, "cannes": ["Palme d'Or (2001)"]},
    "monsoon wedding": {"year": 2001, "venice": ["Golden Lion (2001)"]},
    "gladiator": {"year": 2000, "oscars": ["Best Picture (2001)", "Best Actor (Russell Crowe)", "5 Academy Awards"]},
    "dancer in the dark": {"year": 2000, "cannes": ["Palme d'Or (2000)"]},
    "the circle": {"year": 2000, "venice": ["Golden Lion (2000)"]},
    "crouching tiger, hidden dragon": {"year": 2000, "oscars": ["Best Foreign Language Film", "4 Academy Awards"]},

    # --- 1990s ---
    "american beauty": {"year": 1999, "oscars": ["Best Picture (2000)", "Best Director", "Best Actor", "5 Academy Awards"]},
    "rosetta": {"year": 1999, "cannes": ["Palme d'Or (1999)"]},
    "not one less": {"year": 1999, "venice": ["Golden Lion (1999)"]},
    "the matrix": {"year": 1999, "oscars": ["4 Academy Awards (Visual Effects, Sound, Sound Editing, Editing)"]},
    "shakespeare in love": {"year": 1998, "oscars": ["Best Picture (1999)", "7 Academy Awards"]},
    "eternity and a day": {"year": 1998, "cannes": ["Palme d'Or (1998)"]},
    "the way we laughed": {"year": 1998, "venice": ["Golden Lion (1998)"]},
    "saving private ryan": {"year": 1998, "oscars": ["Best Director (Steven Spielberg)", "5 Academy Awards"]},
    "life is beautiful": {"year": 1997, "oscars": ["Best Actor (Roberto Benigni)", "Best Foreign Language Film", "Best Score"]},
    "titanic": {"year": 1997, "oscars": ["Best Picture (1998)", "Best Director (James Cameron)", "11 Academy Awards"]},
    "taste of cherry": {"year": 1997, "cannes": ["Palme d'Or (1997)"]},
    "the eel": {"year": 1997, "cannes": ["Palme d'Or (1997)"]},
    "hana-bi": {"year": 1997, "venice": ["Golden Lion (1997)"]},
    "the english patient": {"year": 1996, "oscars": ["Best Picture (1997)", "Best Director", "9 Academy Awards"]},
    "secrets & lies": {"year": 1996, "cannes": ["Palme d'Or (1996)"]},
    "michael collins": {"year": 1996, "venice": ["Golden Lion (1996)"]},
    "braveheart": {"year": 1995, "oscars": ["Best Picture (1996)", "Best Director (Mel Gibson)", "5 Academy Awards"]},
    "underground": {"year": 1995, "cannes": ["Palme d'Or (1995)"]},
    "cyclo": {"year": 1995, "venice": ["Golden Lion (1995)"]},
    "forrest gump": {"year": 1994, "oscars": ["Best Picture (1995)", "Best Director", "Best Actor (Tom Hanks)", "6 Academy Awards"]},
    "pulp fiction": {"year": 1994, "cannes": ["Palme d'Or (1994)"], "oscars": ["Best Original Screenplay"]},
    "before the rain": {"year": 1994, "venice": ["Golden Lion (1994)"]},
    "vive l'amour": {"year": 1994, "venice": ["Golden Lion (1994)"]},
    "the shawshank redemption": {"year": 1994, "oscars": ["7 Oscar Nominations"]},
    "the lion king": {"year": 1994, "oscars": ["Best Original Score", "Best Original Song"]},
    "schindler's list": {"year": 1993, "oscars": ["Best Picture (1994)", "Best Director (Steven Spielberg)", "7 Academy Awards"]},
    "the piano": {"year": 1993, "cannes": ["Palme d'Or (1993)"], "oscars": ["Best Actress", "Best Supp. Actress", "Best Screenplay"]},
    "farewell my concubine": {"year": 1993, "cannes": ["Palme d'Or (1993)"]},
    "three colors: blue": {"year": 1993, "venice": ["Golden Lion (1993)"]},
    "short cuts": {"year": 1993, "venice": ["Golden Lion (1993)"]},
    "unforgiven": {"year": 1992, "oscars": ["Best Picture (1993)", "Best Director (Clint Eastwood)", "4 Academy Awards"]},
    "the best intentions": {"year": 1992, "cannes": ["Palme d'Or (1992)"]},
    "the story of qiu ju": {"year": 1992, "venice": ["Golden Lion (1992)"]},
    "the silence of the lambs": {"year": 1991, "oscars": ["Best Picture (1992)", "Best Director", "Best Actor", "Best Actress", "Best Screenplay (Big Five)"]},
    "barton fink": {"year": 1991, "cannes": ["Palme d'Or (1991)"]},
    "urga": {"year": 1991, "venice": ["Golden Lion (1991)"]},
    "dances with wolves": {"year": 1990, "oscars": ["Best Picture (1991)", "Best Director (Kevin Costner)", "7 Academy Awards"]},
    "wild at heart": {"year": 1990, "cannes": ["Palme d'Or (1990)"]},
    "rosencrantz & guildenstern are dead": {"year": 1990, "venice": ["Golden Lion (1990)"]},
    "goodfellas": {"year": 1990, "oscars": ["Best Supp. Actor (Joe Pesci)"], "venice": ["Silver Lion (Best Director)"]},

    # --- Pre-1990 Classics ---
    "driving miss daisy": {"year": 1989, "oscars": ["Best Picture (1990)", "4 Academy Awards"]},
    "sex, lies, and videotape": {"year": 1989, "cannes": ["Palme d'Or (1989)"]},
    "a city of sadness": {"year": 1989, "venice": ["Golden Lion (1989)"]},
    "cinema paradiso": {"year": 1988, "cannes": ["Grand Prix"], "oscars": ["Best Foreign Language Film"]},
    "rain man": {"year": 1988, "oscars": ["Best Picture (1989)", "Best Director", "Best Actor (Dustin Hoffman)"]},
    "pelle the conqueror": {"year": 1987, "cannes": ["Palme d'Or (1988)"], "oscars": ["Best Foreign Language Film"]},
    "the legend of the holy drinker": {"year": 1988, "venice": ["Golden Lion (1988)"]},
    "the last emperor": {"year": 1987, "oscars": ["Best Picture (1988)", "Best Director (Bernardo Bertolucci)", "9 Academy Awards (Clean Sweep)"]},
    "under the sun of satan": {"year": 1987, "cannes": ["Palme d'Or (1987)"]},
    "au revoir les enfants": {"year": 1987, "venice": ["Golden Lion (1987)"]},
    "platoon": {"year": 1986, "oscars": ["Best Picture (1987)", "Best Director (Oliver Stone)", "4 Academy Awards"]},
    "the mission": {"year": 1986, "cannes": ["Palme d'Or (1986)"]},
    "the green ray": {"year": 1986, "venice": ["Golden Lion (1986)"]},
    "out of africa": {"year": 1985, "oscars": ["Best Picture (1986)", "Best Director", "7 Academy Awards"]},
    "when father was away on business": {"year": 1985, "cannes": ["Palme d'Or (1985)"]},
    "vagabond": {"year": 1985, "venice": ["Golden Lion (1985)"]},
    "amadeus": {"year": 1984, "oscars": ["Best Picture (1985)", "Best Director (Miloš Forman)", "8 Academy Awards"]},
    "paris, texas": {"year": 1984, "cannes": ["Palme d'Or (1984)"]},
    "a year of the quiet sun": {"year": 1984, "venice": ["Golden Lion (1984)"]},
    "terms of endearment": {"year": 1983, "oscars": ["Best Picture (1984)", "Best Director", "5 Academy Awards"]},
    "the ballad of narayama": {"year": 1983, "cannes": ["Palme d'Or (1983)"]},
    "first name: carmen": {"year": 1983, "venice": ["Golden Lion (1983)"]},
    "gandhi": {"year": 1982, "oscars": ["Best Picture (1983)", "Best Director", "8 Academy Awards"]},
    "missing": {"year": 1982, "cannes": ["Palme d'Or (1982)"]},
    "yol": {"year": 1982, "cannes": ["Palme d'Or (1982)"]},
    "the state of things": {"year": 1982, "venice": ["Golden Lion (1982)"]},
    "blade runner": {"year": 1982, "oscars": ["2 Academy Award Nominations"]},
    "chariots of fire": {"year": 1981, "oscars": ["Best Picture (1982)", "4 Academy Awards"]},
    "man of iron": {"year": 1981, "cannes": ["Palme d'Or (1981)"]},
    "marianne and juliane": {"year": 1981, "venice": ["Golden Lion (1981)"]},
    "ordinary people": {"year": 1980, "oscars": ["Best Picture (1981)", "Best Director (Robert Redford)"]},
    "kagemusha": {"year": 1980, "cannes": ["Palme d'Or (1980)"]},
    "all that jazz": {"year": 1979, "cannes": ["Palme d'Or (1980)"], "oscars": ["4 Academy Awards"]},
    "atlantic city": {"year": 1980, "venice": ["Golden Lion (1980)"]},
    "gloria": {"year": 1980, "venice": ["Golden Lion (1980)"]},
    "kramer vs. kramer": {"year": 1979, "oscars": ["Best Picture (1980)", "Best Director", "5 Academy Awards"]},
    "apocalypse now": {"year": 1979, "cannes": ["Palme d'Or (1979)"], "oscars": ["2 Academy Awards"]},
    "the tin drum": {"year": 1979, "cannes": ["Palme d'Or (1979)"], "oscars": ["Best Foreign Language Film"]},
    "alien": {"year": 1979, "oscars": ["Best Visual Effects"]},
    "the deer hunter": {"year": 1978, "oscars": ["Best Picture (1979)", "Best Director (Michael Cimino)", "5 Academy Awards"]},
    "the tree of wooden clogs": {"year": 1978, "cannes": ["Palme d'Or (1978)"]},
    "annie hall": {"year": 1977, "oscars": ["Best Picture (1978)", "Best Director (Woody Allen)", "4 Academy Awards"]},
    "padre padrone": {"year": 1977, "cannes": ["Palme d'Or (1977)"]},
    "star wars": {"year": 1977, "oscars": ["6 Academy Awards"]},
    "rocky": {"year": 1976, "oscars": ["Best Picture (1977)", "Best Director"]},
    "taxi driver": {"year": 1976, "cannes": ["Palme d'Or (1976)"]},
    "one flew over the cuckoo's nest": {"year": 1975, "oscars": ["Best Picture (1976)", "Best Director", "Big Five Academy Awards"]},
    "chronicle of the years of fire": {"year": 1975, "cannes": ["Palme d'Or (1975)"]},
    "jaws": {"year": 1975, "oscars": ["3 Academy Awards"]},
    "the godfather part ii": {"year": 1974, "oscars": ["Best Picture (1975)", "Best Director (Francis Ford Coppola)", "6 Academy Awards"]},
    "the conversation": {"year": 1974, "cannes": ["Palme d'Or (1974)"]},
    "the sting": {"year": 1973, "oscars": ["Best Picture (1974)", "Best Director", "7 Academy Awards"]},
    "the hireling": {"year": 1973, "cannes": ["Palme d'Or (1973)"]},
    "scarecrow": {"year": 1973, "cannes": ["Palme d'Or (1973)"]},
    "the godfather": {"year": 1972, "oscars": ["Best Picture (1973)", "Best Actor (Marlon Brando)", "Best Screenplay"]},
    "the working class goes to heaven": {"year": 1971, "cannes": ["Palme d'Or (1972)"]},
    "the mattei affair": {"year": 1972, "cannes": ["Palme d'Or (1972)"]},
    "the french connection": {"year": 1971, "oscars": ["Best Picture (1972)", "Best Director", "5 Academy Awards"]},
    "the go-between": {"year": 1971, "cannes": ["Palme d'Or (1971)"]},
    "a clockwork orange": {"year": 1971, "oscars": ["4 Academy Award Nominations"]},
    "patton": {"year": 1970, "oscars": ["Best Picture (1971)", "Best Director", "7 Academy Awards"]},
    "m*a*s*h": {"year": 1970, "cannes": ["Palme d'Or (1970)"]},
    "midnight cowboy": {"year": 1969, "oscars": ["Best Picture (1970)", "Best Director"]},
    "if....": {"year": 1968, "cannes": ["Palme d'Or (1969)"]},
    "oliver!": {"year": 1968, "oscars": ["Best Picture (1969)", "5 Academy Awards"]},
    "2001: a space odyssey": {"year": 1968, "oscars": ["Best Visual Effects (Stanley Kubrick)"]},
    "in the heat of the night": {"year": 1967, "oscars": ["Best Picture (1968)", "5 Academy Awards"]},
    "blowup": {"year": 1966, "cannes": ["Palme d'Or (1967)"]},
    "the battle of algiers": {"year": 1966, "venice": ["Golden Lion (1966)"]},
    "a man for all seasons": {"year": 1966, "oscars": ["Best Picture (1967)", "6 Academy Awards"]},
    "a man and a woman": {"year": 1966, "cannes": ["Palme d'Or (1966)"]},
    "the sound of music": {"year": 1965, "oscars": ["Best Picture (1966)", "5 Academy Awards"]},
    "sandra": {"year": 1965, "venice": ["Golden Lion (1965)"]},
    "my fair lady": {"year": 1964, "oscars": ["Best Picture (1965)", "8 Academy Awards"]},
    "the umbrellas of cherbourg": {"year": 1964, "cannes": ["Palme d'Or (1964)"]},
    "red desert": {"year": 1964, "venice": ["Golden Lion (1964)"]},
    "tom jones": {"year": 1963, "oscars": ["Best Picture (1964)", "4 Academy Awards"]},
    "the leopard": {"year": 1963, "cannes": ["Palme d'Or (1963)"]},
    "hands over the city": {"year": 1963, "venice": ["Golden Lion (1963)"]},
    "lawrence of arabia": {"year": 1962, "oscars": ["Best Picture (1963)", "Best Director (David Lean)", "7 Academy Awards"]},
    "family diary": {"year": 1962, "venice": ["Golden Lion (1962)"]},
    "ivan's childhood": {"year": 1962, "venice": ["Golden Lion (1962)"]},
    "west side story": {"year": 1961, "oscars": ["Best Picture (1962)", "10 Academy Awards"]},
    "viridiana": {"year": 1961, "cannes": ["Palme d'Or (1961)"]},
    "last year at marienbad": {"year": 1961, "venice": ["Golden Lion (1961)"]},
    "the apartment": {"year": 1960, "oscars": ["Best Picture (1961)", "Best Director (Billy Wilder)", "5 Academy Awards"]},
    "la dolce vita": {"year": 1960, "cannes": ["Palme d'Or (1960)"]},
    "the crossing of the rhine": {"year": 1960, "venice": ["Golden Lion (1960)"]},
    "psycho": {"year": 1960, "oscars": ["4 Academy Award Nominations"]},
    "ben-hur": {"year": 1959, "oscars": ["Best Picture (1960)", "11 Academy Awards"]},
    "black orpheus": {"year": 1959, "cannes": ["Palme d'Or (1959)"], "oscars": ["Best Foreign Language Film"]},
    "the great war": {"year": 1959, "venice": ["Golden Lion (1959)"]},
    "general della rovere": {"year": 1959, "venice": ["Golden Lion (1959)"]},
    "gigi": {"year": 1958, "oscars": ["Best Picture (1959)", "9 Academy Awards"]},
    "the cranes are flying": {"year": 1957, "cannes": ["Palme d'Or (1958)"]},
    "the bridge on the river kwai": {"year": 1957, "oscars": ["Best Picture (1958)", "7 Academy Awards"]},
    "12 angry men": {"year": 1957, "oscars": ["3 Academy Award Nominations"]},
    "around the world in 80 days": {"year": 1956, "oscars": ["Best Picture (1957)", "5 Academy Awards"]},
    "friendly persuasion": {"year": 1956, "cannes": ["Palme d'Or (1957)"]},
    "marty": {"year": 1955, "cannes": ["Palme d'Or (1955)"], "oscars": ["Best Picture (1956)", "4 Academy Awards"]},
    "on the waterfront": {"year": 1954, "oscars": ["Best Picture (1955)", "8 Academy Awards"]},
    "rear window": {"year": 1954, "oscars": ["4 Academy Award Nominations"]},
    "romeo and juliet": {"year": 1954, "venice": ["Golden Lion (1954)"]},
    "from here to eternity": {"year": 1953, "oscars": ["Best Picture (1954)", "8 Academy Awards"]},
    "the wages of fear": {"year": 1953, "cannes": ["Palme d'Or (1953)"]},
    "the golden coach": {"year": 1952, "venice": ["Golden Lion (1952)"]},
    "the greatest show on earth": {"year": 1952, "oscars": ["Best Picture (1953)"]},
    "othello": {"year": 1951, "cannes": ["Palme d'Or (1952)"]},
    "an american in paris": {"year": 1951, "oscars": ["Best Picture (1952)", "6 Academy Awards"]},
    "miracle in milan": {"year": 1951, "cannes": ["Palme d'Or (1951)"]},
    "miss julie": {"year": 1951, "cannes": ["Palme d'Or (1951)"]},
    "rashomon": {"year": 1950, "venice": ["Golden Lion (1951)"], "oscars": ["Honorary Foreign Language Award"]},
    "all about eve": {"year": 1950, "oscars": ["Best Picture (1951)", "6 Academy Awards"]},
    "sunset boulevard": {"year": 1950, "oscars": ["3 Academy Awards"]},
    "the third man": {"year": 1949, "cannes": ["Palme d'Or (1949)"]},
    "manon": {"year": 1949, "venice": ["Golden Lion (1949)"]},
    "casablanca": {"year": 1942, "oscars": ["Best Picture (1944)", "Best Director", "Best Screenplay"]},
    "citizen kane": {"year": 1941, "oscars": ["Best Original Screenplay"]},
    "gone with the wind": {"year": 1939, "oscars": ["Best Picture (1940)", "8 Academy Awards"]}
}

def clean_title_for_lookup(title):
    """Normalize title for fuzzy matching."""
    if not title:
        return ""
    t = str(title).lower().strip()
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)  # remove parentheticals
    t = re.sub(r'[^\w\s]', '', t)  # remove punctuation
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def match_awards_for_film(title, year=None):
    """
    Checks if a film title & year matches our prestigious awards registry.
    Returns: dict with 'has_awards', 'oscars', 'cannes', 'venice', 'all_awards', 'festivals'
    """
    if not title:
        return None
    raw_norm = clean_title_for_lookup(title)
    
    # Try exact match in registry
    match_entry = None
    if raw_norm in AWARDS_REGISTRY:
        match_entry = AWARDS_REGISTRY[raw_norm]
    else:
        # Check without leading 'the ' or 'a '
        norm_no_art = re.sub(r'^(the|a|an)\s+', '', raw_norm)
        for k, entry in AWARDS_REGISTRY.items():
            k_no_art = re.sub(r'^(the|a|an)\s+', '', k)
            if norm_no_art == k_no_art or raw_norm == k:
                match_entry = entry
                break
                
    if not match_entry:
        return None

    # Check year if available (allow delta of 2 years for festival vs release vs oscar)
    if year and pd.notna(year) and str(year).isdigit():
        y = int(year)
        ref_year = match_entry.get("year")
        if ref_year and abs(y - ref_year) > 2:
            return None

    oscars = match_entry.get("oscars", [])
    cannes = match_entry.get("cannes", [])
    venice = match_entry.get("venice", [])

    all_awards = []
    festivals = []
    if oscars:
        all_awards.extend([f"🏆 Oscar: {a}" for a in oscars])
        festivals.append("Oscar")
    if cannes:
        all_awards.extend([f"🌴 Cannes: {a}" for a in cannes])
        festivals.append("Cannes")
    if venice:
        all_awards.extend([f"🦁 Venice: {a}" for a in venice])
        festivals.append("Venice")

    return {
        "has_awards": True,
        "oscars": oscars,
        "cannes": cannes,
        "venice": venice,
        "all_awards": all_awards,
        "festivals": festivals,
        "badge_str": " | ".join(all_awards[:2])
    }

def compute_awards_analytics(df):
    """
    Computes comprehensive awards statistics across the user's movie library.
    Identifies:
    - Liked / Agreed Winners (user rating >= 4.0 stars / 8.0/10)
    - Disliked / Overrated Winners (user rating <= 2.5 stars / < 6.0/10)
    - Neutral Winners
    - Metrics for Oscars vs Cannes vs Venice
    """
    if df.empty:
        return {
            "total_awarded": 0,
            "award_films": pd.DataFrame(),
            "agreed_films": pd.DataFrame(),
            "disagreed_films": pd.DataFrame(),
            "kpis": {}
        }

    matched_records = []
    for idx, row in df.iterrows():
        title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "")
        year = row.get('Year')
        
        info = match_awards_for_film(title, year)
        if info:
            score = row.get('primary_rating_10')
            personal_rating = row.get('Rating')
            tmdb_score = row.get('tmdb_rating')
            dirs = row.get('clean_directors')
            if dirs is None or (isinstance(dirs, float) and np.isnan(dirs)):
                dirs = []
            elif hasattr(dirs, '__iter__') and not isinstance(dirs, (str, bytes)):
                dirs = list(dirs)
            elif isinstance(dirs, str):
                dirs = [d.strip() for d in dirs.split(',') if d.strip()]
            else:
                dirs = []

            # Stance: Liked vs Disliked vs Neutral
            stance = "Neutral"
            if pd.notna(score):
                if score >= 8.0:
                    stance = "Agreed (Loved) 💚"
                elif score < 6.0:
                    stance = "Disagreed (Overrated) 💔"
                else:
                    stance = "Moderate / Balanced ⚖️"

            matched_records.append({
                "Title": title,
                "Year": int(year) if pd.notna(year) and str(year).replace('.0','').isdigit() else 0,
                "Your Rating": f"{personal_rating} ★" if pd.notna(personal_rating) else "-",
                "Personal_Score": score,
                "TMDb Score": tmdb_score,
                "Directors": ", ".join(dirs) if dirs else "N/A",
                "Festivals": ", ".join(info["festivals"]),
                "Major Award": info["badge_str"],
                "All_Awards": "\n".join(info["all_awards"]),
                "Has_Oscar": bool(info["oscars"]),
                "Has_Cannes": bool(info["cannes"]),
                "Has_Venice": bool(info["venice"]),
                "Stance": stance
            })

    if not matched_records:
        return {
            "total_awarded": 0,
            "award_films": pd.DataFrame(),
            "agreed_films": pd.DataFrame(),
            "disagreed_films": pd.DataFrame(),
            "kpis": {
                "total_awarded": 0,
                "pct_of_library": 0.0,
                "oscar_count": 0,
                "cannes_count": 0,
                "venice_count": 0,
                "agreement_rate": 0.0,
                "avg_oscar_rating": "N/A",
                "avg_cannes_rating": "N/A",
                "avg_venice_rating": "N/A"
            }
        }

    award_df = pd.DataFrame(matched_records)
    
    # Sub-dataframes
    agreed = award_df[award_df['Stance'] == "Agreed (Loved) 💚"].sort_values(by='Personal_Score', ascending=False)
    disagreed = award_df[award_df['Stance'] == "Disagreed (Overrated) 💔"].sort_values(by='Personal_Score', ascending=True)

    # Festival breakdowns
    oscar_films = award_df[award_df['Has_Oscar']]
    cannes_films = award_df[award_df['Has_Cannes']]
    venice_films = award_df[award_df['Has_Venice']]

    total_awarded = len(award_df)
    total_library = len(df)
    pct_library = round(total_awarded / total_library * 100, 1) if total_library > 0 else 0.0
    
    rated_awarded = award_df[award_df['Personal_Score'].notna()]
    if not rated_awarded.empty:
        agreed_count = len(rated_awarded[rated_awarded['Personal_Score'] >= 7.0])
        agreement_rate = round(agreed_count / len(rated_awarded) * 100, 1)
    else:
        agreement_rate = 0.0

    avg_oscar = f"{oscar_films['Personal_Score'].mean():.2f}" if not oscar_films.empty and oscar_films['Personal_Score'].notna().any() else "N/A"
    avg_cannes = f"{cannes_films['Personal_Score'].mean():.2f}" if not cannes_films.empty and cannes_films['Personal_Score'].notna().any() else "N/A"
    avg_venice = f"{venice_films['Personal_Score'].mean():.2f}" if not venice_films.empty and venice_films['Personal_Score'].notna().any() else "N/A"

    kpis = {
        "total_awarded": total_awarded,
        "pct_of_library": pct_library,
        "oscar_count": len(oscar_films),
        "cannes_count": len(cannes_films),
        "venice_count": len(venice_films),
        "agreement_rate": agreement_rate,
        "avg_oscar_rating": avg_oscar,
        "avg_cannes_rating": avg_cannes,
        "avg_venice_rating": avg_venice
    }

    return {
        "total_awarded": total_awarded,
        "award_films": award_df.sort_values(by='Year', ascending=False),
        "agreed_films": agreed,
        "disagreed_films": disagreed,
        "kpis": kpis
    }
