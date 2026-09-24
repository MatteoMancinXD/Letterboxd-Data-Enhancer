# services/nationality_service.py
import pandas as pd
import numpy as np

# Country flags and canonical naming
COUNTRY_INFO = {
    "United States of America": {"name": "United States", "flag": "🇺🇸", "region": "North America"},
    "United States": {"name": "United States", "flag": "🇺🇸", "region": "North America"},
    "United Kingdom": {"name": "United Kingdom", "flag": "🇬🇧", "region": "Europe"},
    "Italy": {"name": "Italy", "flag": "🇮🇹", "region": "Europe"},
    "France": {"name": "France", "flag": "🇫🇷", "region": "Europe"},
    "Japan": {"name": "Japan", "flag": "🇯🇵", "region": "Asia"},
    "South Korea": {"name": "South Korea", "flag": "🇰🇷", "region": "Asia"},
    "Germany": {"name": "Germany", "flag": "🇩🇪", "region": "Europe"},
    "Spain": {"name": "Spain", "flag": "🇪🇸", "region": "Europe"},
    "Canada": {"name": "Canada", "flag": "🇨🇦", "region": "North America"},
    "Australia": {"name": "Australia", "flag": "🇦🇺", "region": "Oceania"},
    "New Zealand": {"name": "New Zealand", "flag": "🇳🇿", "region": "Oceania"},
    "China": {"name": "China", "flag": "🇨🇳", "region": "Asia"},
    "Hong Kong": {"name": "Hong Kong", "flag": "🇭🇰", "region": "Asia"},
    "Taiwan": {"name": "Taiwan", "flag": "🇹🇼", "region": "Asia"},
    "India": {"name": "India", "flag": "🇮🇳", "region": "Asia"},
    "Sweden": {"name": "Sweden", "flag": "🇸🇪", "region": "Europe"},
    "Denmark": {"name": "Denmark", "flag": "🇩🇰", "region": "Europe"},
    "Norway": {"name": "Norway", "flag": "🇳🇴", "region": "Europe"},
    "Finland": {"name": "Finland", "flag": "🇫🇮", "region": "Europe"},
    "Ireland": {"name": "Ireland", "flag": "🇮🇪", "region": "Europe"},
    "Mexico": {"name": "Mexico", "flag": "🇲🇽", "region": "Latin America"},
    "Brazil": {"name": "Brazil", "flag": "🇧🇷", "region": "Latin America"},
    "Argentina": {"name": "Argentina", "flag": "🇦🇷", "region": "Latin America"},
    "Poland": {"name": "Poland", "flag": "🇵🇱", "region": "Europe"},
    "Russia": {"name": "Russia", "flag": "🇷🇺", "region": "Europe"},
    "Soviet Union": {"name": "Russia", "flag": "🇷🇺", "region": "Europe"},
    "Iran": {"name": "Iran", "flag": "🇮🇷", "region": "Middle East"},
    "Belgium": {"name": "Belgium", "flag": "🇧🇪", "region": "Europe"},
    "Netherlands": {"name": "Netherlands", "flag": "🇳🇱", "region": "Europe"},
    "Austria": {"name": "Austria", "flag": "🇦🇹", "region": "Europe"},
    "Switzerland": {"name": "Switzerland", "flag": "🇨🇭", "region": "Europe"},
    "Greece": {"name": "Greece", "flag": "🇬🇷", "region": "Europe"},
    "Czech Republic": {"name": "Czech Republic", "flag": "🇨🇿", "region": "Europe"},
    "Hungary": {"name": "Hungary", "flag": "🇭🇺", "region": "Europe"},
    "Romania": {"name": "Romania", "flag": "🇷🇴", "region": "Europe"},
    "Turkey": {"name": "Turkey", "flag": "🇹🇷", "region": "Middle East"},
    "South Africa": {"name": "South Africa", "flag": "🇿🇦", "region": "Africa"},
    "Egypt": {"name": "Egypt", "flag": "🇪🇬", "region": "Africa"},
    "Chile": {"name": "Chile", "flag": "🇨🇱", "region": "Latin America"},
    "Colombia": {"name": "Colombia", "flag": "🇨🇴", "region": "Latin America"},
    "Portugal": {"name": "Portugal", "flag": "🇵🇹", "region": "Europe"},
    "Iceland": {"name": "Iceland", "flag": "🇮🇸", "region": "Europe"},
    "Thailand": {"name": "Thailand", "flag": "🇹🇭", "region": "Asia"},
    "Indonesia": {"name": "Indonesia", "flag": "🇮🇩", "region": "Asia"},
    "Philippines": {"name": "Philippines", "flag": "🇵🇭", "region": "Asia"},
    "Israel": {"name": "Israel", "flag": "🇮🇱", "region": "Middle East"}
}

