"""
Modulo Auto-BOM, Smart Connection Suggestion Engine e Web Part Catalog.
Risolutore idraulico brassicolo multi-opzione per calcolare e suggerire diverse
modalità di collegamento (Raccordo Rapido Camlock, Tri-Clamp Sanitario,
Tubo con Portagomma e Fascetta, Accoppiamento Rigido / Duotight) tra due
componenti qualsiasi posizionati nello spazio 3D.
"""
from typing import List, Dict, Tuple, Optional
from collections import deque
import math

# ── DEFINIZIONE TIPI CONNESSIONE (PORTE IDRAULICHE) ──────────────────────────
PORTS = {
    "TC15": {"nome": "Tri-Clamp 1.5\" (flangia 50.5mm)", "categoria": "Tri-Clamp", "diametro_mm": 50.5},
    "TC20": {"nome": "Tri-Clamp 2.0\" (flangia 64mm)", "categoria": "Tri-Clamp", "diametro_mm": 64.0},
    "TC10": {"nome": "Mini Tri-Clamp 1.0\" (flangia 34mm)", "categoria": "Tri-Clamp", "diametro_mm": 34.0},
    "BSP12M": {"nome": "Filettatura 1/2\" BSP Maschio", "categoria": "Filetto Gas", "genere": "M"},
    "BSP12F": {"nome": "Filettatura 1/2\" BSP Femmina", "categoria": "Filetto Gas", "genere": "F"},
    "BSP34M": {"nome": "Filettatura 3/4\" BSP Maschio", "categoria": "Filetto Gas", "genere": "M"},
    "BSP34F": {"nome": "Filettatura 3/4\" BSP Femmina", "categoria": "Filetto Gas", "genere": "F"},
    "BSP38M": {"nome": "Filettatura 3/8\" BSP Maschio", "categoria": "Filetto Gas", "genere": "M"},
    "BARB12": {"nome": "Portagomma 12 mm (1/2\")", "categoria": "Portagomma", "diametro_mm": 12},
    "BARB10": {"nome": "Portagomma 10 mm (3/8\")", "categoria": "Portagomma", "diametro_mm": 10},
    "BARB15": {"nome": "Portagomma 15 mm (5/8\")", "categoria": "Portagomma", "diametro_mm": 15},
    "CAM_A": {"nome": "Camlock Maschio (Accoppiatore A/F)", "categoria": "Attacco Rapido"},
    "CAM_C": {"nome": "Camlock Femmina (Accoppiatore C/D)", "categoria": "Attacco Rapido"},
    "JG8": {"nome": "Innesto Rapido Duotight / John Guest 8mm (5/16\")", "categoria": "Push-Fit"},
    "DIN25": {"nome": "Bocchettone Enologico DIN 25 Inox", "categoria": "DIN Sanitario"},
    "TUBO12": {"nome": "Tubo Silicone Alimentare 12x18 mm", "categoria": "Flessibile"},
}

