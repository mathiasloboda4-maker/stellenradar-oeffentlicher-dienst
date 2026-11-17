# -*- coding: utf-8 -*-
"""Anbindung an die lokale KI (Ollama).

Aus dem Vorgängerprojekt übernommene Lehren, die den Code bestimmen:

  · `gemma4:12b` ist ein Reasoning-Modell und liefert **leeren** Inhalt, wenn
    man `think` nicht ausdrücklich abschaltet.
  · Ein zu kleines `num_ctx` schneidet den Prompt **stillschweigend** vorne ab —
    also genau dort, wo Werdegang und Kompetenzen stehen. Deshalb großzügig.
  · Kleine Modelle erfinden Fakten. Deshalb bekommt die KI alles Prüfbare
    vorgegeben und wird ausdrücklich an den Ausschreibungstext gebunden.
  · Modelle geben manchmal ihren Denkprozess als Antwort aus. Der wird erkannt
    und entfernt, statt ihn als Ergebnis auszugeben.

Alles läuft über `/api/chat` — nur dort gibt es den `think`-Schalter.
"""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434"
ZEITLIMIT = 600          # große Modelle auf der CPU brauchen Minuten

# Reihenfolge = Vorliebe. gemma4:12b schreibt am saubersten, qwen3.5:9b ist
# schneller, qwen3.5:2b ist der Notnagel für schwache Rechner.
BEVORZUGT = ["gemma4:12b", "qwen3.5:9b", "qwen3.5:2b"]

OLLAMA_EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                          "Programs", "Ollama", "ollama.exe")


class KiFehler(RuntimeError):
    pass


# ----------------------------------------------------------------------------------
# VERFÜGBARKEIT
# ----------------------------------------------------------------------------------

def erreichbar(zeitlimit=4):
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=zeitlimit):
            return True
    except Exception:
        return False


def modelle():
    """Welche Modelle liegen lokal? Leere Liste, wenn Ollama nicht antwortet."""
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=6) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except Exception:
        return []
    return [m.get("name", "") for m in daten.get("models", [])]


def starten():
    """Versucht, den Ollama-Dienst zu starten. Er läuft nicht immer mit."""
    if erreichbar():
        return True
    if not os.path.exists(OLLAMA_EXE):
        return False
    try:
        subprocess.Popen([OLLAMA_EXE, "serve"],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False
    import time
    for _ in range(20):
        time.sleep(1)
        if erreichbar(zeitlimit=2):
            return True
    return False


def bestes_modell(wunsch=None):
    """Welches Modell wird genommen? Gibt None zurück, wenn keines da ist."""
    vorhanden = modelle()
    if not vorhanden:
        return None
    if wunsch and wunsch in vorhanden:
        return wunsch
    for name in BEVORZUGT:
        if name in vorhanden:
            return name
        # Auch ohne genaue Versionsangabe treffen
        for vorhandenes in vorhanden:
            if vorhandenes.split(":")[0] == name.split(":")[0]:
                return vorhandenes
    return vorhanden[0]


# ----------------------------------------------------------------------------------
# ANFRAGE
# ----------------------------------------------------------------------------------

def fragen(systemtext, anweisung, modell=None, num_ctx=16384, temperatur=0.2,
           melden=None):
    """Stellt eine Anfrage an die lokale KI und gibt den bereinigten Text zurück."""
    modell = modell or bestes_modell()
    if not modell:
        raise KiFehler("Es ist kein Modell installiert. In Ollama zum Beispiel "
                       "`ollama pull gemma4:12b` ausführen.")
    if melden:
        melden(f"{modell} arbeitet — das dauert auf der CPU einige Minuten …")

    anfrage = {
        "model": modell,
        "messages": [
            {"role": "system", "content": systemtext},
            {"role": "user", "content": anweisung},
        ],
        "stream": False,
        # Ohne diesen Schalter antwortet ein Reasoning-Modell mit leerem Inhalt.
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": temperatur,
            "num_ctx": num_ctx,
            "num_predict": 1600,
        },
    }
    rohdaten = json.dumps(anfrage).encode("utf-8")
    bitte = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=rohdaten,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(bitte, timeout=ZEITLIMIT) as antwort:
            ergebnis = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.URLError as fehler:
        raise KiFehler(f"Ollama antwortet nicht ({fehler}). Läuft der Dienst?") from fehler
    except Exception as fehler:
        raise KiFehler(f"{type(fehler).__name__}: {fehler}") from fehler

    text = (ergebnis.get("message") or {}).get("content") or ""
    text = aufraeumen(text)
    if len(text.split()) < 25:
        raise KiFehler(f"{modell} hat nichts Brauchbares geliefert "
                       f"({len(text.split())} Wörter).")
    return text, modell


# ----------------------------------------------------------------------------------
# ANTWORT SÄUBERN
# ----------------------------------------------------------------------------------

DENK_KLAMMER = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
DENK_UEBERSCHRIFT = re.compile(
    r"^\s*(?:thinking process|reasoning|analysis|let me think|思考|"
    r"gedankengang|denkprozess|überlegung)\s*:?.*$",
    re.IGNORECASE | re.MULTILINE)


def aufraeumen(text):
    """Entfernt Denkprozess, Markdown-Rauschen und Rahmen um die Antwort."""
    text = DENK_KLAMMER.sub("", text or "")
    text = DENK_UEBERSCHRIFT.sub("", text)
    # Codeblock-Zäune, in die manche Modelle alles einpacken
    text = re.sub(r"^\s*```[a-z]*\s*$", "", text, flags=re.MULTILINE)
    # Fettschrift-Sternchen, aber Aufzählungszeichen behalten
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Höflichkeitsfloskeln am Anfang
    text = re.sub(r"^\s*(?:hier ist|gerne|natürlich|selbstverständlich)[^\n]{0,80}:\s*\n",
                  "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("Ollama erreichbar:", erreichbar())
    if not erreichbar():
        print("Versuche zu starten …", starten())
    print("Modelle:", modelle())
    print("Gewähltes Modell:", bestes_modell())