# Curated registry of director nationalities (lowercase lookup)
DIRECTOR_NATIONALITY_REGISTRY = {
    # United States
    "quentin tarantino": "United States",
    "martin scorsese": "United States",
    "steven spielberg": "United States",
    "david fincher": "United States",
    "francis ford coppola": "United States",
    "george lucas": "United States",
    "robert zemeckis": "United States",
    "clint eastwood": "United States",
    "stanley kubrick": "United States",
    "wes anderson": "United States",
    "paul thomas anderson": "United States",
    "ethan coen": "United States",
    "joel coen": "United States",
    "coen brothers": "United States",
    "david lynch": "United States",
    "brian de palma": "United States",
    "spike lee": "United States",
    "woody allen": "United States",
    "sam raimi": "United States",
    "john lasseter": "United States",
    "brad bird": "United States",
    "andrew stanton": "United States",
    "pete docter": "United States",
    "lee unkrich": "United States",
    "todd phillips": "United States",
    "sylvester stallone": "United States",
    "phil lord": "United States",
    "christopher miller": "United States",
    "tim burton": "United States",
    "ron howard": "United States",
    "joe russo": "United States",
    "anthony russo": "United States",
    "michael mann": "United States",
    "james gray": "United States",
    "jordan peele": "United States",
    "ari aster": "United States",
    "robert eggers": "United States",
    "damien chazelle": "United States",
    "greta gerwig": "United States",
    "noah baumbach": "United States",
    "rian johnson": "United States",
    "j.j. abrams": "United States",
    "zack snyder": "United States",
    "richard linklater": "United States",
    "terrence malick": "United States",
    "oliver stone": "United States",
    "billy wilder": "United States",
    "john ford": "United States",
    "howard hawks": "United States",
    "sidney lumet": "United States",
    "john carpenter": "United States",
    "wes craven": "United States",
    "darren aronofsky": "United States",
    "david o. russell": "United States",
    "spike jonze": "United States",
    "sofia coppola": "United States",
    "alexander payne": "United States",
    "barry jenkins": "United States",
    "sean baker": "United States",
    "frank darabont": "United States",
    "jon favreau": "United States",
    "gore verbinski": "United States",
    "sam mendes": "United Kingdom",
    "michael bay": "United States",
    "m. night shyamalan": "United States",
    "lana wachowski": "United States",
    "lilly wachowski": "United States",
    "wachowskis": "United States",
    "bryan singer": "United States",
    "guy ritchie": "United Kingdom",
    "edgar wright": "United Kingdom",
    "matt reeves": "United States",
    "shane black": "United States",
    "richard donner": "United States",
    "tony scott": "United Kingdom",
    "john mctiernan": "United States",

    # United Kingdom
    "christopher nolan": "United Kingdom",
    "ridley scott": "United Kingdom",
    "david yates": "United Kingdom",
    "danny boyle": "United Kingdom",
    "edgar wright": "United Kingdom",
    "guy ritchie": "United Kingdom",
    "sam mendes": "United Kingdom",
    "alfred hitchcock": "United Kingdom",
    "jonathan glazer": "United Kingdom",
    "steve mcqueen": "United Kingdom",
    "ken loach": "United Kingdom",
    "mike leigh": "United Kingdom",
    "peter greenaway": "United Kingdom",
    "terry gilliam": "United Kingdom",
    "alan parker": "United Kingdom",
    "stephen frears": "United Kingdom",
    "matthew vaughn": "United Kingdom",
    "paul greengrass": "United Kingdom",
    "alex garland": "United Kingdom",
    "martin mcdonagh": "United Kingdom",
    "hugh hudson": "United Kingdom",
    "richard attenborough": "United Kingdom",
    "david lean": "United Kingdom",
    "carol reed": "United Kingdom",
    "charlie chaplin": "United Kingdom",

    # Italy
    "gennaro nunziante": "Italy",
    "federico fellini": "Italy",
    "sergio leone": "Italy",
    "paolo sorrentino": "Italy",
    "giuseppe tornatore": "Italy",
    "roberto benigni": "Italy",
    "bernardo bertolucci": "Italy",
    "michelangelo antonioni": "Italy",
    "luchino visconti": "Italy",
    "pier paolo pasolini": "Italy",
    "vittorio de sica": "Italy",
    "dario argento": "Italy",
    "mario bava": "Italy",
    "lucio fulci": "Italy",
    "matteo garrone": "Italy",
    "alice rohrwacher": "Italy",
    "luca guadagnino": "Italy",
    "nanni moretti": "Italy",
    "gabriele muccino": "Italy",
    "mario monicelli": "Italy",
    "dino risi": "Italy",
    "pietro germi": "Italy",
    "ettore scola": "Italy",
    "carlo verdone": "Italy",
    "massimo troisi": "Italy",
    "paolo virzì": "Italy",
    "marco bellocchio": "Italy",
    "gabriele salvatores": "Italy",
    "franco zeffirelli": "Italy",
    "sergio corbucci": "Italy",
    "enzo g. castellari": "Italy",
    "michele soavi": "Italy",
    "umberto lenzi": "Italy",
    "stefano sollima": "Italy",
    "jonas carpignano": "Italy",

    # France
    "jean-luc godard": "France",
    "françois truffaut": "France",
    "claude chabrol": "France",
    "éric rohmer": "France",
    "jacques demy": "France",
    "luc besson": "France",
    "jean-pierre jeunet": "France",
    "céline sciamma": "France",
    "justine triet": "France",
    "gaspar noé": "France",
    "jacques audiard": "France",
    "mathieu kassovitz": "France",
    "claire denis": "France",
    "olivier assayas": "France",
    "jean renoir": "France",
    "robert bresson": "France",
    "jacques tati": "France",
    "leos carax": "France",
    "alain resnais": "France",
    "louis malle": "France",
    "jean-pierre melville": "France",
    "georges méliès": "France",
    "agnès varda": "France",
    "michel gondry": "France",
    "julia ducournau": "France",
    "robin campillo": "France",
    "laurent cantet": "France",
    "abdelatif kechiche": "France",
    "ladj ly": "France",

    # Japan
    "hayao miyazaki": "Japan",
    "akira kurosawa": "Japan",
    "yasujiro ozu": "Japan",
    "kenji mizoguchi": "Japan",
    "masaki kobayashi": "Japan",
    "isao takahata": "Japan",
    "satoshi kon": "Japan",
    "makoto shinkai": "Japan",
    "mamoru hosoda": "Japan",
    "takeshi kitano": "Japan",
    "takashi miike": "Japan",
    "hirokazu kore-eda": "Japan",
    "ryusuke hamaguchi": "Japan",
    "sion sono": "Japan",
    "hideaki anno": "Japan",
    "kaneto shindo": "Japan",
    "nagisa oshima": "Japan",
    "shohei imamura": "Japan",
    "seijun suzuki": "Japan",
    "kinji fukasaku": "Japan",
    "shinichiro watanabe": "Japan",
    "katsuhiro otomo": "Japan",

    # South Korea
    "bong joon ho": "South Korea",
    "bong joon-ho": "South Korea",
    "park chan-wook": "South Korea",
    "park chan wook": "South Korea",
    "lee chang-dong": "South Korea",
    "kim jee-woon": "South Korea",
    "na hong-jin": "South Korea",
    "yeon sang-ho": "South Korea",
    "hong sang-soo": "South Korea",
    "kim ki-duk": "South Korea",
    "jung byung-gil": "South Korea",
    "choi dong-hoon": "South Korea",

    # Canada
    "denis villeneuve": "Canada",
    "james cameron": "Canada",
    "david cronenberg": "Canada",
    "xavier dolan": "Canada",
    "jean-marc vallée": "Canada",
    "sarah polley": "Canada",
    "atom egoyan": "Canada",
    "brandon cronenberg": "Canada",
    "norman jewison": "Canada",
    "jason reitman": "Canada",

    # Australia & New Zealand
    "george miller": "Australia",
    "peter weir": "Australia",
    "baz luhrmann": "Australia",
    "james wan": "Australia",
    "justin kurzel": "Australia",
    "gillian armstrong": "Australia",
    "bruce beresford": "Australia",
    "andrew adamson": "New Zealand",
    "peter jackson": "New Zealand",
    "taika waititi": "New Zealand",
    "jane campion": "New Zealand",
    "andrew niccol": "New Zealand",

    # Mexico & Latin America
    "guillermo del toro": "Mexico",
    "alfonso cuarón": "Mexico",
    "alejandro gonzález iñárritu": "Mexico",
    "alejandro g. iñárritu": "Mexico",
    "carlos reygadas": "Mexico",
    "amat escalante": "Mexico",
    "fernando meirelles": "Brazil",
    "walter salles": "Brazil",
    "kleber mendonça filho": "Brazil",
    "juan josé campanella": "Argentina",
    "damián szifron": "Argentina",
    "lucrecia martel": "Argentina",
    "pablo larraín": "Chile",
    "sebastián lelio": "Chile",

    # Spain
    "pedro almodóvar": "Spain",
    "pedro almodovar": "Spain",
    "luis buñuel": "Spain",
    "alejandro amenábar": "Spain",
    "j.a. bayona": "Spain",
    "juan antonio bayona": "Spain",
    "carlos saura": "Spain",
    "álex de la iglesia": "Spain",
    "rodrigo sorogoyen": "Spain",
    "víctor erice": "Spain",

    # Germany & Austria
    "fritz lang": "Germany",
    "f.w. murnau": "Germany",
    "werner herzog": "Germany",
    "wim wenders": "Germany",
    "rainer werner fassbinder": "Germany",
    "wolfgang petersen": "Germany",
    "florian henckel von donnersmarck": "Germany",
    "tom tykwer": "Germany",
    "edward berger": "Germany",
    "roland emmerich": "Germany",
    "michael haneke": "Austria",
    "ulrich seidl": "Austria",
    "stefan ruzowitzky": "Austria",

    # Scandinavia
    "ingmar bergman": "Sweden",
    "ruben östlund": "Sweden",
    "ruben ostlund": "Sweden",
    "tomas alfredson": "Sweden",
    "lasse hallström": "Sweden",
    "roy andersson": "Sweden",
    "lukas moodysson": "Sweden",
    "lars von trier": "Denmark",
    "thomas vinterberg": "Denmark",
    "nicolas winding refn": "Denmark",
    "susanne bier": "Denmark",
    "carl theodor dreyer": "Denmark",
    "joachim trier": "Norway",
    "aki kaurismäki": "Finland",

    # Other European
    "yorgos lanthimos": "Greece",
    "theo angelopoulos": "Greece",
    "costa-gavras": "Greece",
    "krzysztof kieślowski": "Poland",
    "krzysztof kieslowski": "Poland",
    "roman polanski": "Poland",
    "andrzej wajda": "Poland",
    "paweł pawlikowski": "Poland",
    "agnieszka holland": "Poland",
    "jean-pierre dardenne": "Belgium",
    "luc dardenne": "Belgium",
    "dardenne brothers": "Belgium",
    "chantal akerman": "Belgium",
    "paul verhoeven": "Netherlands",
    "bela tarr": "Hungary",
    "béla tarr": "Hungary",
    "laszlo nemes": "Hungary",
    "cristian mungiu": "Romania",
    "nuri bilge ceylan": "Turkey",

    # Asia & Middle East
    "wong kar-wai": "Hong Kong",
    "wong kar wai": "Hong Kong",
    "john woo": "Hong Kong",
    "stephen chow": "Hong Kong",
    "tsui hark": "Hong Kong",
    "ang lee": "Taiwan",
    "edward yang": "Taiwan",
    "hou hsiao-hsien": "Taiwan",
    "zhang yimou": "China",
    "chen kaige": "China",
    "jia zhangke": "China",
    "satyajit ray": "India",
    "s.s. rajamouli": "India",
    "anurag kashyap": "India",
    "sanjay leela bhansali": "India",
    "abbas kiarostami": "Iran",
    "asghar farhadi": "Iran",
    "jafar panahi": "Iran"
}

