# -*- coding: utf-8 -*-
"""Arbeitgeber-Register für den Stellenradar.

Drei Suchräume, die zusammen den Anforderungsbereich abdecken:

  1. Öffentlicher Dienst Brandenburg / Raum Potsdam  (aus der Berufsfeld-Analyse)
  2. Öffentlicher Dienst Berlin, Wissenschaft und Bund
  3. Public-Sector-Beratung und Privatwirtschaft

Dazu kommen die zentralen Portale als eigene Quellen (siehe `quelle_interamt.py`):
Interamt bündelt mit einer Umkreissuche um Potsdam rund 830 Stellen des
öffentlichen Dienstes in Berlin, Potsdam und Umgebung — mehr als alle
Einzelseiten zusammen.

Felder je Eintrag:

  name     Anzeigename
  url      Übersichtsseite mit den Ausschreibungen
  sektor   Schlüssel aus einordnung.SEKTOREN
  region   steuert die Passungs-Punkte (siehe einordnung.REGION_PUNKTE)
  ort      Rückfallwert, wenn die Ausschreibung keinen Dienstort nennt
  gruppe   Gliederung in Oberfläche und Bericht
  tief     True = Seite zeigt ihren Inhalt erst im Browser

ALLE URLs wurden am 11.11.2026 mit `pruefe_arbeitgeber.py` abgerufen. Seiten,
die nicht erreichbar waren oder keine Ausschreibungen zeigen, stehen unten in
NICHT_AUFGENOMMEN mit Begründung — lieber ein ehrlich kurzes Register als
Einträge, die dauerhaft null Treffer liefern.
"""

GEPRUEFT_AM = "11.11.2026"

# ----------------------------------------------------------------------------------
# 1 · ÖFFENTLICHER DIENST BRANDENBURG / RAUM POTSDAM
# ----------------------------------------------------------------------------------

