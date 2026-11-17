# Konzept

Warum der Stellenradar so gebaut ist, wie er gebaut ist — und was man ändern
muss, um ihn auf ein anderes Profil, eine andere Region oder eine andere
Branche zu drehen.

Wer das Programm nur bedienen will, liest `README.md`. Wer daran arbeitet,
liest zusätzlich `UEBERGABE.md` (Modultabelle, Datenmodell, Stolperfallen).
Dieses Papier erklärt die Entscheidungen dahinter.

---

## 1. Das Problem

Stellenportale des öffentlichen Dienstes haben drei Eigenschaften gemeinsam,
und jede einzelne macht die Suche mühsam:

**Sie sind zahlreich und verstreut.** Es gibt kein Portal, auf dem alles
steht. Ein Landesministerium schreibt über Interamt aus, eine Hochschule über
ihr eigenes System, ein kommunaler Betrieb über ein Bewerberportal, ein
Beratungshaus über die eigene Karriereseite. Wer nichts übersehen will,
besucht zwei Dutzend Seiten — jede Woche.

**Sie sind schlecht durchsuchbar.** Die Suchmasken kennen Schlagworte, aber
nicht das, wonach man eigentlich sucht. „Anforderungsmanagement" findet die
Stellen, in deren Titel das Wort steht — nicht die, in denen es als dritter
Aufzählungspunkt der Aufgabenbeschreibung auftaucht. Und eine Suche über
mehrere Portale hinweg gibt es nicht.

**Sie nehmen Ausschreibungen nach Fristende offline.** Oft noch am selben Tag.
Wer sich beworben hat und drei Wochen später zum Gespräch eingeladen wird,
findet den Ausschreibungstext nicht mehr — genau den Text, auf den sich jede
Frage im Gespräch beziehen wird.

Dazu kommt das eigentliche Problem einer Bewerbungsphase: **Übersicht
behalten.** Welche Stelle habe ich schon angesehen? Welche verworfen und
warum? Wo läuft die Frist? Wo habe ich mich beworben und wann sollte ich
nachfassen? Eine Tabellenkalkulation leistet das, aber niemand pflegt sie
durch.

---

## 2. Was der Stellenradar deshalb tut

Ein Suchlauf, drei Quellen, ein Ergebnis: eine sortierte Arbeitsliste.

```
 Quellen                Einordnung            Ablage              Arbeiten mit
 ─────────              ──────────            ──────              ────────────
 Interamt          ┐                      ┌ SQLite              Dashboard
 Karriereportal    ├──► Ausschluss ──►    │ (36 Spalten)        Fristen-Ampel
   Berlin          │    Berufsfeld   ──►  ├ Archiv-PDF          Triage
 93 Arbeitgeber-   │    Eckdaten          │ (Seitenkopie)       Favoriten + KI
   seiten          ┘    Punkte            └ Steckbrief-PDF      Verlauf
 + Erfassung
   von Hand
```

Die vier Bausteine, in der Reihenfolge ihrer Wichtigkeit:

1. **Finden, was andere Suchen übersehen** — über den Volltext, nicht über den
   Titel.
2. **Wegwerfen, was nicht passt** — so hart, dass die Liste durchsehbar bleibt.
3. **Sichern, was verschwindet** — jede Ausschreibungsseite als PDF, sofort.
4. **Den Prozess führen** — von „neu" über „vorgemerkt" bis „beworben", mit
   Fristen und Wiedervorlage.

---

## 3. Die Entscheidungen

### 3.1 Lieber zu viel wegwerfen als zu wenig

**Die Grundregel des Filters: Kein Treffer in einem Berufsfeld heißt
verworfen.** Eine Stelle, deren Volltext keines der hinterlegten Stichworte
enthält, wird gar nicht erst gespeichert.

Das ist eine bewusste Entscheidung gegen Vollständigkeit. Ein gemessener Lauf
prüfte 901 Ausschreibungen und behielt 34. Wären es 300 gewesen, hätte sie
niemand durchgesehen — und eine Liste, die man nicht durchsieht, ist
schlechter als keine.

Der Preis: Man übersieht Stellen, die passen würden, aber ungewöhnlich
formuliert sind. Dagegen helfen drei Dinge: die Stichwortlisten sind im
Fenster erweiterbar, `suche.py --nachfiltern` prüft bereits gespeicherte
Stellen gegen die aktuellen Regeln, und Funde aus anderen Kanälen lassen sich
**von Hand erfassen** — die umgehen den Filter vollständig.

