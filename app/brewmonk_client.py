"""
BrewMonk HTTP client.
Performs session-based automation against mybrewmonk.eu:
  - Login via Django CSRF form
  - Push BeerXML recipe (multipart import)
  - Scrape live brew / fermentation / sessions / recipe list pages
"""
import re
import json
from typing import Optional
import httpx
from bs4 import BeautifulSoup

BASE = "https://mybrewmonk.eu"
TIMEOUT = 20


async def _get_csrf(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, timeout=TIMEOUT)
    soup = BeautifulSoup(r.text, "html.parser")
    tag = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if tag:
        return tag.get("value", "")
    csrf = r.cookies.get("csrftoken", "")
    return csrf


async def login(username: str, password: str) -> Optional[httpx.AsyncClient]:
    """Return an authenticated AsyncClient or None on failure."""
    client = httpx.AsyncClient(
        base_url=BASE,
        follow_redirects=True,
        headers={"User-Agent": "GestionaleBirrificio/1.0"},
    )
    try:
        csrf = await _get_csrf(client, "/login")
        r = await client.post(
            "/login",
            data={
                "csrfmiddlewaretoken": csrf,
                "username": username,
                "password": password,
            },
            headers={"Referer": f"{BASE}/login"},
            timeout=TIMEOUT,
        )
        if r.status_code in (200, 302) and "sessionid" in client.cookies:
            return client
        if "/login" not in str(r.url):
            return client
        return None
    except Exception:
        await client.aclose()
        return None


def _scrape_recipe_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select("[data-recipe-id], .RecipeItem, .recipe-item, li[data-id]"):
        rid = item.get("data-recipe-id") or item.get("data-id") or ""
        name_tag = item.select_one(".Name, .recipe-name, h2, h3, strong")
        name = name_tag.get_text(strip=True) if name_tag else item.get_text(strip=True)[:60]
        if name:
            results.append({"id": rid, "nome": name})
    if not results:
        for tag in soup.select("a[href*='/recipe/']"):
            href = tag.get("href", "")
            m = re.search(r"/recipe/(\d+)", href)
            if m:
                results.append({"id": m.group(1), "nome": tag.get_text(strip=True)[:80]})
    return results


async def get_recipes(client: httpx.AsyncClient) -> list[dict]:
    try:
        r = await client.get("/recipe", timeout=TIMEOUT)
        return _scrape_recipe_list(r.text)
    except Exception:
        return []


async def push_recipe_beerxml(
    client: httpx.AsyncClient, xml_bytes: bytes, nome: str
) -> dict:
    """
    Try to import a BeerXML recipe into BrewMonk.
    Returns {"ok": bool, "msg": str, "recipe_id": str|None}
    """
    csrf = client.cookies.get("csrftoken", "")
    try:
        r = await client.post(
            "/recipe/import",
            files={"file": (f"{nome}.xml", xml_bytes, "application/xml")},
            data={"csrfmiddlewaretoken": csrf},
            headers={"X-CSRFToken": csrf, "Referer": f"{BASE}/recipe"},
            timeout=TIMEOUT,
        )
        if r.status_code in (200, 302, 201):
            m = re.search(r"/recipe/(\d+)", str(r.url) + r.text)
            rid = m.group(1) if m else None
            if r.status_code in (302, 201) or (rid and r.status_code == 200):
                return {"ok": True, "msg": "Ricetta importata su BrewMonk", "recipe_id": rid}
        if r.status_code == 404:
            r2 = await client.post(
                "/recipe/new",
                content=xml_bytes,
                headers={
                    "Content-Type": "application/xml",
                    "X-CSRFToken": csrf,
                    "Referer": f"{BASE}/recipe",
                },
                timeout=TIMEOUT,
            )
            if r2.status_code in (200, 201, 302):
                return {"ok": True, "msg": "Ricetta inviata (endpoint /recipe/new)", "recipe_id": None}
        return {
            "ok": False,
            "msg": f"Import non riuscito (HTTP {r.status_code}). Usa il download BeerXML e importa manualmente.",
            "recipe_id": None,
        }
    except Exception as e:
        return {"ok": False, "msg": f"Errore connessione: {e}", "recipe_id": None}