# ── CATALOGO COMPONENTI ADATTATORI & RACCORDI DROPSHIPPING ──────────────────
RACCORDI = [
    {
        "sku": "FIT-TC15-BSP12M",
        "nome": "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Maschio (Inox 304)",
        "p1": "TC15", "p2": "BSP12M",
        "costo_eur": 7.90, "prezzo_consigliato": 11.50,
        "accessori": [("CLAMP-TC15", 1), ("GSK-TC15", 1)],
    },
    {
        "sku": "FIT-TC15-BSP12F",
        "nome": "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Femmina (Inox 304)",
        "p1": "TC15", "p2": "BSP12F",
        "costo_eur": 8.20, "prezzo_consigliato": 11.90,
        "accessori": [("CLAMP-TC15", 1), ("GSK-TC15", 1)],
    },
    {
        "sku": "FIT-TC15-BARB12",
        "nome": "Portagomma Tri-Clamp 1.5\" a 12mm (Inox 304)",
        "p1": "TC15", "p2": "BARB12",
        "costo_eur": 6.80, "prezzo_consigliato": 9.90,
        "accessori": [("CLAMP-TC15", 1), ("GSK-TC15", 1)],
    },
    {
        "sku": "FIT-TC20-TC15",
        "nome": "Riduttore Conico Concentrico Tri-Clamp 2.0\" a 1.5\" (Inox 304)",
        "p1": "TC20", "p2": "TC15",
        "costo_eur": 12.50, "prezzo_consigliato": 17.90,
        "accessori": [("CLAMP-TC20", 1), ("GSK-TC20", 1)],
    },
    {
        "sku": "FIT-TC10-TC15",
        "nome": "Adattatore Mini Tri-Clamp 1.0\" a 1.5\" (Inox 304)",
        "p1": "TC10", "p2": "TC15",
        "costo_eur": 9.50, "prezzo_consigliato": 13.90,
        "accessori": [("CLAMP-TC10", 1), ("GSK-TC10", 1)],
    },
    {
        "sku": "FIT-NIP-12M-12M",
        "nome": "Nipples Esagonale 1/2\" BSP Maschio - Maschio (Inox 316)",
        "p1": "BSP12F", "p2": "BSP12F",
        "costo_eur": 2.40, "prezzo_consigliato": 3.90,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "FIT-MAN-12F-12F",
        "nome": "Manicotto Filettato 1/2\" BSP Femmina - Femmina (Inox 316)",
        "p1": "BSP12M", "p2": "BSP12M",
        "costo_eur": 2.90, "prezzo_consigliato": 4.50,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "FIT-BARB-12M-12",
        "nome": "Portagomma Dritto 1/2\" BSP Maschio a 12 mm (Inox 304)",
        "p1": "BSP12F", "p2": "BARB12",
        "costo_eur": 3.20, "prezzo_consigliato": 4.90,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "FIT-BARB-12F-12",
        "nome": "Portagomma Dritto 1/2\" BSP Femmina a 12 mm (Inox 304)",
        "p1": "BSP12M", "p2": "BARB12",
        "costo_eur": 3.50, "prezzo_consigliato": 5.20,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "FIT-RED-34F-12M",
        "nome": "Riduzione Femmina 3/4\" BSP a Maschio 1/2\" BSP (Inox 316)",
        "p1": "BSP34M", "p2": "BSP12F",
        "costo_eur": 3.80, "prezzo_consigliato": 5.80,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "FIT-RED-34M-12F",
        "nome": "Riduzione Maschio 3/4\" a Femmina 1/2\" BSP (Inox 316)",
        "p1": "BSP34F", "p2": "BSP12F",
        "costo_eur": 3.80, "prezzo_consigliato": 5.80,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "CAM-TYPE-A",
        "nome": "Adattatore Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina)",
        "p1": "BSP12M", "p2": "CAM_A",
        "costo_eur": 4.80, "prezzo_consigliato": 7.50,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "CAM-TYPE-F",
        "nome": "Adattatore Camlock Tipo F (Maschio Camlock x 1/2\" BSP Maschio)",
        "p1": "BSP12F", "p2": "CAM_A",
        "costo_eur": 5.10, "prezzo_consigliato": 7.90,
        "accessori": [("TEFLON-PTFE", 1)],
    },
    {
        "sku": "CAM-TYPE-C",
        "nome": "Accoppiatore Camlock Tipo C (Femmina Camlock x Portagomma 12mm)",
        "p1": "CAM_A", "p2": "BARB12",
        "costo_eur": 7.20, "prezzo_consigliato": 10.90,
        "accessori": [],
    },
    {
        "sku": "FIT-TUBO-CON",
        "nome": "Spezzone Tubo Silicone Platinum Cured 12x18 mm (1.5 m) + 2x Fascette Inox W4",
        "p1": "BARB12", "p2": "BARB12",
        "costo_eur": 4.50, "prezzo_consigliato": 8.50,
        "accessori": [],
    },
]

ACCESSORI_CATALOGO = {
    "CLAMP-TC15": {
        "sku": "CLAMP-TC15",
        "nome": "Morsetto Tri-Clamp 1.5\" ad aletta (Inox 304)",
        "prezzo_consigliato": 4.50,
    },
    "GSK-TC15": {
        "sku": "GSK-TC15",
        "nome": "Guarnizione Silicone Alimentare Tri-Clamp 1.5\"",
        "prezzo_consigliato": 1.20,
    },
    "CLAMP-TC20": {
        "sku": "CLAMP-TC20",
        "nome": "Morsetto Tri-Clamp 2.0\" ad aletta (Inox 304)",
        "prezzo_consigliato": 5.50,
    },
    "GSK-TC20": {
        "sku": "GSK-TC20",
        "nome": "Guarnizione Silicone Alimentare Tri-Clamp 2.0\"",
        "prezzo_consigliato": 1.50,
    },
    "CLAMP-TC10": {
        "sku": "CLAMP-TC10",
        "nome": "Morsetto Mini Tri-Clamp 1.0\" (Inox 304)",
        "prezzo_consigliato": 3.90,
    },
    "GSK-TC10": {
        "sku": "GSK-TC10",
        "nome": "Guarnizione Silicone Mini Tri-Clamp 1.0\"",
        "prezzo_consigliato": 1.00,
    },
    "TEFLON-PTFE": {
        "sku": "TEFLON-PTFE",
        "nome": "Nastro PTFE Sigillante Filetti ad Alta Densità (Certificato MOCA)",
        "prezzo_consigliato": 1.00,
    },
    "FASCETTA-W4-12": {
        "sku": "FASCETTA-W4-12",
        "nome": "Fascetta Stringitubo Inox W4 (12-22 mm) a Bordi Arrotondati",
        "prezzo_consigliato": 1.20,
    },
}


