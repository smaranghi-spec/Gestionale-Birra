"""
Modulo Auto-BOM e Retrofit Engine.
Risolutore idraulico brassicolo a grafo per calcolare la combinazione minima di raccordi,
flange, guarnizioni e tubi necessari per unire due componenti meccanici qualsiasi.
"""
from typing import List, Dict, Tuple, Optional
from collections import deque

# ── DEFINIZIONE TIPI CONNESSIONE ─────────────────────────────────────────────
PORTS = {
    "TC15": {"nome": "Tri-Clamp 1.5\" (flangia 50.5mm)", "categoria": "Tri-Clamp", "diametro_mm": 50.5},
    "TC20": {"nome": "Tri-Clamp 2.0\" (flangia 64mm)", "categoria": "Tri-Clamp", "diametro_mm": 64.0},
    "TC10": {"nome": "Mini Tri-Clamp 1.0\" (flangia 34mm)", "categoria": "Tri-Clamp", "diametro_mm": 34.0},
    "BSP12M": {"nome": "Filettatura 1/2\" BSP Maschio", "categoria": "Filetto Gas", "genere": "M"},
    "BSP12F": {"nome": "Filettatura 1/2\" BSP Femmina", "categoria": "Filetto Gas", "genere": "F"},
    "BSP34M": {"nome": "Filettatura 3/4\" BSP Maschio", "categoria": "Filetto Gas", "genere": "M"},
    "BSP34F": {"nome": "Filettatura 3/4\" BSP Femmina", "categoria": "Filetto Gas", "genere": "F"},
    "BARB12": {"nome": "Portagomma 12 mm (1/2\")", "categoria": "Portagomma", "diametro_mm": 12},
    "BARB10": {"nome": "Portagomma 10 mm (3/8\")", "categoria": "Portagomma", "diametro_mm": 10},
    "CAM_A": {"nome": "Camlock Maschio (Accoppiatore A)", "categoria": "Attacco Rapido"},
    "CAM_C": {"nome": "Camlock Femmina con Portagomma", "categoria": "Attacco Rapido"},
    "CAM_F": {"nome": "Camlock Maschio Filettato", "categoria": "Attacco Rapido"},
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
        "accessori": [],
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
    "TEFLON-PTFE": {
        "sku": "TEFLON-PTFE",
        "nome": "Nastro PTFE Sigillante Filetti ad Alta Densità (Certificato MOCA)",
        "prezzo_consigliato": 1.00,
    },
}

# ── SOLVER IDRAULICO BFS (SHORTEST PATH SUL GRAFO DELLE CONNESSIONI) ────────

def risolvi_connessione(nodo_a: str, nodo_b: str, max_passi: int = 4) -> Dict:
    """
    Risolve il percorso idraulico più breve ed economico tra nodo_a e nodo_b.
    Restituisce la Distinta Base (BOM), il totale economico e la spiegazione del montaggio.
    """
    if nodo_a not in PORTS or nodo_b not in PORTS:
        return {"errore": "Porta non riconosciuta nel dizionario idraulico"}

    if nodo_a == nodo_b:
        # Già identici (es. due barb collegati da un tubo o due TC15 uniti da morsetto)
        if nodo_a == "TC15":
            return {
                "percorso": ["TC15", "TC15"],
                "pezzi": [
                    {"sku": "CLAMP-TC15", "nome": ACCESSORI_CATALOGO["CLAMP-TC15"]["nome"], "qta": 1, "prezzo": 4.50},
                    {"sku": "GSK-TC15", "nome": ACCESSORI_CATALOGO["GSK-TC15"]["nome"], "qta": 1, "prezzo": 1.20},
                ],
                "totale_eur": 5.70,
                "compatibile": True,
                "descrizione": "I due attacchi Tri-Clamp 1.5\" si accoppiano direttamente con morsetto e guarnizione inclusi.",
            }
        elif nodo_a == "BARB12":
            return {
                "percorso": ["BARB12", "BARB12"],
                "pezzi": [
                    {"sku": "FIT-TUBO-CON", "nome": "Spezzone Tubo Silicone Platinum Cured 12x18 mm (1.5 m) + Fascette", "qta": 1, "prezzo": 8.50}
                ],
                "totale_eur": 8.50,
                "compatibile": True,
                "descrizione": "I due portagomma vengono connessi tramite tubo in silicone alimentare 12x18 mm con fascette di sicurezza.",
            }
        elif nodo_a == "BSP12M":
            return {
                "percorso": ["BSP12M", "BSP12M"],
                "pezzi": [
                    {"sku": "FIT-MAN-12F-12F", "nome": "Manicotto Filettato 1/2\" BSP Femmina - Femmina", "qta": 1, "prezzo": 4.50},
                    {"sku": "TEFLON-PTFE", "nome": "Nastro PTFE Sigillante Filetti", "qta": 1, "prezzo": 1.00},
                ],
                "totale_eur": 5.50,
                "compatibile": True,
                "descrizione": "Due filettature maschio 1/2\" BSP vengono unite tramite manicotto femmina-femmina in inox 316.",
            }

    # BFS sul grafo dei raccordi
    # Costruisci grafo adiacenze
    grafo = {}
    for r in RACCORDI:
        p1, p2 = r["p1"], r["p2"]
        grafo.setdefault(p1, []).append((p2, r))
        grafo.setdefault(p2, []).append((p1, r))

    # Coda BFS: (nodo_corrente, [raccordi_usati], [nodi_attraversati])
    coda = deque([(nodo_a, [], [nodo_a])])
    visitati = {nodo_a}
    miglior_soluzione = None

    while coda:
        curr, path_raccordi, nodi = coda.popleft()

        if curr == nodo_b:
            miglior_soluzione = (path_raccordi, nodi)
            break

        if len(path_raccordi) >= max_passi:
            continue

        for vicino, raccordo in grafo.get(curr, []):
            if vicino not in visitati:
                visitati.add(vicino)
                coda.append((vicino, path_raccordi + [raccordo], nodi + [vicino]))

    if not miglior_soluzione:
        # Fallback con ponte Tubo Flessibile (converti A a BARB12, converti B a BARB12 e unisci)
        return _risolvi_con_ponte_flessibile(nodo_a, nodo_b)

    raccordi_scelti, nodi_sequenza = miglior_soluzione
    return _costruisci_bom(raccordi_scelti, nodi_sequenza)

