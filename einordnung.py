# -*- coding: utf-8 -*-
"""Einordnung einer Ausschreibung: Berufsfeld, Sektor, Passung.

Diese Datei ist das Herzstück. Sie entscheidet, was überhaupt gespeichert wird
und wie gut eine Stelle zum Profil passt. Alle Listen sind bewusst hier oben
und von Hand bearbeitbar: Stichwort ergänzen, Programm neu starten, fertig.

Grundregel aus dem Ursprungsauftrag: Kein Treffer in einem Berufsfeld heißt
verworfen. Lieber eine passende Stelle übersehen als eine Liste, die man nicht
mehr durchsieht.
"""

import json
import re
import unicodedata

# ----------------------------------------------------------------------------------
# DIE SECHS BERUFSFELDER
#
# Name, Stichworte und Kompetenzen stehen NICHT mehr hier, sondern in
# konfiguration.py bzw. der Datei berufsfelder.json daneben. Grund: Beides soll
# sich im Fenster ändern lassen — nach einer Weiterbildung kommt eine Kompetenz
# dazu, und Stichwortlisten wachsen mit der Erfahrung.
#
# `neu_laden()` holt die aktuelle Fassung. Die Oberfläche ruft das nach jedem
# Speichern auf, damit Änderungen sofort gelten.
# ----------------------------------------------------------------------------------

import konfiguration

FELDER = {}
FELD_KURZ = {}
FELD_FARBE = {}
FELD_KOMPETENZEN = {}
FELD_STICHWORTE = {}
GEWICHTE = {}


def neu_laden():
    """Liest Berufsfelder und Gewichtung frisch ein."""
    global FELDER, FELD_KURZ, FELD_FARBE, FELD_KOMPETENZEN, FELD_STICHWORTE, GEWICHTE
    felder = konfiguration.felder_laden()
    FELDER = {int(n): f["name"] for n, f in felder.items()}
    FELD_KURZ = {int(n): f.get("zeichen", "") for n, f in felder.items()}
    FELD_FARBE = {int(n): f.get("farbe", "#6366F1") for n, f in felder.items()}
    FELD_KOMPETENZEN = {int(n): list(f.get("kompetenzen", [])) for n, f in felder.items()}
    FELD_STICHWORTE = {
        int(n): {int(stufe): list(worte)
                 for stufe, worte in f["stichworte"].items()}
        for n, f in felder.items()
    }
    GEWICHTE = konfiguration.gewichte_laden()
    return FELDER


neu_laden()


# ----------------------------------------------------------------------------------
# HARTE AUSSCHLÜSSE — haben immer Vorrang vor den positiven Stichworten
# ----------------------------------------------------------------------------------

