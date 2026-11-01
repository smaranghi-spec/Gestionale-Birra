import math
import json


def _to_kg(quantita, unita):
    conversioni = {"kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
    return float(quantita or 0.0) * conversioni.get((unita or "kg").lower(), 1.0)


def _to_g(quantita, unita):
    return _to_kg(quantita, unita) * 1000.0


def plato_from_sg(sg: float) -> float:
    """Converte densità specifica (SG) in Gradi Plato (°P) tramite equazione polinomiale ASBC / Lincoln."""
    if sg <= 1.0:
        return 0.0
    return (-1.0 * 616.868) + (1111.14 * sg) - (630.272 * (sg**2)) + (135.997 * (sg**3))


def _get_val(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def calcola_stats(ricetta, ingredienti=None, efficienza_param=None):
    """
    Calcola statistiche birrarie complete allineate agli standard e algoritmi di Brewfather.
    Supporta signature flessibile:
      - calcola_stats(ricetta, ingredienti)
      - calcola_stats(ricetta) dove ricetta contiene "ingredienti"
      - calcola_stats(ingredienti, volume, efficienza)
    """
    if isinstance(ricetta, (list, tuple)) and not hasattr(ricetta, "volume_target_litri") and not (isinstance(ricetta, dict) and "volume_target_litri" in ricetta):
        actual_ingredienti = ricetta
        actual_volume = ingredienti
        actual_eff = efficienza_param
        ricetta_obj = None
    else:
        actual_ingredienti = ingredienti if ingredienti is not None else (_get_val(ricetta, "ingredienti") or [])
        actual_volume = _get_val(ricetta, "volume_target_litri")
        actual_eff = _get_val(ricetta, "efficienza")
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

    gu_mashed = 0.0
    gu_unmashed = 0.0
    gu_unfermentable = 0.0
    mcu = 0.0
    grist_totale_kg = 0.0
    attenuazione_lievito = None
    hop_entries = []

    # 1. Analisi ingredienti (Fermentabili, Luppoli, Lieviti)
    for i in actual_ingredienti:
        try:
            categoria = (getattr(i, "categoria", None) or (i.get("categoria") if isinstance(i, dict) else "") or "").lower()
            quantita = getattr(i, "quantita", None) or (i.get("quantita") if isinstance(i, dict) else 0.0) or 0.0
            unita = getattr(i, "unita", None) or (i.get("unita") if isinstance(i, dict) else "kg") or "kg"
            nome = str(getattr(i, "nome", None) or (i.get("nome") if isinstance(i, dict) else "") or "").strip()
            nome_lower = nome.lower()

            if categoria == "grain":
                q_kg = _to_kg(float(quantita), unita)
                ftype = str(getattr(i, "fermentable_type", None) or (i.get("fermentable_type") if isinstance(i, dict) else "") or "").strip()
                ftype_lower = ftype.lower()

                # Controllo se è uno zucchero/estratto che non subisce perdite di ammostamento (efficienza 100%)
                is_sugar_or_extract = (
                    ftype_lower in ("sugar", "dry extract", "liquid extract", "extract")
                    or any(k in nome_lower for k in ("sugar", "zucchero", "candi", "miele", "honey", "dextrose", "destrosio", "dme", "lme", "sciroppo", "syrup", "estratto"))
                )

                # Controllo se è non fermentabile (es. Lattosio, Maltodestrina)
                is_unfermentable = any(k in nome_lower for k in ("lactose", "lattosio", "maltodextrin", "maltodestrina"))

                # Resa potenziale (Yield % su base fine dry basis, standard saccarosio = 100% = 46.21 PPG = 383.9 PKE)
                yield_raw = getattr(i, "yield_percent", None) or (i.get("yield_percent") if isinstance(i, dict) else 0.0) or 0.0
                try:
                    y = float(yield_raw) / 100.0 if float(yield_raw) > 0 else (1.0 if is_sugar_or_extract else 0.78)
                except (ValueError, TypeError):
                    y = 1.0 if is_sugar_or_extract else 0.78

                color_raw = getattr(i, "color_srm", None) or (i.get("color_srm") if isinstance(i, dict) else 0.0) or 0.0
                try:
                    color = max(0.0, float(color_raw))
                except (ValueError, TypeError):
                    color = 2.0

                # Calcolo punti gravità (GU)
                if volume > 0 and q_kg > 0:
                    if is_sugar_or_extract:
                        pts = q_kg * y * 1.0 * 383.9 / volume
                        gu_unmashed += pts
                    else:
                        pts = q_kg * y * efficienza * 383.9 / volume
                        gu_mashed += pts
                        grist_totale_kg += q_kg

                    if is_unfermentable:
                        gu_unfermentable += pts

                # Calcolo colore Morey MCU
                q_lb = q_kg * 2.20462
                v_gal = volume / 3.78541
                if v_gal > 0 and color > 0:
                    mcu += (color * q_lb) / v_gal

            elif categoria == "hop":
                alpha_raw = getattr(i, "alpha_acid", None) or (i.get("alpha_acid") if isinstance(i, dict) else None)
                if alpha_raw:
                    q_g = _to_g(float(quantita), unita)
                    alpha = float(alpha_raw) / 100.0
                    t_raw = getattr(i, "time_min", None) or (i.get("time_min") if isinstance(i, dict) else 0) or 0
                    t = float(t_raw) if t_raw is not None else 0.0
                    use = str(getattr(i, "hop_use", None) or (i.get("hop_use") if isinstance(i, dict) else "Boil") or "Boil").strip()
                    form = str(getattr(i, "hop_form", None) or (i.get("hop_form") if isinstance(i, dict) else "Pellet") or "Pellet").strip()
                    hop_entries.append({
                        "q_g": q_g,
                        "alpha": alpha,
                        "time_min": t,
                        "use": use,
                        "form": form,
                    })

            elif categoria == "yeast":
                att_raw = getattr(i, "attenuation", None) or (i.get("attenuation") if isinstance(i, dict) else None)
                if att_raw:
                    try:
                        attenuazione_lievito = float(att_raw) / 100.0
                    except (ValueError, TypeError):
                        pass
        except Exception:
            continue

    total_gu = gu_mashed + gu_unmashed
    og = 1.0 + (total_gu / 1000.0)

    # 2. Modulazione dell'attenuazione da temperatura di ammostamento (Stile Brewfather)
    temp_mash_effettiva = 67.0
    pm = _get_val(ricetta_obj, "profilo_mash")
    if pm:
        steps = None
        if isinstance(pm, dict):
            steps = pm.get("steps") or pm.get("steps_json")
        elif hasattr(pm, "steps_json"):
            steps = getattr(pm, "steps_json")
        elif hasattr(pm, "steps"):
            steps = getattr(pm, "steps")

        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except Exception:
                steps = None

        if isinstance(steps, list):
            for st in steps:
                if isinstance(st, dict):
                    t_step = float(st.get("temp_gradi") or st.get("step_temp") or st.get("temp") or 0)
                    if 60 <= t_step <= 72:
                        temp_mash_effettiva = t_step
                        break

    att_base = attenuazione_lievito if attenuazione_lievito is not None else 0.76
    # Brewfather: per ogni grado sotto 67°C beta-amilasi favorisce fermentescibilità (+0.8%/°C, max +3%)
    # per ogni grado sopra 67°C alfa-amilasi crea destrine non fermentabili (-1.2%/°C, max -4%)
    delta_t = temp_mash_effettiva - 67.0
    if delta_t < 0:
        mash_att_mod = min(0.03, abs(delta_t) * 0.008)
    else:
        mash_att_mod = -min(0.045, delta_t * 0.012)
    att_effettiva = max(0.60, min(0.95, att_base + mash_att_mod))

    # Punti fermentabili vs non fermentabili (Lattosio / maltodestrine)
    gu_fermentable = max(0.0, total_gu - gu_ununfermentable_pts if (gu_ununfermentable_pts := gu_unfermentable) else total_gu)
    fg_pts = (gu_fermentable * (1.0 - att_effettiva)) + gu_unfermentable
    fg = 1.0 + (fg_pts / 1000.0)

    # 3. Calcolo Alcol (ABV): Formula Hall / Brewfather per massima precisione, più standard
    abv_std = max(0.0, (og - fg) * 131.25)
    if og > fg and (1.775 - og) > 0 and fg > 0:
        abv_adv = (76.08 * (og - fg) / (1.775 - og)) * (fg / 0.794)
        abv = abv_adv
    else:
        abv = abv_std

    # Alcol in peso (ABW)
    abw = (abv * 0.79336 / fg) if fg > 0 else 0.0

    # Gradi Plato (°P)
    plato_og = plato_from_sg(og)
    plato_fg = plato_from_sg(fg)

    # Attenuazione apparente reale misurata
    att_apparente = ((og - fg) / (og - 1.0) * 100.0) if og > 1.0 else 0.0

    # Calorie per bottiglia 33 cl (Brewfather caloric estimation)
    real_extract = (0.1808 * plato_og) + (0.8192 * plato_fg)
    calorie_33cl = max(0.0, ((6.9 * abw) + 4.0 * (real_extract - 0.1)) * fg * 3.3)

    # 4. Calcolo IBU Metodo Tinseth Metrico Esatto (Brewfather Aligned)
    total_ibu = 0.0
    bigness = 1.65 * (0.000125 ** (max(1.0, og) - 1.0))

    for h in hop_entries:
        q_g = h["q_g"]
        alpha = h["alpha"]
        t = h["time_min"]
        use = h["use"].lower()
        form = h["form"].lower()

        pellet_factor = 1.10 if form == "pellet" or not form else 1.00

        if "dry" in use or "freddo" in use:
            # Dry Hop non apporta IBU da isomerizzazione
            u = 0.0
        elif "first" in use or "fwh" in use:
            # First Wort Hop: resa circa +10% rispetto a 60 min boil
            tf = (1.0 - math.exp(-0.04 * 60.0)) / 4.15
            u = bigness * tf * 1.10
        elif "whirl" in use or "hopstand" in use or "fiamma" in use or "steep" in use:
            # Whirlpool sub-ebollizione (~85°C): tasso isomerizzazione ~35% con stima 10m se a fine fiamma
            durata_whirl = t if t > 0 else 10.0
            tf = (1.0 - math.exp(-0.04 * durata_whirl)) / 4.15
            u = bigness * tf * 0.35
        elif "mash" in use:
            tf = (1.0 - math.exp(-0.04 * 60.0)) / 4.15
            u = bigness * tf * 0.20
        else:
            # Boil standard
            tf = (1.0 - math.exp(-0.04 * t)) / 4.15 if t > 0 else 0.0
            u = bigness * tf

        utilization = u * pellet_factor
        if volume > 0 and q_g > 0 and alpha > 0:
            hop_ibu = (q_g * alpha * 1000.0 * utilization) / volume
            total_ibu += hop_ibu

    # 5. Colore Morey
    srm = 1.4922 * (mcu**0.6859) if mcu > 0 else 0.0
    ebc = srm * 1.97

    # 6. Bilanciamento Amaro BU/GU & Ray Daniels Ratio
    bu_gu = round(total_ibu / total_gu, 2) if total_gu > 0 else 0.0
    if bu_gu < 0.35:
        bilanciamento_desc = "Molto maltosa"
    elif bu_gu < 0.50:
        bilanciamento_desc = "Maltosa"
    elif bu_gu < 0.65:
        bilanciamento_desc = "Bilanciata"
    elif bu_gu < 0.85:
        bilanciamento_desc = "Luppolata"
    else:
        bilanciamento_desc = "Molto amara"

    # 7. Budget Acqua e Volumi di Cotta (Stile Brewfather con Profilo Impianto)
    pb = _get_val(ricetta_obj, "profilo_birrificio")
    v_boil_loss = float(_get_val(pb, "boil_off_litri_ora") or 2.5)
    v_trub_loss = float(_get_val(pb, "trub_loss_litri") or 1.5)
    v_deadspace = float(_get_val(pb, "mash_tun_deadspace_litri") or 0.0)
    grain_absorp = float(_get_val(pb, "assorbimento_grani_l_kg") or 0.96)
    mash_ratio = float(_get_val(pb, "rapporto_mash_l_kg") or 3.0)

    v_preboil = volume + v_boil_loss + v_trub_loss
    assorbimento_grani = grist_totale_kg * grain_absorp
    acqua_totale = v_preboil + assorbimento_grani + v_deadspace
    acqua_mash = round((grist_totale_kg * mash_ratio) + v_deadspace, 1) if grist_totale_kg > 0 else 0.0
    acqua_sparge = round(max(0.0, acqua_totale - acqua_mash), 1)

    temp_mash_target = temp_mash_effettiva or 67.0
    strike_water_temp = round(temp_mash_target + 0.4 * (grist_totale_kg / max(1.0, acqua_mash)) * (temp_mash_target - 20.0), 1) if acqua_mash > 0 else temp_mash_target

    preboil_gu = (gu_mashed * volume / v_preboil) if v_preboil > 0 else 0.0
    preboil_og = 1.0 + (preboil_gu / 1000.0)
    preboil_plato = plato_from_sg(preboil_og)

    # 8. Moduli Avanzati Brewfather (pH Mash, Acidi, Pitch Rate, Priming)
    ph_info = calcola_ph_mash(ricetta_obj, actual_ingredienti, _get_val(ricetta_obj, "profilo_acqua"))
    acidi_info = calcola_dosi_acido(acqua_mash, acqua_sparge, ph_info["ph_stimato"])

    stile_obj = _get_val(ricetta_obj, "stile")
    stile_nome = str(_get_val(stile_obj, "nome") or _get_val(ricetta_obj, "stile_nome") or "")
    pitch_info = calcola_pitch_rate(og, volume, stile_nome)

    priming_info = calcola_priming(volume, 20.0, 2.4)

    volumi_dict = {
        "volume_target": round(volume, 1),
        "peso_grani_kg": round(grist_totale_kg, 2),
        "preboil_volume": round(v_preboil, 1),
        "preboil_og": round(preboil_og, 3),
        "preboil_plato": round(preboil_plato, 1),
        "acqua_totale": round(acqua_totale, 1),
        "acqua_mash": round(acqua_mash, 1),
        "acqua_sparge": round(acqua_sparge, 1),
        "strike_water_temp": strike_water_temp,
        "assorbimento_grani": round(assorbimento_grani, 1),
        "deadspace": v_deadspace,
        "boil_loss": v_boil_loss,
        "trub_loss": v_trub_loss,
    }

    return {
        "og": round(og, 3),
        "fg": round(fg, 3),
        "abv": round(abv, 1),
        "abv_standard": round(abv_std, 1),
        "abw": round(abw, 1),
        "plato_og": round(plato_og, 1),
        "plato_fg": round(plato_fg, 1),
        "og_plato": round(plato_og, 1),
        "fg_plato": round(plato_fg, 1),
        "attenuazione": round(att_apparente, 1),
        "attenuazione_apparente": round(att_apparente, 1),
        "ibu": round(total_ibu, 1),
        "srm": round(srm, 1),
        "ebc": round(ebc, 1),
        "bu_gu": bu_gu,
        "gu": round(total_gu, 1),
        "bilanciamento": bilanciamento_desc,
        "calorie_33cl": int(round(calorie_33cl)),
        "preboil_volume": round(v_preboil, 1),
        "preboil_og": round(preboil_og, 3),
        "preboil_plato": round(preboil_plato, 1),
        "acqua_totale": round(acqua_totale, 1),
        "acqua_mash": round(acqua_mash, 1),
        "acqua_sparge": round(acqua_sparge, 1),
        "strike_water_temp": strike_water_temp,
        "assorbimento_grani": round(assorbimento_grani, 1),
        "volumi": volumi_dict,
        "ph_mash": ph_info,
        "acidi": acidi_info,
        "pitch_rate": pitch_info,
        "priming": priming_info,
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
    try:
        srm = max(0.0, float(srm or 0))
    except (ValueError, TypeError):
        return "#F3F993"
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


def calcola_ph_mash(ricetta, ingredienti, profilo_acqua=None):
    """
    Stima il pH dell'impasto (Mash pH) in base al grist dei malti e all'alcalinità residua dell'acqua
    secondo il modello buffer di Palmer & Troester (ASBC buffer system).
    """
    grist_kg = 0.0
    sauermalz_kg = 0.0
    delta_crystal = 0.0
    delta_roasted = 0.0

    for i in ingredienti or []:
        categoria = (getattr(i, "categoria", None) or (i.get("categoria") if isinstance(i, dict) else "") or "").lower()
        if categoria == "grain":
            quantita = getattr(i, "quantita", None) or (i.get("quantita") if isinstance(i, dict) else 0.0) or 0.0
            unita = getattr(i, "unita", None) or (i.get("unita") if isinstance(i, dict) else "kg") or "kg"
            q_kg = _to_kg(quantita, unita)
            if q_kg <= 0:
                continue
            grist_kg += q_kg
            nome = str(getattr(i, "nome", None) or (i.get("nome") if isinstance(i, dict) else "") or "").lower()
            color_srm = float(getattr(i, "color_srm", None) or (i.get("color_srm") if isinstance(i, dict) else 0.0) or 0.0)

            if any(k in nome for k in ["sauermalz", "acidulated", "acido", "acid malt"]):
                sauermalz_kg += q_kg
            elif color_srm >= 200 or any(k in nome for k in ["roasted", "black", "chocolate", "carafa", "de-husked"]):
                delta_roasted += -0.0022 * color_srm * q_kg
            elif color_srm >= 15 or any(k in nome for k in ["crystal", "caramel", "cara"]):
                delta_crystal += -0.0035 * color_srm * q_kg

    # 1. Impatto Malti
    base_distilled_ph = 5.72
    if grist_kg > 0:
        pct_sauermalz = (sauermalz_kg / grist_kg) * 100.0
        delta_sauermalz = -0.10 * pct_sauermalz
        delta_crystal_norm = max(-0.35, (delta_crystal / grist_kg) / 10.0)
        delta_roasted_norm = max(-0.45, (delta_roasted / grist_kg) / 10.0)
        ph_malts = base_distilled_ph + delta_sauermalz + delta_crystal_norm + delta_roasted_norm
    else:
        ph_malts = base_distilled_ph

    # 2. Impatto Acqua (Alcalinità Residua - Kolbach & Palmer)
    ra_ppm = 50.0  # default tap water
    if profilo_acqua:
        ca = float(getattr(profilo_acqua, "ca", None) or (profilo_acqua.get("ca") if isinstance(profilo_acqua, dict) else 0.0) or 0.0)
        mg = float(getattr(profilo_acqua, "mg", None) or (profilo_acqua.get("mg") if isinstance(profilo_acqua, dict) else 0.0) or 0.0)
        hco3 = float(getattr(profilo_acqua, "hco3", None) or (profilo_acqua.get("hco3") if isinstance(profilo_acqua, dict) else 0.0) or 0.0)
        ra_meq = (hco3 / 61.0) - ((ca / 70.14) + (mg / 85.05))
        ra_ppm = ra_meq * 50.04

    # Ogni 50 ppm di RA sposta il pH del mosto di circa +0.082 unità
    delta_water = (ra_ppm / 50.0) * 0.082
    ph_stimato = round(max(4.6, min(6.3, ph_malts + delta_water)), 2)

    if 5.2 <= ph_stimato <= 5.55:
        stato_ph = "Ottimale (5.2 - 5.5)"
        colore_badge = "#15803d"
    elif ph_stimato > 5.55:
        stato_ph = "Alto (Consigliata acidificazione)"
        colore_badge = "#b45309"
    else:
        stato_ph = "Basso"
        colore_badge = "#1d4ed8"

    return {
        "ph_stimato": ph_stimato,
        "stato": stato_ph,
        "colore_badge": colore_badge,
        "alcalinita_residua_ppm": round(ra_ppm, 1),
        "ph_base_malti": round(ph_malts, 2),
    }


def calcola_dosi_acido(vol_mash, vol_sparge, ph_stimato, ph_target_mash=5.35, ph_target_sparge=5.8):
    """
    Calcola il fabbisogno di acidificazione in mL di Acido Lattico 80% o Acido Fosforico 75%.
    """
    delta_mash = max(0.0, ph_stimato - ph_target_mash)
    lattico_mash_ml = round(delta_mash * 10.0 * 0.055 * max(1.0, vol_mash), 1) if delta_mash > 0 else 0.0
    lattico_sparge_ml = round(max(0.0, vol_sparge * 0.12), 1)

    fosforico_mash_ml = round(lattico_mash_ml * 0.82, 1)
    fosforico_sparge_ml = round(lattico_sparge_ml * 0.82, 1)

    return {
        "lattico_mash_ml": lattico_mash_ml,
        "lattico_sparge_ml": lattico_sparge_ml,
        "lattico_totale_ml": round(lattico_mash_ml + lattico_sparge_ml, 1),
        "fosforico_mash_ml": fosforico_mash_ml,
        "fosforico_sparge_ml": fosforico_sparge_ml,
        "fosforico_totale_ml": round(fosforico_mash_ml + fosforico_sparge_ml, 1),
    }


def calcola_pitch_rate(og, volume_litri, stile_nome="", yeast_type="", yeast_form=""):
    """
    Calcola il Pitch Rate raccomandato e il fabbisogno in miliardi di cellule e bustine/fiale.
    """
    plato = plato_from_sg(og)
    nome_low = (stile_nome or "").lower()
    type_low = (yeast_type or "").lower()
    is_lager = "lager" in type_low or any(k in nome_low for k in ["lager", "pils", "bock", "märzen", "helles", "dunkel", "schwarzbier"])
    is_high_gravity = plato > 14.5

    if is_lager:
        rate = 2.0 if is_high_gravity else 1.5
        tipo_desc = "Lager (Alta densità)" if is_high_gravity else "Lager Standard"
    else:
        rate = 1.0 if is_high_gravity else 0.75
        tipo_desc = "Ale (Alta gravità)" if is_high_gravity else "Ale Standard"

    v_ml = max(1.0, float(volume_litri or 20.0)) * 1000.0
    cellule_miliardi = round((rate * v_ml * max(1.0, plato)) / 1000.0)

    bustine_secco = max(1, math.ceil(cellule_miliardi / 160.0))
    fiale_liquido = max(1, math.ceil(cellule_miliardi / 100.0))

    starter_consigliato = cellule_miliardi > 180 or (is_lager and "dry" not in (yeast_form or "").lower())
    starter_vol_l = round(max(0.8, min(4.0, cellule_miliardi / 160.0 * 0.9)), 1)
    starter_dme_g = round(starter_vol_l * 100.0)

    return {
        "pitch_rate": rate,
        "tipo_desc": tipo_desc,
        "is_lager": is_lager,
        "cellule_miliardi": cellule_miliardi,
        "bustine_secco_11g": bustine_secco,
        "fiale_liquido": fiale_liquido,
        "starter_consigliato": starter_consigliato,
        "starter_vol_litri": starter_vol_l,
        "starter_dme_g": starter_dme_g,
    }


def calcola_priming(volume_litri, temp_max_ferm=20.0, co2_vols_target=2.4):
    """
    Calcola i grammi di zucchero per priming in bottiglia e la pressione per infustamento (keg).
    """
    t = float(temp_max_ferm or 20.0)
    v_target = float(co2_vols_target or 2.4)
    vol = float(volume_litri or 20.0)

    co2_diss = max(0.6, min(1.8, 1.013 * (0.0101 * (t**2) - 0.285 * t + 2.716)))
    delta_co2 = max(0.0, v_target - co2_diss)

    g_l_saccarosio = round(delta_co2 * 4.0, 2)
    g_l_destrosio = round(delta_co2 * 4.4, 2)
    g_l_dme = round(delta_co2 * 5.8, 2)
    g_l_miele = round(delta_co2 * 5.3, 2)

    p_bar = round(max(0.2, -1.13 + (0.042 * 4.0) + (0.177 * v_target) + (0.0037 * 4.0 * v_target)), 2)
    p_psi = round(p_bar * 14.5038, 1)

    return {
        "co2_target": round(v_target, 1),
        "co2_dissolta": round(co2_diss, 2),
        "delta_co2": round(delta_co2, 2),
        "saccarosio": {
            "grammi_totali": round(g_l_saccarosio * vol),
            "grammi_litro": g_l_saccarosio,
        },
        "destrosio": {
            "grammi_totali": round(g_l_destrosio * vol),
            "grammi_litro": g_l_destrosio,
        },
        "dme": {
            "grammi_totali": round(g_l_dme * vol),
            "grammi_litro": g_l_dme,
        },
        "miele": {
            "grammi_totali": round(g_l_miele * vol),
            "grammi_litro": g_l_miele,
        },
        "keg_4c": {
            "bar": p_bar,
            "psi": p_psi,
        },
    }

