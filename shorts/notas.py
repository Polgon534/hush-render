"""NOTAS — Hush Satisfy Lab (Pol 24-11, como el vídeo de referencia que mandó: el cuadrado que va abriendo camino).

Un cuadradito brillante viaja en diagonal por un bloque gris y va EXCAVANDO un pasillo; cada vez que choca con una
pared rebota, la pared se enciende, saltan chispas, el rastro cambia de color… y suena la SIGUIENTE NOTA de una melodía
famosa. Al final del vídeo se revela qué canción era («¿la has adivinado?»).

Melodías: SOLO de dominio público (compositores muertos hace más de 80 años o populares antiguas): Beethoven, Mozart,
Grieg, Offenbach, Brahms, Bizet, Pachelbel, Tchaikovsky, Rossini, Pierpont, populares… Nada de canciones con derechos.

Cómo se construye (determinista: misma fecha → mismo vídeo): la melodía da los instantes de cada nota; el cuadrado va
a velocidad constante, así que entre nota y nota recorre una distancia fija y en ese punto pone la PARED con la que
choca (gira 90°: cambia el signo de X o de Y, eligiendo el que lo devuelve hacia el centro). El pasillo es el rastro del
cuadrado. La cámara sigue al cuadrado con suavidad (como la referencia). Sonido: cada choque = la nota exacta.
"""
from __future__ import annotations

import datetime as dt
import math
import random

import numpy as np

from . import satisfy_base as SB

SR = SB.SR
MECANISMO = "notas"
NOMBRE = "Notas que excavan"
COMPOSICION = "Satisfy2D"

# (nombre, compositor, bpm, notas [(midi o None=silencio, beats)])  · do4 = 60
def _m(s):
    """'E4:1 D#4:0.5 ...' → [(midi, beats)]"""
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    out = []
    for tok in s.split():
        n, b = tok.split(":")
        if n == "R":
            out.append((None, float(b))); continue
        alt = 1 if "#" in n else (-1 if n[1:2] == "b" else 0)
        oct_ = int(n[-1])
        out.append((12 * (oct_ + 1) + base[n[0]] + alt, float(b)))
    return out