_BB = [
    # Zentrales Landesportal und Ministerien
    ("Karriere in Brandenburg (Landesportal)", "https://karriere-in-brandenburg.de/stellenangebote", "Brandenburg", "Potsdam", False),
    ("Ministerium des Innern und für Kommunales", "https://mik.brandenburg.de/mik/de/ministerium/beruf-und-karriere/stellenangebote/", "Potsdam", "Potsdam", False),
    ("Ministerium der Justiz und für Digitalisierung", "https://mdjd.brandenburg.de/mdjd/de/ministerium/stellenausschreibungen/", "Potsdam", "Potsdam", False),
    ("Ministerium der Finanzen", "https://mdf.brandenburg.de/mdf/de/service/stellenausschreibungen/", "Potsdam", "Potsdam", False),
    ("Ministerium für Wirtschaft, Energie und Klimaschutz", "https://mwaek.brandenburg.de/de/stellen-im-mweke/brandenburg_06.c.900549.de", "Potsdam", "Potsdam", False),
    ("Ministerium für Arbeit, Soziales, Gesundheit", "https://masgz.brandenburg.de/masgz/de/ministerium/stellenausschreibungen/", "Potsdam", "Potsdam", False),
    ("Ministerium für Infrastruktur und Landesplanung", "https://mil.brandenburg.de/mil/de/ministerium/karriere-im-mil/", "Potsdam", "Potsdam", False),
    ("Ministerium für Landwirtschaft, Umwelt und Verbraucherschutz", "https://mleuv.brandenburg.de/mleuv/de/aktuelles/stellenangebote/", "Potsdam", "Potsdam", False),
    ("Ministerium für Bildung, Jugend und Sport", "https://mbjs.brandenburg.de/einstellungen.html", "Potsdam", "Potsdam", False),
    ("Ministerium für Wissenschaft, Forschung und Kultur", "https://mwfk.brandenburg.de/mwfk/de/ministerium/stellenausschreibungen/", "Potsdam", "Potsdam", False),
    # Landesbehörden und Landesbetriebe
    ("ZIT-BB (Landes-IT-Dienstleister)", "https://zit-bb.brandenburg.de/zit-bb/de/karriere/fachkraefte/stellenausschreibungen/", "Potsdam", "Potsdam", False),
    ("Landtag Brandenburg", "https://www.landtag.brandenburg.de/de/landtag_kennenlernen/gebaeude_und_verwaltung/karriere_im_landtag/24468", "Potsdam", "Potsdam", False),
    ("Landesrechnungshof Brandenburg", "https://www.lrh-brandenburg.de/lrh/de/karriere/", "Potsdam", "Potsdam", False),
    ("Investitionsbank des Landes Brandenburg", "https://www.ilb-karriere.de/", "Potsdam", "Potsdam", False),
    ("Landesamt für Umwelt", "https://lfu.brandenburg.de/lfu/de/stellenangebote/", "Potsdam", "Potsdam", False),
    ("Landesamt für Arbeitsschutz, Verbraucherschutz und Gesundheit", "https://lavg.brandenburg.de/lavg/de/karriere/aktuelle-stellenangebote/", "Potsdam", "Potsdam", False),
    ("Landesvermessung und Geobasisinformation", "https://geobasis-bb.de/lgb/de/karriere/stellenangebote/", "Potsdam", "Potsdam", False),
    ("Brandenburgischer Landesbetrieb für Liegenschaften", "https://blb.brandenburg.de/blb/de/karriere/stellenangebote/", "Potsdam", "Potsdam", False),
    ("Landesbetrieb Straßenwesen", "https://www.ls.brandenburg.de/ls/de/ueber-uns/karriere/", "Brandenburg", "Hoppegarten", False),
    ("Amt für Statistik Berlin-Brandenburg", "https://www.statistik-berlin-brandenburg.de/karriere", "Potsdam", "Potsdam", False),
    # Kommunales im Raum Potsdam
    ("Landeshauptstadt Potsdam", "https://bewerberportal-lhp.dikom-bb.de/bewerber-web/?companyEid=LHP&tenant=&lang=D#positions", "Potsdam", "Potsdam", True),
    ("Landkreis Potsdam-Mittelmark", "https://www.potsdam-mittelmark.de/de/karriere/uebersicht", "Potsdam-Mittelmark", "Bad Belzig", False),
    ("Stadt Werder (Havel)", "https://www.werder-havel.de/politik-rathaus/service/stellenangebote/", "Werder", "Werder (Havel)", False),
    ("Stadtwerke Potsdam / EWP", "https://karriere.ewp-potsdam.de/", "Potsdam", "Potsdam", False),
    ("ProPotsdam", "https://karriere.propotsdam.de/jobs", "Potsdam", "Potsdam", True),
    ("Klinikum Ernst von Bergmann (Verwaltung)", "https://www.evb-gesundheit.de/stellenanzeigen", "Potsdam", "Potsdam", False),
    ("Studierendenwerk West:Brandenburg", "https://www.stwwb.de/wir-ueber-uns/karriere-im-studierendenwerk", "Potsdam", "Potsdam", False),
    ("DIKOM Brandenburg (kommunale IT)", "https://www.dikom-bb.de/karriere/", "Brandenburg", "Potsdam", False),
    # Körperschaften, Kammern, Verbände
    ("IHK Potsdam", "https://www.ihk.de/potsdam/servicemarken/ueber-uns/karriere-und-jobs-3297300", "Potsdam", "Potsdam", False),
    ("Handwerkskammer Potsdam", "https://www.hwk-potsdam.de/artikel/aktuelle-stellenangebote-9,0,6188.html", "Potsdam", "Potsdam", False),
    ("Kassenärztliche Vereinigung Brandenburg", "https://kvbb-karriere.dvinci.de/de/jobs", "Potsdam", "Potsdam", False),
    ("AOK Nordost", "https://www.aok.de/karriere/stellenangebote/", "Brandenburg", "Potsdam", False),
    ("Städte- und Gemeindebund Brandenburg", "https://www.stgb-brandenburg.de/wir-ueber-uns/stellenangebote/", "Potsdam", "Potsdam", False),
    ("DigitalAgentur Brandenburg", "https://www.digital-agentur.de/karriere/", "Potsdam", "Potsdam", False),
    ("Wirtschaftsförderung Land Brandenburg (WFBB)", "https://www.wfbb.de/die-wfbb/karriere", "Potsdam", "Potsdam", False),
]