def _adattatore_verso_target(porta: str, target: str) -> List[Dict]:
    """Restituisce la lista di articoli necessari per convertire `porta` nello standard `target`."""
    if porta == target:
        return []
    # Adattatori verso Portagomma 12mm (BARB12)
    if target == "BARB12":
        mapping = {
            "TC15": [
                {"sku": "FIT-TC15-BARB12", "nome": "Portagomma Tri-Clamp 1.5\" a 12mm Inox 304", "qta": 1, "prezzo": 9.90},
                {"sku": "CLAMP-TC15", "nome": "Morsetto Tri-Clamp 1.5\" Inox 304", "qta": 1, "prezzo": 4.50},
                {"sku": "GSK-TC15", "nome": "Guarnizione Silicone Tri-Clamp 1.5\"", "qta": 1, "prezzo": 1.20},
            ],
            "TC20": [
                {"sku": "FIT-TC20-BARB12", "nome": "Portagomma Tri-Clamp 2.0\" a 12mm Inox 304", "qta": 1, "prezzo": 12.90},
                {"sku": "CLAMP-TC20", "nome": "Morsetto Tri-Clamp 2.0\" Inox 304", "qta": 1, "prezzo": 5.50},
                {"sku": "GSK-TC20", "nome": "Guarnizione Silicone Tri-Clamp 2.0\"", "qta": 1, "prezzo": 1.50},
            ],
            "TC10": [
                {"sku": "FIT-TC10-BARB12", "nome": "Portagomma Mini Tri-Clamp 1.0\" a 12mm Inox", "qta": 1, "prezzo": 8.90},
                {"sku": "CLAMP-TC10", "nome": "Morsetto Mini Tri-Clamp 1.0\"", "qta": 1, "prezzo": 3.90},
                {"sku": "GSK-TC10", "nome": "Guarnizione Mini Tri-Clamp 1.0\"", "qta": 1, "prezzo": 1.00},
            ],
            "BSP12M": [
                {"sku": "FIT-BARB-12F-12", "nome": "Portagomma 1/2\" BSP Femmina a 12mm Inox 304", "qta": 1, "prezzo": 5.20},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP12F": [
                {"sku": "FIT-BARB-12M-12", "nome": "Portagomma 1/2\" BSP Maschio a 12mm Inox 304", "qta": 1, "prezzo": 4.90},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP34M": [
                {"sku": "FIT-BARB-34F-12", "nome": "Portagomma 3/4\" BSP Femmina a 12mm Inox 304", "qta": 1, "prezzo": 6.50},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP34F": [
                {"sku": "FIT-BARB-34M-12", "nome": "Portagomma 3/4\" BSP Maschio a 12mm Inox 304", "qta": 1, "prezzo": 6.20},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "CAM_A": [
                {"sku": "CAM-TYPE-C", "nome": "Camlock Tipo C Femmina x Portagomma 12mm Inox", "qta": 1, "prezzo": 10.90},
            ],
            "CAM_C": [
                {"sku": "CAM-TYPE-E", "nome": "Camlock Tipo E Maschio x Portagomma 12mm Inox", "qta": 1, "prezzo": 8.90},
            ],
        }
        return mapping.get(porta, [
            {"sku": f"FIT-ADAPT-{porta}-BARB12", "nome": f"Adattatore Inox da {PORTS.get(porta, {}).get('nome', porta)} a Portagomma 12mm", "qta": 1, "prezzo": 7.90}
        ])

    # Adattatori verso Camlock Maschio sul componente (CAM_A)
    if target == "CAM_A":
        mapping = {
            "BSP12M": [
                {"sku": "CAM-TYPE-A", "nome": "Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina)", "qta": 1, "prezzo": 7.50},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP12F": [
                {"sku": "CAM-TYPE-F", "nome": "Camlock Tipo F (Maschio Camlock x 1/2\" BSP Maschio)", "qta": 1, "prezzo": 7.90},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP34M": [
                {"sku": "FIT-RED-34F-12M", "nome": "Riduzione Inox 3/4\" F a 1/2\" M", "qta": 1, "prezzo": 5.80},
                {"sku": "CAM-TYPE-A", "nome": "Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina)", "qta": 1, "prezzo": 7.50},
            ],
            "TC15": [
                {"sku": "FIT-TC15-CAM-A", "nome": "Flangia Tri-Clamp 1.5\" con Innesto Maschio Camlock", "qta": 1, "prezzo": 13.50},
                {"sku": "CLAMP-TC15", "nome": "Morsetto Tri-Clamp 1.5\" Inox 304", "qta": 1, "prezzo": 4.50},
                {"sku": "GSK-TC15", "nome": "Guarnizione Silicone Tri-Clamp 1.5\"", "qta": 1, "prezzo": 1.20},
            ],
        }
        return mapping.get(porta, [
            {"sku": f"CAM-ADAPT-{porta}", "nome": f"Adattatore Innesto Rapido Camlock per {PORTS.get(porta, {}).get('nome', porta)}", "qta": 1, "prezzo": 9.50}
        ])

    # Adattatori verso Tri-Clamp 1.5" (TC15)
    if target == "TC15":
        mapping = {
            "BSP12M": [
                {"sku": "FIT-TC15-BSP12F", "nome": "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Femmina Inox", "qta": 1, "prezzo": 11.90},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "BSP12F": [
                {"sku": "FIT-TC15-BSP12M", "nome": "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Maschio Inox", "qta": 1, "prezzo": 11.50},
                {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante MOCA", "qta": 1, "prezzo": 1.00},
            ],
            "TC20": [
                {"sku": "FIT-TC20-TC15", "nome": "Riduttore Conico Tri-Clamp 2.0\" a 1.5\" Inox", "qta": 1, "prezzo": 17.90},
                {"sku": "CLAMP-TC20", "nome": "Morsetto Tri-Clamp 2.0\" Inox 304", "qta": 1, "prezzo": 5.50},
                {"sku": "GSK-TC20", "nome": "Guarnizione Silicone Tri-Clamp 2.0\"", "qta": 1, "prezzo": 1.50},
            ],
        }
        return mapping.get(porta, [
            {"sku": f"TC15-ADAPT-{porta}", "nome": f"Flangia Adattatrice Tri-Clamp 1.5\" per {PORTS.get(porta, {}).get('nome', porta)}", "qta": 1, "prezzo": 12.50}
        ])

    return []


def _aggrega_pezzi(lista_pezzi: List[Dict]) -> Tuple[List[Dict], float]:
    mappa = {}
    for p in lista_pezzi:
        sku = p["sku"]
        if sku in mappa:
            mappa[sku]["qta"] += p["qta"]
        else:
            mappa[sku] = dict(p)
    items = list(mappa.values())
    totale = round(sum(i["prezzo"] * i["qta"] for i in items), 2)
    return items, totale


def suggerisci_opzioni_connessione(nodo_a: str, nodo_b: str, distanza_m: float = 1.5) -> Dict:
    """
    Motore di suggerimento intelligente per connettere due porte qualsiasi nello spazio 3D.
    Restituisce 3-4 soluzioni concrete:
      1. Raccordo Rapido Camlock Inox + Tubo Silicone (Sgancio Rapido)
      2. Connessione Sanitaria Tri-Clamp 1.5" + Morsetti + Tubo Silicone
      3. Tubo Alimentare con Portagomma e Fascetta Inox (Economica & Universale)
      4. Innesto Rapido Push-Fit Duotight / Accoppiamento Diretto Rigido
    """
    nome_a = PORTS.get(nodo_a, {}).get("nome", nodo_a)
    nome_b = PORTS.get(nodo_b, {}).get("nome", nodo_b)
    lunghezza_tubo = max(0.5, round(float(distanza_m or 1.5) * 1.15, 1))  # +15% lasco curva morbida
    prezzo_tubo = round(lunghezza_tubo * 5.20, 2)

    opzioni = []

    # ── OPZIONE 1: RACCORDO RAPIDO CAMLOCK INOX + TUBO SILICONE ───────────────
    pezzi_cam = []
    pezzi_cam.extend(_adattatore_verso_target(nodo_a, "CAM_A"))
    pezzi_cam.extend(_adattatore_verso_target(nodo_b, "CAM_A"))
    pezzi_cam.extend([
        {"sku": "CAM-TYPE-C", "nome": "Accoppiatore Rapido Camlock Tipo C Femmina x Portagomma 12mm Inox", "qta": 2, "prezzo": 10.90},
        {"sku": f"TUBO-SIL-{int(lunghezza_tubo*10)}", "nome": f"Tubo Silicone Platinum Cured 12x18mm ({lunghezza_tubo} m)", "qta": 1, "prezzo": prezzo_tubo},
        {"sku": "FASCETTA-W4-12", "nome": "Fascetta Stringitubo Inox W4 su Camlock", "qta": 2, "prezzo": 1.20},
    ])
    items_cam, tot_cam = _aggrega_pezzi(pezzi_cam)
    opzioni.append({
        "id": "camlock_rapido",
        "titolo": "⚡ Raccordo Rapido Camlock Inox + Tubo Silicone",
        "badge": "Consigliato · Sgancio Rapido",
        "colore_3d": "#f97316",
        "stile_tubo": "camlock",
        "descrizione": f"Converte {nome_a} e {nome_b} in attacchi rapidi Camlock Inox 316 con leva a camme e tubo in silicone ({lunghezza_tubo} m). Sganci il tubo in 2 secondi senza chiavi.",
        "pezzi": items_cam,
        "totale_eur": tot_cam,
        "lunghezza_m": lunghezza_tubo,
    })

    # ── OPZIONE 2: CONNESSIONE SANITARIA TRI-CLAMP 1.5" ───────────────────────
    pezzi_tc = []
    pezzi_tc.extend(_adattatore_verso_target(nodo_a, "TC15"))
    pezzi_tc.extend(_adattatore_verso_target(nodo_b, "TC15"))
    if distanza_m <= 0.45:
        # Accoppiamento diretto flangia-a-flangia
        pezzi_tc.extend([
            {"sku": "CLAMP-TC15", "nome": "Morsetto Tri-Clamp 1.5\" ad aletta Inox 304", "qta": 1, "prezzo": 4.50},
            {"sku": "GSK-TC15", "nome": "Guarnizione Silicone Alimentare Tri-Clamp 1.5\"", "qta": 1, "prezzo": 1.20},
        ])
        desc_tc = f"Accoppiamento sanitario rigido diretto Tri-Clamp 1.5\" tra {nome_a} e {nome_b} con morsetto a farfalla e guarnizione."
    else:
        pezzi_tc.extend([
            {"sku": "FIT-TC15-BARB12", "nome": "Portagomma Sanitario Tri-Clamp 1.5\" a 12mm Inox 304", "qta": 2, "prezzo": 9.90},
            {"sku": "CLAMP-TC15", "nome": "Morsetto Tri-Clamp 1.5\" ad aletta Inox 304", "qta": 2, "prezzo": 4.50},
            {"sku": "GSK-TC15", "nome": "Guarnizione Silicone Alimentare Tri-Clamp 1.5\"", "qta": 2, "prezzo": 1.20},
            {"sku": f"TUBO-SIL-{int(lunghezza_tubo*10)}", "nome": f"Tubo Silicone Platinum Cured 12x18mm ({lunghezza_tubo} m)", "qta": 1, "prezzo": prezzo_tubo},
            {"sku": "FASCETTA-W4-12", "nome": "Fascetta Stringitubo Inox W4", "qta": 2, "prezzo": 1.20},
        ])
        desc_tc = f"Connessione sanitaria professionale Tri-Clamp 1.5\" (zero filetti a contatto col mosto, smontaggio rapido per sanificazione CIP) + linea silicone ({lunghezza_tubo} m)."

    items_tc, tot_tc = _aggrega_pezzi(pezzi_tc)
    opzioni.append({
        "id": "triclamp_sanitario",
        "titolo": "🏥 Clamp Sanitario Tri-Clamp 1.5\" + Guarnizione",
        "badge": "Standard Birrificio · Igiene CIP",
        "colore_3d": "#38bdf8",
        "stile_tubo": "triclamp",
        "descrizione": desc_tc,
        "pezzi": items_tc,
        "totale_eur": tot_tc,
        "lunghezza_m": lunghezza_tubo,
    })

    # ── OPZIONE 3: PORTAGOMMA + TUBO SILICONE CON FASCETTA INOX ───────────────
    pezzi_barb = []
    pezzi_barb.extend(_adattatore_verso_target(nodo_a, "BARB12"))
    pezzi_barb.extend(_adattatore_verso_target(nodo_b, "BARB12"))
    pezzi_barb.extend([
        {"sku": f"TUBO-SIL-{int(lunghezza_tubo*10)}", "nome": f"Tubo Silicone Alimentare Alta Temp 12x18mm ({lunghezza_tubo} m)", "qta": 1, "prezzo": prezzo_tubo},
        {"sku": "FASCETTA-W4-12", "nome": "Fascetta Stringitubo a Vite Inox W4 (12-22mm)", "qta": 2, "prezzo": 1.20},
    ])
    items_barb, tot_barb = _aggrega_pezzi(pezzi_barb)
    opzioni.append({
        "id": "tubo_fascetta",
        "titolo": "🔧 Portagomma + Tubo Silicone con Fascetta Inox",
        "badge": "Più Economico · Universale",
        "colore_3d": "#10b981",
        "stile_tubo": "fascetta",
        "descrizione": f"Soluzione classica ed economica: {nome_a} e {nome_b} portati a portagomma da 12mm, collegati con tubo in silicone alimentare ({lunghezza_tubo} m) e bloccati con 2 fascette stringitubo Inox.",
        "pezzi": items_barb,
        "totale_eur": tot_barb,
        "lunghezza_m": lunghezza_tubo,
    })

    # ── OPZIONE 4: INNESTO RAPIDO JOHN GUEST / DUOTIGHT 8MM ───────────────────
    pezzi_jg = [
        {"sku": f"JG-ADAPT-{nodo_a}", "nome": f"Innesto Rapido Push-Fit Duotight 8mm per {nome_a}", "qta": 1, "prezzo": 4.50},
        {"sku": f"JG-ADAPT-{nodo_b}", "nome": f"Innesto Rapido Push-Fit Duotight 8mm per {nome_b}", "qta": 1, "prezzo": 4.50},
        {"sku": f"TUBO-EVABARRIER-{int(lunghezza_tubo*10)}", "nome": f"Tubo Rigido EVABarrier 8mm Doppia Parete ({lunghezza_tubo} m)", "qta": 1, "prezzo": round(lunghezza_tubo * 2.80, 2)},
        {"sku": "CLIP-JG-8", "nome": "Clip Sicurezza Antisfilamento John Guest 8mm", "qta": 2, "prezzo": 0.50},
    ]
    items_jg, tot_jg = _aggrega_pezzi(pezzi_jg)
    opzioni.append({
        "id": "pushfit_duotight",
        "titolo": "🔌 Innesto Rapido Push-Fit (John Guest / Duotight)",
        "badge": "Ideale Acqua / Gas / Glicole",
        "colore_3d": "#a855f7",
        "stile_tubo": "pushfit",
        "descrizione": f"Innesti rapidi a pressione con doppia guarnizione O-Ring EPDM e tubo semirigido EVABarrier ({lunghezza_tubo} m). Inserimento a spinta senza attrezzi.",
        "pezzi": items_jg,
        "totale_eur": tot_jg,
        "lunghezza_m": lunghezza_tubo,
    })

    return {
        "nodo_a": nodo_a,
        "nodo_b": nodo_b,
        "distanza_m": round(distanza_m, 2),
        "opzioni": opzioni,
        "default_opzione": opzioni[0],
    }


# ── SOLVER IDRAULICO BFS (RETROCOMPATIBILITÀ API) ───────────────────────────

def risolvi_connessione(nodo_a: str, nodo_b: str, max_passi: int = 4, distanza_m: float = 1.5) -> Dict:
    """
    Risolve il percorso idraulico tra nodo_a e nodo_b e include anche tutte le
    opzioni di connessione suggerite (`opzioni_suggerite`).
    """
    if nodo_a not in PORTS or nodo_b not in PORTS:
        return {"errore": "Porta non riconosciuta nel dizionario idraulico"}

    multi = suggerisci_opzioni_connessione(nodo_a, nodo_b, distanza_m=distanza_m)
    scelta = multi["default_opzione"]

    return {
        "percorso": [nodo_a, scelta["id"].upper(), nodo_b],
        "pezzi": scelta["pezzi"],
        "totale_eur": scelta["totale_eur"],
        "compatibile": True,
        "descrizione": scelta["descrizione"],
        "opzioni_suggerite": multi["opzioni"],
    }
