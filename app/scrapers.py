"""
Scraper asincrono per confronto prezzi ingredienti e attrezzature birra.
Supporta:
- Pinta (Catalogo completo ingredienti e accessori)
- Polsinelli (Attrezzature, malti, cereali, fermentatori)
- Enosystem (API JSON per malti, lieviti, fiocchi e strumenti)
- Beer and Wine (Shopify store con espansione sinonimi birrari)
- MrMalt (Link diretto e fallback trasparente)
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("scrapers")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
TIMEOUT = 9.0

# Mappatura intelligente dei sinonimi birrari (Italiano <-> Inglese / Nomi d'uso)
SINONIMI_BIRRARI = {
    "frumento": ["wheat", "weizen"],
    "wheat": ["frumento", "weizen"],
    "grano": ["frumento", "wheat"],
    "avena": ["oats", "oat"],
    "oats": ["avena"],
    "oat": ["avena"],
    "segale": ["rye"],
    "rye": ["segale"],
    "orzo": ["barley"],
    "barley": ["orzo"],
    "fiocchi": ["flaked"],
    "flaked": ["fiocchi"],
    "torrefatto": ["torrified"],
    "torrified": ["torrefatto"],
    "destrosio": ["dextrose"],
    "dextrose": ["destrosio"],
    "lattosio": ["lactose"],
    "lactose": ["lattosio"],
    "lievito": ["yeast"],
    "yeast": ["lievito"],
    "luppolo": ["hops", "hop"],
    "luppoli": ["hops"],
    "hops": ["luppolo"],
    "hop": ["luppolo"],
    "chiller": ["scambiatore", "serpentina"],
    "serpentina": ["chiller"],
    "densimetro": ["idrometro", "hydrometer"],
    "idrometro": ["densimetro"],
    "rifrattometro": ["refractometer"],
    "mulino": ["macinamalto"],
    "macinamalto": ["mulino"],
    "tappatrice": ["capper"],
    "sanificante": ["starsan", "chemipro"],
    "starsan": ["sanificante"],
}


def _clean_price(txt: Any) -> Optional[float]:
    """Normalizza prezzi stringa in float."""
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    s = str(txt).replace("€", "").replace("\xa0", "").replace("&euro;", "").strip()
    m = re.search(r"[\d]+[.,][\d]{1,2}", s)
    if m:
        val = m.group().replace(",", ".")
        try:
            return float(val)
        except ValueError:
            pass
    m = re.search(r"[\d]+", s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None


def _get_synonym_queries(q: str) -> List[str]:
    """Genera varianti della query basate sui sinonimi birrari."""
    q_clean = q.lower().strip()
    words = q_clean.split()
    alternatives = []
    
    # 1. Ricerca diretta parola singola
    if q_clean in SINONIMI_BIRRARI:
        for syn in SINONIMI_BIRRARI[q_clean]:
            if syn not in alternatives:
                alternatives.append(syn)

    # 2. Sostituzione delle singole parole nella frase
    for i, w in enumerate(words):
        if w in SINONIMI_BIRRARI:
            for syn in SINONIMI_BIRRARI[w]:
                new_words = list(words)
                new_words[i] = syn
                alt = " ".join(new_words)
                if alt not in alternatives and alt != q_clean:
                    alternatives.append(alt)
    return alternatives


# ── 1. ENOSYSTEM (API JSON rapida) ─────────────────────────────────────────────

async def scrape_enosystem(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Enosystem"
    base_url = "https://www.enosystem.it"
    url_ricerca = f"{base_url}/module/ambjolisearch/jolisearch?ajax=1&s={quote(query)}"
    
    async def _fetch(q_str: str) -> list:
        u = f"{base_url}/module/ambjolisearch/jolisearch?ajax=1&s={quote(q_str)}"
        r = await client.get(u, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        data = r.json()
        prods = []
        for p in data.get("products", []):
            if p.get("type") == "product" and p.get("pname"):
                link = p.get("link", "")
                if link and not link.startswith("http"):
                    link = urljoin(base_url, link)
                prods.append({
                    "nome": p.get("pname")[:120],
                    "prezzo": _clean_price(p.get("price")),
                    "url": link or u,
                })
        return prods

    try:
        results = await _fetch(query)
        if not results:
            for alt in _get_synonym_queries(query):
                results = await _fetch(alt)
                if results:
                    break
        return {"fornitore": fornitore, "url_ricerca": f"{base_url}/module/ambjolisearch/jolisearch?s={quote(query)}", "risultati": results[:10], "errore": None}
    except Exception as e:
        logger.warning(f"Errore scrape Enosystem: {e}")
        return {"fornitore": fornitore, "url_ricerca": f"{base_url}/module/ambjolisearch/jolisearch?s={quote(query)}", "risultati": [], "errore": None}


# ── 2. PINTA (Catalogo Pinta.it) ──────────────────────────────────────────────

async def scrape_pinta(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Pinta"
    base_url = "https://www.pinta.it"
    url_ricerca = f"{base_url}/it/search?search={quote(query)}"

    async def _fetch(q_str: str) -> list:
        u = f"{base_url}/it/search?search={quote(q_str)}"
        r = await client.get(u, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        prods = []
        for form in soup.select("form[id^='form_']"):
            p_inp = form.select_one("input[name='prezzo']")
            prezzo = _clean_price(p_inp.get("value")) if p_inp else None
            h3_el = form.select_one("h3")
            link_el = form.select_one(".title a, a[href*='/it/']")
            nome = h3_el.get_text(strip=True) if h3_el else (link_el.get("title") if link_el else None)
            href = link_el.get("href") if link_el else None
            if nome and href:
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                prods.append({
                    "nome": nome[:120],
                    "prezzo": prezzo,
                    "url": href,
                })
        return prods

    try:
        results = await _fetch(query)
        if not results:
            for alt in _get_synonym_queries(query):
                results = await _fetch(alt)
                if results:
                    break
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": results[:10], "errore": None}
    except Exception as e:
        logger.warning(f"Errore scrape Pinta: {e}")
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": [], "errore": None}


# ── 3. POLSINELLI (Attrezzature e materie prime) ──────────────────────────────

async def scrape_polsinelli(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Polsinelli"
    base_url = "https://www.polsinelli.it"
    url_ricerca = f"{base_url}/catalog.htm?search={quote(query)}"

    async def _fetch(q_str: str) -> list:
        u = f"{base_url}/catalog.htm?search={quote(q_str)}"
        r = await client.get(u, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        prods = []
        for el in soup.select("[data-gtm-product-url]"):
            rel_url = el.get("data-gtm-product-url", "")
            title = el.get("alt") or el.get("title") or el.get_text(strip=True)
            if rel_url and title:
                full_url = urljoin(base_url, rel_url)
                if not any(p["url"] == full_url for p in prods):
                    card = el.find_parent(class_=re.compile(r"item|product|box|col", re.I))
                    prezzo = None
                    if card:
                        p_el = card.select_one(".price, .product-price, .amount, [class*='price']")
                        if p_el:
                            prezzo = _clean_price(p_el.get_text())
                    prods.append({
                        "nome": title[:120],
                        "prezzo": prezzo,
                        "url": full_url,
                    })
        # Se i prezzi non sono stati estratti dal DOM delle card, estraili dai blocchi itemName/price
        if prods and any(p["prezzo"] is None for p in prods):
            html_txt = r.text
            for p in prods:
                if p["prezzo"] is None:
                    idx = html_txt.find(p["nome"][:25])
                    if idx != -1:
                        chunk = html_txt[idx:idx+800]
                        m = re.search(r"\"price\":\s*\"?([\d\.]+)\"?", chunk)
                        if m:
                            p["prezzo"] = _clean_price(m.group(1))
        return prods

    try:
        try:
            await client.get(base_url, headers=HEADERS, timeout=5.0)
        except Exception:
            pass
        results = await _fetch(query)
        if not results:
            for alt in _get_synonym_queries(query):
                results = await _fetch(alt)
                if results:
                    break
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": results[:10], "errore": None}
    except Exception as e:
        logger.warning(f"Errore scrape Polsinelli: {e}")
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": [], "errore": None}


# ── 4. BEER AND WINE (Shopify con espansione sinonimi) ─────────────────────────

async def scrape_beerandwine(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Beer and Wine"
    base_url = "https://www.beerandwine.it"
    url_ricerca = f"{base_url}/search?type=product&q={quote(query)}"

    async def _fetch(q_str: str) -> list:
        u = f"{base_url}/search?type=product&q={quote(q_str)}"
        r = await client.get(u, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        prods = []
        for art in soup.select(".thumbnail, [itemtype*='Product'], .product-wrap, .product-item"):
            t_el = art.select_one(".title[itemprop='name'], .product-details .title, .title, h3, h2")
            p_el = art.select_one(".money, .price, [class*='price']")
            l_el = art.select_one("a[href*='/products/']")
            if t_el and l_el:
                nome = t_el.get_text(strip=True)
                href = l_el.get("href", "")
                if href and not href.startswith("http"):
                    href = urljoin(base_url, href)
                prezzo = _clean_price(p_el.get_text(strip=True)) if p_el else None
                if nome and href and not any(p["url"] == href for p in prods):
                    prods.append({
                        "nome": nome[:120],
                        "prezzo": prezzo,
                        "url": href,
                    })
        return prods

    try:
        results = await _fetch(query)
        if not results:
            for alt in _get_synonym_queries(query):
                results = await _fetch(alt)
                if results:
                    break
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": results[:10], "errore": None}
    except Exception as e:
        logger.warning(f"Errore scrape Beer and Wine: {e}")
        return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": [], "errore": None}


# ── 5. MR. MALT (Con link diretto protetto) ───────────────────────────────────

async def scrape_mrmalt(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "MrMalt"
    base_url = "https://www.mr-malt.it"
    url_ricerca = f"{base_url}/ricerca?controller=search&s={quote(query)}"
    
    try:
        r = await client.get(url_ricerca, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code == 200 and "Just a moment" not in r.text and "challenge-platform" not in r.text:
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            for art in soup.select(".product-miniature, article.product-miniature, .product-item"):
                nome_el = art.select_one(".product-title a, h2 a, h3 a")
                prezzo_el = art.select_one(".price, .product-price")
                link_el = art.select_one("a[href]")
                if nome_el and nome_el.get_text(strip=True):
                    href = link_el.get("href", "") if link_el else ""
                    results.append({
                        "nome": nome_el.get_text(strip=True)[:120],
                        "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                        "url": urljoin(base_url, href) if href else url_ricerca,
                    })
            if results:
                return {"fornitore": fornitore, "url_ricerca": url_ricerca, "risultati": results[:10], "errore": None}
    except Exception:
        pass

    return {
        "fornitore": fornitore,
        "url_ricerca": url_ricerca,
        "risultati": [
            {
                "nome": f"Cerca '{query}' nel catalogo completo Mr. Malt",
                "prezzo": None,
                "url": url_ricerca,
            }
        ],
        "errore": None,
    }


# ── ENTRY POINT GLOBALE ────────────────────────────────────────────────────────

async def cerca_prezzi(query: str, fornitori: Optional[List[str]] = None) -> List[Dict]:
    """
    Cerca prezzi su tutti i fornitori in parallelo, garantendo:
    - Espansione automatica dei sinonimi birrari
    - Tolleranza ai timeout per singolo fornitore
    - Ordinamento dei risultati prioritizzando i fornitori con offerte e prezzi validi
    """
    query = (query or "").strip()
    if not query:
        return []

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=TIMEOUT) as client:
        tutti = {
            "Pinta": scrape_pinta(query, client),
            "Polsinelli": scrape_polsinelli(query, client),
            "Enosystem": scrape_enosystem(query, client),
            "Beer and Wine": scrape_beerandwine(query, client),
            "MrMalt": scrape_mrmalt(query, client),
        }
        
        if fornitori:
            tasks = [v for k, v in tutti.items() if k in fornitori]
        else:
            tasks = list(tutti.values())
        
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        clean_results = []
        for res in raw_results:
            if isinstance(res, Exception):
                logger.error(f"Eccezione in scraper: {res}")
                continue
            if isinstance(res, dict):
                clean_results.append(res)

        def _score(fd: Dict) -> int:
            ris = fd.get("risultati") or []
            con_prezzo = sum(1 for r in ris if r.get("prezzo") is not None)
            return len(ris) + (con_prezzo * 2)

        clean_results.sort(key=_score, reverse=True)
        return clean_results