def normalize_country_name(name):
    """Returns canonical country name and flag."""
    if not name or not isinstance(name, str):
        return "Unknown", "🌐"
    cleaned = name.strip()
    if cleaned in COUNTRY_INFO:
        info = COUNTRY_INFO[cleaned]
        return info["name"], info["flag"]
    # Case-insensitive search
    for k, v in COUNTRY_INFO.items():
        if k.lower() == cleaned.lower():
            return v["name"], v["flag"]
    return cleaned, "🌐"

def resolve_film_nationality(row, mode='director'):
    """
    Resolves the nationality of a film row.
    If mode == 'director':
        Tries to match any director in 'clean_directors' against the DIRECTOR_NATIONALITY_REGISTRY.
        If not found, falls back to the first production country in 'production_countries'.
    If mode == 'production':
        Uses the first production country in 'production_countries'.
    Returns: (country_name, flag_emoji, attribution_note)
    """
    directors = row.get('clean_directors')
    if directors is None or (isinstance(directors, float) and np.isnan(directors)):
        directors = row.get('directors')
    if directors is None or (isinstance(directors, float) and np.isnan(directors)):
        directors = []
    elif isinstance(directors, str):
        directors = [d.strip() for d in directors.split(',') if d.strip()]
    elif hasattr(directors, '__iter__') and not isinstance(directors, (str, bytes)):
        directors = [str(d).strip() for d in directors if d and str(d).strip()]
        
    prod_countries = row.get('production_countries')
    if prod_countries is None or (isinstance(prod_countries, float) and np.isnan(prod_countries)):
        prod_countries = []
    elif hasattr(prod_countries, '__iter__') and not isinstance(prod_countries, (str, bytes)):
        prod_countries = [str(c).strip() for c in prod_countries if c and str(c).strip()]
    elif isinstance(prod_countries, str):
        prod_countries = [c.strip() for c in prod_countries.split(',') if c.strip()]
    else:
        prod_countries = []

    if mode == 'director' and directors:
        for d in directors:
            d_norm = str(d).strip().lower()
            if d_norm in DIRECTOR_NATIONALITY_REGISTRY:
                c_name = DIRECTOR_NATIONALITY_REGISTRY[d_norm]
                c_canonical, flag = normalize_country_name(c_name)
                return c_canonical, flag, f"Director ({d})"

    # Fallback to production country
    if prod_countries:
        first_country = prod_countries[0]
        c_canonical, flag = normalize_country_name(first_country)
        return c_canonical, flag, "Production Country"

    return "International / Other", "🌐", "Unknown"