### 3.2 Punkte sortieren, sie entscheiden nicht

Jede Stelle bekommt Punkte: für die Region, die Entgeltgruppe, den Sektor, ein
unbefristetes Verhältnis, Leitungsverantwortung, Treffer in mehreren
Berufsfeldern. Die Punkte legen die **Reihenfolge** fest, nicht die Auswahl.
Verworfen wird nur, was durch den Stichwortfilter fällt.

Und: **die Gewichtung gehört der Person, nicht dem Programm.** Ob Nähe mehr
zählt als Bezahlung, ändert sich mit der Lebenslage. Deshalb steht sie in
`gewichtung.json`, ist im Fenster einstellbar (mit vier Schnellvorlagen), und
nach dem Speichern wird der gesamte Bestand neu bewertet.

### 3.3 Das Profil steht nicht im Code

Drei JSON-Dateien neben dem Programm, alle drei im Fenster pflegbar, alle drei
in `.gitignore`:

| Datei | Inhalt |
|---|---|
| `profil.json` | Name, Abschluss, Wohnort, Werdegang, Stärken, Weiterbildungen |
| `berufsfelder.json` | je Berufsfeld die eigenen Kompetenzen |
| `gewichtung.json` | wie viele Punkte wofür |

In `konfiguration.py` liegt nur ein neutrales Beispiel, das greift, solange
keine eigene Datei da ist. Der Grund ist praktisch und grundsätzlich zugleich:
Nach einer Weiterbildung kommt eine Kompetenz dazu, und dafür soll niemand
eine `.py`-Datei öffnen müssen. Und personenbezogene Daten haben in einem
Repository nichts verloren.

### 3.4 Drei Quellen, drei Techniken

Nicht aus Vorliebe, sondern weil jede Quelle anders gebaut ist.

| Quelle | Technik | Warum |
|---|---|---|
| **Interamt** | Browser (Scrapling `StealthyFetcher`) | Apache Wicket, die Trefferliste entsteht erst per JavaScript. Dafür liefert sie Frist, Entgelt und Entfernung schon in der Liste. Detailseiten dann wieder über einfaches HTTP. |
| **Karriereportal Berlin** | HTTP | Blättert über `?start=0/20/40…`, kein Browser nötig. |
| **93 Arbeitgeberseiten** | HTTP, bei Bedarf Browser | 67 gehen über HTTP, 26 brauchen den Browser. Das Register sagt pro Eintrag, was gilt. |

Dass Interamt eine eigene Quelle ist und nicht ein Eintrag unter 93, hat einen
gemessenen Grund: Die Umkreissuche liefert rund 830 Stellen für Berlin,
Potsdam und das Umland — mehr als alle Arbeitgeberseiten zusammen. Dasselbe
beim Karriereportal Berlin: als eine von 93 Seiten gelesen brachte es genau
einen Treffer, als eigene Quelle 629 Stellen und acht neue passende.

**Die Lehre daraus, für jede Anpassung:** Wo ein großes Portal die Stellen
vieler Arbeitgeber bündelt, lohnt sich eine eigene Quelle mit eigener
Blätterlogik. Eine Karriereseite abzurufen ist billig, aber eine Trefferliste
mit 600 Einträgen holt man damit nicht ab.

### 3.5 Jede Seite wird sofort archiviert

Nach jedem Suchlauf wird jede neu gefundene Ausschreibungsseite als PDF
gesichert — Chrome oder Edge im Headless-Modus, direkt von der URL, 7–10
Sekunden und 0,2–1 MB je Seite. Nichts wird automatisch gelöscht.

Das ist die Antwort auf das Offline-Problem aus Abschnitt 1. Es ist außerdem
der Grund, warum eine Funktion *nicht* gebaut wurde: zu erkennen, dass eine
Stelle vom Portal verschwunden ist. Wenn die Seitenkopie ohnehin vorliegt,
löst sich das Problem von selbst.

Gegenstück: **Wer eine Stelle verwirft, löscht auch ihre Dokumente.** Sonst
wächst ein Archiv aus Unterlagen zu Stellen, die niemanden mehr interessieren.

### 3.6 Die KI darf einschätzen, nicht berichten

Zu jedem Favoriten entsteht ein Briefing für Gespräch und Anschreiben. Es ist
bewusst zweigeteilt:

