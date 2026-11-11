import json
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ProceduraOperativa

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DEFAULT_SOPS = [
    {
        "codice": "SOP-01",
        "titolo": "Preparazione Sala Cotta, Trattamento Acqua e Molitura",
        "fase": "pianificata",
        "revisione": "Rev. 2.0",
        "scopo": "Garantire la corretta preparazione igienico-tecnica dell'impianto, il condizionamento salino/acido dell'acqua di processo e la granulometria ottimale dei malti prima del Mash-In.",
        "dpi_attrezzature": "Mascherina antipolvere FFP2 (molitura), guanti in nitrile, pH-metro tarato a 2 punti (pH 4.01 e 7.01), bilancia di precisione (0.1g per sali).",
        "parametri_critici": "Gap rulli mulino: 1.1 – 1.3 mm | Cloro libero acqua: 0 ppm | Temperatura Strike Water: +4/+6°C rispetto a T° Mash",
        "steps": [
            {"titolo": "Ispezione visiva e risciacquo impianto", "descrizione": "Verificare l'assenza di residui o odori nel tino di ammostamento/bollitura, falso fondo, pompa di ricircolo e tubazioni.", "critico": "Valvole chiuse prima del carico acqua"},
            {"titolo": "Carico acqua di Mash e declorazione", "descrizione": "Caricare il volume di acqua di Mash previsto in ricetta. Se acqua di rete clorata, filtrare su carbone attivo o aggiungere metabisolfito di potassio (0.5 g per 100 L).", "critico": "Assenza totale di cloro/cloramine (prevenzione clorofenoli)"},
            {"titolo": "Aggiunta sali minerali e correzione acida", "descrizione": "Pesare ed aggiungere CaSO4 (Gypsum), CaCl2, MgSO4 secondo il profilo acqua target. Pre-acidificare l'acqua di sparge a pH 5.4–5.6 con Acido Lattico 80% o Fosforico.", "critico": "Sciogliere completamente i sali sotto agitazione"},
            {"titolo": "Controllo lotti FEFO e pesatura grani", "descrizione": "Prelevare i malti dal magazzino seguendo l'ordine FEFO (scadenza più ravvicinata), verificare i numeri di lotto e pesare il grist in contenitori puliti.", "critico": "Tenere separati i malti tostati/scuri se previsto late-addition"},
            {"titolo": "Molitura controllata del malto", "descrizione": "Macinare il malto verificando che le glumelle restino il più possibile integre (letto filtrante) e l'endosperma sia ben frantumato senza eccesso di farina.", "critico": "Gap mulino: 1.1–1.3 mm (malto d'orzo), 0.8–0.9 mm (frumento/segale)"}
        ]
    },
    {
        "codice": "SOP-02",
        "titolo": "Ammostamento (Mash-In, Conversione Enzimatica e Mash-Out)",
        "fase": "brewday",
        "revisione": "Rev. 2.0",
        "scopo": "Ottenere la completa conversione degli amidi in zuccheri fermentabili e destrine secondo il profilo termico della ricetta, massimizzando l'efficienza di estrazione.",
        "dpi_attrezzature": "Guanti termici, pala da ammostamento inox, pH-metro con ATC, rifrattometro/densimetro, tintura di iodio.",
        "parametri_critici": "pH Mash (a 20°C): 5.2 – 5.5 | Tolleranza T° step: ±0.5°C | Test Iodio: Negativo (nessun viraggio blu/nero)",
        "steps": [
            {"titolo": "Raggiungimento Strike Temperature e Mash-In", "descrizione": "Portare l'acqua di mash alla temperatura di Strike calcolata. Versare il malto macinato gradualmente mescolando vigorosamente con la pala per rompere tutti i grumi (dough balls).", "critico": "Pompa di ricircolo spenta durante l'inserimento grani e per i primi 5 min"},
            {"titolo": "Avvio ricircolo e controllo temperatura step", "descrizione": "Attendere 5 minuti per l'assestamento del letto dei grani, quindi avviare dolcemente la pompa di ricircolo regolando la portata per evitare il compattamento del letto.", "critico": "Non superare la portata di drenaggio naturale del falso fondo"},
            {"titolo": "Misura e correzione pH Mash (a +15 min)", "descrizione": "Prelevare un campione di mosto, raffreddarlo a 20–25°C e misurare il pH. Se superiore a 5.5, correggere con Acido Lattico 80%; se inferiore a 5.1, correggere con Bicarbonato/Idrossido di Calcio.", "critico": "Target pH Mash (20°C): 5.2 – 5.4 (birre chiare) / 5.3 – 5.5 (birre scure)"},
            {"titolo": "Test di conversione con Tintura di Iodio", "descrizione": "Al termine dello step di saccarificazione (65–68°C), prelevare alcune gocce di mosto limpido su piattino bianco e aggiungere 1 goccia di tintura di iodio. Se vira al nero/viola, prolungare lo step di 10–15 min.", "critico": "Conversione completa = colore giallo/ambrato invariato"},
            {"titolo": "Rampa termica e Mash-Out (77–78°C per 10 min)", "descrizione": "Innalzare la temperatura a 77–78°C e mantenere per 10 minuti per inattivare le beta-amilasi, fissare il profilo fermentabile e ridurre la viscosità del mosto prima della filtrazione.", "critico": "Non superare MAI gli 80°C per evitare l'estrazione di tannini astringenti"}
        ]
    },
    {
        "codice": "SOP-03",
        "titolo": "Filtrazione (Vorlauf), Sparge e Bilancio Pre-Bollitura",
        "fase": "brewday",
        "revisione": "Rev. 2.0",
        "scopo": "Separare il mosto limpido dalle trebbie ed estrarre gli zuccheri residui tramite lavaggio (sparge) senza estrarre polifenoli/tannini.",
        "dpi_attrezzature": "Guanti termici, rifrattometro ottico/digitale, cilindro graduato, densimetro, pH-metro.",
        "parametri_critici": "Temp. acqua Sparge: 77–78°C | Stop Sparge: SG ultimo colaggio ≥ 1.010 (2.5 °Plato) e pH ≤ 5.8",
        "steps": [
            {"titolo": "Vorlauf (Ricircolo di chiarificazione)", "descrizione": "Ricircolare i primi litri di mosto sopra il letto delle trebbie finché il liquido in uscita non risulta limpido e privo di frammenti di glumelle.", "critico": "Evitare cadute a cascata del mosto caldo (prevenzione Hot-Side Aeration)"},
            {"titolo": "Lavaggio delle trebbie (Fly / Batch Sparge)", "descrizione": "Irrigare uniformemente il letto dei grani con acqua di sparge a 77–78°C (acidificata a pH < 5.6), mantenendo sempre 2–3 cm di liquido sopra i grani.", "critico": "Non lasciare asciugare né canalizzare il letto filtrante"},
            {"titolo": "Controllo fine Sparge (pH e Densità di coda)", "descrizione": "Monitorare la densità e il pH dell'ultimo mosto in uscita dalle trebbie. Interrompere la raccolta se la densità scende sotto 1.010 SG o se il pH supera 5.8.", "critico": "Prevenzione astringenza da silicati e polifenoli delle glumelle"},
            {"titolo": "Misura Volume e Densità Pre-Bollitura (Pre-Boil)", "descrizione": "Mescolare bene il mosto in caldaia per stratificazione omogenea, misurare i litri raccolti e la densità Pre-Boil. Verificare con il tool di Correzione Pre-Boil se diluire o prolungare la bollitura.", "critico": "Registrare Volume Pre-Boil e pH Pre-Boil nella scheda della cotta"}
        ]
    },
    {
        "codice": "SOP-04",
        "titolo": "Bollitura, Luppolatura, Chiarifica e Whirlpool",
        "fase": "brewday",
        "revisione": "Rev. 2.0",
        "scopo": "Sterilizzare il mosto, isomerizzare gli alfa-acidi del luppolo, coagulare le proteine (hot break), eliminare i precursori volatili (DMS) e separare il trub nel whirlpool.",
        "dpi_attrezzature": "Guanti termici, bilancia di precisione per luppoli, timer multi-gittata, pala inox per whirlpool.",
        "parametri_critici": "Evaporazione (Boil-off): 6–10%/ora | Bollitura: vigorosa e scoperta (no coperchio) | Temp. Whirlpool: 80–85°C (luppoli aromatici)",
        "steps": [
            {"titolo": "Raggiungimento bollitura e gestione Hot-Break", "descrizione": "Portare il mosto a ebollizione. Rimuovere o abbattere la schiuma iniziale proteica evitando traboccamenti (boil-over) e avviare il timer di bollitura.", "critico": "Mantenere la caldaia parzialmente scoperta per far evaporare il DMS (dimetilsolfuro)"},
            {"titolo": "Gittate di Luppolo, Spezie e Chiarificanti", "descrizione": "Eseguire le gittate di luppolo agli esatti minuti residui indicati in ricetta. A -15 min da fine bollitura aggiungere eventuale Irish Moss/Whirlfloc (2–4 g/20L) e nutriente lievito.", "critico": "Pesare e verificare gli Alfa-Acidi reali del lotto di luppolo impiegato"},
            {"titolo": "Spegnimento fiamma (Flame-Out) e Whirlpool", "descrizione": "A fine bollitura spegnere il riscaldamento. Se previsti luppoli in Whirlpool/Hop Stand, abbassare la T° a 80–85°C per limitare l'isomerizzazione amara e massimizzare gli oli essenziali.", "critico": "Creare un vortice circolare costante per 2 min, poi lasciare sedimentare il cono per 15–20 min"}
        ]
    },
    {
        "codice": "SOP-05",
        "titolo": "Raffreddamento, Ossigenazione e Inoculo Lievito (Pitching)",
        "fase": "fermentazione",
        "revisione": "Rev. 2.0",
        "scopo": "Abbattere rapidamente la temperatura del mosto (cold break), trasferirlo in condizioni asettiche nel fermentatore e inoculare il corretto tasso di cellule vitali.",
        "dpi_attrezzature": "Acido Peracetico (PAA 0.1–0.2%) o StarSan, bombola O2 alimentare o agitatore, termometro, densimetro.",
        "parametri_critici": "Tempo raffreddamento: < 30 min | Temp. Inoculo: 18–20°C (Ale) / 9–12°C (Lager) | Pitch Rate: 0.75M (Ale) – 1.5M (Lager) cellule/mL/°Plato",
        "steps": [
            {"titolo": "Sanitizzazione linea fredda e fermentatore", "descrizione": "Far circolare soluzione sanitizzante (PAA o StarSan) nello scambiatore di calore, tubi e fermentatore per almeno 15 minuti prima del trasferimento.", "critico": "Dal lato freddo ogni contatto non sanitizzato è rischio di contaminazione"},
            {"titolo": "Raffreddamento rapido e trasferimento in fermentatore", "descrizione": "Aprire l'acqua di raffreddamento e trasferire il mosto limpido (evitando il cono centrale di trub) regolando il flusso per uscire già alla temperatura di inoculo.", "critico": "Prelevare il campione per la misura ufficiale della OG Reale e dei Litri nel fermentatore"},
            {"titolo": "Ossigenazione del mosto freddo", "descrizione": "Insufflare ossigeno puro alimentare tramite candela porosa (1 L/min per 60–90 sec) oppure agitare vigorosamente per garantire 8–10 ppm di O2 disciolto.", "critico": "Ossigenare SOLO a mosto freddo (< 25°C)"},
            {"titolo": "Reidratazione / Inoculo del Lievito e chiusura", "descrizione": "Inoculare il lievito (secco o starter liquido alla stessa temperatura del mosto ±3°C), chiudere il fermentatore, installare gorgogliatore con liquido sanitizzante e impostare il termoregolatore.", "critico": "Registrare Data/Ora inoculo, OG Reale e Lotto del lievito nella scheda Cotta"}
        ]
    },
    {
        "codice": "SOP-06",
        "titolo": "Gestione Fermentazione Primaria, Diacetil Rest e Dry Hopping",
        "fase": "secondaria",
        "revisione": "Rev. 2.0",
        "scopo": "Guidare la cinetica fermentativa, riassorbire i sottoprodotti indesiderati (diacetile/acetaldeide) ed eseguire il Dry Hop prevenendo l'ossidazione e l'hop creep.",
        "dpi_attrezzature": "Densimetro/Rifrattometro o sensore IoT (iSpindel/Tilt), bombola CO2 per flussaggio.",
        "parametri_critici": "Innalzamento Diacetil Rest: +2/+3°C al 70–80% di attenuazione | Contatto Dry Hop: 48–72 ore a 14–16°C | O2 ingresso: 0 ppm",
        "steps": [
            {"titolo": "Monitoraggio quotidiano Densità (SG) e Temperatura", "descrizione": "Registrare giornalmente nel Diario della Cotta la densità e la temperatura per verificare la partenza (fine lag-phase entro 12–24h) e la regolarità della curva.", "critico": "Se si usa il rifrattometro in fermentazione, usare il convertitore Brix→SG corretto per l'alcol"},
            {"titolo": "Diacetil Rest (Pausa Diacetile)", "descrizione": "Raggiunto il 70–80% dell'attenuazione prevista (es. 1.018–1.020), alzare la temperatura di 2–3°C per 48 ore per favorire il riassorbimento del diacetile (aroma burro/mou) da parte del lievito.", "critico": "Eseguire test forzato VDK (riscaldamento campione a 60°C per 20 min e valutazione olfattiva) prima del freddo"},
            {"titolo": "Spurgo lievito e Dry Hopping sotto copertura CO2", "descrizione": "Spurgare il lievito esausto dal cono inferiore (se troncoconico). Inserire il luppolo da Dry Hop flussando CO2 dall'oblò superiore per impedire l'ingresso di aria.", "critico": "Limitare il contatto a 2–3 giorni per evitare note erbacee/astringenti e Hop Creep"}
        ]
    },
    {
        "codice": "SOP-07",
        "titolo": "Cold Crash, Chiarifica e Maturazione a Freddo",
        "fase": "condizionamento",
        "revisione": "Rev. 2.0",
        "scopo": "Precipitare lievito in sospensione, residui di luppolo e complessi polifenoli-proteine (chill haze) ottenendo stabilità colloidale e limpidezza.",
        "dpi_attrezzature": "Linea CO2 con riduttore di pressione, valvola di spunding/non-ritorno.",
        "parametri_critici": "FG stabile per 48h prima del freddo | Pressione positiva: 0.2–0.5 bar CO2 | Temp. Cold Crash: 0°C – 2°C per 48–96 ore",
        "steps": [
            {"titolo": "Conferma fine attenuazione (FG Stabile)", "descrizione": "Verificare che la densità finale (FG) sia identica in due letture distanziate di 48 ore e in linea con la FG stimata della ricetta.", "critico": "Mai abbattere la temperatura se la fermentazione o l'hop creep sono ancora attivi"},
            {"titolo": "Messa in pressione positiva / Rimozione gorgogliatore", "descrizione": "Prima di accendere il glicole/frigo per il Cold Crash, rimuovere il gorgogliatore e applicare una leggera pressione di CO2 (0.2–0.5 bar) o tappo cieco per evitare che la contrazione termica risucchi aria e liquido sanitizzante.", "critico": "Evitare categoricamente il suck-back di ossigeno nella birra finita"},
            {"titolo": "Abbattimento a 0–2°C e spurgo fondami", "descrizione": "Impostare la temperatura a 0–2°C per 2–4 giorni. Dopo 24–48 ore eseguire lo spurgo dei sedimenti dal fondo del cono.", "critico": "Registrare Data, Temperatura e Limpidezza visiva nella sezione Condizionamento"}
        ]
    },
    {
        "codice": "SOP-08",
        "titolo": "Imbottigliamento / Infustamento, Tracciabilità Lotto e Ciclo CIP",
        "fase": "imbottigliamento",
        "revisione": "Rev. 2.0",
        "scopo": "Confezionare il prodotto finito con il corretto livello di carbonatazione, assegnare il Lotto e il TMC di legge ed eseguire il lavaggio CIP dell'impianto.",
        "dpi_attrezzature": "Occhiali protettivi, guanti chimici (per NaOH/Acido), bilancia per zucchero di priming, tappatrice/riempitrice.",
        "parametri_critici": "PAA risciacquo bottiglie/fusti: 150 ppm | Sciroppo Priming: bollito 10 min e raffreddato | CIP Soda Caustica: 1.5–2% a 75–80°C per 20–30 min",
        "steps": [
            {"titolo": "Calcolo Carbonatazione e Preparazione Sciroppo di Priming", "descrizione": "Calcolare i grammi di zucchero (destrosio/saccarosio) nel calcolatore Priming della Cotta in base ai litri netti effettivi e alla temperatura massima raggiunta dalla birra. Bollire in poca acqua per 10 min e raffreddare.", "critico": "Miscelare in modo omogeneo senza ossigenare (niente splash)"},
            {"titolo": "Sanitizzazione Bottiglie/Fusti, Riempimento e Tappatura", "descrizione": "Sanitizzare i contenitori con PAA, scolare, riempire dal basso (meglio in contropressione o con asta di riempimento previa spurgatura CO2) e tappare immediatamente su schiuma (fobbing).", "critico": "Scartare bottiglie con livello di riempimento anomalo (neck space eccessivo = ossidazione)"},
            {"titolo": "Registrazione Prodotto Finito, Lotto e Stampa Etichette", "descrizione": "Aprire la schermata '🍾 Imbottiglia' della Cotta, registrare i pezzi prodotti per ciascun formato (33cl, 75cl, Fusto) per generare il Codice Lotto automatico e scaricare i vuoti da magazzino.", "critico": "Conservare le bottiglie in rifermentazione a 20–22°C per 10–14 giorni prima dello stoccaggio al fresco"},
            {"titolo": "Ciclo CIP Fermentatore (Alcalino + Acido + Sanitizzazione)", "descrizione": "1) Risciacquo acqua tiepida; 2) Lavaggio alcalino NaOH 2% a 75°C per 25 min; 3) Risciacquo fino a pH neutro; 4) Passaggio acido (Acido Nitrico/Fosforico 1%) per rimuovere birra-pietra (ossalato di calcio); 5) Registrazione nel Registro Pulizie.", "critico": "Non usare mai soda caustica in fermentatori ancora pieni di CO2 (rischio implosione da vuoto!)"}
        ]
    }
]

