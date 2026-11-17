# -*- coding: utf-8 -*-
"""Prüflauf über das Arbeitgeber-Register.

Für jede Seite wird festgestellt:
  · ist sie erreichbar (HTTP-Status, Weiterleitung)
  · kommt genug Text an, oder entsteht der Inhalt erst per JavaScript
  · sieht sie überhaupt wie eine Stellenseite aus

Aufruf:
    .venv\\Scripts\\python.exe pruefe_arbeitgeber.py            (alle, nur HTTP)
    .venv\\Scripts\\python.exe pruefe_arbeitgeber.py --browser  (dünne auch im Browser)
    .venv\\Scripts\\python.exe pruefe_arbeitgeber.py --nur Berlin
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
BASIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASIS)

import arbeitgeber as ag_modul          # noqa: E402
from einordnung import GESCHLECHT_RE, URL_MARKER   # noqa: E402

ERGEBNIS_DATEI = os.path.join(BASIS, "pruefbericht_arbeitgeber.json")

# Ab wie viel Text eine Seite als "liefert Inhalt" gilt.
TEXT_SCHWELLE = 1200


def seite_pruefen(eintrag):
    """Ruft eine Karriereseite ab und beurteilt sie."""
    from scrapling.fetchers import Fetcher
    befund = {"name": eintrag["name"], "url": eintrag["url"],
              "sektor": eintrag["sektor"], "gruppe": eintrag["gruppe"]}
    try:
        antwort = Fetcher.get(eintrag["url"], timeout=25, stealthy_headers=True,
                              follow_redirects=True, retries=2)
    except Exception as fehler:
        befund.update(status=None, urteil="FEHLER",
                      hinweis=f"{type(fehler).__name__}: {str(fehler)[:120]}")
        return befund

    befund["status"] = antwort.status
    try:
        ziel = str(antwort.url)
    except Exception:
        ziel = eintrag["url"]
    befund["ziel"] = ziel
    if ziel.rstrip("/") != eintrag["url"].rstrip("/"):
        befund["weitergeleitet"] = ziel

    if antwort.status >= 400:
        befund["urteil"] = f"HTTP {antwort.status}"
        return befund

    text = ""
    try:
        text = antwort.get_all_text(ignore_tags=("script", "style", "noscript"))
    except Exception:
        try:
            text = antwort.body if isinstance(antwort.body, str) else ""
        except Exception:
            text = ""
    befund["zeichen"] = len(text or "")

    # Wie viele Links sehen nach Ausschreibungs-Detailseiten aus?
    treffer_links = 0
    try:
        for a in antwort.css("a"):
            href = (a.attrib.get("href") or "").lower()
            if any(m in href for m in URL_MARKER):
                treffer_links += 1
    except Exception:
        pass
    befund["job_links"] = treffer_links
    befund["gender_token"] = len(GESCHLECHT_RE.findall(text or ""))

    if befund["zeichen"] < TEXT_SCHWELLE:
        befund["urteil"] = "DUENN (JavaScript?)"
    elif treffer_links >= 2 or befund["gender_token"] >= 1:
        befund["urteil"] = "OK"
    else:
        befund["urteil"] = "ERREICHBAR, keine Stellen erkennbar"
    return befund


def im_browser_pruefen(befund):
    """Zweiter Versuch mit Browser für dünne Seiten."""
    from scrapling.fetchers import StealthyFetcher
    try:
        antwort = StealthyFetcher.fetch(befund["url"], headless=True,
                                        network_idle=True, timeout=45000,
                                        wait=2500, disable_resources=False)
    except Exception as fehler:
        befund["browser"] = f"FEHLER {type(fehler).__name__}: {str(fehler)[:90]}"
        return befund
    try:
        text = antwort.get_all_text(ignore_tags=("script", "style", "noscript"))
    except Exception:
        text = ""
    treffer_links = 0
    try:
        for a in antwort.css("a"):
            href = (a.attrib.get("href") or "").lower()
            if any(m in href for m in URL_MARKER):
                treffer_links += 1
    except Exception:
        pass
    befund["browser_zeichen"] = len(text or "")
    befund["browser_job_links"] = treffer_links
    befund["browser_gender"] = len(GESCHLECHT_RE.findall(text or ""))
    if len(text or "") >= TEXT_SCHWELLE and (treffer_links >= 2 or befund["browser_gender"]):
        befund["browser"] = "OK — braucht Browser"
        befund["urteil"] = "OK (Browser)"
    elif len(text or "") >= TEXT_SCHWELLE:
        befund["browser"] = "Text da, aber keine Stellen erkennbar"
    else:
        befund["browser"] = "auch im Browser leer"
    return befund


def main():
    args = sys.argv[1:]
    mit_browser = "--browser" in args
    filter_text = None
    if "--nur" in args:
        filter_text = args[args.index("--nur") + 1].lower()

    liste = ag_modul.ARBEITGEBER
    if filter_text:
        liste = [e for e in liste
                 if filter_text in e["name"].lower() or filter_text in e["gruppe"].lower()]

    print(f"Prüfe {len(liste)} Karriereseiten über HTTP (6 parallel) …\n")
    start = time.time()
    befunde = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for befund in pool.map(seite_pruefen, liste):
            befunde.append(befund)
            marke = {"OK": "✓"}.get(befund["urteil"], "·")
            print(f"  {marke} {befund['name'][:46]:48} {befund['urteil']}"
                  f"  ({befund.get('zeichen', 0)} Z., {befund.get('job_links', 0)} Job-Links)")

    duenn = [b for b in befunde if b["urteil"].startswith("DUENN")]
    if mit_browser and duenn:
        print(f"\n{len(duenn)} dünne Seiten jetzt im Browser (einzeln, dauert) …\n")
        for befund in duenn:
            im_browser_pruefen(befund)
            print(f"  · {befund['name'][:46]:48} {befund.get('browser')}"
                  f"  ({befund.get('browser_zeichen', 0)} Z., "
                  f"{befund.get('browser_job_links', 0)} Job-Links)")

    with open(ERGEBNIS_DATEI, "w", encoding="utf-8") as f:
        json.dump(befunde, f, ensure_ascii=False, indent=1)

    print(f"\n{'=' * 74}")
    from collections import Counter
    zaehler = Counter(b["urteil"] for b in befunde)
    for urteil, anzahl in zaehler.most_common():
        print(f"  {anzahl:3}  {urteil}")
    print(f"\n{time.time() - start:.0f}s · Bericht: {ERGEBNIS_DATEI}")


if __name__ == "__main__":
    main()
