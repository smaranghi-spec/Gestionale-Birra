"""
Template e profili predefiniti di ammostamento in stile Brewfather / BJCP.
"""

MASH_TEMPLATES = {
    "Singolo Infuso - Medio (Bilanciato)": [
        {"nome": "Saccarificazione", "temp_gradi": 66.5, "durata_min": 60, "tipo": "Infusion"},
        {"nome": "Mash Out", "temp_gradi": 76.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Singolo Infuso - Bassa Temp (Secco/Attenuato)": [
        {"nome": "Saccarificazione (Beta)", "temp_gradi": 64.5, "durata_min": 75, "tipo": "Infusion"},
        {"nome": "Mash Out", "temp_gradi": 76.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Singolo Infuso - Alta Temp (Corpo Pieno/Dolce)": [
        {"nome": "Saccarificazione (Alfa)", "temp_gradi": 68.5, "durata_min": 60, "tipo": "Infusion"},
        {"nome": "Mash Out", "temp_gradi": 76.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "BIAB (Brew In A Bag)": [
        {"nome": "Ammostamento Unico", "temp_gradi": 66.0, "durata_min": 60, "tipo": "Infusion"},
        {"nome": "Mash Out", "temp_gradi": 76.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Step Mash - Hochkurz (Lager Tedesche)": [
        {"nome": "Maltasi / Beta-Amilasi", "temp_gradi": 63.0, "durata_min": 35, "tipo": "Temperature"},
        {"nome": "Alfa-Amilasi", "temp_gradi": 72.0, "durata_min": 35, "tipo": "Temperature"},
        {"nome": "Mash Out", "temp_gradi": 77.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Step Mash - Tradizionale 4 Step (Weizen/Frumento)": [
        {"nome": "Acid Rest (Fitasi/Ferulico)", "temp_gradi": 44.0, "durata_min": 15, "tipo": "Temperature"},
        {"nome": "Protein Rest", "temp_gradi": 52.0, "durata_min": 20, "tipo": "Temperature"},
        {"nome": "Saccarificazione", "temp_gradi": 66.0, "durata_min": 45, "tipo": "Temperature"},
        {"nome": "Mash Out", "temp_gradi": 77.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Decozione Singola (Pilsner/Bock)": [
        {"nome": "Ammostamento 1", "temp_gradi": 64.0, "durata_min": 35, "tipo": "Infusion"},
        {"nome": "Sosta post-decozione", "temp_gradi": 72.0, "durata_min": 30, "tipo": "Decoction"},
        {"nome": "Mash Out", "temp_gradi": 77.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "Decozione Doppia (Bavarese)": [
        {"nome": "Protein Rest", "temp_gradi": 50.0, "durata_min": 20, "tipo": "Infusion"},
        {"nome": "Step 1 (post decozione 1)", "temp_gradi": 65.0, "durata_min": 35, "tipo": "Decoction"},
        {"nome": "Step 2 (post decozione 2)", "temp_gradi": 72.0, "durata_min": 25, "tipo": "Decoction"},
        {"nome": "Mash Out", "temp_gradi": 77.0, "durata_min": 10, "tipo": "Temperature"},
    ],
    "No-Sparge": [
        {"nome": "Saccarificazione", "temp_gradi": 67.0, "durata_min": 75, "tipo": "Infusion"},
    ],
}

MASH_TEMPLATES_ALIASES = {
    "Singolo Infuso": "Singolo Infuso - Medio (Bilanciato)",
    "Step Mash": "Step Mash - Hochkurz (Lager Tedesche)",
    "Decozione": "Decozione Singola (Pilsner/Bock)",
    "BIAB": "BIAB (Brew In A Bag)",
    "No-Sparge": "No-Sparge",
}

def get_template_steps(nome: str):
    """Restituisce la lista degli step per un template dato o None."""
    if not nome:
        return None
    if nome in MASH_TEMPLATES:
        return [dict(st) for st in MASH_TEMPLATES[nome]]
    if nome in MASH_TEMPLATES_ALIASES:
        target = MASH_TEMPLATES_ALIASES[nome]
        return [dict(st) for st in MASH_TEMPLATES[target]]
    return None