def compute_nationality_statistics(df, mode='director'):
    """
    Analyzes film nationalities across the dataframe.
    Returns:
    - country_summary (pd.DataFrame): Country, Flag, Display_Name, Film_Count, Percent, Avg_Rating, Top_Directors
    - kpi_dict: total_countries, top_country, intl_percent, highest_rated_country
    - enriched_df: df with added 'country' and 'country_flag' columns
    """
    if df.empty:
        return pd.DataFrame(), {}, df

    records = []
    enriched_rows = []
    
    for idx, row in df.iterrows():
        c_name, flag, note = resolve_film_nationality(row, mode=mode)
        score = row.get('primary_rating_10')
        title = row.get('Name') if pd.notna(row.get('Name')) else (row.get('Title') if pd.notna(row.get('Title')) else "Untitled")
        dirs = row.get('clean_directors')
        if dirs is None or (isinstance(dirs, float) and np.isnan(dirs)):
            dirs = []
        elif hasattr(dirs, '__iter__') and not isinstance(dirs, (str, bytes)):
            dirs = [str(d) for d in dirs if d]
        elif isinstance(dirs, str):
            dirs = [d.strip() for d in dirs.split(',') if d.strip()]
        else:
            dirs = []
        
        records.append({
            'Country': c_name,
            'Flag': flag,
            'Display': f"{flag} {c_name}",
            'Title': title,
            'Score': score,
            'Directors': dirs
        })
        enriched_rows.append((c_name, f"{flag} {c_name}"))

    temp_df = pd.DataFrame(records)
    
    # Aggregation per country
    def get_top_dirs(series_of_lists):
        all_d = [d for sub in series_of_lists for d in sub]
        if not all_d:
            return "N/A"
        c = pd.Series(all_d).value_counts()
        top = c.head(2).index.tolist()
        return ", ".join(top)

    grouped = temp_df.groupby(['Country', 'Flag', 'Display']).agg(
        Film_Count=('Title', 'count'),
        Avg_Rating=('Score', 'mean'),
        Top_Directors=('Directors', get_top_dirs)
    ).reset_index()

    total_films = len(df)
    grouped['Percent'] = (grouped['Film_Count'] / total_films * 100).round(1)
    grouped['Avg_Rating'] = grouped['Avg_Rating'].round(2)
    grouped = grouped.sort_values(by=['Film_Count', 'Avg_Rating'], ascending=[False, False]).reset_index(drop=True)

    # Attach to original dataframe copy
    res_df = df.copy()
    res_df['film_country'] = [r[0] for r in enriched_rows]
    res_df['film_country_display'] = [r[1] for r in enriched_rows]

    # KPIs
    unique_countries = len(grouped)
    top_country = f"{grouped.iloc[0]['Display']} ({grouped.iloc[0]['Film_Count']} films)" if not grouped.empty else "N/A"
    
    # International share (non-US)
    us_films = grouped[grouped['Country'] == 'United States']['Film_Count'].sum()
    intl_films = total_films - us_films
    intl_pct = round((intl_films / total_films * 100), 1) if total_films > 0 else 0.0

    # Highest rated country with at least 2 films
    multi_film_countries = grouped[(grouped['Film_Count'] >= 2) & grouped['Avg_Rating'].notna()]
    if not multi_film_countries.empty:
        best_country_row = multi_film_countries.sort_values(by=['Avg_Rating', 'Film_Count'], ascending=[False, False]).iloc[0]
        highest_rated = f"{best_country_row['Display']} ({best_country_row['Avg_Rating']:.1f} ★)"
    elif not grouped.empty:
        highest_rated = f"{grouped.iloc[0]['Display']} ({grouped.iloc[0]['Avg_Rating']:.1f} ★)"
    else:
        highest_rated = "N/A"

    kpis = {
        "unique_countries": unique_countries,
        "top_country": top_country,
        "intl_percent": intl_pct,
        "highest_rated_country": highest_rated,
        "total_films": total_films
    }

    return grouped, kpis, res_df