def _risolvi_con_ponte_flessibile(nodo_a: str, nodo_b: str) -> Dict:
    """Risolve accoppiando A e B tramite tubazione flessibile alimentare a sgancio rapido."""
    parti_a = risolvi_connessione(nodo_a, "BARB12", max_passi=2)
    parti_b = risolvi_connessione(nodo_b, "BARB12", max_passi=2)
    
    pezzi_aggregati = {}
    for p in parti_a.get("pezzi", []) + parti_b.get("pezzi", []):
        sku = p["sku"]
        if sku in pezzi_aggregati:
            pezzi_aggregati[sku]["qta"] += p["qta"]
        else:
            pezzi_aggregati[sku] = dict(p)

    # Aggiungi tubo di connessione centrale
    tubo = {
        "sku": "FIT-TUBO-CON",
        "nome": "Spezzone Tubo Silicone Platinum Cured 12x18 mm (1.5 m) + 2x Fascette Inox W4",
        "qta": 1,
        "prezzo": 8.50
    }
    pezzi_aggregati[tubo["sku"]] = tubo

    totale = sum(item["prezzo"] * item["qta"] for item in pezzi_aggregati.values())

    return {
        "percorso": [nodo_a, "BARB12", "TUBO12", "BARB12", nodo_b],
        "pezzi": list(pezzi_aggregati.values()),
        "totale_eur": round(totale, 2),
        "compatibile": True,
        "descrizione": f"Connessione universale: {PORTS[nodo_a]['nome']} portato a portagomma, unito a {PORTS[nodo_b]['nome']} tramite tubo alimentare flessibile.",
    }

def _costruisci_bom(raccordi: List[Dict], nodi: List[str]) -> Dict:
    pezzi_map = {}
    totale = 0.0

    for r in raccordi:
        sku = r["sku"]
        if sku not in pezzi_map:
            pezzi_map[sku] = {
                "sku": sku,
                "nome": r["nome"],
                "qta": 1,
                "prezzo": r["prezzo_consigliato"]
            }
        else:
            pezzi_map[sku]["qta"] += 1

        # Aggiungi accessori indispensabili (morsetti, guarnizioni, teflon)
        for acc_sku, acc_qta in r.get("accessori", []):
            if acc_sku in ACCESSORI_CATALOGO:
                acc_info = ACCESSORI_CATALOGO[acc_sku]
                if acc_sku not in pezzi_map:
                    pezzi_map[acc_sku] = {
                        "sku": acc_sku,
                        "nome": acc_info["nome"],
                        "qta": acc_qta,
                        "prezzo": acc_info["prezzo_consigliato"]
                    }
                else:
                    pezzi_map[acc_sku]["qta"] += acc_qta

    pezzi_list = list(pezzi_map.values())
    totale = sum(p["prezzo"] * p["qta"] for p in pezzi_list)

    return {
        "percorso": nodi,
        "pezzi": pezzi_list,
        "totale_eur": round(totale, 2),
        "compatibile": True,
        "descrizione": f"Combinazione minima calcolata: {len(raccordi)} raccordo/i con accessori di tenuta stagna inclusi.",
    }
