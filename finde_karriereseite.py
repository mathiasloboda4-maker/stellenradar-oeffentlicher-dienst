# -*- coding: utf-8 -*-
"""Sucht die echte Karriereseite eines Arbeitgebers.

Hintergrund: Geratene Karriere-URLs sind fast immer falsch — Behörden und
Beratungshäuser bauen ihre Seiten regelmäßig um. Statt zu raten, fragen wir die
Startseite: Welche Links führen zu Stellen? Die Kandidaten werden bewertet und
dann wirklich abgerufen. Nur was Stellen zeigt, kommt ins Register.

Aufruf:
    .venv\\Scripts\\python.exe finde_karriereseite.py https://www.bsr.de
    .venv\\Scripts\\python.exe finde_karriereseite.py --aus-bericht
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

sys.stdout.reconfigure(encoding="utf-8")
BASIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASIS)

from einordnung import GESCHLECHT_RE, URL_MARKER   # noqa: E402

# Wortstämme, die auf eine Karriere- oder Stellenseite hindeuten, mit Gewicht.
SIGNALE = [
    (r"stellenausschreibung", 10), (r"stellenangebot", 10), (r"stellenanzeige", 9),
    (r"offene[-_ ]?stellen", 9), (r"stellensuche", 8), (r"stellenboerse", 8),
    (r"stellenb[öo]rse", 8), (r"jobsuche", 8), (r"job[-_ ]?search", 7),
    (r"trefferliste", 7), (r"vacanc", 7), (r"/jobs", 6), (r"stellen", 6),
    (r"karriere", 4), (r"career", 4), (r"arbeiten-bei", 3), (r"jobs-und-karriere", 5),
]

# Links, die zwar „Karriere" heißen, aber keine Stellenliste sind.
GEGENSIGNALE = [r"ausbildung", r"praktik", r"werkstudent", r"schueler", r"schüler",
                r"studium", r"azubi", r"benefits", r"warum", r"bewerbungstipp",
                r"bewerbungsprozess", r"faq", r"kontakt", r"impressum", r"datenschutz",
                r"initiativbewerbung", r"podcast", r"blog", r"news"]

KOPFZEILEN = {"Accept-Language": "de-DE,de;q=0.9,en;q=0.6"}


def _punkte(href, text):
    """Bewertet einen Link daraufhin, wie sehr er nach Stellenliste aussieht."""
    ziel = (href or "").lower()
    bezeichnung = (text or "").lower()
    punkte = 0
    for muster, gewicht in SIGNALE:
        if re.search(muster, ziel):
            punkte += gewicht
        if re.search(muster, bezeichnung):
            punkte += gewicht - 1
    for muster in GEGENSIGNALE:
        if re.search(muster, ziel) or re.search(muster, bezeichnung):
            punkte -= 6
    # Kurze, saubere Pfade sind meist die Übersichtsseite
    tiefe = urlparse(ziel).path.strip("/").count("/")
    if tiefe <= 2:
        punkte += 1
    return punkte


def kandidaten_sammeln(start_url, mit_browser=False):
    """Holt eine Seite und gibt bewertete Karriere-Link-Kandidaten zurück."""
    if mit_browser:
        from scrapling.fetchers import StealthyFetcher
        antwort = StealthyFetcher.fetch(start_url, headless=True, network_idle=True,
                                        timeout=45000, wait=2000)
    else:
        from scrapling.fetchers import Fetcher
        antwort = Fetcher.get(start_url, timeout=25, stealthy_headers=True,
                              follow_redirects=True, retries=2, headers=KOPFZEILEN)
    if antwort.status >= 400:
        return []
    gefunden = {}
    for a in antwort.css("a"):
        href = a.attrib.get("href") or ""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        voll = urljoin(str(antwort.url), href)
        if urlparse(voll).netloc and urlparse(voll).netloc != urlparse(start_url).netloc:
            # Fremde Domain nur erlauben, wenn sie klar ein Bewerberportal ist
            if not re.search(r"dvinci|personio|softgarden|workday|successfactors|"
                             r"greenhouse|recruitee|smartrecruiters|jobvite|interamt|"
                             r"rexx|concludis|bewerber|jobs\.|karriere\.", voll, re.I):
                continue
        text = " ".join((a.text or "").split())[:80]
        punkte = _punkte(voll, text)
        if punkte <= 3:
            continue
        if voll not in gefunden or punkte > gefunden[voll][0]:
            gefunden[voll] = (punkte, text)
    liste = [{"url": u, "punkte": p, "text": t} for u, (p, t) in gefunden.items()]
    liste.sort(key=lambda k: -k["punkte"])
    return liste


def kandidat_pruefen(url):
    """Ruft einen Kandidaten ab und zählt, was nach Ausschreibungen aussieht."""
    from scrapling.fetchers import Fetcher
    ergebnis = {"url": url, "status": None, "zeichen": 0, "job_links": 0, "gender": 0}
    try:
        antwort = Fetcher.get(url, timeout=25, stealthy_headers=True,
                              follow_redirects=True, retries=1, headers=KOPFZEILEN)
    except Exception as fehler:
        ergebnis["fehler"] = f"{type(fehler).__name__}"
        return ergebnis
    ergebnis["status"] = antwort.status
    if antwort.status >= 400:
        return ergebnis
    try:
        text = antwort.get_all_text(ignore_tags=("script", "style", "noscript"))
    except Exception:
        text = ""
    ergebnis["zeichen"] = len(text or "")
    ergebnis["gender"] = len(GESCHLECHT_RE.findall(text or ""))
    try:
        for a in antwort.css("a"):
            href = (a.attrib.get("href") or "").lower()
            if any(m in href for m in URL_MARKER):
                ergebnis["job_links"] += 1
    except Exception:
        pass
    ergebnis["taugt"] = (ergebnis["zeichen"] >= 1200
                         and (ergebnis["job_links"] >= 2 or ergebnis["gender"] >= 1))
    return ergebnis


def beste_karriereseite(start_url, name=""):
    """Gesamtablauf für einen Arbeitgeber: sammeln, prüfen, Bestes zurückgeben."""
    wurzel = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    befund = {"name": name, "start": start_url, "wurzel": wurzel}
    kandidaten = []
    for mit_browser in (False, True):
        try:
            kandidaten = kandidaten_sammeln(wurzel, mit_browser=mit_browser)
        except Exception as fehler:
            befund.setdefault("hinweise", []).append(
                f"{'Browser' if mit_browser else 'HTTP'}: {type(fehler).__name__}")
            kandidaten = []
        if kandidaten:
            befund["quelle"] = "Browser" if mit_browser else "HTTP"
            break
    if not kandidaten:
        befund["ergebnis"] = None
        return befund

    befund["kandidaten"] = kandidaten[:8]
    # Die besten drei wirklich abrufen
    geprueft = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for pruefung in pool.map(kandidat_pruefen, [k["url"] for k in kandidaten[:4]]):
            geprueft.append(pruefung)
    befund["geprueft"] = geprueft
    tauglich = [g for g in geprueft if g.get("taugt")]
    if tauglich:
        tauglich.sort(key=lambda g: -(g["job_links"] * 2 + g["gender"]))
        befund["ergebnis"] = tauglich[0]["url"]
    else:
        # Kein Volltreffer: die Seite mit dem meisten Inhalt als Hinweis zurückgeben
        erreichbar = [g for g in geprueft if g["status"] and g["status"] < 400]
        erreichbar.sort(key=lambda g: -g["zeichen"])
        befund["ergebnis"] = None
        befund["vorschlag"] = erreichbar[0]["url"] if erreichbar else None
    return befund


def main():
    args = sys.argv[1:]
    if "--aus-bericht" in args:
        with open(os.path.join(BASIS, "pruefbericht_arbeitgeber.json"),
                  encoding="utf-8") as f:
            bericht = json.load(f)
        offen = [b for b in bericht
                 if b["urteil"] != "OK" and not b["urteil"].startswith("OK (")]
        print(f"{len(offen)} Arbeitgeber ohne brauchbare Seite — suche Karriereseiten\n")
        gefunden = {}
        for befund_alt in offen:
            befund = beste_karriereseite(befund_alt["url"], befund_alt["name"])
            treffer = befund.get("ergebnis")
            marke = "✓" if treffer else "·"
            print(f"  {marke} {befund_alt['name'][:42]:44} "
                  f"{treffer or befund.get('vorschlag') or '— nichts gefunden'}")
            if treffer:
                gefunden[befund_alt["name"]] = treffer
            elif befund.get("vorschlag"):
                gefunden[befund_alt["name"]] = "?" + befund["vorschlag"]
        ziel = os.path.join(BASIS, "gefundene_karriereseiten.json")
        with open(ziel, "w", encoding="utf-8") as f:
            json.dump(gefunden, f, ensure_ascii=False, indent=1)
        klar = sum(1 for v in gefunden.values() if not v.startswith("?"))
        print(f"\n{klar} sicher, {len(gefunden) - klar} unsicher (mit ?) · {ziel}")
        return

    if not args:
        print(__doc__)
        return
    befund = beste_karriereseite(args[0])
    print(json.dumps(befund, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
