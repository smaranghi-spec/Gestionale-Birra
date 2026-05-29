"""
Dataset completo ingredienti: malti, luppoli, lieviti, altro.
Ogni record è un dict pronto per costruire un CatalogoIngrediente.
"""

# ── MALTI ──────────────────────────────────────────────────────────────────
# (nome, fermentable_type, yield_percent, color_srm)
_MALTI_RAW = [
    # Base malts
    ("Pale Ale Malt (Maris Otter)",  "Grain",   78.0,  3.0),
    ("Pale Ale Malt (Crisp)",        "Grain",   77.0,  3.0),
    ("Pilsner Malt (Weyermann)",     "Grain",   80.0,  1.7),
    ("Pilsner Malt (Best Malz)",     "Grain",   80.5,  1.8),
    ("Pilsner Malt (Dingemans)",     "Grain",   79.5,  1.8),
    ("Vienna Malt (Weyermann)",      "Grain",   78.0,  4.0),
    ("Vienna Malt (Bestmalz)",       "Grain",   77.5,  3.5),
    ("Munich Malt Light (Weyermann)","Grain",   77.0,  9.0),
    ("Munich Malt Dark (Weyermann)", "Grain",   76.0, 15.0),
    ("Munich Malt (Bestmalz)",       "Grain",   77.0,  8.0),
    ("Pale Malt (2-Row)",            "Grain",   79.0,  2.0),
    ("Pale Malt (6-Row)",            "Grain",   74.0,  2.5),
    ("Mild Malt",                    "Grain",   77.0,  4.0),
    ("Golden Promise",               "Grain",   79.0,  3.0),
    ("Maris Otter Low Colour",       "Grain",   79.0,  2.5),
    ("Floor-Malted Bohemian Pils",   "Grain",   80.0,  1.7),
    ("Wheat Malt (Weyermann)",       "Grain",   83.0,  2.0),
    ("Wheat Malt (White)",           "Grain",   84.0,  2.0),
    ("Wheat Malt (Red)",             "Grain",   84.0,  3.0),
    ("Rye Malt",                     "Grain",   75.0,  3.7),
    ("Oat Malt",                     "Grain",   70.0,  2.0),
    ("Spelt Malt",                   "Grain",   74.0,  2.5),
    ("Barley Malt (Raw)",            "Grain",   58.0,  1.5),
    ("Smoked Malt (Beechwood)",      "Grain",   77.0,  3.0),
    ("Rauch Malt (Weyermann)",       "Grain",   78.0,  3.0),
    ("Melanoidin Malt",              "Grain",   73.0, 28.0),
    ("Aromatic Malt",                "Grain",   74.0, 26.0),
    ("Biscuit Malt",                 "Grain",   72.0, 25.0),
    ("Victory Malt",                 "Grain",   75.0, 25.0),
    ("Amber Malt",                   "Grain",   75.0, 22.0),
    ("Brown Malt",                   "Grain",   65.0, 65.0),
    # Crystal / Caramel
    ("Caramel Malt 10L",             "Crystal", 75.0, 10.0),
    ("Caramel Malt 20L",             "Crystal", 74.0, 20.0),
    ("Caramel Malt 40L",             "Crystal", 74.0, 40.0),
    ("Caramel Malt 60L",             "Crystal", 72.0, 60.0),
    ("Caramel Malt 80L",             "Crystal", 71.0, 80.0),
    ("Caramel Malt 120L",            "Crystal", 70.0,120.0),
    ("CaraPils (Dextrine Malt)",     "Crystal", 72.0,  2.0),
    ("CaraFoam (Weyermann)",         "Crystal", 75.0,  2.0),
    ("CaraVienna I (Weyermann)",     "Crystal", 73.0,  9.0),
    ("CaraVienna II (Weyermann)",    "Crystal", 72.0, 17.0),
    ("CaraMunich I (Weyermann)",     "Crystal", 73.0, 26.0),
    ("CaraMunich II (Weyermann)",    "Crystal", 72.0, 31.0),
    ("CaraMunich III (Weyermann)",   "Crystal", 71.0, 57.0),
    ("CaraRed (Weyermann)",          "Crystal", 71.0, 20.0),
    ("CaraAmber (Weyermann)",        "Crystal", 70.0, 30.0),
    ("CaraAroma (Weyermann)",        "Crystal", 67.0,130.0),
    ("Special B (Dingemans)",        "Crystal", 65.0,180.0),
    ("Crystal 45 (Crisp)",           "Crystal", 72.0, 45.0),
    ("Crystal 150 (Crisp)",          "Crystal", 68.0,150.0),
    # Roasted
    ("Chocolate Malt",               "Roasted", 60.0,350.0),
    ("Chocolate Wheat Malt",         "Roasted", 58.0,400.0),
    ("Carafa I (Weyermann)",         "Roasted", 65.0,340.0),
    ("Carafa II (Weyermann)",        "Roasted", 63.0,430.0),
    ("Carafa III (Weyermann)",       "Roasted", 60.0,525.0),
    ("Carafa Special I",             "Roasted", 65.0,340.0),
    ("Carafa Special II",            "Roasted", 63.0,430.0),
    ("Carafa Special III",           "Roasted", 60.0,525.0),
    ("Black Patent Malt",            "Roasted", 55.0,530.0),
    ("Roasted Barley",               "Roasted", 55.0,300.0),
    ("Pale Chocolate Malt",          "Roasted", 60.0,200.0),
    # Adjuncts / unmalted
    ("Flaked Barley",                "Adjunct", 65.0,  2.0),
    ("Flaked Corn (Maize)",          "Adjunct", 81.0,  1.3),
    ("Flaked Oats",                  "Adjunct", 70.0,  2.0),
    ("Flaked Rice",                  "Adjunct", 78.0,  1.0),
    ("Flaked Rye",                   "Adjunct", 65.0,  2.0),
    ("Flaked Wheat",                 "Adjunct", 77.0,  2.0),
    ("Raw Wheat",                    "Adjunct", 78.0,  2.0),
    ("Corn Sugar (Dextrose)",        "Sugar",   91.0,  1.0),
    ("Cane Sugar",                   "Sugar",   96.0,  1.0),
    ("Honey",                        "Sugar",   73.0,  1.0),
    ("Dry Malt Extract (Light)",     "Dry Extract", 96.0, 4.0),
    ("Dry Malt Extract (Pilsner)",   "Dry Extract", 96.0, 2.0),
    ("Liquid Malt Extract (Light)",  "Liquid Extract", 76.0, 4.0),
    ("Turbinado Sugar",              "Sugar",   94.0,  7.0),
    ("Lactose (Milk Sugar)",         "Sugar",   70.0,  1.0),
]