_BB_WISS = [
    ("Universität Potsdam", "https://www.uni-potsdam.de/de/verwaltung/dezernat3/stellenausschreibungen", "Potsdam", "Potsdam", False),
    ("Fachhochschule Potsdam", "https://www.fh-potsdam.de/hochschule-karriere/karriere/stellenangebote-fh-potsdam", "Potsdam", "Potsdam", False),
    ("Filmuniversität Babelsberg", "https://www.filmuniversitaet.de/filmuni/aktuelles/stellenausschreibungen", "Babelsberg", "Potsdam-Babelsberg", False),
    ("Hasso-Plattner-Institut", "https://jobs.plattnerfoundation.org/HPI/search", "Babelsberg", "Potsdam-Babelsberg", True),
    ("GFZ Helmholtz-Zentrum für Geoforschung", "https://www.gfz.de/karriere/stellenangebote", "Potsdam", "Potsdam", False),
    ("Potsdam-Institut für Klimafolgenforschung", "https://www.pik-potsdam.de/de/aktuelles/stellen", "Potsdam", "Potsdam", False),
    ("Leibniz-Institut für Astrophysik", "https://www.aip.de/de/career/jobs/", "Potsdam", "Potsdam", False),
    ("Deutsches Institut für Ernährungsforschung", "https://www.dife.de/karriere/stellenangebote/", "Potsdam", "Potsdam-Rehbrücke", False),
    ("Fraunhofer IAP", "https://www.iap.fraunhofer.de/de/stellen.html", "Potsdam", "Potsdam", False),
    ("Max-Planck-Gesellschaft (Jobboard)", "https://www.mpg.de/jobboard", "Bundesweit", "verschieden", False),
    ("Leibniz-Gemeinschaft (Stellenportal)", "https://www.leibniz-gemeinschaft.de/karriere/stellenportal", "Bundesweit", "verschieden", False),
]

# ----------------------------------------------------------------------------------
# 2 · ÖFFENTLICHER DIENST BERLIN
# ----------------------------------------------------------------------------------

_BE = [
    # Zentrales Portal — deckt Senatsverwaltungen und Bezirksämter gemeinsam ab
    ("Karriereportal Land Berlin", "https://www.berlin.de/karriereportal/stellensuche/", "Berlin", "Berlin", False),
    # Landesbetriebe, Anstalten, landeseigene Gesellschaften
    ("ITDZ Berlin (Landes-IT-Dienstleister)", "https://www.itdz-berlin.de/karriere/stellenangebote/", "Berlin", "Berlin", False),
    ("BIM Berliner Immobilienmanagement", "https://www.bim-berlin.de/karriere/stellenangebote", "Berlin", "Berlin", False),
    ("Berlin Partner für Wirtschaft und Technologie", "https://www.berlin-partner.de/ueber-uns/karriere", "Berlin", "Berlin", False),
    ("Investitionsbank Berlin", "https://www.ibb.de/de/ueber-uns/karriere/karriere.html", "Berlin", "Berlin", False),
    ("Technologiestiftung Berlin", "https://www.technologiestiftung-berlin.de/ueber-uns/jobs", "Berlin", "Berlin", False),
    ("Vivantes (Verwaltung)", "https://karriere.vivantes.de/stellenangebote", "Berlin", "Berlin", False),
    ("Charité (Verwaltung)", "https://karriere.charite.de/stellenangebote/", "Berlin", "Berlin", False),
    ("Gewobag", "https://www.gewobag.de/ueber-uns/jobs-und-karriere/", "Berlin", "Berlin", False),
    ("degewo", "https://www.degewo.de/wir-sind-degewo/karriere/berufserfahrene", "Berlin", "Berlin", False),
    ("HOWOGE", "https://karriere.howoge.de/", "Berlin", "Berlin", False),
    # Körperschaften und Verbände mit Sitz Berlin
    ("Deutsche Rentenversicherung Bund", "https://www.deutsche-rentenversicherung.de/DRV/DE/Ueber-uns-und-Presse/Karriere/karriere_node.html", "Berlin", "Berlin", False),
    ("Kassenärztliche Bundesvereinigung", "https://www.karriere.kbv.de/", "Berlin", "Berlin", False),
    ("GKV-Spitzenverband", "https://www.gkv-spitzenverband.de/gkv_spitzenverband/karriere/stellenausschreibungen/stellenausschreibungen.jsp", "Berlin", "Berlin", False),
    ("Stiftung Preußischer Kulturbesitz", "https://www.preussischer-kulturbesitz.de/ueber-uns/karriere.html", "Berlin", "Berlin", False),
    ("Handwerkskammer Berlin", "https://www.hwk-berlin.de/artikel/stellenausschreibungen-91,348,153.html", "Berlin", "Berlin", False),
]

