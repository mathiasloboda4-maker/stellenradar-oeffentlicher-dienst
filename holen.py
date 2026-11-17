# -*- coding: utf-8 -*-
"""Abrufschicht auf Basis von Scrapling.

Zwei Wege, wie im Scrapling-Handbuch vorgesehen:

  Fetcher          normale Seiten, ohne Browser, schnell  (Standard)
  StealthyFetcher  Seiten, deren Inhalt erst per JavaScript entsteht

Welcher Weg nötig ist, steht je Arbeitgeber im Register (`tief`). Wo der
einfache Weg zu wenig liefert, wird einmal auf den Browser hochgeschaltet —
dasselbe Vorgehen wie beim Vorläufer, nur ohne eigenen Playwright-Code.

Rücksicht: erkennbare Kennung, Pausen zwischen Abrufen, Obergrenze je
Arbeitgeber. Das Programm ist für die persönliche Stellensuche gedacht.
"""

import re
import time
from urllib.parse import urljoin, urlparse

from einordnung import (GESCHLECHT_RE, URL_MARKER, aufraeumen, ist_menuetext,
                        sieht_nach_stelle_aus)

KOPFZEILEN = {"Accept-Language": "de-DE,de;q=0.9,en;q=0.5"}

# Unter so viel Text gilt eine Seite als „hat ihren Inhalt nicht im HTML".
ZU_WENIG = 1200

PAUSE_LISTE = 0.8          # zwischen zwei Arbeitgebern
PAUSE_DETAIL = 0.45        # zwischen zwei Detailseiten
MAX_JE_ARBEITGEBER = 25    # Fairness-Grenze

# Beschriftungen, die in Stellenkarten statt des Titels im Linktext stehen.
KARTEN_FUELLWORT = re.compile(
    r"^(?:mehr|details?|ansehen|anzeigen|weiterlesen|zur stelle|zum stellenangebot|"
    r"jetzt bewerben|bewerben|lesen|öffnen|info|mehr erfahren|stellenausschreibung "
    r"öffnen)\b", re.IGNORECASE)


class AbrufFehler(RuntimeError):
    pass


# ----------------------------------------------------------------------------------
# ABRUF
# ----------------------------------------------------------------------------------

def _text_von(antwort):
    try:
        return antwort.get_all_text(ignore_tags=("script", "style", "noscript")) or ""
    except Exception:
        return ""


def seite_holen(url, tief=False, zeitlimit=28):
    """Holt eine Seite. Gibt (antwort, weg) zurück; weg ist 'http' oder 'browser'.

    Schaltet selbsttätig auf den Browser hoch, wenn über HTTP zu wenig Text
    ankommt — viele Karriereseiten laden ihre Liste nach."""
    if not tief:
        try:
            from scrapling.fetchers import Fetcher
            antwort = Fetcher.get(url, timeout=zeitlimit, stealthy_headers=True,
                                  follow_redirects=True, retries=2,
                                  headers=KOPFZEILEN)
            if antwort.status < 400 and len(_text_von(antwort)) >= ZU_WENIG:
                return antwort, "http"
        except Exception:
            pass        # dann eben im Browser

    try:
        from scrapling.fetchers import StealthyFetcher
        antwort = StealthyFetcher.fetch(
            url, headless=True, network_idle=True, timeout=max(45000, zeitlimit * 1000),
            wait=2500, disable_resources=False)
    except Exception as fehler:
        raise AbrufFehler(f"{type(fehler).__name__}: {str(fehler)[:160]}") from fehler
    if antwort.status >= 400:
        raise AbrufFehler(f"HTTP {antwort.status}")
    return antwort, "browser"


def volltext_holen(url, tief=False):
    """Ausschreibungstext einer Detailseite."""
    antwort, _ = seite_holen(url, tief=tief)
    text = _text_von(antwort)
    time.sleep(PAUSE_DETAIL)
    return _rahmen_entfernen(text)


# Zeilen, die auf praktisch jeder Behördenseite stehen und nichts über die
# Stelle sagen. Sie würden sonst die Stichwortsuche und das PDF zumüllen.
_RAHMEN_ZEILEN = re.compile(
    r"^\s*(?:zum hauptinhalt springen|hochkontrast|leichte sprache|gebärdensprache|"
    r"vorlesen|seite drucken|drucken|seite teilen|teilen|impressum|datenschutz(?:erklärung)?|"
    r"barrierefreiheit|erklärung zur barrierefreiheit|cookie[- ]?einstellungen|"
    r"inhaltsverzeichnis|sitemap|newsletter|zur suche|suche|menü|navigation|"
    r"startseite|english|rss|nach oben|login|anmelden|registrieren|hilfe)\s*$",
    re.IGNORECASE | re.MULTILINE)