MALTI = []
for row in _MALTI_RAW:
    nome, ftype, yld, color = row
    MALTI.append({
        "nome": nome,
        "categoria": "grain",
        "fermentable_type": ftype,
        "yield_percent": yld,
        "color_srm": color,
    })


# ── LUPPOLI ────────────────────────────────────────────────────────────────
# (nome, alpha_acid, hop_use, hop_form, note_origine)
_LUPPOLI_RAW = [
    # Americani
    ("Amarillo",      8.5,  "Boil/Aroma/Dry Hop", "Pellet"),
    ("Cascade",       5.5,  "Boil/Aroma",          "Pellet"),
    ("Centennial",   10.0,  "Boil/Aroma",          "Pellet"),
    ("Chinook",      13.0,  "Boil",                "Pellet"),
    ("Citra",        12.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Columbus (CTZ)",15.0, "Boil",                "Pellet"),
    ("Galaxy",       14.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Hallertau Blanc",10.0,"Aroma/Dry Hop",       "Pellet"),
    ("Idaho 7",      14.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Loral",        11.0,  "Boil/Aroma",          "Pellet"),
    ("Magnum (US)",  14.0,  "Boil",                "Pellet"),
    ("Meridian",      6.5,  "Aroma/Dry Hop",       "Pellet"),
    ("Millennium",   16.5,  "Boil",                "Pellet"),
    ("Mosaic",       12.5,  "Aroma/Dry Hop",       "Pellet"),
    ("Motueka",       7.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Nugget",       13.0,  "Boil",                "Pellet"),
    ("Sabro",        15.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Simcoe",       13.0,  "Boil/Aroma/Dry Hop",  "Pellet"),
    ("Strata",       13.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Summit",       17.0,  "Boil",                "Pellet"),
    ("Talus",        10.0,  "Aroma/Dry Hop",       "Pellet"),
    ("Warrior",      16.0,  "Boil",                "Pellet"),
    ("Willamette",    5.0,  "Aroma",               "Pellet"),
    ("Waimea",       19.0,  "Boil/Aroma",          "Pellet"),
    ("Zythos",       10.0,  "Boil/Aroma",          "Pellet"),
    # Europei
    ("Hallertauer Mittelfrüh",  4.0, "Aroma",      "Pellet"),
    ("Tettnang",               4.5,  "Aroma",      "Pellet"),
    ("Spalt",                  4.0,  "Aroma",      "Pellet"),
    ("Saaz",                   3.5,  "Aroma",      "Pellet"),
    ("Styrian Goldings",       5.5,  "Aroma",      "Pellet"),
    ("Fuggles",                4.5,  "Aroma",      "Pellet"),
    ("East Kent Goldings",     5.0,  "Aroma",      "Pellet"),
    ("Challenger",            7.5,   "Boil",       "Pellet"),
    ("Northern Brewer",        9.0,  "Boil",       "Pellet"),
    ("Perle",                  8.0,  "Boil",       "Pellet"),
    ("Target",                11.0,  "Boil",       "Pellet"),
    ("Magnum (DE)",           14.0,  "Boil",       "Pellet"),
    ("Polaris",               20.0,  "Boil",       "Pellet"),
    ("Herkules",              17.0,  "Boil",       "Pellet"),
    ("Saphir",                 3.5,  "Aroma",      "Pellet"),
    ("Smaragd",                4.5,  "Aroma",      "Pellet"),
    ("Opal",                   7.5,  "Boil/Aroma", "Pellet"),
    ("Callista",               4.0,  "Aroma",      "Pellet"),
    ("Merkur",                13.5,  "Boil",       "Pellet"),
    ("Mandarina Bavaria",      8.5,  "Aroma",      "Pellet"),
    ("Hallertau Blanc",       10.0,  "Aroma",      "Pellet"),
    ("Tradition",              6.0,  "Aroma",      "Pellet"),
    ("Admiral",               13.5,  "Boil",       "Pellet"),
    ("First Gold",             7.5,  "Boil/Aroma", "Pellet"),
    # New World
    ("Nelson Sauvin",         12.0,  "Aroma/Dry Hop", "Pellet"),
    ("Riwaka",                 5.5,  "Aroma/Dry Hop", "Pellet"),
    ("Pacific Jade",          13.0,  "Boil",          "Pellet"),
    ("Green Bullet",          13.0,  "Boil",          "Pellet"),
    ("Vic Secret",            17.0,  "Aroma/Dry Hop", "Pellet"),
    ("Enigma",                18.0,  "Aroma/Dry Hop", "Pellet"),
    ("Ella (Stella)",         13.5,  "Aroma/Dry Hop", "Pellet"),
    ("Topaz",                 17.0,  "Boil",          "Pellet"),
    ("Ekuanot",               13.0,  "Aroma/Dry Hop", "Pellet"),
    ("El Dorado",             15.0,  "Aroma/Dry Hop", "Pellet"),
    ("HBC 638 (Triumph)",     14.0,  "Boil/Aroma",    "Pellet"),
    # Belgi / storici
    ("Styrian Wolf",          15.0,  "Boil",       "Pellet"),
    ("Hallertauer Tradition",  6.0,  "Aroma",      "Pellet"),
    ("Progress",               6.5,  "Aroma",      "Pellet"),
    ("Syrian Celeia",          5.0,  "Aroma",      "Pellet"),
    ("Nugget (IT Trentino)",  13.0,  "Boil",       "Pellet"),
    ("Cascade (IT)",           5.5,  "Boil/Aroma", "Pellet"),
]

LUPPOLI = []
for row in _LUPPOLI_RAW:
    nome, alpha, uso, forma = row
    LUPPOLI.append({
        "nome": nome,
        "categoria": "hop",
        "alpha_acid": alpha,
        "hop_use": uso,
        "hop_form": forma,
    })


# ── LIEVITI ────────────────────────────────────────────────────────────────
# (nome, attenuation, yeast_type, yeast_form)
_LIEVITI_RAW = [
    # Fermentis (secchi)
    ("Fermentis Safale US-05",         77.0, "Ale",    "Dry"),
    ("Fermentis Safale S-04",          75.0, "Ale",    "Dry"),
    ("Fermentis Safale S-33",          72.0, "Ale",    "Dry"),
    ("Fermentis Saflager W-34/70",     82.0, "Lager",  "Dry"),
    ("Fermentis Saflager S-23",        82.0, "Lager",  "Dry"),
    ("Fermentis Safbrew WB-06",        78.0, "Wheat",  "Dry"),
    ("Fermentis Safbrew T-58",         72.0, "Ale",    "Dry"),
    ("Fermentis Safbrew BE-256",       82.0, "Ale",    "Dry"),
    ("Fermentis Safbrew BE-134",       90.0, "Ale",    "Dry"),
    ("Fermentis Saflager S-189",       82.0, "Lager",  "Dry"),
    ("Fermentis SafCider AB-1",        82.0, "Cider",  "Dry"),
    # Lallemand (secchi)
    ("Lallemand BRY-97",               77.0, "Ale",    "Dry"),
    ("Lallemand Nottingham",           82.0, "Ale",    "Dry"),
    ("Lallemand Windsor",              72.0, "Ale",    "Dry"),
    ("Lallemand Munich Classic",       79.0, "Wheat",  "Dry"),
    ("Lallemand Abbaye",               76.0, "Ale",    "Dry"),
    ("Lallemand Köln",                 80.0, "Ale",    "Dry"),
    ("Lallemand Diamond (Lager)",      80.0, "Lager",  "Dry"),
    ("Lallemand New England",          77.0, "Ale",    "Dry"),
    ("Lallemand Voss Kveik",           82.0, "Kveik",  "Dry"),
    # Wyeast (liquidi)
    ("Wyeast 1056 American Ale",       75.0, "Ale",    "Liquid"),
    ("Wyeast 1068 American Ale",       73.0, "Ale",    "Liquid"),
    ("Wyeast 1272 American Ale II",    73.0, "Ale",    "Liquid"),
    ("Wyeast 1318 London Ale III",     73.0, "Ale",    "Liquid"),
    ("Wyeast 1335 British Ale II",     73.0, "Ale",    "Liquid"),
    ("Wyeast 1450 Denny's Favorite",   74.0, "Ale",    "Liquid"),
    ("Wyeast 1469 West Yorkshire Ale", 67.0, "Ale",    "Liquid"),
    ("Wyeast 1968 London ESB",         67.0, "Ale",    "Liquid"),
    ("Wyeast 2124 Bohemian Lager",     75.0, "Lager",  "Liquid"),
    ("Wyeast 2206 Bavarian Lager",     75.0, "Lager",  "Liquid"),
    ("Wyeast 2308 Munich Lager",       73.0, "Lager",  "Liquid"),
    ("Wyeast 3068 Weihenstephan Weizen",73.0,"Wheat",  "Liquid"),
    ("Wyeast 3787 Trappist High Grav.", 74.0, "Ale",   "Liquid"),
    ("Wyeast 3724 Belgian Saison",     77.0, "Ale",    "Liquid"),
    ("Wyeast 3944 Belgian Witbier",    72.0, "Ale",    "Liquid"),
    ("Wyeast 4783 Sweet Mead",         71.0, "Mead",   "Liquid"),
    # White Labs (liquidi)
    ("White Labs WLP001 California Ale", 76.0, "Ale",  "Liquid"),
    ("White Labs WLP002 English Ale",    67.0, "Ale",  "Liquid"),
    ("White Labs WLP004 Irish Ale",      69.0, "Ale",  "Liquid"),
    ("White Labs WLP007 Dry English Ale",80.0, "Ale",  "Liquid"),
    ("White Labs WLP023 Burton Ale",     69.0, "Ale",  "Liquid"),
    ("White Labs WLP028 Edinburgh Ale",  70.0, "Ale",  "Liquid"),
    ("White Labs WLP029 Kölsch",         75.0, "Ale",  "Liquid"),
    ("White Labs WLP036 Düsseldorf Alt", 72.0, "Ale",  "Liquid"),
    ("White Labs WLP041 Pacific Ale",    73.0, "Ale",  "Liquid"),
    ("White Labs WLP051 Cali. Ale V",    74.0, "Ale",  "Liquid"),
    ("White Labs WLP067 Coastal Haze",   75.0, "Ale",  "Liquid"),
    ("White Labs WLP095 Burlington Ale", 77.0, "Ale",  "Liquid"),
    ("White Labs WLP300 Hefeweizen",     73.0, "Wheat","Liquid"),
    ("White Labs WLP380 Hefeweizen IV",  73.0, "Wheat","Liquid"),
    ("White Labs WLP500 Trappist Ale",   75.0, "Ale",  "Liquid"),
    ("White Labs WLP530 Abbey Ale",      75.0, "Ale",  "Liquid"),
    ("White Labs WLP545 Belgian Strong", 78.0, "Ale",  "Liquid"),
    ("White Labs WLP565 Saison I",       70.0, "Ale",  "Liquid"),
    ("White Labs WLP568 Belgian Style",  70.0, "Ale",  "Liquid"),
    ("White Labs WLP800 Pilsner Lager",  75.0, "Lager","Liquid"),
    ("White Labs WLP802 Czech Budejovice",75.0,"Lager","Liquid"),
    ("White Labs WLP820 Oktoberfest",    73.0, "Lager","Liquid"),
    ("White Labs WLP830 German Lager",   74.0, "Lager","Liquid"),
    ("White Labs WLP833 German Bock",    74.0, "Lager","Liquid"),
    # Omega / Bootleg / The Yeast Bay
    ("Omega OYL-011 Thames Valley",      74.0, "Ale",  "Liquid"),
    ("Omega OYL-052 DIPA",               80.0, "Ale",  "Liquid"),
    ("Omega OYL-057 Diastatic DIPA",     92.0, "Ale",  "Liquid"),
    ("Omega OYL-071 Lutra Kveik",        82.0, "Kveik","Liquid"),
    ("Omega OYL-091 Hornindal Kveik",    81.0, "Kveik","Liquid"),
    ("Kveik Voss (Mead Works)",          82.0, "Kveik","Liquid"),
    ("The Yeast Bay Wallonian Farmhouse", 80.0, "Ale", "Liquid"),
]

LIEVITI = []
for row in _LIEVITI_RAW:
    nome, att, tipo, forma = row
    LIEVITI.append({
        "nome": nome,
        "categoria": "yeast",
        "attenuation": att,
        "yeast_type": tipo,
        "yeast_form": forma,
    })


# ── ALTRO ──────────────────────────────────────────────────────────────────
# (nome, misc_type, misc_use)
_MISC_RAW = [
    # Chiarificanti
    ("Irish Moss",              "Fining",    "Boil"),
    ("Whirlfloc Tablet",        "Fining",    "Boil"),
    ("Protofloc",               "Fining",    "Boil"),
    ("Gelatin (food grade)",    "Fining",    "Dry Hop"),
    ("Isinglass",               "Fining",    "Secondary"),
    ("Bentonite",               "Fining",    "Secondary"),
    ("Super-Kleer KC",          "Fining",    "Secondary"),
    ("Carrageenan",             "Fining",    "Boil"),
    ("Biofine Clear",           "Fining",    "Primary"),
    # Minerali acqua
    ("Gypsum (CaSO4)",          "Water Agent","Mash"),
    ("Calcium Chloride (CaCl2)","Water Agent","Mash"),
    ("Magnesium Sulfate (MgSO4)","Water Agent","Mash"),
    ("Sodium Chloride (NaCl)",  "Water Agent","Mash"),
    ("Calcium Carbonate (CaCO3)","Water Agent","Mash"),
    ("Sodium Bicarbonate",      "Water Agent","Mash"),
    ("Chalk",                   "Water Agent","Mash"),
    # Acidi / basi
    ("Lactic Acid 88%",         "Acid",      "Mash"),
    ("Phosphoric Acid 10%",     "Acid",      "Mash"),
    ("Citric Acid",             "Acid",      "Boil"),
    # Nutrienti lievito
    ("Yeast Nutrient (generic)","Yeast Nutrition","Boil"),
    ("Fermaid-O",               "Yeast Nutrition","Primary"),
    ("Fermaid-K",               "Yeast Nutrition","Primary"),
    ("DAP",                     "Yeast Nutrition","Primary"),
    # Spezie & aromi
    ("Coriander Seeds",         "Spice",     "Boil"),
    ("Orange Peel (Dried)",     "Flavor",    "Boil"),
    ("Orange Peel (Fresh)",     "Flavor",    "Boil"),
    ("Lemon Peel (Fresh)",      "Flavor",    "Boil"),
    ("Cinnamon",                "Spice",     "Secondary"),
    ("Vanilla Bean",            "Flavor",    "Secondary"),
    ("Cardamom",                "Spice",     "Secondary"),
    ("Ginger Root",             "Spice",     "Boil"),
    ("Juniper Berries",         "Flavor",    "Boil"),
    ("Anise Seed",              "Spice",     "Boil"),
    ("Chamomile",               "Flavor",    "Boil"),
    ("Black Pepper",            "Spice",     "Secondary"),
    ("Grains of Paradise",      "Spice",     "Boil"),
    # Campagna enzimi e altro
    ("Whirlpool Hops (loose)",  "Other",     "Whirlpool"),
    ("Lactic Acid (food-grade 80%)", "Acid", "Mash"),
    ("Calcium Hydroxide (Pickling Lime)", "Water Agent", "Mash"),
    ("Oak Chips",               "Other",     "Secondary"),
    ("Oak Spirals",             "Other",     "Secondary"),
    ("Campden Tablet (K-metabisulfite)", "Other", "Primary"),
    ("Potassium Sorbate",       "Preservation","Primary"),
    ("Lactose (Milk Sugar)",    "Adjunct",   "Boil"),
    ("Maltodextrin",            "Adjunct",   "Boil"),
    ("Coffee (Cold Brew)",      "Flavor",    "Secondary"),
    ("Cacao Nibs",              "Flavor",    "Secondary"),
    ("Coconut Flakes",          "Flavor",    "Secondary"),
    ("Honey (varietal)",        "Flavor",    "Secondary"),
    ("Maple Syrup",             "Flavor",    "Boil"),
    ("Molasses",                "Flavor",    "Boil"),
]

MISC = []
for row in _MISC_RAW:
    nome, mtype, muse = row
    MISC.append({
        "nome": nome,
        "categoria": "misc",
        "misc_type": mtype,
        "misc_use": muse,
    })

TUTTO = MALTI + LUPPOLI + LIEVITI + MISC