_BE_WISS = [
    ("Humboldt-Universität zu Berlin", "https://www.hu-berlin.de/universitaet/arbeiten-an-der-hu/stellenangebote", "Berlin", "Berlin", True),
    ("Freie Universität Berlin", "https://www.fu-berlin.de/universitaet/beruf-karriere/jobs/", "Berlin", "Berlin", False),
    ("Technische Universität Berlin", "https://www.jobs.tu-berlin.de/stellenausschreibungen", "Berlin", "Berlin", False),
    ("HTW Berlin", "https://www.htw-berlin.de/karriere/jobs/", "Berlin", "Berlin", False),
    ("Hochschule für Wirtschaft und Recht Berlin", "https://www.hwr-berlin.de/hwr-berlin/stellenangebote/", "Berlin", "Berlin", False),
    ("Berliner Hochschule für Technik", "https://www.bht-berlin.de/jobs", "Berlin", "Berlin", False),
    ("Wissenschaftszentrum Berlin (WZB)", "https://www.wzb.eu/de/jobs", "Berlin", "Berlin", False),
    ("DIW Berlin", "https://www.diw.de/de/diw_01.c.100300.de/jobs.html", "Berlin", "Berlin", False),
]

# ----------------------------------------------------------------------------------
# 3 · BUND MIT SITZ BERLIN
#     Die meisten Bundesbehörden schreiben über Interamt aus. Hier stehen nur
#     die Häuser mit eigener, erreichbarer Stellenseite.
# ----------------------------------------------------------------------------------

_BUND = [
    ("Bundesministerium des Innern", "https://www.bmi.bund.de/DE/service/stellenangebote/stellenangebote-node.html", "Berlin", "Berlin", False),
    ("Bundesverwaltungsamt", "https://www.bva.bund.de/DE/Karriere/karrierebva_node.html", "Bundesweit", "Köln/Berlin", False),
    ("Robert Koch-Institut", "https://www.rki.de/DE/Institut/Das-RKI/Karriere/karriere-node.html", "Berlin", "Berlin", False),
    ("Bundesinstitut für Arzneimittel und Medizinprodukte", "https://www.bfarm.de/DE/Das-BfArM/Karriere-im-BfArM/Stellenangebote/_node.html", "Bundesweit", "Bonn", False),
    ("DigitalService GmbH des Bundes", "https://digitalservice.bund.de/karriere", "Berlin", "Berlin", False),
    ("Zentrum für Digitale Souveränität (ZenDiS)", "https://zendis.de/karriere", "Bundesweit", "Bochum/Berlin", True),
]

# ----------------------------------------------------------------------------------
# 4 · PUBLIC-SECTOR-BERATUNG UND PRIVATWIRTSCHAFT
#     Beratungshäuser, die für die öffentliche Verwaltung arbeiten. Für das
#     Profil besonders interessant: Digitalisierung, Prozess- und
#     Anforderungsmanagement sind dort das Tagesgeschäft.
# ----------------------------------------------------------------------------------

_BERATUNG = [
    # Spezialisten für die öffentliche Hand
    ("PD – Berater der öffentlichen Hand", "https://karriere.pd-g.de/", "Berlin", "Berlin", False),
    ("INFORA GmbH", "https://www.infora.de/karriere/", "Berlin", "Berlin", False),
    ("init AG (]init[)", "https://www.init.de/karriere", "Berlin", "Berlin", False),
    ("Materna Information & Communications", "https://karriere.materna.de/", "Berlin", "Berlin", False),
    ("msg systems / msg public sector", "https://www.msg.group/karriere/stellenangebote", "Berlin", "Berlin", False),
    ("Prognos AG", "https://www.prognos.com/de/karriere", "Berlin", "Berlin", False),
    ("IFOK GmbH", "https://www.ifok.de/karriere/", "Berlin", "Berlin", False),
    ("Zebralog", "https://www.zebralog.de/jobs", "Berlin", "Berlin", False),
    ("Dataport AöR", "https://karriere.dataport.de/", "Berlin", "Altenholz/Berlin", False),
    ("Telekom MMS", "https://www.telekom-mms.com/karriere/stellenboerse", "Berlin", "Berlin", False),
    ("Detecon International", "https://www.detecon.com/en/career", "Berlin", "Berlin", False),
    # Große Beratungen mit Public-Sector-Einheit
    ("BearingPoint", "https://www.bearingpoint.com/de-de/karriere/stellenangebote/", "Berlin", "Berlin", False),
    ("EY Deutschland", "https://careers.ey.com/ey/search/", "Berlin", "Berlin", False),
    ("PwC Deutschland", "https://jobs.pwc.de/de/jobsuche", "Berlin", "Berlin", False),
    ("Atos / Eviden Deutschland", "https://jobs.atos.net/search/", "Berlin", "Berlin", False),
    ("Bechtle", "https://www.bechtle.com/karriere", "Berlin", "Berlin", False),
    ("SAP Deutschland", "https://jobs.sap.com/search/?q=&locationsearch=Berlin", "Berlin", "Berlin", False),
]