MELODIAS = {
    "himno_alegria": ("Himno de la alegría", "Beethoven", 132, _m(
        "E4:1 E4:1 F4:1 G4:1 G4:1 F4:1 E4:1 D4:1 C4:1 C4:1 D4:1 E4:1 E4:1.5 D4:0.5 D4:2 "
        "E4:1 E4:1 F4:1 G4:1 G4:1 F4:1 E4:1 D4:1 C4:1 C4:1 D4:1 E4:1 D4:1.5 C4:0.5 C4:2 "
        "D4:1 D4:1 E4:1 C4:1 D4:1 E4:0.5 F4:0.5 E4:1 C4:1 D4:1 E4:0.5 F4:0.5 E4:1 D4:1 C4:1 D4:1 G3:2 "
        "E4:1 E4:1 F4:1 G4:1 G4:1 F4:1 E4:1 D4:1 C4:1 C4:1 D4:1 E4:1 D4:1.5 C4:0.5 C4:2")),
    "para_elisa": ("Para Elisa", "Beethoven", 150, _m(
        "E5:0.5 D#5:0.5 E5:0.5 D#5:0.5 E5:0.5 B4:0.5 D5:0.5 C5:0.5 A4:1.5 C4:0.5 E4:0.5 A4:0.5 B4:1.5 E4:0.5 G#4:0.5 B4:0.5 C5:1.5 "
        "E4:0.5 E5:0.5 D#5:0.5 E5:0.5 D#5:0.5 E5:0.5 B4:0.5 D5:0.5 C5:0.5 A4:1.5 C4:0.5 E4:0.5 A4:0.5 B4:1.5 E4:0.5 C5:0.5 B4:0.5 A4:2 "
        "E5:0.5 D#5:0.5 E5:0.5 D#5:0.5 E5:0.5 B4:0.5 D5:0.5 C5:0.5 A4:1.5 C4:0.5 E4:0.5 A4:0.5 B4:1.5 E4:0.5 G#4:0.5 B4:0.5 C5:1.5 "
        "E4:0.5 E5:0.5 D#5:0.5 E5:0.5 D#5:0.5 E5:0.5 B4:0.5 D5:0.5 C5:0.5 A4:1.5 C4:0.5 E4:0.5 A4:0.5 B4:1.5 E4:0.5 C5:0.5 B4:0.5 A4:2")),
    "rey_montana": ("En la gruta del rey de la montaña", "Grieg", 150, _m(
        "B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:1 F4:0.5 C#4:0.5 F4:1 E4:0.5 C4:0.5 E4:1 "
        "B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:0.5 B4:0.5 A4:0.5 F#4:0.5 D4:0.5 F#4:0.5 A4:2 "
        "B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:1 F4:0.5 C#4:0.5 F4:1 E4:0.5 C4:0.5 E4:1 "
        "B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:0.5 B4:0.5 A4:0.5 F#4:0.5 D4:0.5 F#4:0.5 A4:2 "
        "F#4:0.5 G#4:0.5 A#4:0.5 B4:0.5 C#5:0.5 A#4:0.5 C#5:1 D5:0.5 A#4:0.5 D5:1 C#5:0.5 A#4:0.5 C#5:1 "
        "F#4:0.5 G#4:0.5 A#4:0.5 B4:0.5 C#5:0.5 A#4:0.5 C#5:1 D5:0.5 A#4:0.5 D5:1 C#5:2")),
    "jingle_bells": ("Jingle Bells", "J. L. Pierpont", 150, _m(
        "E4:1 E4:1 E4:2 E4:1 E4:1 E4:2 E4:1 G4:1 C4:1.5 D4:0.5 E4:4 F4:1 F4:1 F4:1.5 F4:0.5 F4:1 E4:1 E4:1 E4:0.5 E4:0.5 "
        "E4:1 D4:1 D4:1 E4:1 D4:2 G4:2 E4:1 E4:1 E4:2 E4:1 E4:1 E4:2 E4:1 G4:1 C4:1.5 D4:0.5 E4:4 "
        "F4:1 F4:1 F4:1.5 F4:0.5 F4:1 E4:1 E4:1 E4:0.5 E4:0.5 G4:1 G4:1 F4:1 D4:1 C4:4")),
    "estrellita": ("Estrellita, ¿dónde estás?", "Popular (Mozart: variaciones)", 120, _m(
        "C4:1 C4:1 G4:1 G4:1 A4:1 A4:1 G4:2 F4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:2 "
        "G4:1 G4:1 F4:1 F4:1 E4:1 E4:1 D4:2 G4:1 G4:1 F4:1 F4:1 E4:1 E4:1 D4:2 "
        "C4:1 C4:1 G4:1 G4:1 A4:1 A4:1 G4:2 F4:1 F4:1 E4:1 E4:1 D4:1 D4:1 C4:2")),
    "nana_brahms": ("La nana de Brahms", "Brahms", 110, _m(
        "E4:0.5 E4:0.5 G4:2 E4:0.5 E4:0.5 G4:2 E4:0.5 G4:0.5 C5:1 B4:1.5 A4:0.5 A4:1 G4:1 "
        "D4:0.5 E4:0.5 F4:1 D4:1 D4:0.5 E4:0.5 F4:2 D4:0.5 F4:0.5 B4:0.5 A4:0.5 G4:1 B4:1 C5:2 "
        "C4:0.5 C4:0.5 C5:2 A4:0.5 F4:0.5 G4:2 E4:0.5 C4:0.5 F4:1 G4:1 A4:1 G4:2 "
        "C4:0.5 C4:0.5 C5:2 A4:0.5 F4:0.5 G4:2 E4:0.5 C4:0.5 F4:1 E4:0.5 D4:0.5 C4:2")),
    "frere_jacques": ("Frère Jacques", "Popular francesa", 120, _m(
        "C4:1 D4:1 E4:1 C4:1 C4:1 D4:1 E4:1 C4:1 E4:1 F4:1 G4:2 E4:1 F4:1 G4:2 "
        "G4:0.5 A4:0.5 G4:0.5 F4:0.5 E4:1 C4:1 G4:0.5 A4:0.5 G4:0.5 F4:0.5 E4:1 C4:1 C4:1 G3:1 C4:2 C4:1 G3:1 C4:2")),
    "cucaracha": ("La cucaracha", "Popular", 150, _m(
        "C4:0.5 C4:0.5 C4:0.5 F4:1.5 A4:1 C4:0.5 C4:0.5 C4:0.5 F4:1.5 A4:2 F4:0.5 F4:0.5 E4:0.5 E4:0.5 D4:0.5 D4:0.5 C4:2 "
        "C4:0.5 C4:0.5 C4:0.5 E4:1.5 G4:1 C4:0.5 C4:0.5 C4:0.5 E4:1.5 G4:2 C5:0.5 D5:0.5 C5:0.5 Bb4:0.5 A4:0.5 G4:0.5 F4:2")),
}