- **Abschnitte ①–③** (Eckdaten, Ansprechpersonen, hinterlegte Kompetenzen)
  kommen deterministisch aus der Datenbank. Sie stimmen.
- **Abschnitte ④–⑧** (was die Stelle verlangt, wo die Kompetenzen passen, der
  Elefant im Raum, zum Arbeitgeber, Fragen fürs Gespräch) schreibt ein lokales
  Sprachmodell über Ollama.

Der Systemtext bindet das Modell strikt an Ausschreibungstext und Profil.
Nur ein einziger Abschnitt darf Allgemeinwissen verwenden — „Zum Arbeitgeber"
— und der ist als **ungeprüftes Modellwissen gekennzeichnet**.

Der Anlass dafür war konkret: Im Vorläuferprojekt schrieb ein kleines Modell
dem Profil eine „fünfjährige Erfahrung in leitenden Positionen" zu, die
nirgends hinterlegt war. In einem Bewerbungsgespräch wäre das peinlich
geworden.

**Lokal, nicht in der Cloud** — und optional. Bewerbungsunterlagen und
Lebenslaufdaten gehen keine Schnittstelle nach außen. Ohne Ollama zeigen die
Favoriten die Eckdaten ohne Einschätzung; das Programm bleibt vollständig
benutzbar.

### 3.7 Was der Mensch entschieden hat, bleibt unangetastet

Status, Notizen, Favoriten, von Hand erfasste Stellen und der Bewerbungs-
verlauf überleben jeden Suchlauf. **Verworfene Stellen kommen nie wieder** —
sonst müsste man dieselbe Absage jede Woche neu treffen.

Status (`neu`, `vorgemerkt`, `beworben`, `verworfen`) und Favorit sind zwei
getrennte Merkmale, kein gemeinsames. Eine Stelle, auf die man sich beworben
hat, darf weiterhin Favorit sein.

### 3.8 Für einen Rechner, nicht für einen Server

SQLite, Tkinter, eine `.venv` im Projektordner, Start per Desktop-Symbol.
Keine Container, kein Webserver, kein Konto. Die Zielperson ist niemand, der
ein `docker compose up` eintippt — sondern jemand, der einen Ordner kopiert,
auf `INSTALLIEREN.bat` doppelklickt und arbeiten will.

Das prägt auch die Fehlerbehandlung: Ein Fenster-Programm, das per Verknüpfung
startet, stirbt **wortlos**, wenn beim Start etwas schiefgeht. Deshalb
schreibt das Programm `fehler.log`, leitet alle Ausgaben nach `lauf.log` um
und zeigt im Fehlerfall eine Meldung.

---

## 4. Aufbau

18 Module, rund 7.800 Zeilen, alles auf Deutsch — Code, Kommentare,
Variablennamen, Oberfläche.

| Schicht | Module | Aufgabe |
|---|---|---|
| **Quellen** | `quelle_interamt`, `quelle_berlin`, `arbeitgeber`, `holen` | Portale abrufen, Trefferlisten lesen, Volltexte holen |
| **Verstehen** | `einordnung`, `konfiguration` | Ausschluss, Berufsfeld, Eckdaten, Punkte |
| **Ablegen** | `datenbank`, `archiv` | SQLite, Seitenkopien, Tagessicherung |
| **Steuern** | `suche`, `erfassen` | Suchlauf, manuelle Erfassung, Nachbearbeitung |
| **Ausgeben** | `steckbrief`, `briefing`, `ki` | PDF, Briefing, Ollama |
| **Bedienen** | `stellenradar`, `oberflaeche` | neun Ansichten, Bausteine der Oberfläche |
| **Pflegen** | `pruefe_arbeitgeber`, `finde_karriereseite`, `erkunde_portale` | Register warten, nicht Teil des laufenden Programms |

Eine Abhängigkeitsregel: **`einordnung` kennt keine Quelle, und keine Quelle
kennt die Oberfläche.** Eine neue Quelle anzubinden heißt deshalb: ein Modul
nach dem Muster von `quelle_berlin.py` schreiben und es in `suche.py`
einhängen. Mehr nicht.

---

## 5. Das auf etwas anderes drehen

Der Stellenradar ist auf ein Profil im Umfeld Verwaltungsdigitalisierung und
auf Berlin/Brandenburg eingestellt. Das ist der Auslieferungsstand, nicht die
Architektur.

### Anderes Profil, gleiche Region