def _parse_brew_status(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    status: dict = {"stato": "inattivo", "step": None, "temperatura": None, "progresso": None, "ricetta": None}
    temp_tag = soup.find(string=re.compile(r"\d+[,.]?\d*\s*°C", re.I))
    if temp_tag:
        m = re.search(r"(\d+[,.]?\d*)\s*°C", temp_tag)
        if m:
            status["temperatura"] = m.group(1).replace(",", ".") + "°C"
    prog_tag = soup.select_one(".progress-bar, [class*='progress'], [class*='Progress']")
    if prog_tag:
        pct = prog_tag.get("style", "")
        m = re.search(r"width:\s*(\d+)%", pct)
        if m:
            status["progresso"] = int(m.group(1))
    step_tag = soup.select_one(".StepName, .step-name, [class*='Step'] span, h2, h3")
    if step_tag:
        status["step"] = step_tag.get_text(strip=True)[:50]
    recipe_tag = soup.select_one(".RecipeName, .recipe-name, [class*='Recipe'] h2")
    if recipe_tag:
        status["ricetta"] = recipe_tag.get_text(strip=True)[:60]
    active_indicators = soup.find(string=re.compile(r"(mash|sparge|boil|cool|mashing|bollente|ammostamento)", re.I))
    if active_indicators or status["temperatura"] or status["progresso"]:
        status["stato"] = "attivo"
    return status


def _parse_ferment_status(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    status: dict = {"stato": "inattivo", "step": None, "temperatura": None, "giorni": None, "ricetta": None}
    temp_tag = soup.find(string=re.compile(r"\d+[,.]?\d*\s*°C", re.I))
    if temp_tag:
        m = re.search(r"(\d+[,.]?\d*)\s*°C", temp_tag)
        if m:
            status["temperatura"] = m.group(1).replace(",", ".") + "°C"
    giorni_tag = soup.find(string=re.compile(r"\d+\s*(day|giorni|giorno)", re.I))
    if giorni_tag:
        m = re.search(r"(\d+)", giorni_tag)
        if m:
            status["giorni"] = int(m.group(1))
    step_tag = soup.select_one(".StepName, [class*='Phase'], [class*='Ferment'] h3")
    if step_tag:
        status["step"] = step_tag.get_text(strip=True)[:50]
    if status["temperatura"] or status["giorni"]:
        status["stato"] = "attivo"
    return status


async def get_brew_status(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get("/brew", timeout=TIMEOUT)
        return _parse_brew_status(r.text)
    except Exception as e:
        return {"stato": "errore", "msg": str(e)}


async def get_ferment_status(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get("/fermentation", timeout=TIMEOUT)
        return _parse_ferment_status(r.text)
    except Exception as e:
        return {"stato": "errore", "msg": str(e)}


def _parse_sessions(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sessions = []
    for row in soup.select("tr, .SessionItem, [class*='session'], [class*='Session']"):
        tds = row.select("td")
        if len(tds) >= 2:
            sessions.append({
                "data": tds[0].get_text(strip=True),
                "ricetta": tds[1].get_text(strip=True),
                "note": tds[2].get_text(strip=True) if len(tds) > 2 else "",
            })
        elif row.select_one("a"):
            sessions.append({
                "data": "",
                "ricetta": row.get_text(strip=True)[:60],
                "note": "",
            })
    return sessions[:20]


async def get_sessions(client: httpx.AsyncClient) -> list[dict]:
    try:
        r = await client.get("/sessions", timeout=TIMEOUT)
        return _parse_sessions(r.text)
    except Exception as e:
        return []
