# -*- coding: utf-8 -*-
"""Untersucht die drei zentralen Stellenportale.

Sie sind die wertvollsten Quellen: Interamt bündelt Bund und Kommunen, das
Karriereportal Berlin die Senatsverwaltungen und Bezirksämter, Karriere in
Brandenburg das Land Brandenburg. Alle drei sind Suchanwendungen — die Liste
entsteht erst im Browser oder kommt über eine eigene Schnittstelle.

Das Skript zeichnet den Netzverkehr mit und sucht darin die Schnittstelle, die
die Trefferliste liefert. Mit ihr lässt sich später viel schneller und
schonender arbeiten als mit einem Browser je Seitenaufruf.
"""

import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASIS)

PORTALE = {
    "interamt": "https://www.interamt.de/koop/app/trefferliste",
    "berlin": "https://www.berlin.de/karriereportal/stellensuche/",
    "lhp": "https://bewerberportal-lhp.dikom-bb.de/bewerber-web/"
           "?companyEid=LHP&tenant=&lang=D#positions",
}

# Netzaufrufe, die wie eine Trefferliste aussehen.
SCHNITTSTELLE_RE = re.compile(
    r"(?:such|search|trefferliste|results?|stellen|jobs?|positions?|vacan|"
    r"api|rest|graphql|query|list)", re.IGNORECASE)


def erkunden(name, url):
    from scrapling.fetchers import StealthySession
    print("=" * 78)
    print(f"{name}  ·  {url}")
    print("=" * 78)
    bericht = {"name": name, "url": url}

    with StealthySession(headless=True, record_requests=True,
                         network_idle=True, disable_resources=False) as sitzung:
        try:
            seite = sitzung.fetch(url, timeout=60000, wait=6000)
        except Exception as fehler:
            print(f"  FEHLER: {type(fehler).__name__}: {str(fehler)[:160]}")
            return {"name": name, "url": url, "fehler": str(fehler)[:200]}

        print(f"  Status {seite.status}")
        try:
            text = seite.get_all_text(ignore_tags=("script", "style", "noscript"))
        except Exception:
            text = ""
        bericht["zeichen"] = len(text or "")
        print(f"  Sichtbarer Text: {len(text or '')} Zeichen")

        # Was sieht nach Ausschreibungs-Zeilen aus?
        from einordnung import GESCHLECHT_RE, URL_MARKER
        treffer = GESCHLECHT_RE.findall(text or "")
        bericht["gender_token"] = len(treffer)
        print(f"  Geschlechtskürzel im Text: {len(treffer)}")

        links = []
        try:
            for a in seite.css("a"):
                href = a.attrib.get("href") or ""
                if any(m in href.lower() for m in URL_MARKER):
                    links.append((href, " ".join((a.text or "").split())[:70]))
        except Exception:
            pass
        bericht["job_links"] = len(links)
        print(f"  Links auf Detailseiten: {len(links)}")
        for href, beschriftung in links[:6]:
            print(f"      {beschriftung[:52]:54} {href[:70]}")

        # Netzverkehr durchsehen
        kandidaten = []
        try:
            for antwort in sitzung.network.search(url_pattern=r".*", limit=None):
                ziel = str(antwort.url)
                art = antwort.meta.get("resource_type", "")
                if art in ("image", "font", "stylesheet", "media"):
                    continue
                if not SCHNITTSTELLE_RE.search(ziel):
                    continue
                koerper = antwort.meta.get("body_note") or antwort.body or ""
                if not isinstance(koerper, str):
                    koerper = ""
                kandidaten.append({
                    "url": ziel[:220], "status": antwort.status, "art": art,
                    "laenge": len(koerper),
                    "json": koerper.lstrip()[:1].strip() in ("{", "["),
                    "anfang": koerper[:200].replace("\n", " "),
                })
        except Exception as fehler:
            print(f"  (Netzverkehr nicht lesbar: {type(fehler).__name__})")

        kandidaten.sort(key=lambda k: -k["laenge"])
        bericht["schnittstellen"] = kandidaten[:12]
        print(f"\n  {len(kandidaten)} mögliche Schnittstellen-Aufrufe, die größten:")
        for k in kandidaten[:8]:
            marke = "JSON" if k["json"] else k["art"][:4]
            print(f"    [{marke:4}] {k['status']} {k['laenge']:7} B  {k['url'][:96]}")
            if k["json"] and k["laenge"] > 200:
                print(f"             {k['anfang'][:130]}")
    print()
    return bericht


def main():
    auswahl = sys.argv[1:] or list(PORTALE)
    berichte = []
    for name in auswahl:
        if name not in PORTALE:
            print(f"(unbekannt: {name})")
            continue
        berichte.append(erkunden(name, PORTALE[name]))
    ziel = os.path.join(BASIS, "portalbericht.json")
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(berichte, f, ensure_ascii=False, indent=1)
    print(f"Bericht: {ziel}")


if __name__ == "__main__":
    main()
