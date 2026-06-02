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
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}
TIMEOUT = 12.0

# URL di ricerca precisi per ogni fornitore
FORNITORE_INFO = {
    "MrMalt":          {"url_base": "https://www.mr-malt.it",      "search_tpl": "https://www.mr-malt.it/ricerca?controller=search&s={q}"},
    "Pinta":           {"url_base": "https://www.pinta.it",         "search_tpl": "https://www.pinta.it/search?type=product&q={q}"},
    "Beer and Wine":   {"url_base": "https://www.beerandwine.it",   "search_tpl": "https://www.beerandwine.it/search?type=product&q={q}"},
    "Polsinelli":      {"url_base": "https://www.polsinelli.it",    "search_tpl": "https://www.polsinelli.it/cerca?q={q}"},
    "Forniture Birra": {"url_base": "https://forniturebirra.com",   "search_tpl": "https://forniturebirra.com/?s={q}&post_type=product"},
    "Enosystem":       {"url_base": "https://www.enosystem.it",     "search_tpl": "https://www.enosystem.it/recherche?s={q}&controller=search"},
}


def _clean_price(txt: str) -> float | None:
    if not txt:
        return None
    txt = txt.strip().replace("\xa0", "").replace(" ", "")
    m = re.search(r"[\d]+[,.][\d]{1,2}", txt)
    if m:
        return float(m.group().replace(",", "."))
    m = re.search(r"[\d]+", txt)
    return float(m.group()) if m else None


def _abs_url(href: str, base: str) -> str:
    if not href:
        return base
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    return base.rstrip("/") + "/" + href.lstrip("/")


def _extract_products(soup: BeautifulSoup, url_search: str, base: str, limit=8) -> list:
    """Estrae prodotti da pagine PrestaShop, Shopify, WooCommerce generiche."""
    results = []
    selectors = [
        ".product-miniature", "article.product-miniature",
        ".product-item", ".grid__item", ".product-card",
        "li.product", ".ajax_block_product", ".product_list li",
        "article.product", ".woocommerce-loop-product__link",
    ]
    for sel in selectors:
        items = soup.select(sel)
        if items:
            for art in items[:limit]:
                nome_el = art.select_one(
                    ".product-title a, h2.product-title a, h3.product-title a, "
                    ".product-item__title, .product-card__name, .card__heading a, "
                    ".product-name a, h2 a, h3 a, h4 a, .woocommerce-loop-product__link"
                )
                prezzo_el = art.select_one(
                    ".price, .product-price, span[itemprop='price'], "
                    ".price__regular, .price-item--regular, .our_price_display, "
                    "ins .amount, .price bdi"
                )
                link_el = art.select_one("a[href]")
                if nome_el and nome_el.get_text(strip=True):
                    href = link_el.get("href", "") if link_el else ""
                    results.append({
                        "nome": nome_el.get_text(strip=True)[:120],
                        "prezzo": _clean_price(prezzo_el.get_text() if prezzo_el else ""),
                        "url": _abs_url(href, base),
                    })
            if results:
                return results
    return results


# ── MrMalt ────────────────────────────────────────────────────────────────────

async def scrape_mrmalt(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "MrMalt"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Polsinelli ────────────────────────────────────────────────────────────────

async def scrape_polsinelli(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Polsinelli"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Beer and Wine ─────────────────────────────────────────────────────────────

async def scrape_beerandwine(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Beer and Wine"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Pinta ─────────────────────────────────────────────────────────────────────

async def scrape_pinta(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Pinta"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        if not results:
            results.append({"nome": f"Cerca '{query}' su Pinta", "prezzo": None, "url": url_search})
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Forniture Birra ───────────────────────────────────────────────────────────

async def scrape_forniture_birra(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Forniture Birra"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        if not results:
            results.append({"nome": f"Cerca '{query}' su Forniture Birra", "prezzo": None, "url": url_search})
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": results, "errore": None}
    except Exception as e:
        return {"fornitore": fornitore, "url_ricerca": url_search, "risultati": [], "errore": str(e)[:80]}


# ── Enosystem ─────────────────────────────────────────────────────────────────

async def scrape_enosystem(query: str, client: httpx.AsyncClient) -> Dict:
    fornitore = "Enosystem"
    info = FORNITORE_INFO[fornitore]
    url_search = info["search_tpl"].format(q=query.replace(" ", "+"))
    try:
        r = await client.get(url_search, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        results = _extract_products(soup, url_search, info["url_base"])
        if not results:
            results.append({"nome": f"Cerca '{query}' su Enosystem", "prezzo": None, "url": url_search})
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
            "Pinta": scrape_pinta(query, client),
            "Forniture Birra": scrape_forniture_birra(query, client),
            "Enosystem": scrape_enosystem(query, client),
        }
        if fornitori:
            tasks = [v for k, v in tutti.items() if k in fornitori]
        else:
            tasks = list(tutti.values())
        return await asyncio.gather(*tasks)
