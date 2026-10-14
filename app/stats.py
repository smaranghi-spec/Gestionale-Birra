import math


def _to_kg(quantita, unita):
    conversioni = {"kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
    return quantita * conversioni.get(unita, 1.0)


def _to_g(quantita, unita):
    return _to_kg(quantita, unita) * 1000


def calcola_stats(ricetta, ingredienti=None, efficienza_param=None):
    # Support signature: calcola_stats(ingredienti, volume, efficienza) as well as calcola_stats(ricetta, ingredienti)
    if isinstance(ricetta, (list, tuple)) and not hasattr(ricetta, "volume_target_litri"):
        actual_ingredienti = ricetta
        actual_volume = ingredienti
        actual_eff = efficienza_param
        ricetta_obj = None
    else:
        actual_ingredienti = ingredienti if ingredienti is not None else []
        actual_volume = getattr(ricetta, "volume_target_litri", None) if ricetta else None
        actual_eff = getattr(ricetta, "efficienza", None) if ricetta else None
        ricetta_obj = ricetta

    try:
        vol = float(actual_volume) if actual_volume is not None and float(actual_volume) > 0 else 20.0
    except (ValueError, TypeError):
        vol = 20.0

    try:
        eff_raw = float(actual_eff) if actual_eff is not None and float(actual_eff) > 0 else 75.0
    except (ValueError, TypeError):
        eff_raw = 75.0
    eff = eff_raw / 100.0

    volume = vol
    efficienza = eff

    gu = 0.0
    ibu = 0.0
    mcu = 0.0
    attenuazione_lievito = None

    for i in actual_ingredienti:
        try:
            categoria = getattr(i, "categoria", None) or (i.get("categoria") if isinstance(i, dict) else "")
            quantita = getattr(i, "quantita", None) or (i.get("quantita") if isinstance(i, dict) else 0.0) or 0.0
            unita = getattr(i, "unita", None) or (i.get("unita") if isinstance(i, dict) else "kg") or "kg"

            if categoria == "grain":
                q_kg = _to_kg(float(quantita), unita)
                yield_raw = getattr(i, "yield_percent", None) or (i.get("yield_percent") if isinstance(i, dict) else 0.0) or 0.0
                y = float(yield_raw) / 100.0
                color_raw = getattr(i, "color_srm", None) or (i.get("color_srm") if isinstance(i, dict) else 0.0) or 0.0
                color = float(color_raw)
                if volume > 0:
                    gu += q_kg * y * efficienza * 383.6 / volume
                q_lb = q_kg * 2.2046
                v_gal = volume / 3.785
                if v_gal > 0:
                    mcu += (color * q_lb) / v_gal

            elif categoria == "hop":
                alpha_raw = getattr(i, "alpha_acid", None) or (i.get("alpha_acid") if isinstance(i, dict) else None)
                if alpha_raw:
                    q_g = _to_g(float(quantita), unita)
                    alpha = float(alpha_raw) / 100.0
                    t_raw = getattr(i, "time_min", None) or (i.get("time_min") if isinstance(i, dict) else 0) or 0
                    t = float(t_raw)
                    og_for_util = 1.0 + gu / 1000.0
                    bigness = 1.65 * (0.000125 ** (og_for_util - 1.0))
                    if t > 0:
                        boil_factor = (1.0 - math.exp(-0.04 * t)) / 4.15
                    else:
                        boil_factor = 0.0
                    utilization = bigness * boil_factor
                    if volume > 0:
                        ibu += (alpha * q_g * utilization * 1000.0) / (volume * 1.34095)

            elif categoria == "yeast":
                att_raw = getattr(i, "attenuation", None) or (i.get("attenuation") if isinstance(i, dict) else None)
                if att_raw:
                    attenuazione_lievito = float(att_raw) / 100.0
        except Exception:
            continue

    og = 1.0 + gu / 1000.0
    att = attenuazione_lievito if attenuazione_lievito is not None else 0.75
    fg = 1.0 + (gu / 1000.0) * (1.0 - att)
    abv = max(0.0, (og - fg) * 131.25)

    srm = 1.4922 * (mcu**0.6859) if mcu > 0 else 0.0
    ebc = srm * 1.97
    bu_gu = round(ibu / gu, 2) if gu > 0 else 0.0

    return {
        "og": round(og, 3),
        "fg": round(fg, 3),
        "abv": round(abv, 1),
        "ibu": round(ibu, 1),
        "srm": round(srm, 1),
        "ebc": round(ebc, 1),
        "bu_gu": bu_gu,
        "gu": round(gu, 1),
    }


def _check(valore, minv, maxv):
    if minv is None or maxv is None:
        return "na"
    if valore < minv:
        return "sotto"
    if valore > maxv:
        return "sopra"
    return "ok"


def calcola_percentuali(ingredienti):
    from collections import defaultdict

    PESO_UNITA = {"g", "kg", "lb", "oz"}

    cat_totals = defaultdict(float)
    ing_norms = {}

    for i in ingredienti:
        q = i.quantita or 0.0
        u = (i.unita or "").lower()

        if i.categoria == "grain":
            norm = _to_kg(q, u)
        elif i.categoria == "hop":
            norm = _to_g(q, u)
        elif i.categoria == "yeast":
            norm = q
        else:
            norm = _to_g(q, u) if u in PESO_UNITA else q

        ing_norms[i.id] = norm
        cat_totals[i.categoria] += norm

    UNITA_BASE = {"grain": "kg", "hop": "g", "yeast": "pz", "misc": "g"}

    result = {}
    for i in ingredienti:
        totale = cat_totals[i.categoria]
        norm = ing_norms.get(i.id, 0.0)
        perc = round(norm / totale * 100, 1) if totale > 0 else 0.0
        result[i.id] = {
            "perc": perc,
            "norm": round(norm, 4),
            "cat_totale": round(totale, 4),
            "unita_base": UNITA_BASE.get(i.categoria, ""),
        }

    return result


def confronta_stile(stats, stile):
    if stile is None:
        return None
    return {
        "nome": stile.nome,
        "linea_guida": stile.linea_guida,
        "og": {
            "valore": stats["og"],
            "min": stile.og_min,
            "max": stile.og_max,
            "stato": _check(stats["og"], stile.og_min, stile.og_max),
        },
        "fg": {
            "valore": stats["fg"],
            "min": stile.fg_min,
            "max": stile.fg_max,
            "stato": _check(stats["fg"], stile.fg_min, stile.fg_max),
        },
        "ibu": {
            "valore": stats["ibu"],
            "min": stile.ibu_min,
            "max": stile.ibu_max,
            "stato": _check(stats["ibu"], stile.ibu_min, stile.ibu_max),
        },
        "srm": {
            "valore": stats["srm"],
            "min": stile.srm_min,
            "max": stile.srm_max,
            "stato": _check(stats["srm"], stile.srm_min, stile.srm_max),
        },
        "ebc": {
            "valore": stats["ebc"],
            "min": stile.ebc_min,
            "max": stile.ebc_max,
            "stato": _check(stats["ebc"], stile.ebc_min, stile.ebc_max),
        },
        "abv": {
            "valore": stats["abv"],
            "min": stile.abv_min,
            "max": stile.abv_max,
            "stato": _check(stats["abv"], stile.abv_min, stile.abv_max),
        },
    }


SRM_COLORS = [
    (2, "#F3F993"),
    (3, "#F5F75C"),
    (4, "#F6F513"),
    (5, "#EAE615"),
    (6, "#E0D01B"),
    (7, "#D5BC26"),
    (8, "#CDAA37"),
    (9, "#C1963C"),
    (10, "#BE8C3A"),
    (12, "#BE823A"),
    (14, "#BC7A3A"),
    (16, "#B87033"),
    (18, "#B56727"),
    (20, "#B26033"),
    (24, "#A85839"),
    (30, "#985336"),
    (40, "#8D4C32"),
    (50, "#7C3D2B"),
    (60, "#6B3122"),
    (80, "#520F06"),
]


def srm_to_hex(srm):
    """Converte un valore SRM nel colore esadecimale corrispondente."""
    srm = max(0.0, float(srm or 0))
    if srm <= 0:
        return "#F3F993"
    for threshold, color in SRM_COLORS:
        if srm <= threshold:
            return color
    return "#0F0101"


def calcola_costo(ingredienti):
    """Calcola costo totale materie prime (prezzo_unitario × quantita per ingrediente)."""
    totale = 0.0
    dettaglio = []
    for i in ingredienti:
        pu = getattr(i, "prezzo_unitario", None) or 0.0
        costo = round(pu * (i.quantita or 0.0), 4)
        totale += costo
        if pu > 0:
            dettaglio.append(
                {
                    "id": i.id,
                    "nome": i.nome,
                    "quantita": i.quantita,
                    "unita": i.unita,
                    "prezzo_unitario": round(pu, 4),
                    "costo": round(costo, 2),
                }
            )
    return {"totale": round(totale, 2), "dettaglio": dettaglio}