AUSSCHLUSS = [
    # Studierende, Einstieg, Nebenrollen
    "werkstudent", "werkstudier", "studentische", "studierende -", "studierende (",
    "minijob", "aushilfe", "praktik", "hospitanz", "fsj", "bfd", "bundesfreiwillig",
    "azubi", "ausbildung", "auszubildende", "duales studium", "dual studierende",
    "dualer student", "trainee", "volontariat", "hilfskraft", "anwärter",
    "referendar", "stipendi", "schülerpraktik", "quereinstieg in den vorbereitungsdienst",
    # Pflege, Medizin, Therapie, Soziales, Pädagogik
    "pflegefach", "krankenpfleg", "altenpfleg", "pflegehelfer", "pflegedienst",
    "therapeut", "logopäd", "ergotherap", "physiotherap", "hebamme", "psycholog",
    "arzt", "ärztin", "ärztlich", "medizinisch", "zahnmedizin", "psychiatr",
    "erzieher", "sozialarbeit", "sozialpädagog", "heilerziehung", "lehrkraft",
    "lehrer", "dozent", "kita", "hort ", "kinderpfleg", "betreuungskraft",
    # Rein wissenschaftliche Qualifikationsstellen
    "doktorand", "postdoc", "post-doc", "phd", "promotionsstelle", "professur",
    "professor", "juniorprofess", "wissenschaftliche hilfskraft", "research fellow",
    "research associate", "akademische*r mitarbeiter", "akademischer mitarbeiter",
    "akademische mitarbeiterin", "wissenschaftliche*r mitarbeiter",
    # Küche, Reinigung, Handwerk, Fahrdienste, Technik-Gewerke
    "küche", "koch ", "köchin", "reinigung", "hausmeister", "haustechnik",
    "fahrer", "kraftfahrer", "busfahrer", "straßenwärter", "gärtner", "forstwirt",
    "handwerk", "elektriker", "elektroniker", "elektrotechnik", "mechatronik",
    "installateur", "anlagenmechanik", "tischler", "maler ", "lagerist", "monteur",
    "schlosser", "bautechnik", "bauingenieur", "vermessungstechnik",
    "vermessungsingenieur", "statiker", "bauleiter", "polier ", "tiefbau",
    "hochbau", "architekt", "landschaftsplan", "stadtplan",
    # Sekretariat, Empfang, Sicherheit
    "sekretariat", "sekretär", "empfang", "sicherheitsdienst", "wachschutz",
    "pförtner", "schreibkraft", "assistenz der geschäftsführung", "teamassistenz",
    "vorstandsassistenz", "büromitarbeiter", "sachbearbeitung im schreibdienst",
    # Profilfremd: rein juristisch, reine Entwicklung/Administration, Vollzug
    "jurist", "richter", "staatsanwalt", "rechtsanwalt", "notariat", "justiziar",
    "rechtsreferent", "syndikus",
    "softwareentwickler", "software engineer", "software developer", "fullstack",
    "full-stack", "frontend-entwickl", "backend-entwickl", "webentwickl",
    "fachinformatiker", "systemadministrator", "netzwerkadministrator",
    "datenbankadministrator", "administrator", "devops engineer", "sap-entwickl",
    "development architect", "solution architect", "system engineer",
    "data engineer", "data scientist", "cloud engineer", "penetrationstest",
    "sicherheitsanalyst", "soc-analyst", "netzwerktechnik",
    "polizeivollzug", "kommissar", "polizeimeister", "brandmeister", "feuerwehr",
    "justizvollzug", "veterinär", "bibliothekar", "archivar", "steuerfahndung",
    "steueramtsanwalt", "finanzwirt", "steuersachbearbeit",
    # Nachgezogen nach dem ersten Probelauf am 11.11.2026: Diese Stellen hatten
    # ein passendes Schlagwort im Titel ("Projektleitung", "Koordination"), aber
    # ein Sachgebiet, das mit dem Profil nichts zu tun hat.
    "kinderschutz", "jugendhilfe", "sozialdienst", "vormundschaft",
    "unterhaltsvorschuss", "wohngeld", "betreuungsrecht", "eingliederungshilfe",
    "verfahrenstechnik", "baumaßnahme", "bauwesen", "bauaufsicht", "bauordnung",
    "gebäudeausrüstung", "tragwerk", "konstruktiver ingenieurbau", "maschinenbau",
    "verkehrsplanung", "straßenplanung", "wasserwirtschaft", "abfallwirtschaft",
    "grünflächen", "gartenbau", "denkmalpfleg", "kampfmittel", "liegenschaftsvermess",
    "naturschutz", "immissionsschutz", "lebensmittelüberwach", "schulbau",
    # Nachgezogen nach dem ersten echten Lauf am 11.11.2026
    "anwendungsentwickl", "bürosachbearbeit", "buerosachbearbeit",
    "servicemitarbeiter", "servicekraft", "fuhrpark", "poststelle",
    "registratur", "telefonzentrale", "schreibdienst", "datenerfass",
    "kassenverwalt", "buchhalt", "rechnungswesen", "lohnbuchhalt",
    "personalsachbearbeit", "beihilfesachbearbeit", "versorgungsamt",
    "versorgungstechnik", "elektroanlagen", "gebäudeautomation", "gebäudetechnik",
    "redakteur", "öffentlichkeitsarbeit", "pressesprecher", "grafiker",
    # „Entwickler" in jeder Schreibweise. Die Vergleichsform entfernt vorher
    # Gendersonderzeichen, deshalb genügt hier die einfache Form.
    "entwickler", "entwicklerin", "programmier",
]

