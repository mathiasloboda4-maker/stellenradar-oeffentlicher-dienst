# Abhängigkeiten und ihre Lizenzen

Der Stellenradar selbst steht unter der **MIT-Lizenz** (siehe `LICENSE`).

## Mitbenutzt

| Paket | Lizenz | Wofür |
|---|---|---|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | BSD 3-Clause | die Abrufschicht für alle Portale, inklusive Browser-Modus für JavaScript-Seiten |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD 3-Clause | setzt nachträglich die Metadaten der erzeugten PDFs |
| Tkinter | Python Software Foundation License | die Oberfläche (Teil der Standardbibliothek) |
| SQLite | Public Domain | die Datenbank (Teil der Standardbibliothek) |

Alle vier sind mit MIT verträglich.

## Optional, nicht mitgeliefert

| Werkzeug | Lizenz | Wofür |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) | MIT | das KI-Briefing der Favoriten |
| Chrome oder Edge | — | PDF-Erzeugung im Headless-Modus |

**Ollama wird nur angesprochen, wenn es lokal läuft.** Das Programm
funktioniert vollständig ohne — die Favoriten zeigen dann die Eckdaten ohne
KI-Einschätzung. Es gibt keine Cloud-KI und keine Übertragung von
Profildaten nach außen.

Ohne Chrome oder Edge entstehen keine Steckbriefe und kein Archiv; alles
andere läuft.

## Bewusst nicht verwendet

| Paket | Lizenz | Warum nicht |
|---|---|---|
| PyMuPDF | **AGPL-3.0** | Hätte dieses Programm unter die AGPL gezwungen. Für die PDF-Erzeugung genügt Chrome oder Edge im Headless-Modus. |

Wer eine Abhängigkeit ergänzt, prüft bitte zuerst ihre Lizenz — siehe
`CONTRIBUTING.md`.