PALETAS = {   # rastro: cada choque, el color siguiente
    "neon": ["#ff2d75", "#ffb703", "#3cff8f", "#2fd5ff", "#8f5bff", "#ff5c2d"],
    "fuego": ["#ff3d3d", "#ff8a1f", "#ffd21f", "#ff4fa0", "#ff6a00", "#ffe066"],
    "hielo": ["#4dd2ff", "#7d8bff", "#c38bff", "#5cffe1", "#9fe7ff", "#ff8bd8"],
    "dulce": ["#ff6fb5", "#ffd166", "#06d6a0", "#4cc9f0", "#b5179e", "#f77f00"],
}
TITULOS = ["Cada choque toca una nota… ¿ADIVINAS la canción?", "¿Qué CANCIÓN suena? Cada rebote es una nota",
           "Este cuadrado toca una canción FAMOSA rebotando", "Solo el 1 % la reconoce antes del FINAL"]


FONDOS = {"gris": "#77777e", "arena": "#8a8073", "pizarra": "#69737f", "salvia": "#6f7c6d", "malva": "#7b6f80",
          "arcilla": "#86706a", "azul": "#5f6f86"}   # (25-11) el bloque cambia de color cada vídeo


def disenar(fecha: dt.date, overrides: dict | None = None, historial: list[dict] | None = None, turno: int = 1) -> dict:
    rng = random.Random(f"notas-{fecha.isoformat()}-{turno}")
    usadas = [h.get("melodia") for h in (historial or [])][-len(MELODIAS) + 1:]
    libres = [k for k in MELODIAS if k not in usadas] or list(MELODIAS)
    mel = libres[fecha.toordinal() % len(libres)]
    previos = [h for h in (historial or []) if h.get("fecha", "") < fecha.isoformat()]   # (25-11) nada repetido de cerca
    evita_p = {h.get("paleta") for h in previos[-3:]}
    evita_f = {h.get("fondo") for h in previos[-3:]}
    d = dict(fecha=fecha.isoformat(), mecanismo=MECANISMO, fps=60, melodia=mel,
             paleta=rng.choice([p for p in PALETAS if p not in evita_p] or list(PALETAS)),
             fondo=rng.choice([f for f in FONDOS if f not in evita_f] or list(FONDOS)),
             lado=rng.choice([30, 34, 38]), velocidad=rng.choice([300.0, 330.0, 360.0]), semilla=rng.randrange(1 << 30),
             reverb=0.22, volumen=1.0, cama=False)
    for k, v in (overrides or {}).items():
        if v is not None:
            d[k] = v
    d["slug"] = f"satisfy-{d['fecha']}-notas-{mel.replace('_', '-')}"
    return d