Reine Bedienung, kein Code:

1. Im Fenster unter **Berufsfelder** die sechs Felder umbenennen, ihre
   Stichworte ersetzen und die eigenen Kompetenzen eintragen.
2. Unter **Gewichtung** die Regionen und Entgeltgruppen anpassen.
3. `suche.py --nachfiltern` und `--punkte-neu` über den Bestand laufen lassen.

Die Stichworte sind nach Gewicht gruppiert: `3` = sehr aussagekräftig,
`2` = deutlich, `1` = schwaches Signal. Sie werden gegen den **kleingeschrie-
benen Volltext ohne Gendersonderzeichen** geprüft (`einordnung.vergleichsform`)
— ein Stichwort muss also nicht in jeder Schreibweise hinterlegt werden.

### Andere Region

1. `quelle_interamt.py`: die Postleitzahl der Umkreissuche austauschen.
2. `quelle_berlin.py`: Das Karriereportal Berlin ist landesspezifisch. Andere
   Länder haben eigene Portale — hier lohnt eine eigene Quelle nach demselben
   Muster.
3. `arbeitgeber.py`: das Register austauschen. **Adressen nicht raten** —
   `finde_karriereseite.py <startseite>` sucht die echte Karriereseite und
   ruft sie zur Probe ab. 38 von 123 geratenen Adressen waren seinerzeit 404.
4. In der Gewichtung die Regionen neu setzen.

### Andere Branche

Dann fällt der öffentliche Dienst als Klammer weg, und damit die Logik um
Entgeltgruppen (`E 11`, `A 13`) und Sektoren. Das steckt in
`einordnung.entgelt_pruefen()` und `SEKTOREN`. Interamt und das Berliner
Portal sind dann nutzlos; es bliebe das Arbeitgeberregister — und dafür ist
das Programm nicht gebaut. Ehrlicher wäre, die Quellenschicht neu zu schreiben
und den Rest zu behalten.

---

## 6. Was bewusst fehlt

Nichts davon ist vergessen worden.

| Fehlt | Warum |
|---|---|
| **Dublettenerkennung** zwischen den Quellen | Gemessen: null Dubletten. Nicht auf Verdacht bauen. Sobald Interamt vollständig läuft, erneut messen. |
| **Erkennen, dass eine Stelle offline ging** | Das Archiv-PDF löst das Problem schon. |
| **Anschreiben erzeugen** | Das Briefing liefert die Bausteine (Anforderung → Beleg, Elefant im Raum). Der Schritt zum fertigen Text fehlt noch. |
| **Bundesagentur-Jobsuche-API** | Wäre der Hebel für die großen Beratungshäuser, antwortet aber mit 403 und braucht einen Schlüssel. |
| **Mehrbenutzerbetrieb, Server, Konto** | Siehe 3.8. Ein Rechner, ein Mensch. |
| **Anti-Bot- oder CAPTCHA-Umgehung** | Nicht gebaut und nicht erwünscht. Scrapling wird benutzt, weil es JavaScript-Seiten liest, nicht weil es Schutzmechanismen aushebelt. |

---

## 7. Arbeitsgrundsätze

Sie stehen in `CLAUDE.md` für KI-Assistenten und gelten genauso für Menschen:

1. **Nichts erfinden.** Keine Arbeitgeber, keine Adressen, keine Zahlen ohne
   Prüfung. Jede Adresse im Register wurde wirklich abgerufen.
2. **Messen statt schätzen.** Wer an der Erkennung etwas ändert, misst die
   Wirkung an echten Daten. `suche.py --nachfiltern` ist dafür da.
3. **Ehrlich berichten.** Wenn eine Seite nichts liefert, steht das so im
   Register — mit Begründung. 20 Arbeitgeber wurden aus benannten Gründen
   *nicht* aufgenommen; diese Liste ist Teil des Codes.
4. **Kommentare erklären das Warum.** Fast jeder Umweg im Code hat einen
   gemessenen Grund, der danebensteht. Wer ihn nicht kennt, baut ihn zurück
   und den Fehler wieder ein.

---

## 8. Danke

Das Programm steht auf [Scrapling](https://github.com/D4Vinci/Scrapling) von
D4Vinci. Ohne dessen Browser-Modus wären drei der Portale unlesbar geblieben —
ein kommunales Bewerberportal etwa lieferte dem Vorläufer null Zeichen und
liefert jetzt 23 Ausschreibungen.