# ----------------------------------------------------------------------------------
# NICHT AUFGENOMMEN — mit Begründung, damit die Lücken bekannt sind
# ----------------------------------------------------------------------------------

NICHT_AUFGENOMMEN = [
    ("Mittelbrandenburgische Sparkasse", "Karriereseite nicht auffindbar, Startseite verweist nur auf Filialen"),
    ("Berliner Sparkasse", "wie MBS: keine erreichbare Stellenübersicht gefunden"),
    ("Berliner Stadtreinigung (BSR)", "Stellensuche nur als Suchmaske ohne feste Adresse"),
    ("Berliner Verkehrsbetriebe (BVG)", "Karriereportal nicht auffindbar"),
    ("Berliner Wasserbetriebe", "Karriereseite liefert keine Ausschreibungsliste"),
    ("IHK Berlin", "keine Stellenübersicht gefunden"),
    ("Helmholtz-Gemeinschaft (jobs.helmholtz.de)", "Namensauflösung schlägt fehl"),
    ("Bundesministerium der Finanzen / BMBF / BMAS / BMDV / BMWK", "schreiben über Interamt aus, keine eigene Liste"),
    ("Bundesdruckerei-Gruppe", "Namensauflösung schlägt fehl"),
    ("govdigital eG", "keine Karriereseite gefunden"),
    ("Bundesrechnungshof", "keine erreichbare Stellenübersicht"),
    ("Umweltbundesamt", "Stellenseite umgezogen, neue Adresse nicht auffindbar"),
    ("Bundesagentur für Arbeit", "eigene Suchmaschine; der öffentliche Dienst dort ist über Interamt abgedeckt"),
    ("Nortal AG", "Karriereseite ohne maschinenlesbare Stellenliste"),
    ("Cassini Consulting", "Stellenliste nur über eingebettetes Portal ohne feste Adresse"),
    ("Civity Management Consultants", "keine Stellenliste erkennbar"),
    ("Ramboll Management Consulting", "Karriereseite ohne Stellenliste"),
    ("Capgemini, Accenture, Deloitte, KPMG, Kienbaum", "Stellensuche nur über JavaScript-Portale ohne feste Adresse"),
    ("adesso SE, T-Systems, IBM Deutschland", "wie oben: Suchmaske statt Liste"),
    ("Stadt Werder, Studierendenwerk u. a.", "aufgenommen, zeigten beim Prüflauf aber keine offenen Stellen"),
]


def _bauen():
    eintraege = []
    for liste, sektor, gruppe in (
            (_BB, "oed_bb", "Öffentlicher Dienst Brandenburg"),
            (_BB_WISS, "wissenschaft", "Wissenschaft Potsdam"),
            (_BE, "oed_be", "Öffentlicher Dienst Berlin"),
            (_BE_WISS, "wissenschaft", "Wissenschaft Berlin"),
            (_BUND, "oed_bund", "Bund"),
            (_BERATUNG, "beratung", "Public-Sector-Beratung")):
        for name, url, region, ort, tief in liste:
            eintraege.append({
                "name": name, "url": url, "sektor": sektor, "region": region,
                "ort": ort, "gruppe": gruppe, "tief": tief,
            })
    return eintraege


ARBEITGEBER = _bauen()

GRUPPEN = ["Öffentlicher Dienst Brandenburg", "Wissenschaft Potsdam",
           "Öffentlicher Dienst Berlin", "Wissenschaft Berlin", "Bund",
           "Public-Sector-Beratung"]


def nach_gruppe():
    ordnung = {g: [] for g in GRUPPEN}
    for eintrag in ARBEITGEBER:
        ordnung.setdefault(eintrag["gruppe"], []).append(eintrag)
    return ordnung


def finden(name):
    for eintrag in ARBEITGEBER:
        if eintrag["name"] == name:
            return eintrag
    return None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{len(ARBEITGEBER)} Arbeitgeber im Register (geprüft {GEPRUEFT_AM})\n")
    for gruppe, eintraege in nach_gruppe().items():
        tief = sum(1 for e in eintraege if e["tief"])
        print(f"  {gruppe:36} {len(eintraege):3}  (davon {tief} mit Browser)")
    print(f"\n{len(NICHT_AUFGENOMMEN)} Einträge bewusst nicht aufgenommen:")
    for name, grund in NICHT_AUFGENOMMEN:
        print(f"  · {name[:46]:48} {grund}")