def _notas(d: dict) -> list[tuple[float, int, float]]:
    """(t, midi, dur) de cada nota (los silencios no chocan)."""
    nombre, _, bpm, notas = MELODIAS[d["melodia"]]
    beat = 60.0 / bpm
    t, out = 1.2, []                       # 1,2 s de entrada: el cuadrado ya se mueve antes de la primera nota
    for vuelta in range(3):                 # si la melodía es corta, se repite (más rápida la 2.ª vez) hasta ~28 s
        for m, b in notas:
            if m is not None:
                out.append((round(t, 4), m, b * beat))
            t += b * beat
        if t > 22.0:
            break
        beat *= 0.88
        t += beat
    return out


def plan(d: dict, log=print) -> dict:
    notas = _notas(d)
    L = d["lado"]
    rng = random.Random(d["semilla"])
    # velocidad según el ritmo: el tramo típico entre notas mide ~4,5 cuadrados (zigzag claro, nada de amasijo)
    gaps = sorted(b[0] - a[0] for a, b in zip(notas, notas[1:]))
    v = max(260.0, min(700.0, 4.5 * L / max(0.05, gaps[len(gaps) // 2])))
    k = v / math.sqrt(2)                    # componente de la velocidad en cada eje
    # «rumbo»: el pasillo avanza en zigzag en una dirección y de vez en cuando gira 90° hacia la zona libre
    rumbo = rng.choice(["+x", "-x", "+y", "-y"])
    dirx = 1 if rumbo == "+x" else (-1 if rumbo == "-x" else rng.choice([1, -1]))
    diry = 1 if rumbo == "+y" else (-1 if rumbo == "-y" else rng.choice([1, -1]))
    t = 0.0
    t_ini = notas[0][0]
    x, y = -dirx * k * t_ini, -diry * k * t_ini
    verts = [[0.0, round(x, 2), round(y, 2)]]
    golpes, visto = [], [(x, y)]
    cambio = rng.randint(5, 9)
    for i, (tn, m, dur) in enumerate(notas):
        dt_ = tn - t
        x += dirx * k * dt_
        y += diry * k * dt_
        t = tn
        cambio -= 1
        if cambio <= 0:                         # gira hacia donde menos ha pasado
            cx_ = sum(p[0] for p in visto[-60:]) / len(visto[-60:])
            cy_ = sum(p[1] for p in visto[-60:]) / len(visto[-60:])
            if rumbo in ("+y", "-y"):
                rumbo = "+x" if x >= cx_ else "-x"
            else:
                rumbo = "+y" if y >= cy_ else "-y"
            cambio = rng.randint(5, 10)
        if rumbo in ("+y", "-y"):
            quiere = 1 if rumbo == "+y" else -1
            eje = "y" if diry != quiere else "x"
        else:
            quiere = 1 if rumbo == "+x" else -1
            eje = "x" if dirx != quiere else "y"
        if eje == "x":
            dirx = -dirx
            lado_pared = "der" if dirx < 0 else "izq"
        else:
            diry = -diry
            lado_pared = "abajo" if diry < 0 else "arriba"
        verts.append([round(t, 4), round(x, 2), round(y, 2)])
        visto.append((x, y))
        golpes.append(dict(t=round(t, 4), x=round(x, 2), y=round(y, 2), pared=lado_pared, c=i % len(PALETAS[d["paleta"]]), midi=m))
    final = notas[-1][0] + 2.0
    x += dirx * k * (final - t)
    y += diry * k * (final - t)
    verts.append([round(final, 4), round(x, 2), round(y, 2)])
    seg = max(32.0, final + 3.5)
    nombre, autor, _, _ = MELODIAS[d["melodia"]]
    return dict(fps=d["fps"], frames=int(round(seg * d["fps"])), segundos=round(seg, 3), estilo="notas", lado=L,
                verts=verts, golpes=golpes, colores=PALETAS[d["paleta"]], cancion=nombre, autor=autor,
                revela=round(notas[-1][0] + 0.6, 3), fondo=FONDOS.get(d.get("fondo", "gris"), "#77777e"))


def eventos(d: dict, pl: dict) -> list[dict]:
    notas = _notas(d)
    ev = []
    for (tn, m, dur), g in zip(notas, pl["golpes"]):
        pan = max(-0.6, min(0.6, g["x"] / 900))
        ev.append(dict(t=tn, tipo="nota", midi=m, dur=dur, pan=pan, gain=1.0))
        ev.append(dict(t=tn, tipo="toc", midi=m, pan=pan, gain=0.5))
    ev.append(dict(t=pl["revela"], tipo="final", midi=notas[-1][1], pan=0.0, gain=0.9))
    return ev


def _tono(hz: float, dur: float, gain: float) -> np.ndarray:
    """nota redonda tipo piano eléctrico / marimba: fundamental + armónicos suaves, ataque rápido, cola larga"""
    n = int(max(0.5, dur + 0.9) * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 0.004) * np.exp(-t / max(0.35, dur * 0.9))
    s = (np.sin(2 * np.pi * hz * t) + 0.32 * np.sin(2 * np.pi * 2 * hz * t) * np.exp(-t / 0.25)
         + 0.12 * np.sin(2 * np.pi * 3 * hz * t) * np.exp(-t / 0.12) + 0.18 * np.sin(2 * np.pi * hz / 2 * t))
    return s * env * gain


def sintetiza(d: dict, ev: list[dict], segundos: float) -> np.ndarray:
    rng = np.random.default_rng(d["semilla"])
    seco = np.zeros((int(segundos * SR) + SR, 2))
    for e in ev:
        if e["tipo"] == "nota":
            SB.mezcla_en(seco, _tono(SB.midi_hz(e["midi"]), e["dur"], 0.42), e["t"], e["pan"], e["gain"])
        elif e["tipo"] == "toc":                     # golpecito suave del choque (grave, nada agudo)
            m = int(0.05 * SR)
            s = SB.ruido_filtrado(m, rng, 120, 900) * np.exp(-np.arange(m) / SR / 0.012) * 0.25
            SB.mezcla_en(seco, s, e["t"], e["pan"], e["gain"])
        elif e["tipo"] == "final":
            for j, iv in enumerate((0, 4, 7, 12)):
                SB.mezcla_en(seco, _tono(SB.midi_hz(e["midi"] - 12 + iv), 1.6, 0.2), e["t"] + 0.05 * j, 0.0, 1.0)
    seco = seco[: int(segundos * SR)]
    return SB.acaba(seco, d["semilla"], d["reverb"], d["volumen"])


def revisa(d: dict, pl: dict, ev: list[dict], mix: np.ndarray) -> list[str]:
    f = []
    if np.abs(mix).max() > 0.95:
        f.append("el audio satura")
    if len(pl["golpes"]) < 25:
        f.append("la melodía tiene muy pocas notas")
    gs = [g["t"] for g in pl["golpes"]]
    if gs[0] > 2.0:
        f.append("el primer choque tarda")
    if max(np.diff(gs)) > 2.2:
        f.append("hay un hueco largo sin choques")
    if not 25 <= pl["segundos"] <= 60:
        f.append(f"dura {pl['segundos']} s")
    return f


def publicacion(d: dict, pl: dict) -> str:
    rng = random.Random(d["slug"])
    desc = ("Cada vez que el cuadrado choca con una pared suena la siguiente nota de una canción muy famosa. "
            "¿La has reconocido antes del final? 🎧 Mejor con cascos.")
    return f"{rng.choice(TITULOS)}\n\n{desc}\n\n#satisfying #asmr #oddlysatisfying #musica #shorts\n"


def resumen(d: dict, pl: dict, ev: list[dict]) -> str:
    return f"{MELODIAS[d['melodia']][0]} · {len(pl['golpes'])} choques · {pl['segundos']} s · paleta {d['paleta']}"
