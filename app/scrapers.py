"""
Scraper asincrono per confronto prezzi ingredienti birra.
Supporta: MrMalt, Polsinelli, Beer&Wine, AEB Group.
"""
import asyncio
import re
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 10.0


def _clean_price(txt: str) -> float | None:
    if not txt:
        return None
    txt = txt.strip().replace("\xa0", "").replace(" ", "")
    m = re.search(r"[\d]+[,.][\d]{1,2}", txt)
    if m:
        return float(m.group().replace(",", "."))
    m = re.search(r"[\d]+", txt)
    return float(m.group()) if m else None


# ── MrMalt ────────────────────────────────────────────────────────────────────

async def scrape_mrmalt(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "MrMalt"
    url_base = "https://www.mrmalt.com"
    url_search = f"{url_base}/it/ricerca?controller=search&s={query.replace(' ', '+')}"
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        # Schede prodotto standard PrestaShop
        for art in soup.select(".product-miniature, article.product-miniature")[:8]:
            nome_el = art.select_one(".product-title a, h2.product-title a, h3 a")
            prezzo_el = art.select_one(".price, .product-price, span[itemprop='price']")
            link_el = art.select_one("a[href]")
            if nome_el:
                results.append({
                    "nome": nome_el.get_text(strip=True),
                    "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                    "url": link_el["href"] if link_el else url_search,
                })
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Polsinelli ────────────────────────────────────────────────────────────────

async def scrape_polsinelli(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Polsinelli"
    url_search = f"https://www.polsinelli.it/cerca?q={query.replace(' ', '+')}"
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for art in soup.select(".product-item, .product_list li, .ajax_block_product")[:8]:
            nome_el = art.select_one(".product-name a, .product_name a, h3 a, h2 a")
            prezzo_el = art.select_one(".price, .product-price, .our_price_display")
            link_el = art.select_one("a[href]")
            if nome_el:
                results.append({
                    "nome": nome_el.get_text(strip=True),
                    "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                    "url": link_el["href"] if link_el else url_search,
                })
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Beer and Wine ─────────────────────────────────────────────────────────────

async def scrape_beerandwine(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Beer and Wine"
    url_search = f"https://www.beerandwine.it/search?q={query.replace(' ', '+')}"
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        # Shopify-style themes
        for art in soup.select(".product-item, .grid__item, .product-card, article")[:8]:
            nome_el = art.select_one(".product-item__title, .product-card__name, h2 a, h3 a, .card__heading a")
            prezzo_el = art.select_one(".price, .product-price, .price__regular, .price-item")
            link_el = art.select_one("a[href]")
            if nome_el:
                href = link_el["href"] if link_el else url_search
                if href.startswith("/"):
                    href = "https://www.beerandwine.it" + href
                results.append({
                    "nome": nome_el.get_text(strip=True),
                    "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                    "url": href,
                })
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── AEB Group ─────────────────────────────────────────────────────────────────

async def scrape_aeb(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "AEB Group"
    url_search = f"https://www.aeb-group.com/it/cerca?search={query.replace(' ', '+')}"
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for art in soup.select(".product-item, .search-result-item, article, .card")[:8]:
            nome_el = art.select_one("h2 a, h3 a, .product-name a, .title a")
            prezzo_el = art.select_one(".price, .product-price")
            link_el = art.select_one("a[href]")
            if nome_el:
                href = link_el["href"] if link_el else url_search
                if href.startswith("/"):
                    href = "https://www.aeb-group.com" + href
                results.append({
                    "nome": nome_el.get_text(strip=True),
                    "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                    "url": href,
                })
        # AEB is B2B and may not show prices — provide direct link
        if not results:
            results.append({
                "nome": f"Cerca '{query}' su AEB Group",
                "prezzo": None,
                "url": url_search,
                "nota": "Sito B2B — prezzi su richiesta",
            })
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Pinta ─────────────────────────────────────────────────────────────────────

async def scrape_pinta(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Pinta"
    url_search = f"https://www.pinta.it/search?q={query.replace(' ', '+')}"
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for art in soup.select(".product-item, .grid__item, .product-card, article, .product")[:8]:
            nome_el = art.select_one(".product-item__title, .product__title, .product-name, h2 a, h3 a, .card__heading a")
            prezzo_el = art.select_one(".price, .product-price, .price__regular, .price-item, .product__price")
            link_el = art.select_one("a[href]")
            if nome_el:
                href = link_el["href"] if link_el else url_search
                if href.startswith("/"):
                    href = "https://www.pinta.it" + href
                results.append({
                    "nome": nome_el.get_text(strip=True),
                    "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                    "url": href,
                })
        if not results:
            results.append({
                "nome": f"Cerca '{query}' su Pinta",
                "prezzo": None,
                "url": url_search,
            })
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Entry point ────────────────────────────────────────────────────────────────

async def cerca_prezzi(query: str, fornitori: list[str] | None = None) -> List[Dict]:
    """Cerca prezzi su tutti i fornitori in parallelo."""
    async with httpx.AsyncClient() as client:
        tutti = {
            "MrMalt": scrape_mrmalt(query, client),
            "Polsinelli": scrape_polsinelli(query, client),
            "Beer and Wine": scrape_beerandwine(query, client),
            "AEB Group": scrape_aeb(query, client),
            "Pinta": scrape_pinta(query, client),
        }
        if fornitori:
            tasks = [v for k, v in tutti.items() if k in fornitori]
        else:
            tasks = list(tutti.values())
        return await asyncio.gather(*tasks)