# Navigations- und Menütexte, die keine Ausschreibungen sind.
MENUE_TEXTE = [
    "impressum", "datenschutz", "kontakt", "newsletter", "vorlesen", "english",
    "leichte sprache", "gebärdensprache", "sitemap", "login", "anmelden", "cookie",
    "startseite", "zurück", "weiter", "mehr erfahren", "faq", "presse", "suche",
    "barrierefrei", "initiativbewerbung", "karriereportal", "stellenangebote",
    "aktuelle stellen", "jobs und karriere", "karriere im", "arbeiten bei",
    "bewerbungsprozess", "benefits", "über uns", "home", "menü", "drucken",
    "seite teilen", "rss", "abonnieren", "jobabo", "job-abo", "merkliste",
    "anspringen", "einwilligung", "webanalyse", "embed", "inhalt laden",
    "schriftgröße", "kontrast", "vergrößern", "verkleinern", "alle stellen",
    "stellenmarkt", "offene stellen", "unsere stellenangebote", "zur stellenbörse",
    "jetzt bewerben", "bewerben", "weitere informationen", "details", "mehr",
    "zur übersicht", "alle anzeigen", "filter", "sortieren", "seite 1", "nächste seite",
]

# Geschlechtskürzel. Uneinheitlich geschrieben, deshalb allgemein gefasst:
# zwei oder drei Kürzelbuchstaben, getrennt durch / _ | oder Komma.
_KUERZEL = r"(?:[mwdxifa]|gn)"
GESCHLECHT_RE = re.compile(
    r"\(\s*" + _KUERZEL + r"\s*[/_|,]\s*" + _KUERZEL +
    r"(?:\s*[/_|,]\s*" + _KUERZEL + r")?\s*\*?\s*\)"
    r"|\(\s*(?:gn\s*\*?|all\s*genders|divers|w/m/divers|m/w/divers)\s*\)"
    r"|(?<![a-z])(?:m/w/d|w/m/d|f/m/d|m/w/x)(?![a-z])",
    re.IGNORECASE)

# URL-Bestandteile, die auf eine Detailseite hindeuten.
URL_MARKER = ["stellenangebot", "stellenausschreibung", "stellenanzeige", "jobposting",
              "jobdetail", "job-detail", "/job/", "/jobs/", "/stellen/", "vacanc",
              "jobid", "job_id", "ausschreibung", "/position", "karriere/stelle",
              "/offer", "/detail", "/vakanz", "/einstellung"]


# ----------------------------------------------------------------------------------
# SEKTOREN — die neue zweite Dimension neben dem Berufsfeld
# ----------------------------------------------------------------------------------

SEKTOREN = {
    "oed_bb": "Öffentlicher Dienst Brandenburg",
    "oed_be": "Öffentlicher Dienst Berlin",
    "oed_bund": "Bund (Berlin)",
    "wissenschaft": "Wissenschaft & Hochschulen",
    "beratung": "Public-Sector-Beratung",
    "privat": "Privatwirtschaft",
}

SEKTOR_KURZ = {
    "oed_bb": "ÖD BB", "oed_be": "ÖD BE", "oed_bund": "Bund",
    "wissenschaft": "Wiss.", "beratung": "Beratung", "privat": "Privat",
}


# ----------------------------------------------------------------------------------
# HILFSFUNKTIONEN
# ----------------------------------------------------------------------------------