FASI_SOP = {
    "pianificata": "📋 Pre-Cotta & Molitura",
    "brewday": "🔥 Sala Cotta (Mash, Sparge, Boil)",
    "fermentazione": "🧫 Raffreddamento & Inoculo",
    "secondaria": "🌿 Fermentazione & Dry Hop",
    "condizionamento": "❄️ Cold Crash & Maturazione",
    "imbottigliamento": "🍾 Confezionamento & CIP",
    "pulizia": "🧹 Igiene & Manutenzione HACCP",
}


def ensure_default_sops(db: Session):
    """Popola le 8 Procedure Operative Standard se la tabella è vuota."""
    try:
        count = db.query(ProceduraOperativa).count()
        if count == 0:
            for item in DEFAULT_SOPS:
                sop = ProceduraOperativa(
                    codice=item["codice"],
                    titolo=item["titolo"],
                    fase=item["fase"],
                    revisione=item["revisione"],
                    scopo=item["scopo"],
                    dpi_attrezzature=item["dpi_attrezzature"],
                    parametri_critici=item["parametri_critici"],
                    steps_json=json.dumps(item["steps"], ensure_ascii=False),
                    attiva=True,
                )
                db.add(sop)
            db.commit()
    except Exception:
        db.rollback()


def get_sops_parsed(db: Session):
    """Restituisce tutte le SOP attive con steps decodificati."""
    ensure_default_sops(db)
    sops = db.query(ProceduraOperativa).order_by(ProceduraOperativa.codice.asc(), ProceduraOperativa.id.asc()).all()
    out = []
    for s in sops:
        try:
            steps = json.loads(s.steps_json or "[]")
        except Exception:
            steps = []
        out.append({
            "id": s.id,
            "codice": s.codice,
            "titolo": s.titolo,
            "fase": s.fase,
            "fase_label": FASI_SOP.get(s.fase, s.fase.capitalize()),
            "revisione": s.revisione or "Rev. 1.0",
            "scopo": s.scopo or "",
            "dpi_attrezzature": s.dpi_attrezzature or "",
            "parametri_critici": s.parametri_critici or "",
            "steps": steps,
            "attiva": s.attiva,
            "updated_at": s.updated_at or "",
        })
    return out