def _rahmen_entfernen(text):
    text = _RAHMEN_ZEILEN.sub("", text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ----------------------------------------------------------------------------------
# AUSSCHREIBUNGS-LINKS AUS EINER ÜBERSICHTSSEITE
# ----------------------------------------------------------------------------------

def _titel_aus_umgebung(link_element):
    """Wenn der Linktext nur „mehr erfahren" ist, steht der Titel in der Karte
    drumherum. Dann wird im Elternelement nach einer Überschrift gesucht."""
    try:
        eltern = link_element.parent
    except Exception:
        return None
    for _ in range(3):
        if eltern is None:
            return None
        for auswahl in ("h1", "h2", "h3", "h4", "h5", ".title", ".job-title",
                        "[class*=titel]", "[class*=title]", "strong"):
            try:
                treffer = eltern.css(auswahl)
            except Exception:
                treffer = []
            for element in treffer[:3]:
                text = aufraeumen(element.get_all_text() or "")
                if text and len(text) >= 8 and not ist_menuetext(text):
                    return text
        try:
            eltern = eltern.parent
        except Exception:
            return None
    return None


def stellen_links(antwort, basis_url, grenze=MAX_JE_ARBEITGEBER):
    """Findet Links auf Ausschreibungs-Detailseiten.

    Zwei Wege, wie beim Vorläufer bewährt:
      1. Geschlechtskürzel im Linktext — das stärkste Signal
      2. Detailseiten-typische URL plus brauchbarer Titel
    Dazu der Karten-Fall, bei dem der Titel neben dem Link steht."""
    gefunden, gesehen = [], set()
    eigene_domain = urlparse(basis_url).netloc

    try:
        verweise = antwort.css("a")
    except Exception:
        return []

    for element in verweise:
        try:
            href = element.attrib.get("href") or ""
        except Exception:
            continue
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        ziel = urljoin(basis_url, href)
        if ziel in gesehen:
            continue

        fremd = urlparse(ziel).netloc and urlparse(ziel).netloc != eigene_domain
        if fremd and not re.search(
                r"dvinci|personio|softgarden|workday|successfactors|greenhouse|"
                r"recruitee|smartrecruiters|jobvite|interamt|rexx|concludis|"
                r"bewerber|jobs\.|karriere\.|stellen\.", ziel, re.IGNORECASE):
            continue

        titel = aufraeumen(element.get_all_text() or "")
        if not titel or KARTEN_FUELLWORT.match(titel):
            aus_karte = _titel_aus_umgebung(element)
            if aus_karte:
                titel = aus_karte
        if not titel:
            continue

        if not sieht_nach_stelle_aus(titel, ziel, basis_url):
            continue

        gesehen.add(ziel)
        gefunden.append({"titel": titel, "url": ziel})
        if len(gefunden) >= grenze:
            break
    return gefunden


def seiten_titel_stellen(antwort, basis_url, grenze=MAX_JE_ARBEITGEBER):
    """Rückfall für Seiten, die ihre Ausschreibungen ohne eigene Links auflisten
    (etwa als Aufzählung mit PDF-Anhang oder als reiner Text).

    Dann werden Zeilen mit Geschlechtskürzel als Stellen gewertet und die
    Übersichtsseite selbst als Adresse verwendet — ehrlicher, als sie zu
    übersehen, und im Steckbrief steht, dass die Quelle die Liste ist."""
    text = _text_von(antwort)
    gefunden, gesehen = [], set()
    for zeile in (text or "").splitlines():
        zeile = aufraeumen(zeile)
        if not zeile or len(zeile) < 14 or len(zeile) > 190:
            continue
        if not GESCHLECHT_RE.search(zeile):
            continue
        if ist_menuetext(zeile) or zeile.lower() in gesehen:
            continue
        gesehen.add(zeile.lower())
        gefunden.append({"titel": zeile, "url": basis_url, "aus_liste": True})
        if len(gefunden) >= grenze:
            break
    return gefunden


def arbeitgeber_durchsuchen(eintrag, melden=None):
    """Eine Arbeitgeberseite abklappern. Gibt (treffer, weg, hinweis) zurück."""
    def sagen(was):
        if melden:
            melden(was)

    url = eintrag["url"]
    try:
        antwort, weg = seite_holen(url, tief=eintrag.get("tief", False))
    except AbrufFehler as fehler:
        return [], None, str(fehler)

    treffer = stellen_links(antwort, url)
    if not treffer:
        # Zweiter Versuch im Browser, falls bisher nur HTTP gelaufen ist
        if weg == "http":
            try:
                antwort, weg = seite_holen(url, tief=True)
                treffer = stellen_links(antwort, url)
            except AbrufFehler:
                pass
    if not treffer:
        treffer = seiten_titel_stellen(antwort, url)

    time.sleep(PAUSE_LISTE)
    hinweis = None if treffer else "keine Ausschreibungen erkannt"
    sagen(f"{eintrag['name']}: {len(treffer)} Treffer ({weg})")
    return treffer, weg, hinweis