def aufraeumen(text):
    """Vereinheitlicht einen Titel für den Stichwortvergleich."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = text.replace("­", "")              # weiches Trennzeichen
    text = re.sub(r"[‐-―−]", "-", text)   # alle Strichformen
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# Gendersonderzeichen im Wortinneren. „Mitarbeiter:in", „Mitarbeiter*in" und
# „Mitarbeiter_in" müssen dieselbe Vergleichsform ergeben — sonst greift ein
# Stichwort nur bei der Schreibweise, in der es zufällig notiert wurde.
_GENDER_ZEICHEN = re.compile(r"(?<=[a-zäöüß])[*:_·](?=[a-zäöüß])", re.IGNORECASE)


def vergleichsform(text):
    """Klein geschrieben und ohne Gendersonderzeichen im Wortinneren.
    Grundlage für jeden Stichwortvergleich, nie für die Anzeige."""
    return _GENDER_ZEICHEN.sub("", aufraeumen(text).lower())


def ist_ausgeschlossen(text):
    """Harter Ausschluss. Gibt den auslösenden Begriff zurück, sonst None."""
    klein = vergleichsform(text)
    for begriff in AUSSCHLUSS:
        if vergleichsform(begriff) in klein:
            return begriff
    return None


def ist_menuetext(titel):
    """Navigations- oder Menütext statt Ausschreibung?"""
    klein = aufraeumen(titel).lower().strip(" ·–-:|»«>")
    if not klein:
        return True
    for begriff in MENUE_TEXTE:
        if klein == begriff or klein.startswith(begriff + " ") or klein == begriff + ":":
            return True
    # Reine Menütexte sind kurz und enthalten kein Geschlechtskürzel
    if len(klein) < 14 and not GESCHLECHT_RE.search(titel):
        return True
    return False


def felder_bestimmen(text):
    """Welche Berufsfelder passen? Ergebnis: Liste (feld, punkte), stärkstes zuerst."""
    klein = vergleichsform(text)
    ergebnis = []
    for feld, stufen in FELD_STICHWORTE.items():
        punkte, treffer = 0, []
        for gewicht, worte in stufen.items():
            for wort in worte:
                if wort in klein:
                    punkte += gewicht
                    treffer.append(wort)
        if punkte:
            ergebnis.append((feld, punkte, treffer))
    ergebnis.sort(key=lambda e: (-e[1], e[0]))
    return ergebnis


def sieht_nach_stelle_aus(titel, url="", basis_url=None):
    """Ist das überhaupt eine Ausschreibung? Strenger als nötig ist hier richtig:
    Ein verpasster Treffer ist ärgerlich, eine Liste voller Menüeinträge nutzlos."""
    titel = aufraeumen(titel)
    if not titel or len(titel) < 8:
        return False
    if ist_menuetext(titel):
        return False
    if basis_url and url and _gleiche_seite(url, basis_url):
        return False
    # Geschlechtskürzel im Titel ist das stärkste Signal
    if GESCHLECHT_RE.search(titel):
        return True
    # Sonst: Detailseiten-URL plus aussagekräftiger Titel
    klein_url = (url or "").lower()
    if any(m in klein_url for m in URL_MARKER) and len(titel.split()) >= 2:
        return True
    return False


def _gleiche_seite(href, basis_url):
    """Verweist der Link auf die Übersichtsseite selbst? Die Listen-URLs enthalten
    oft 'stellenausschreibung', was sonst als Selbsttreffer gezählt wird."""
    def kern(u):
        u = (u or "").split("#")[0].split("?")[0].rstrip("/").lower()
        return u
    return kern(href) == kern(basis_url)


# ----------------------------------------------------------------------------------
# ECKDATEN AUS DEM AUSSCHREIBUNGSTEXT
# ----------------------------------------------------------------------------------

# Entgelt- und Besoldungsgruppen. Welche davon Punkte bringen, steht in der
# Gewichtung (im Fenster einstellbar), nicht hier.
ENTGELT_RE = re.compile(
    r"(?:entgeltgruppe|eg|e)\s*[\.\s]?\s*(\d{1,2})\s*(?:tv-?l|tv-?öd|tvöd|tv-l)?"
    r"|(?:besoldungsgruppe|bes\.?\s?gr\.?)\s*(a|b)\s*(\d{1,2})"
    r"|\b(a|a\s)\s?(\d{2})\b\s*(?:bbesg|lbesg|bundesbesoldung|landesbesoldung)"
    r"|\b(e|eg)\s?(\d{1,2})\b",
    re.IGNORECASE)

ENTGELT_KLAR_RE = re.compile(
    r"\b(?:entgeltgruppe|eg\.?|e)\s*(\d{1,2})\b"
    r"|\b(?:besoldungsgruppe|bes\.\s?gr\.?)\s*([AB]\s?\d{1,2})\b"
    r"|\b([AB]\s?1[0-6])\b",
    re.IGNORECASE)

# Zwischen Beschriftung und Datum darf ein Zeilenumbruch stehen. In
# Tabellen-Layouts ist genau das der Normalfall:
#     Bewerbungsfrist:
#     26.11.2026
# Vorher verbot das Muster Zeilenumbrüche ausdrücklich — dadurch blieben
# erkennbare Fristen unentdeckt. Eine Leerzeile beendet die Suche, sonst
# würde das Muster über den halben Text greifen und falsche Daten einsammeln.
_FRIST_LUECKE = r"(?:[^\d\n]|\n(?!\s*\n)){0,40}"
FRIST_RE = re.compile(
    r"(?:bewerbungsfrist|bewerbungsschluss|bewerbungen?\s+(?:bitte\s+)?bis|"
    r"bis\s+(?:zum|spätestens)|frist(?:ende)?|ende\s+der\s+bewerbungsfrist|"
    r"ausschreibungsfrist|bewerben\s+sie\s+sich\s+bis|"
    r"bewerbungen?\s+(?:werden\s+)?erbeten\s+bis|"
    r"eingang\s+der\s+bewerbung(?:en)?\s+bis|"
    r"bewerbungseingang|einsendeschluss|annahmeschluss)"
    + _FRIST_LUECKE +
    r"(\d{1,2})\s*[\.\-/]\s*(\d{1,2}|[a-zäöü]+)\s*[\.\-/]?\s*(\d{2,4})",
    re.IGNORECASE)

EINTRITT_RE = re.compile(
    r"(?:zum|ab|beginn(?:end)?(?:\s+zum)?|eintritt(?:sdatum)?|besetzung\s+zum|"
    r"zu\s+besetzen\s+(?:zum|ab))"
    r"\s*(?:dem\s+)?(\d{1,2}\s*[\.\-/]\s*(?:\d{1,2}|[a-zäöü]+)\s*[\.\-/]?\s*\d{2,4}"
    r"|nächstmöglichen\s+zeitpunkt|sofort|baldmöglichst)",
    re.IGNORECASE)

MONATE = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
          "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
          "november": 11, "dezember": 12, "jan": 1, "feb": 2, "mrz": 3, "apr": 4,
          "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12}


def datum_normieren(tag, monat, jahr):
    """Macht aus Textteilen ein ISO-Datum. Gibt None zurück, wenn es unsinnig ist."""
    try:
        t = int(tag)
    except (TypeError, ValueError):
        return None
    m = None
    monat = str(monat).strip().lower()
    if monat.isdigit():
        m = int(monat)
    else:
        for name, nummer in MONATE.items():
            if monat.startswith(name):
                m = nummer
                break
    if not m:
        return None
    try:
        j = int(jahr)
    except (TypeError, ValueError):
        return None
    if j < 100:
        j += 2000
    if not (1 <= t <= 31 and 1 <= m <= 12 and 2024 <= j <= 2032):
        return None
    try:
        from datetime import date
        return date(j, m, t).isoformat()
    except ValueError:
        return None


def frist_finden(text):
    """Bewerbungsfrist als ISO-Datum. Nimmt die erste plausible Angabe."""
    for treffer in FRIST_RE.finditer(text or ""):
        iso = datum_normieren(*treffer.groups()[:3])
        if iso:
            return iso
    return None


def eintritt_finden(text):
    """Eintrittstermin, entweder als Datum oder als Wortangabe."""
    treffer = EINTRITT_RE.search(text or "")
    if not treffer:
        return None
    rohtext = treffer.group(1).strip()
    teile = re.match(r"(\d{1,2})\s*[\.\-/]\s*(\d{1,2}|[a-zäöü]+)\s*[\.\-/]?\s*(\d{2,4})",
                     rohtext, re.IGNORECASE)
    if teile:
        return datum_normieren(*teile.groups()) or rohtext
    if "nächstmöglich" in rohtext.lower():
        return "nächstmöglich"
    if "sofort" in rohtext.lower() or "baldmöglich" in rohtext.lower():
        return "sofort"
    return rohtext


# Höchste tatsächlich vorkommende Gruppen. Ohne diese Grenze wird aus einer
# Kennziffer schnell eine Entgeltgruppe: Im Probelauf stand „E 17" in der Liste,
# die es im TVöD nicht gibt.
HOECHSTE_GRUPPE = {"E": 15, "A": 16, "B": 11}


def entgelt_pruefen(bezeichnung):
    """Prüft, ob eine Gruppe wie 'E 13' überhaupt existieren kann."""
    treffer = re.fullmatch(r"([EAB])\s?(\d{1,2})", (bezeichnung or "").strip().upper())
    if not treffer:
        return None
    buchstabe, nummer = treffer.group(1), int(treffer.group(2))
    if 1 <= nummer <= HOECHSTE_GRUPPE[buchstabe]:
        return f"{buchstabe} {nummer}"
    return None


def entgelt_finden(text):
    """Entgelt- oder Besoldungsgruppe, zum Beispiel 'E 13' oder 'A 14'."""
    text = text or ""
    treffer = ENTGELT_KLAR_RE.search(text)
    if not treffer:
        return None
    if treffer.group(1):
        return entgelt_pruefen(f"E {treffer.group(1)}")
    gruppe = (treffer.group(2) or treffer.group(3) or "").upper().replace(" ", "")
    return entgelt_pruefen(gruppe)


def umfang_finden(text):
    klein = (text or "").lower()
    voll = "vollzeit" in klein
    teil = "teilzeit" in klein
    if voll and teil:
        return "Vollzeit oder Teilzeit"
    if voll:
        return "Vollzeit"
    if teil:
        return "Teilzeit"
    return None


def befristung_finden(text):
    klein = (text or "").lower()
    if "unbefristet" in klein:
        return "unbefristet"
    if re.search(r"befristet|zeitlich\s+begrenzt|sachgrundlos|elternzeitvertretung|"
                 r"mutterschutz|krankheitsvertretung", klein):
        return "befristet"
    return None


# Achtung: re.IGNORECASE würde auch [A-ZÄÖÜ] unwirksam machen, dann gilt jedes
# klein geschriebene Wort als Name. Der Schalter gilt deshalb nur für die
# Signalwörter, der Namensteil bleibt groß/klein-empfindlich.
# Akademische Titel müssen mit Leerzeichen abschließen, sonst bleibt von
# "Frau Dr. Katrin Mueller" nur "Frau Dr" übrig.
_TITEL = r"(?:(?:Dr|Prof|Dipl|Mag|Dipl\.-\w+)\.?\s+)*"
KONTAKT_RE = re.compile(
    r"(?i:ansprechpartner(?:in)?|ansprechperson|auskunft|rückfragen|"
    r"für\s+(?:weitere\s+)?(?:fach|inhaltliche)?\s*(?:auskünfte|fragen)|"
    r"kontakt|wenden\s+sie\s+sich\s+an)"
    r"[^\n]{0,80}?\b(Frau|Herrn?)\s+" + _TITEL +
    r"([A-ZÄÖÜ][\wäöüß\-]+(?:\s+[A-ZÄÖÜ][\wäöüß\-]+){0,2})")

ANREDE_RE = re.compile(r"\b(Frau|Herrn?)\s+((?:Dr\.|Prof\.)?\s*[A-ZÄÖÜ][\wäöüß\-]+"
                       r"(?:\s+[A-ZÄÖÜ][\wäöüß\-]+){0,2})")

TELEFON_RE = re.compile(
    r"(?:telefon|tel\.?|fon|durchwahl|rufnummer|☎)\s*:?\s*"
    r"(\+?[\d][\d\s/().\-]{6,24}\d)", re.IGNORECASE)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}")

ORT_RE = re.compile(
    r"\b(?:Dienstort|Einsatzort|Arbeitsort|Standort|Dienstsitz)\s*:?\s*"
    r"([A-ZÄÖÜ][\wäöüß\-. ]{2,40}?)(?:\s*[\n,;.]|$)")


def kontakt_finden(text):
    """Name der Ansprechperson samt Anrede. Die Anrede muss mit, sonst wird in der
    Anschrift aus 'Herr Hökendorf' schnell eine 'Frau Hökendorf'."""
    text = text or ""
    treffer = KONTAKT_RE.search(text)
    if treffer:
        anrede = treffer.group(1).strip().rstrip("n")
        return f"{anrede} {treffer.group(2).strip()}"
    # Zweiter Versuch: irgendeine Anrede im Umfeld einer Telefonnummer
    tel = TELEFON_RE.search(text)
    if tel:
        umfeld = text[max(0, tel.start() - 260):tel.start()]
        namen = ANREDE_RE.findall(umfeld)
        if namen:
            anrede, name = namen[-1]
            return f"{anrede.rstrip('n')} {name.strip()}"
    return None


def telefon_finden(text):
    treffer = TELEFON_RE.search(text or "")
    if not treffer:
        return None
    nummer = re.sub(r"\s{2,}", " ", treffer.group(1)).strip(" .-/")
    ziffern = re.sub(r"\D", "", nummer)
    return nummer if 7 <= len(ziffern) <= 16 else None


def email_finden(text):
    """Bewerbungsadresse. Postfach-Adressen sind brauchbarer als persönliche."""
    treffer = EMAIL_RE.findall(text or "")
    if not treffer:
        return None
    bevorzugt = [m for m in treffer
                 if re.search(r"bewerb|personal|karriere|jobs?@|stellen", m, re.I)]
    gewaehlt = (bevorzugt or treffer)[0]
    return gewaehlt.rstrip(".,;:)")


def ort_finden(text, rueckfall=None):
    treffer = ORT_RE.search(text or "")
    if treffer:
        ort = treffer.group(1).strip(" .,;")
        if 2 < len(ort) < 42:
            return ort
    return rueckfall


# ----------------------------------------------------------------------------------
# PASSUNGS-PUNKTE
#
# Die Punkte sortieren die Liste. Sie ersetzen kein Urteil, sie sparen Lesezeit:
# oben steht, was man zuerst ansehen sollte.
# ----------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------
# PASSUNGS-PUNKTE
#
# Die Punkte sortieren die Liste. Sie ersetzen kein Urteil, sie sparen Lesezeit:
# oben steht, was man zuerst ansehen sollte.
#
# WIE VIELE Punkte es wofuer gibt, steht in der Gewichtung (gewichtung.json,
# bearbeitbar im Fenster unter „Gewichtung"). Wer gerade auf kurze Wege aus ist,
# dreht die Regionen hoch; wer aufs Entgelt schaut, die Entgeltgruppen.
# ----------------------------------------------------------------------------------

LEITUNG_RE = re.compile(
    r"leit(ung|er|erin)|referatsleit|teamleit|gruppenleit|abteilungsleit|"
    r"sachgebietsleit|geschaeftsstellenleit|geschäftsstellenleit|stabsstelle",
    re.IGNORECASE)


def punkte_berechnen(daten, gewichte=None):
    """Passungs-Punkte. Die Begruendung wird mitgeliefert, damit nachvollziehbar
    bleibt, warum eine Stelle oben steht."""
    g = gewichte or GEWICHTE or konfiguration.STANDARD_GEWICHTE
    punkte, gruende = 0, []

    felder = daten.get("felder") or []
    if isinstance(felder, str):
        felder = json.loads(felder or "[]")

    # 1. Berufsfeld-Staerke (fachlich das Wichtigste)
    grenze = int(g.get("berufsfeld_hoechstens", 9))
    feldpunkte = min(int(daten.get("feld_punkte") or 0), grenze)
    if feldpunkte:
        punkte += feldpunkte
        gruende.append(f"Berufsfeld-Treffer: +{feldpunkte}")

    # 2. Mehrere Felder gleichzeitig = breit passend
    mehrere = int(g.get("mehrere_felder", 0))
    if len(felder) >= 2 and mehrere:
        punkte += mehrere
        gruende.append(f"passt auf mehrere Berufsfelder: {mehrere:+d}")

    # 3. Region — der Regler fuer „Naehe"
    region = daten.get("region") or "Sonstige"
    wert = int(g.get("regionen", {}).get(region,
                                         g.get("regionen", {}).get("Sonstige", 1)))
    if wert:
        punkte += wert
        gruende.append(f"Region {region}: {wert:+d}")

    # 4. Sektor
    sektor = daten.get("sektor") or "privat"
    wert = int(g.get("sektoren", {}).get(sektor, 1))
    if wert:
        punkte += wert
        gruende.append(f"{SEKTOREN.get(sektor, sektor)}: {wert:+d}")

    # 5. Entgelt — der Regler fuer „Bezahlung"
    entgelt = daten.get("entgelt")
    if entgelt:
        wert = g.get("entgelt", {}).get(entgelt)
        if wert is not None and int(wert):
            punkte += int(wert)
            gruende.append(f"{entgelt}: {int(wert):+d}")

    # 6. Befristung
    if daten.get("befristung") == "unbefristet":
        wert = int(g.get("unbefristet", 0))
        if wert:
            punkte += wert
            gruende.append(f"unbefristet: {wert:+d}")
    elif daten.get("befristung") == "befristet":
        wert = int(g.get("befristet", 0))
        if wert:
            punkte += wert
            gruende.append(f"befristet: {wert:+d}")

    # 7. Leitungsanteil im Titel
    wert = int(g.get("leitungsfunktion", 0))
    if wert and LEITUNG_RE.search(daten.get("titel") or ""):
        punkte += wert
        gruende.append(f"Leitungs- oder Stabsfunktion: {wert:+d}")

    # 8. Eine konkrete Frist hilft bei der Planung
    wert = int(g.get("frist_vorhanden", 0))
    if wert and daten.get("frist"):
        punkte += wert
        gruende.append(f"Frist angegeben: {wert:+d}")

    return max(0, punkte), gruende


def einordnen(titel, volltext="", url="", arbeitgeber=None):
    """Vollständige Einordnung einer Ausschreibung.

    Gibt None zurück, wenn die Stelle verworfen wird — mit Grund im zweiten
    Rückgabewert, damit sich der Filter nachvollziehen lässt."""
    titel = aufraeumen(titel)
    arbeitgeber = arbeitgeber or {}
    pruefgrundlage = titel + "\n" + (volltext or "")

    grund = ist_ausgeschlossen(titel)
    if grund:
        return None, f"ausgeschlossen durch '{grund}' im Titel"

    # Im Volltext schließen wir nur bei sehr eindeutigen Begriffen aus, sonst
    # fliegen zu viele Stellen raus, die den Begriff nur beiläufig nennen.
    treffer = felder_bestimmen(pruefgrundlage)
    if not treffer:
        return None, "kein Berufsfeld erkannt"

    # Der Titel wiegt doppelt: eine Stelle, deren Feld nur im Fließtext auftaucht,
    # ist meist keine Stelle in diesem Feld.
    titel_treffer = felder_bestimmen(titel)
    if titel_treffer:
        haupt, feld_punkte = titel_treffer[0][0], titel_treffer[0][1] + 2
    else:
        haupt, feld_punkte = treffer[0][0], max(1, treffer[0][1] - 2)

    daten = {
        "titel": titel,
        "felder": [f for f, _, _ in treffer],
        "feld_haupt": haupt,
        "feld_punkte": feld_punkte,
        "arbeitgeber": arbeitgeber.get("name"),
        "sektor": arbeitgeber.get("sektor"),
        "region": arbeitgeber.get("region"),
        "url": url,
        "frist": frist_finden(volltext),
        "eintritt": eintritt_finden(volltext),
        "entgelt": entgelt_finden(pruefgrundlage),
        "umfang": umfang_finden(volltext),
        "befristung": befristung_finden(volltext),
        "kontakt": kontakt_finden(volltext),
        "telefon": telefon_finden(volltext),
        "email": email_finden(volltext),
        "ort": ort_finden(volltext, arbeitgeber.get("ort")),
        "volltext": volltext or "",
    }
    daten["punkte"], daten["punkte_gruende"] = punkte_berechnen(daten)
    return daten, None
