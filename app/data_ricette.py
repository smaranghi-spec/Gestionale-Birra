"""
Dataset delle ricette predefinite per consultazione e importazione diretta.
Collezione di 18 stili iconici mondiali (BJCP aligned) calcolati per all-grain (23 litri, eff. 75%).
"""
import json

RICETTE_PREDEFINITE = [
    {
        "slug": "czech-bohemian-pilsner",
        "nome": "Bohemian Pilsner Tradizionale",
        "stile_nome": "Czech Premium Pale Lager",
        "stile_bjcp": "3B",
        "categoria_macro": "Lager & Bassa Fermentazione",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.048,
        "fg": 1.011,
        "abv": 4.8,
        "ibu": 38,
        "ebc": 8.0,
        "srm": 4.1,
        "descrizione": "La classica regina delle birre chiare boeme: ricca di malto Pilsner fragrante, con il caratteristico profilo floreale e speziato del luppolo nobile Saaz in quattro gittate. Fermentazione a bassa temperatura pulita e morbida.",
        "consigli_brewday": "Ammostamento a step o decoczione raccomandato. Acqua molto dolce con bassissimo contenuto di minerali (stile Pilsen). Lagering di almeno 4-6 settimane a 2°C.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Weyermann)", "categoria": "grain", "quantita": 4.8, "unita": "kg", "color_srm": 1.7, "yield_percent": 80.0, "fermentable_type": "Grain"},
            {"nome": "CaraPils (Dextrine Malt)", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 2.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 40.0, "unita": "g", "alpha_acid": 3.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 3.5, "time_min": 30, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 3.5, "time_min": 10, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 3.5, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Fermentis Saflager W-34/70", "categoria": "yeast", "quantita": 2.0, "unita": "bustina", "attenuation": 82.0, "yeast_type": "Lager", "yeast_form": "Dry"},
            {"nome": "Irish Moss", "categoria": "misc", "quantita": 5.0, "unita": "g", "time_min": 15, "misc_use": "Boil"}
        ],
        "profilo_mash": {
            "nome": "Step Mash Boemo Tradizionale",
            "steps": [
                {"step_order": 1, "name": "Protein Rest", "step_temp": 52, "step_time": 15, "step_type": "Infusion"},
                {"step_order": 2, "name": "Beta Amilasi", "step_temp": 64, "step_time": 45, "step_type": "Temperature"},
                {"step_order": 3, "name": "Alfa Amilasi", "step_temp": 72, "step_time": 20, "step_type": "Temperature"},
                {"step_order": 4, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Pilsen (Acqua Dolce)", "ca": 10.0, "mg": 3.0, "na": 4.0, "cl": 10.0, "so4": 10.0, "hco3": 15.0}
    },
    {
        "slug": "american-ipa-west-coast",
        "nome": "American IPA \"West Coast\"",
        "stile_nome": "American IPA",
        "stile_bjcp": "21A",
        "categoria_macro": "Luppolate (IPA & Pale Ale)",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.062,
        "fg": 1.012,
        "abv": 6.5,
        "ibu": 62,
        "ebc": 13.0,
        "srm": 6.6,
        "descrizione": "IPA secca, brillante e decisa nello stile della costa ovest americana. Un'esplosione di note agrumate di pompelmo, pino e frutta tropicale data dalla combinazione classica Citra, Simcoe, Centennial e Columbus.",
        "consigli_brewday": "Acqua a prevalenza di solfati (rapporto SO4:Cl almeno 2.5:1) per accentuare la nettezza dell'amaro. Dry hopping a fine fermentazione per 3-4 giorni a 16-18°C.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Maris Otter)", "categoria": "grain", "quantita": 5.4, "unita": "kg", "color_srm": 3.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 0.5, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "CaraPils (Dextrine Malt)", "categoria": "grain", "quantita": 0.3, "unita": "kg", "color_srm": 2.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Columbus (CTZ)", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 15.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Centennial", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 10.0, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Citra", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 12.0, "time_min": 5, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Simcoe", "categoria": "hop", "quantita": 40.0, "unita": "g", "alpha_acid": 13.0, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Citra", "categoria": "hop", "quantita": 40.0, "unita": "g", "alpha_acid": 12.0, "time_min": 0, "hop_use": "Dry Hop", "hop_form": "Pellet"},
            {"nome": "Mosaic", "categoria": "hop", "quantita": 40.0, "unita": "g", "alpha_acid": 12.5, "time_min": 0, "hop_use": "Dry Hop", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale US-05", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 77.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Secco",
            "steps": [
                {"step_order": 1, "name": "Ammostamento", "step_temp": 65, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Profilo Bitter/IPA (Alto Solfato)", "ca": 110.0, "mg": 15.0, "na": 15.0, "cl": 50.0, "so4": 250.0, "hco3": 40.0}
    },
    {
        "slug": "new-england-hazy-ipa",
        "nome": "New England Hazy IPA (NEIPA)",
        "stile_nome": "Hazy IPA",
        "stile_bjcp": "21B",
        "categoria_macro": "Luppolate (IPA & Pale Ale)",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.064,
        "fg": 1.015,
        "abv": 6.4,
        "ibu": 35,
        "ebc": 9.5,
        "srm": 4.8,
        "descrizione": "Birra opalescente e succosa dal corpo morbido e setoso grazie all'alta percentuale di fiocchi d'avena e frumento. Amaro contenuto e delicato, con un imponente aroma tropicale (mango, frutto della passione, ananas).",
        "consigli_brewday": "Rapporto Cloruri:Solfati inverso (Cl:SO4 circa 2:1 o 150:75 ppm) per garantire rotondità. Luppoli quasi esclusivamente in whirlpool a 80°C e doppio dry hopping a contatto breve per evitare note erbacee.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Maris Otter)", "categoria": "grain", "quantita": 4.2, "unita": "kg", "color_srm": 3.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Flaked Oats", "categoria": "grain", "quantita": 1.2, "unita": "kg", "color_srm": 2.0, "yield_percent": 70.0, "fermentable_type": "Adjunct"},
            {"nome": "Flaked Wheat", "categoria": "grain", "quantita": 0.8, "unita": "kg", "color_srm": 2.0, "yield_percent": 77.0, "fermentable_type": "Adjunct"},
            {"nome": "CaraPils (Dextrine Malt)", "categoria": "grain", "quantita": 0.3, "unita": "kg", "color_srm": 2.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Magnum (US)", "categoria": "hop", "quantita": 10.0, "unita": "g", "alpha_acid": 14.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Citra", "categoria": "hop", "quantita": 35.0, "unita": "g", "alpha_acid": 12.0, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Mosaic", "categoria": "hop", "quantita": 35.0, "unita": "g", "alpha_acid": 12.5, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Galaxy", "categoria": "hop", "quantita": 50.0, "unita": "g", "alpha_acid": 14.0, "time_min": 0, "hop_use": "Dry Hop", "hop_form": "Pellet"},
            {"nome": "Citra", "categoria": "hop", "quantita": 50.0, "unita": "g", "alpha_acid": 12.0, "time_min": 0, "hop_use": "Dry Hop", "hop_form": "Pellet"},
            {"nome": "Lallemand New England", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 77.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Corpo Pieno",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 67, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "NEIPA Soft (Alto Cloruro)", "ca": 90.0, "mg": 10.0, "na": 15.0, "cl": 150.0, "so4": 75.0, "hco3": 40.0}
    },
    {
        "slug": "american-pale-ale-cascade",
        "nome": "American Pale Ale (APA) Tradizionale",
        "stile_nome": "American Pale Ale",
        "stile_bjcp": "18B",
        "categoria_macro": "Luppolate (IPA & Pale Ale)",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.052,
        "fg": 1.012,
        "abv": 5.2,
        "ibu": 36,
        "ebc": 14.0,
        "srm": 7.1,
        "descrizione": "Il grande classico della rivoluzione brassicola artigianale (ispirata alla leggendaria Sierra Nevada Pale Ale). Base malto pulita con lieve tocco biscottato e caramellato, unita all'inconfondibile bouquet agrumato e floreale del Cascade.",
        "consigli_brewday": "Birra versatile, facile da produrre e amatissima da tutti i palati. Fermentazione a 19°C costanti per esaltare la pulizia aromatica del ceppo US-05.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Crisp)", "categoria": "grain", "quantita": 4.6, "unita": "kg", "color_srm": 3.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 0.4, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "Caramel Malt 40L", "categoria": "grain", "quantita": 0.3, "unita": "kg", "color_srm": 40.0, "yield_percent": 74.0, "fermentable_type": "Crystal"},
            {"nome": "Cascade", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 5.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Cascade", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 5.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Cascade", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 5.5, "time_min": 5, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Cascade", "categoria": "hop", "quantita": 35.0, "unita": "g", "alpha_acid": 5.5, "time_min": 0, "hop_use": "Dry Hop", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale US-05", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 77.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Equilibrato",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 66, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Pale Ale Bilanciata", "ca": 75.0, "mg": 10.0, "na": 10.0, "cl": 60.0, "so4": 120.0, "hco3": 40.0}
    },
    {
        "slug": "belgian-blanche-witbier",
        "nome": "Belgian Blanche / Witbier",
        "stile_nome": "Witbier",
        "stile_bjcp": "24A",
        "categoria_macro": "Frumento & Weizen",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.048,
        "fg": 1.010,
        "abv": 5.0,
        "ibu": 16,
        "ebc": 6.8,
        "srm": 3.5,
        "descrizione": "Tradizionale birra bianca belga di frumento, dissetante e delicatamente acidula. Caratterizzata da schiuma densa e candida, aroma fresco speziato di coriandolo macinato fresco e scorza d'arancia amara.",
        "consigli_brewday": "Utilizzare un protein rest a 52°C per facilitare la filtrazione con il 40% di cereali non maltati. Aggiungere le spezie pestate solo negli ultimi 5 minuti di bollitura per preservarne gli oli essenziali.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Dingemans)", "categoria": "grain", "quantita": 2.6, "unita": "kg", "color_srm": 1.8, "yield_percent": 79.5, "fermentable_type": "Grain"},
            {"nome": "Flaked Wheat", "categoria": "grain", "quantita": 2.0, "unita": "kg", "color_srm": 2.0, "yield_percent": 77.0, "fermentable_type": "Adjunct"},
            {"nome": "Flaked Oats", "categoria": "grain", "quantita": 0.4, "unita": "kg", "color_srm": 2.0, "yield_percent": 70.0, "fermentable_type": "Adjunct"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 3.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Hallertauer Mittelfrüh", "categoria": "hop", "quantita": 15.0, "unita": "g", "alpha_acid": 4.0, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Coriander Seeds", "categoria": "misc", "quantita": 15.0, "unita": "g", "time_min": 5, "misc_use": "Boil"},
            {"nome": "Orange Peel (Dried)", "categoria": "misc", "quantita": 15.0, "unita": "g", "time_min": 5, "misc_use": "Boil"},
            {"nome": "Chamomile", "categoria": "misc", "quantita": 2.0, "unita": "g", "time_min": 5, "misc_use": "Boil"},
            {"nome": "Fermentis Safbrew T-58", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 72.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Multi-step per Cereali Non Maltati",
            "steps": [
                {"step_order": 1, "name": "Protein Rest", "step_temp": 52, "step_time": 15, "step_type": "Infusion"},
                {"step_order": 2, "name": "Saccarificazione", "step_temp": 66, "step_time": 50, "step_type": "Temperature"},
                {"step_order": 3, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Dolce per Blanche", "ca": 50.0, "mg": 5.0, "na": 10.0, "cl": 50.0, "so4": 50.0, "hco3": 60.0}
    },
    {
        "slug": "bavarian-hefeweizen",
        "nome": "Bavarian Hefeweizen (Weissbier)",
        "stile_nome": "Weissbier",
        "stile_bjcp": "10A",
        "categoria_macro": "Frumento & Weizen",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.050,
        "fg": 1.012,
        "abv": 5.0,
        "ibu": 14,
        "ebc": 8.0,
        "srm": 4.1,
        "descrizione": "La classica birra di frumento bavarese per antonomasia: opalescente, con schiuma cremosissima e gli inconfondibili aromi naturali di banana matura (acetato di isoamile) e chiodi di garofano (4-vinilguaiacolo) prodotti dal ceppo di lievito weizen.",
        "consigli_brewday": "Step ferulico a 44°C fondamentale per produrre i precursori dei chiodi di garofano. Fermentare tra 18°C (più speziata) e 21°C (più banana). Servire con i lieviti in sospensione.",
        "ingredienti": [
            {"nome": "Wheat Malt (Weyermann)", "categoria": "grain", "quantita": 2.8, "unita": "kg", "color_srm": 2.0, "yield_percent": 83.0, "fermentable_type": "Grain"},
            {"nome": "Pilsner Malt (Weyermann)", "categoria": "grain", "quantita": 2.2, "unita": "kg", "color_srm": 1.7, "yield_percent": 80.0, "fermentable_type": "Grain"},
            {"nome": "CaraVienna I (Weyermann)", "categoria": "grain", "quantita": 0.2, "unita": "kg", "color_srm": 9.0, "yield_percent": 73.0, "fermentable_type": "Crystal"},
            {"nome": "Hallertauer Mittelfrüh", "categoria": "hop", "quantita": 22.0, "unita": "g", "alpha_acid": 4.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 12.0, "unita": "g", "alpha_acid": 4.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safbrew WB-06", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 78.0, "yeast_type": "Wheat", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Step Mash Bavarese Tradizionale (Pausa Ferulica)",
            "steps": [
                {"step_order": 1, "name": "Pausa Ferulica", "step_temp": 44, "step_time": 20, "step_type": "Infusion"},
                {"step_order": 2, "name": "Protein Rest", "step_temp": 53, "step_time": 15, "step_type": "Temperature"},
                {"step_order": 3, "name": "Saccarificazione", "step_temp": 67, "step_time": 45, "step_type": "Temperature"},
                {"step_order": 4, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Bavarese Moderata", "ca": 60.0, "mg": 10.0, "na": 5.0, "cl": 40.0, "so4": 50.0, "hco3": 70.0}
    },
    {
        "slug": "belgian-saison-farmhouse",
        "nome": "Belgian Farmhouse Saison",
        "stile_nome": "Saison",
        "stile_bjcp": "25B",
        "categoria_macro": "Belghe & Saison",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.054,
        "fg": 1.004,
        "abv": 6.6,
        "ibu": 28,
        "ebc": 9.5,
        "srm": 4.8,
        "descrizione": "La classica birra delle fattorie valloni: attenuatissima, secca, effervescente, con note pepate, fenoliche e terrose accompagnate da una freschezza agrumata irresistibile. Dissetante ma complessa.",
        "consigli_brewday": "Mash basso a 64°C per massimizzare la fermentescibilità del mosto. Lasciar salire liberamente la temperatura di fermentazione fino a 26-28°C per stimolare l'espressività del lievito Saison.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Dingemans)", "categoria": "grain", "quantita": 4.4, "unita": "kg", "color_srm": 1.8, "yield_percent": 79.5, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 0.4, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "Wheat Malt (Weyermann)", "categoria": "grain", "quantita": 0.4, "unita": "kg", "color_srm": 2.0, "yield_percent": 83.0, "fermentable_type": "Grain"},
            {"nome": "Cane Sugar", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 1.0, "yield_percent": 96.0, "fermentable_type": "Sugar"},
            {"nome": "Styrian Goldings", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 5.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 3.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 3.5, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Fermentis Safbrew BE-134", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 90.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Prolungato ad Alta Fermentescibilità",
            "steps": [
                {"step_order": 1, "name": "Beta Amilasi Secca", "step_temp": 64, "step_time": 75, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Stagionale Belga", "ca": 70.0, "mg": 10.0, "na": 15.0, "cl": 60.0, "so4": 110.0, "hco3": 45.0}
    },
    {
        "slug": "dry-irish-stout",
        "nome": "Dry Irish Stout (Guinness Style)",
        "stile_nome": "Irish Stout",
        "stile_bjcp": "15B",
        "categoria_macro": "Scure (Stout & Porter)",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.042,
        "fg": 1.009,
        "abv": 4.3,
        "ibu": 35,
        "ebc": 75.0,
        "srm": 38.0,
        "descrizione": "L'iconica birra nera irlandese: corpo leggero e beverino, schiuma densa color cappuccino, decise note di caffè tostato, cacao amaro e finale pulito e piacevolmente asciutto grazie all'orzo tostato non maltato.",
        "consigli_brewday": "Aggiungere l'orzo tostato (Roasted Barley) per l'intera durata del mash o durante gli ultimi 15 minuti se si desidera limitare l'astringenza. Servire preferibilmente con carbo moderata.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Maris Otter)", "categoria": "grain", "quantita": 3.8, "unita": "kg", "color_srm": 3.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Flaked Barley", "categoria": "grain", "quantita": 0.7, "unita": "kg", "color_srm": 2.0, "yield_percent": 65.0, "fermentable_type": "Adjunct"},
            {"nome": "Roasted Barley", "categoria": "grain", "quantita": 0.45, "unita": "kg", "color_srm": 300.0, "yield_percent": 55.0, "fermentable_type": "Roasted"},
            {"nome": "Chocolate Malt", "categoria": "grain", "quantita": 0.15, "unita": "kg", "color_srm": 350.0, "yield_percent": 60.0, "fermentable_type": "Roasted"},
            {"nome": "East Kent Goldings", "categoria": "hop", "quantita": 45.0, "unita": "g", "alpha_acid": 5.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale S-04", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 75.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo per Stout",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 66, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Dublino (Carbonati Moderati)", "ca": 110.0, "mg": 10.0, "na": 15.0, "cl": 55.0, "so4": 60.0, "hco3": 140.0}
    },
    {
        "slug": "belgian-tripel-abbazia",
        "nome": "Belgian Tripel d'Abbazia",
        "stile_nome": "Belgian Tripel",
        "stile_bjcp": "26C",
        "categoria_macro": "Belghe & Saison",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.078,
        "fg": 1.010,
        "abv": 8.9,
        "ibu": 32,
        "ebc": 9.5,
        "srm": 4.8,
        "descrizione": "Maestosa birra trappista dorata: alcolica e calda ma straordinariamente beverina grazie all'aggiunta di zucchero candito chiaro. Ricca di esteri fruttati (pera, albicocca, mela gialla) e spezie pepate del lievito belga.",
        "consigli_brewday": "Aggiungere lo zucchero candito negli ultimi 10 minuti di bollitura. Iniziare la fermentazione a 19°C e lasciarla salire a 24-25°C per garantire una totale attenuazione.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Dingemans)", "categoria": "grain", "quantita": 6.2, "unita": "kg", "color_srm": 1.8, "yield_percent": 79.5, "fermentable_type": "Grain"},
            {"nome": "Aromatic Malt", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 26.0, "yield_percent": 74.0, "fermentable_type": "Grain"},
            {"nome": "Cane Sugar", "categoria": "grain", "quantita": 0.7, "unita": "kg", "color_srm": 1.0, "yield_percent": 96.0, "fermentable_type": "Sugar"},
            {"nome": "Saaz", "categoria": "hop", "quantita": 35.0, "unita": "g", "alpha_acid": 3.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Styrian Goldings", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 5.5, "time_min": 20, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 4.5, "time_min": 5, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safbrew BE-256", "categoria": "yeast", "quantita": 2.0, "unita": "bustina", "attenuation": 82.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Doppio Step Belga",
            "steps": [
                {"step_order": 1, "name": "Beta Amilasi", "step_temp": 64, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Alfa Amilasi", "step_temp": 69, "step_time": 20, "step_type": "Temperature"},
                {"step_order": 3, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Belga Alta Gradazione", "ca": 80.0, "mg": 10.0, "na": 15.0, "cl": 70.0, "so4": 90.0, "hco3": 50.0}
    },
    {
        "slug": "belgian-dubbel-scura",
        "nome": "Belgian Dubbel Tradizionale",
        "stile_nome": "Belgian Dubbel",
        "stile_bjcp": "26B",
        "categoria_macro": "Belghe & Saison",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.066,
        "fg": 1.012,
        "abv": 7.1,
        "ibu": 22,
        "ebc": 36.0,
        "srm": 18.3,
        "descrizione": "Classica birra d'abbazia color ambrato scuro/tonaca di frate: profumo inebriante di uvetta, prugne secche, datteri e caramello tostato, sostenuto da un finale morbido e alcolico ben bilanciato.",
        "consigli_brewday": "L'uso del malto Special B e dello zucchero scuro Candi Syrup è fondamentale per ottenere il caratteristico bouquet di frutta disidratata scura.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Dingemans)", "categoria": "grain", "quantita": 4.8, "unita": "kg", "color_srm": 1.8, "yield_percent": 79.5, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Dark (Weyermann)", "categoria": "grain", "quantita": 0.8, "unita": "kg", "color_srm": 15.0, "yield_percent": 76.0, "fermentable_type": "Grain"},
            {"nome": "CaraMunich II (Weyermann)", "categoria": "grain", "quantita": 0.35, "unita": "kg", "color_srm": 31.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Special B (Dingemans)", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 180.0, "yield_percent": 65.0, "fermentable_type": "Crystal"},
            {"nome": "Cane Sugar", "categoria": "grain", "quantita": 0.45, "unita": "kg", "color_srm": 1.0, "yield_percent": 96.0, "fermentable_type": "Sugar"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 4.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Styrian Goldings", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 5.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safbrew T-58", "categoria": "yeast", "quantita": 2.0, "unita": "bustina", "attenuation": 74.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Corpulento",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 66, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Ambrata Belga", "ca": 75.0, "mg": 10.0, "na": 15.0, "cl": 60.0, "so4": 70.0, "hco3": 80.0}
    },
    {
        "slug": "munich-helles-bavarese",
        "nome": "Munich Helles Bavarese",
        "stile_nome": "Munich Helles",
        "stile_bjcp": "4A",
        "categoria_macro": "Lager & Bassa Fermentazione",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.048,
        "fg": 1.011,
        "abv": 4.9,
        "ibu": 18,
        "ebc": 7.2,
        "srm": 3.7,
        "descrizione": "Il simbolo dei biergarten di Monaco di Baviera: limpida e dorata, con note dolci e fragranti di pane bianco e cereale maltato. Amaro delicatissimo di luppolo nobile, estremamente beverina.",
        "consigli_brewday": "Bollitura di 75-90 minuti per evitare DMS. Profilo acqua con solfati bassi per preservare la rotondità maltata. Lagering di 4 settimane a 1-3°C.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Weyermann)", "categoria": "grain", "quantita": 4.6, "unita": "kg", "color_srm": 1.7, "yield_percent": 80.0, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 0.45, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "CaraPils (Dextrine Malt)", "categoria": "grain", "quantita": 0.15, "unita": "kg", "color_srm": 2.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Hallertauer Mittelfrüh", "categoria": "hop", "quantita": 26.0, "unita": "g", "alpha_acid": 4.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 15.0, "unita": "g", "alpha_acid": 4.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Saflager W-34/70", "categoria": "yeast", "quantita": 2.0, "unita": "bustina", "attenuation": 82.0, "yeast_type": "Lager", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Maltato",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 65, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Monaco di Baviera (Morbida)", "ca": 60.0, "mg": 15.0, "na": 5.0, "cl": 35.0, "so4": 30.0, "hco3": 75.0}
    },
    {
        "slug": "english-extra-special-bitter",
        "nome": "English Extra Special Bitter (ESB)",
        "stile_nome": "Strong Bitter / ESB",
        "stile_bjcp": "11C",
        "categoria_macro": "Classiche UK & Tedesche",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.054,
        "fg": 1.013,
        "abv": 5.4,
        "ibu": 38,
        "ebc": 22.0,
        "srm": 11.2,
        "descrizione": "L'apice dei pub inglesi: birra ambrata con una straordinaria profondità di malto Maris Otter, sfumature di crosta di pane, caramello tostato e l'inconfondibile eleganza terrosa e floreale dei luppoli tradizionali britannici.",
        "consigli_brewday": "Servire a temperatura di cantina (11-13°C) con carbonazione moderata (1.6-1.9 vol). Il malto Maris Otter conferisce un tocco nocciolato inimitabile.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Maris Otter)", "categoria": "grain", "quantita": 4.8, "unita": "kg", "color_srm": 3.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Crystal 45 (Crisp)", "categoria": "grain", "quantita": 0.35, "unita": "kg", "color_srm": 45.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Biscuit Malt", "categoria": "grain", "quantita": 0.2, "unita": "kg", "color_srm": 25.0, "yield_percent": 72.0, "fermentable_type": "Grain"},
            {"nome": "Black Patent Malt", "categoria": "grain", "quantita": 0.03, "unita": "kg", "color_srm": 530.0, "yield_percent": 55.0, "fermentable_type": "Roasted"},
            {"nome": "Challenger", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 7.5, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "East Kent Goldings", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 5.0, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fuggles", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 4.5, "time_min": 5, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale S-04", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 75.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Inglese Tradizionale",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 67, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Burton-on-Trent Moderata", "ca": 120.0, "mg": 15.0, "na": 20.0, "cl": 60.0, "so4": 180.0, "hco3": 80.0}
    },
    {
        "slug": "german-kolsch",
        "nome": "German Kölsch di Colonia",
        "stile_nome": "Kölsch",
        "stile_bjcp": "5B",
        "categoria_macro": "Classiche UK & Tedesche",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.046,
        "fg": 1.009,
        "abv": 4.8,
        "ibu": 24,
        "ebc": 7.0,
        "srm": 3.6,
        "descrizione": "Specialità tipica della città di Colonia: fermentata ad alta temperatura ma maturata a freddo (lagerizzata), unisce la delicatezza fruttata di un'ale alla pulizia cristallina e fragrante di una lager.",
        "consigli_brewday": "Fermentare a 16-17°C con ceppo Kölsch dedicato o US-05 freddo. Dopo la fermentazione, lagerizzare a 2°C per 3 settimane per ottenere limpidezza brillante.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Weyermann)", "categoria": "grain", "quantita": 4.2, "unita": "kg", "color_srm": 1.7, "yield_percent": 80.0, "fermentable_type": "Grain"},
            {"nome": "Vienna Malt (Weyermann)", "categoria": "grain", "quantita": 0.45, "unita": "kg", "color_srm": 4.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Wheat Malt (Weyermann)", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 2.0, "yield_percent": 83.0, "fermentable_type": "Grain"},
            {"nome": "Hallertau Tradition", "categoria": "hop", "quantita": 28.0, "unita": "g", "alpha_acid": 6.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 18.0, "unita": "g", "alpha_acid": 4.5, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Lallemand Köln", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 80.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Secco",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 65, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Colonia (Acqua Bilanciata)", "ca": 60.0, "mg": 10.0, "na": 10.0, "cl": 50.0, "so4": 70.0, "hco3": 50.0}
    },
    {
        "slug": "robust-porter-cioccolato",
        "nome": "Robust Porter al Cioccolato",
        "stile_nome": "Robust Porter",
        "stile_bjcp": "20A",
        "categoria_macro": "Scure (Stout & Porter)",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.058,
        "fg": 1.014,
        "abv": 5.8,
        "ibu": 34,
        "ebc": 60.0,
        "srm": 30.5,
        "descrizione": "Birra scura corposa e confortante: note dominanti di cioccolato fondente, nocciola tostata, toffee e una lieve sfumatura di caffè, bilanciate da un amaro erbaceo deciso ma non aggressivo.",
        "consigli_brewday": "Il malto Brown combinato al Chocolate dona complessità senza il carattere tagliente tipico dell'orzo tostato della Stout.",
        "ingredienti": [
            {"nome": "Pale Ale Malt (Maris Otter)", "categoria": "grain", "quantita": 4.6, "unita": "kg", "color_srm": 3.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 0.6, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "Brown Malt", "categoria": "grain", "quantita": 0.35, "unita": "kg", "color_srm": 65.0, "yield_percent": 65.0, "fermentable_type": "Grain"},
            {"nome": "Chocolate Malt", "categoria": "grain", "quantita": 0.35, "unita": "kg", "color_srm": 350.0, "yield_percent": 60.0, "fermentable_type": "Roasted"},
            {"nome": "Caramel Malt 80L", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 80.0, "yield_percent": 71.0, "fermentable_type": "Crystal"},
            {"nome": "Northern Brewer", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 9.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "East Kent Goldings", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 5.0, "time_min": 15, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale S-04", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 75.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Corpulento",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 67, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Londra Scure", "ca": 90.0, "mg": 10.0, "na": 15.0, "cl": 60.0, "so4": 60.0, "hco3": 110.0}
    },
    {
        "slug": "golden-ale-mandarina",
        "nome": "Summer Golden Ale",
        "stile_nome": "Blonde / Golden Ale",
        "stile_bjcp": "12A",
        "categoria_macro": "Classiche UK & Tedesche",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.045,
        "fg": 1.010,
        "abv": 4.6,
        "ibu": 22,
        "ebc": 7.0,
        "srm": 3.6,
        "descrizione": "Birra estiva rinfrescante, leggera e dal bel colore biondo dorato. Profumi morbidi di mandarino, pesca bianca e note floreali grazie al luppolo tedesco Mandarina Bavaria a fine bollitura.",
        "consigli_brewday": "Perfetta come birra della casa o per principianti. Molto rapida da maturare: pronta in bottiglia o fusto dopo soli 15-20 giorni.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Best Malz)", "categoria": "grain", "quantita": 4.0, "unita": "kg", "color_srm": 1.8, "yield_percent": 80.5, "fermentable_type": "Grain"},
            {"nome": "CaraPils (Dextrine Malt)", "categoria": "grain", "quantita": 0.3, "unita": "kg", "color_srm": 2.0, "yield_percent": 72.0, "fermentable_type": "Crystal"},
            {"nome": "Wheat Malt (Weyermann)", "categoria": "grain", "quantita": 0.2, "unita": "kg", "color_srm": 2.0, "yield_percent": 83.0, "fermentable_type": "Grain"},
            {"nome": "Magnum (DE)", "categoria": "hop", "quantita": 14.0, "unita": "g", "alpha_acid": 14.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Mandarina Bavaria", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 8.5, "time_min": 10, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Mandarina Bavaria", "categoria": "hop", "quantita": 30.0, "unita": "g", "alpha_acid": 8.5, "time_min": 0, "hop_use": "Whirlpool", "hop_form": "Pellet"},
            {"nome": "Fermentis Safale US-05", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 77.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Beverino",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 65, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Leggera Estiva", "ca": 50.0, "mg": 8.0, "na": 10.0, "cl": 45.0, "so4": 65.0, "hco3": 40.0}
    },
    {
        "slug": "vienna-lager-tradizionale",
        "nome": "Vienna Lager Tradizionale",
        "stile_nome": "Vienna Lager",
        "stile_bjcp": "7A",
        "categoria_macro": "Lager & Bassa Fermentazione",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.050,
        "fg": 1.012,
        "abv": 5.0,
        "ibu": 25,
        "ebc": 19.0,
        "srm": 9.6,
        "descrizione": "Lager ambrata elegante e raffinata, nata nel 1841 grazie a Anton Dreher. Protagonista assoluto è il malto Vienna, che dona un ricco sapore tostato di crosta di pane e nocciola senza mai risultare stucchevole.",
        "consigli_brewday": "La decoczione esalta la maltosità caratteristica dello stile. Un tocco minimo di Carafa Special colora senza rilasciare note tostate bruciate.",
        "ingredienti": [
            {"nome": "Vienna Malt (Weyermann)", "categoria": "grain", "quantita": 3.6, "unita": "kg", "color_srm": 4.0, "yield_percent": 78.0, "fermentable_type": "Grain"},
            {"nome": "Munich Malt Light (Weyermann)", "categoria": "grain", "quantita": 1.2, "unita": "kg", "color_srm": 9.0, "yield_percent": 77.0, "fermentable_type": "Grain"},
            {"nome": "CaraFoam (Weyermann)", "categoria": "grain", "quantita": 0.25, "unita": "kg", "color_srm": 2.0, "yield_percent": 75.0, "fermentable_type": "Crystal"},
            {"nome": "Carafa Special II", "categoria": "grain", "quantita": 0.04, "unita": "kg", "color_srm": 430.0, "yield_percent": 63.0, "fermentable_type": "Roasted"},
            {"nome": "Hallertauer Mittelfrüh", "categoria": "hop", "quantita": 28.0, "unita": "g", "alpha_acid": 4.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Tettnang", "categoria": "hop", "quantita": 20.0, "unita": "g", "alpha_acid": 4.5, "time_min": 20, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Saflager W-34/70", "categoria": "yeast", "quantita": 2.0, "unita": "bustina", "attenuation": 82.0, "yeast_type": "Lager", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Step Mash Tradizionale Viennese",
            "steps": [
                {"step_order": 1, "name": "Beta Amilasi", "step_temp": 64, "step_time": 45, "step_type": "Infusion"},
                {"step_order": 2, "name": "Alfa Amilasi", "step_temp": 71, "step_time": 25, "step_type": "Temperature"},
                {"step_order": 3, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Vienna Classica", "ca": 75.0, "mg": 15.0, "na": 10.0, "cl": 45.0, "so4": 60.0, "hco3": 110.0}
    },
    {
        "slug": "italian-grape-ale-bianca",
        "nome": "Italian Grape Ale (IGA) all'Uva Bianca",
        "stile_nome": "Italian Grape Ale",
        "stile_bjcp": "X4",
        "categoria_macro": "Belghe & Saison",
        "tipo": "All Grain",
        "volume_target_litri": 23.0,
        "efficienza": 75.0,
        "og": 1.060,
        "fg": 1.008,
        "abv": 6.8,
        "ibu": 18,
        "ebc": 8.0,
        "srm": 4.1,
        "descrizione": "Il primo stile birrario ufficialmente riconosciuto a livello internazionale nato in Italia: ponte armonioso tra mondo brassicolo ed enologico, caratterizzato dall'unione di malto d'orzo chiaro e mosto di uva bianca fresca (es. Trebbiano o Malvasia).",
        "consigli_brewday": "Aggiungere il mosto d'uva (pastorizzato o fresco) a fine bollitura o all'avvio della fermentazione tumultuosa. Il luppolo Hallertau Blanc regala naturali note vinose e di uva spina.",
        "ingredienti": [
            {"nome": "Pilsner Malt (Dingemans)", "categoria": "grain", "quantita": 4.2, "unita": "kg", "color_srm": 1.8, "yield_percent": 79.5, "fermentable_type": "Grain"},
            {"nome": "Wheat Malt (Weyermann)", "categoria": "grain", "quantita": 0.6, "unita": "kg", "color_srm": 2.0, "yield_percent": 83.0, "fermentable_type": "Grain"},
            {"nome": "Cane Sugar", "categoria": "grain", "quantita": 0.2, "unita": "kg", "color_srm": 1.0, "yield_percent": 96.0, "fermentable_type": "Sugar"},
            {"nome": "Hallertau Blanc", "categoria": "hop", "quantita": 18.0, "unita": "g", "alpha_acid": 10.0, "time_min": 60, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Hallertau Blanc", "categoria": "hop", "quantita": 25.0, "unita": "g", "alpha_acid": 10.0, "time_min": 10, "hop_use": "Boil", "hop_form": "Pellet"},
            {"nome": "Fermentis Safbrew BE-134", "categoria": "yeast", "quantita": 1.0, "unita": "bustina", "attenuation": 90.0, "yeast_type": "Ale", "yeast_form": "Dry"}
        ],
        "profilo_mash": {
            "nome": "Infuso Singolo Secco IGA",
            "steps": [
                {"step_order": 1, "name": "Saccarificazione", "step_temp": 64, "step_time": 60, "step_type": "Infusion"},
                {"step_order": 2, "name": "Mash Out", "step_temp": 78, "step_time": 10, "step_type": "Temperature"}
            ]
        },
        "profilo_acqua": {"nome": "Acqua Dolce per IGA", "ca": 50.0, "mg": 6.0, "na": 10.0, "cl": 40.0, "so4": 50.0, "hco3": 45.0}
    }
]


def get_ricette_libreria():
    """Restituisce l'elenco completo delle ricette predefinite."""
    return RICETTE_PREDEFINITE


def get_ricetta_by_slug(slug: str):
    """Cerca una ricetta predefinita per slug."""
    for r in RICETTE_PREDEFINITE:
        if r["slug"] == slug:
            return r
    return None