@router.get("/procedure", response_class=HTMLResponse)
def pagina_procedure(request: Request, fase: str = "", db: Session = Depends(get_db)):
    sops = get_sops_parsed(db)
    if fase:
        sops_filtrate = [s for s in sops if s["fase"] == fase]
    else:
        sops_filtrate = sops

    return templates.TemplateResponse(
        request,
        "procedure.html",
        {
            "sops": sops_filtrate,
            "tutte_sops": sops,
            "fasi_sop": FASI_SOP,
            "fase_attiva": fase,
            "session": request.session,
        },
    )


@router.post("/procedure/nuova")
async def crea_procedura(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    codice = (form.get("codice") or "").strip().upper()
    titolo = (form.get("titolo") or "").strip()
    fase = (form.get("fase") or "brewday").strip()
    revisione = (form.get("revisione") or "Rev. 1.0").strip()
    scopo = (form.get("scopo") or "").strip()
    dpi_attrezzature = (form.get("dpi_attrezzature") or "").strip()
    parametri_critici = (form.get("parametri_critici") or "").strip()

    if not codice:
        n = db.query(ProceduraOperativa).count() + 1
        codice = f"SOP-{n:02d}"

    steps = []
    i = 0
    while f"step_titolo_{i}" in form:
        st_tit = (form.get(f"step_titolo_{i}") or "").strip()
        st_desc = (form.get(f"step_desc_{i}") or "").strip()
        st_crit = (form.get(f"step_crit_{i}") or "").strip()
        if st_tit or st_desc:
            steps.append({
                "titolo": st_tit or f"Passo {len(steps)+1}",
                "descrizione": st_desc,
                "critico": st_crit,
            })
        i += 1

    nuova = ProceduraOperativa(
        codice=codice,
        titolo=titolo or "Nuova Procedura Operativa",
        fase=fase,
        revisione=revisione,
        scopo=scopo,
        dpi_attrezzature=dpi_attrezzature,
        parametri_critici=parametri_critici,
        steps_json=json.dumps(steps, ensure_ascii=False),
        attiva=True,
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    db.add(nuova)
    db.commit()
    return RedirectResponse("/procedure?msg=Procedura+creata+con+successo", status_code=303)


@router.post("/procedure/{sop_id}/elimina")
def elimina_procedura(sop_id: int, db: Session = Depends(get_db)):
    sop = db.query(ProceduraOperativa).filter(ProceduraOperativa.id == sop_id).first()
    if sop:
        db.delete(sop)
        db.commit()
    return RedirectResponse("/procedure", status_code=303)


@router.post("/procedure/ripristina-default")
def ripristina_default_sops(db: Session = Depends(get_db)):
    esistenti = {s.codice for s in db.query(ProceduraOperativa).all()}
    for item in DEFAULT_SOPS:
        if item["codice"] not in esistenti:
            db.add(ProceduraOperativa(
                codice=item["codice"],
                titolo=item["titolo"],
                fase=item["fase"],
                revisione=item["revisione"],
                scopo=item["scopo"],
                dpi_attrezzature=item["dpi_attrezzature"],
                parametri_critici=item["parametri_critici"],
                steps_json=json.dumps(item["steps"], ensure_ascii=False),
                attiva=True,
            ))
    db.commit()
    return RedirectResponse("/procedure?msg=Procedure+standard+ripristinate", status_code=303)
