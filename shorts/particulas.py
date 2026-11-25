"""PARTICLE FLOW — PHYSICS & ASMR (Hush Satisfy Lab). Modalidad nueva e independiente (Pol, 15-11).

Vídeos de 30 s a 60 fps, 1080x1920: miles de bolitas brillantes en una figura 3D caen a la vez, chocan contra una
plataforma blanca con UN solo «pip», y a partir de ahí rebotan por grupos (anillos, espirales, pétalos...) que se
desfasan poco a poco; cada impacto de cada grupo es una nota de una escala pentatónica. Termina con un impacto
colectivo sincronizado y un pequeño eco.

NO usa ElevenLabs, ni voces, ni muñecos: no toca nada del resto del proyecto. Todo es determinista:

    diseño del día (fecha → figura, patrón, paleta, escala, instrumento, cámara; sin repetir los últimos días)
        → coreografía  (una tabla de impactos por grupo: instante + altura del salto siguiente)
        → audio        (sale de ESA MISMA tabla → cada nota cae en el fotograma exacto del impacto)
        → plan.json    (motor3d/src/videos/particulas: Three.js evalúa la misma tabla en cada fotograma)
        → render       (Remotion, 60 fps) → videos-finales/satisfy/<slug>/

Uso:
    python -m shorts particulas                 el vídeo de hoy (diseño nuevo, render y carpeta final)
    python -m shorts particulas --simular       solo enseña el diseño elegido
    python -m shorts particulas --solo-plan     plan + audio, sin render (para revisar)
    python -m shorts particulas --forma toroide --paleta fuego --escala do_mayor_penta --bolas 2566 ...
El lote diario (hacer-lote.ps1 → `shorts lote`) llama a diario() al final: un vídeo de partículas por día.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from .config import ROOT

CANAL = "satisfy"
MARCA = "Hush Satisfy Lab"
MOTOR3D = ROOT / "motor3d"
PUBLIC = MOTOR3D / "public" / "particulas"
REGISTRO = ROOT / "stories" / "particulas-usadas.json"
SR = 48000

# ============================================================ catálogo (lo que cambia de un día a otro)
FORMAS = ("toroide", "disco_hex", "lente", "galaxia", "flor", "estrella", "corazon", "caracola", "piramide",
          "ondas", "tornado", "mandala")
PATRONES = ("anillos", "espiral", "petalos", "diana", "interferencia", "remolino")
PALETAS = {   # degradados (de dentro a fuera / de abajo a arriba); «fuego» es la del encargo original
    "fuego": ["#c8102e", "#ff4d1a", "#ff8c1a", "#ffc21a", "#ffd966", "#e8b04a"],
    "oro_rosa": ["#7a1f3d", "#c2185b", "#ff6f91", "#ffb38a", "#ffd9a8", "#f5c26b"],
    "oceano": ["#03256c", "#0a58ca", "#1fa2ff", "#48e5c2", "#b8fff0", "#e6fffb"],
    "aurora": ["#2b0f54", "#6a1fd0", "#2e8bff", "#17d4a7", "#9cff6b", "#e8ffb0"],
    "neon": ["#ff006e", "#fb5607", "#ffbe0b", "#8338ec", "#3a86ff", "#00f5d4"],
    "caramelo": ["#ff5d8f", "#ff97b7", "#ffd6a5", "#fdffb6", "#caffbf", "#9bf6ff"],
    "hielo": ["#4a6fa5", "#7fa7d8", "#b9d6f2", "#e3f2fd", "#ffffff", "#cfd8dc"],
    "lava": ["#3d0000", "#950101", "#ff0000", "#ff6d00", "#ffab00", "#fff3b0"],
}
ESCALAS = {   # grados en semitonos dentro de la octava; tónica en MIDI (octava 5 = Do5 = 72)
    "do_mayor_penta": ([0, 2, 4, 7, 9], 72),
    "re_mayor_penta": ([0, 2, 4, 7, 9], 74),
    "fa_mayor_penta": ([0, 2, 4, 7, 9], 77),
    "sol_mayor_penta": ([0, 2, 4, 7, 9], 79 - 12),
    "la_menor_penta": ([0, 3, 5, 7, 10], 69),
    "mi_menor_penta": ([0, 3, 5, 7, 10], 76 - 12),
    "do_lidia_hexa": ([0, 2, 4, 6, 7, 11], 72),
    "re_dorica_penta": ([0, 2, 3, 7, 9], 74),
}
INSTRUMENTOS = {   # mezcla marimba / cristal / xilófono / mallet FM (el encargo: los cuatro mezclados)
    "cristal_marimba": dict(marimba=0.45, cristal=0.55, xilo=0.10, mallet=0.15),
    "marimba_brillante": dict(marimba=0.70, cristal=0.20, xilo=0.25, mallet=0.10),
    "campanas": dict(marimba=0.15, cristal=0.75, xilo=0.05, mallet=0.30),
    "xilofono_cristal": dict(marimba=0.25, cristal=0.40, xilo=0.55, mallet=0.10),
    "caja_musica": dict(marimba=0.20, cristal=0.45, xilo=0.15, mallet=0.55),
    # 20-11 (Pol: «que no siempre suene igual»): caja de música GRAVE + madera, sin nada de cristal
    "caja_grave_madera": dict(cajag=0.75, madera=0.50, grave=1),
}
CAMARAS = ("orbita", "acercamiento", "grua", "respira", "cortes")   # «cortes»: bajo → cenital → general, con corte seco
PLATAFORMAS = ("blanca", "blanca_aro", "perla")

DEFECTO = dict(
    bolas=2566, segundos=30.0, fps=60, ancho=1080, alto=1920,
    gravedad=5.6, elasticidad=1.0,          # elasticidad: escala de la altura de los rebotes (1 = diseño)
    # 22-11 (Pol: «que las bolas no tarden 2-3 s en caer, que sea desde el principio»): caen desde el fotograma 0
    # y todas tocan la plataforma a los 1,1 s (antes: quietas 2 s → impacto a los 3,4 s)
    altura_caida=5.2, t_suelta=0.0, t_impacto=1.1,
    t_final=27.4,                             # impacto colectivo final; después, eco y calma hasta 30 s
    rebote_min=1.4, rebote_max=3.1,         # altura base de los saltos (al principio → al final)
    variedad_min=0.17, variedad_max=0.95,    # cuánto difieren los grupos (ruptura de simetría progresiva)
    dispersion=0.32, giro=0.55,              # expansión radial máxima y giro (rad) de la figura en el aire
    grupos=28, radio_plataforma=4.45, radio_figura=3.2,
    volumen=1.0, reverb=0.26,
)


def _hash01(*xs) -> float:
    h = hashlib.sha1(("|".join(map(str, xs))).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


# ============================================================ diseño del día
def _registro() -> list[dict]:
    if REGISTRO.is_file():
        try:
            return json.loads(REGISTRO.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def disenar(fecha: dt.date, overrides: dict | None = None, historial: list[dict] | None = None) -> dict:
    """Elige una composición nueva para `fecha`: la figura no se repite en 9 días, la combinación figura+patrón en
    40, y la paleta/escala/instrumento/cámara no coinciden con los del día anterior. Misma fecha → mismo diseño
    (si el render se corta y se repite, sale idéntico)."""
    hist = historial if historial is not None else _registro()
    rng = random.Random(f"satisfy-{fecha.isoformat()}")
    recientes = [h for h in hist if h.get("fecha", "") < fecha.isoformat()]     # solo lo de antes (hay días adelantados)
    recientes.sort(key=lambda h: h.get("fecha", ""))

    def dias(h):
        try:
            return (fecha - dt.date.fromisoformat(h["fecha"])).days
        except Exception:
            return 999

    vetadas_forma = {h.get("forma") for h in recientes if 0 < dias(h) <= 9}
    vetados_combo = {(h.get("forma"), h.get("patron")) for h in recientes if 0 < dias(h) <= 40}
    ayer = recientes[-1] if recientes else {}

    def elige(opciones, clave, extra_veto=()):
        ops = [o for o in opciones if o != ayer.get(clave) and o not in extra_veto] or list(opciones)
        return rng.choice(ops)

    forma = elige(FORMAS, "forma", vetadas_forma)
    pats = [p for p in PATRONES if (forma, p) not in vetados_combo and p != ayer.get("patron")] or list(PATRONES)
    patron = rng.choice(pats)
    d = dict(DEFECTO)
    d.update(
        fecha=fecha.isoformat(), forma=forma, patron=patron,
        paleta=elige(list(PALETAS), "paleta"), escala=elige(list(ESCALAS), "escala"),
        instrumento=elige(list(INSTRUMENTOS), "instrumento"), camara=elige(CAMARAS, "camara"),
        plataforma=elige(PLATAFORMAS, "plataforma"),
        brazos=rng.choice((2, 3, 4, 5)), petalos=rng.choice((3, 4, 5, 6, 8)),
        ondas=round(rng.uniform(1.2, 2.4), 2), velocidad_onda=round(rng.uniform(0.18, 0.34), 3),
        semilla=rng.randrange(1 << 30),
    )
    for k, v in (overrides or {}).items():
        if v is not None:
            d[k] = v
    d["slug"] = f"satisfy-{d['fecha']}-{d['forma']}-{d['patron']}"
    return d


# ============================================================ figuras iniciales (x, y, z) — y = altura sobre la base
def _hex_lattice(s: float, R: float) -> np.ndarray:
    n = int(R / s) + 2
    pts = []
    for j in range(-2 * n, 2 * n + 1):
        for i in range(-2 * n, 2 * n + 1):
            x = (i + 0.5 * (j % 2)) * s
            z = j * s * math.sqrt(3) / 2
            if x * x + z * z <= R * R:
                pts.append((x, z))
    return np.array(pts, float).reshape(-1, 2)


def _en_poligono(x, z, poly):
    dentro = np.zeros_like(x, bool)
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        cruza = ((z1 > z) != (z2 > z)) & (x < (x2 - x1) * (z - z1) / (z2 - z1 + 1e-12) + x1)
        dentro ^= cruza
    return dentro


def _rellena(mask, altura, R, objetivo, capas=1, sep=0.0):
    """Red hexagonal dentro de `mask` (función de x,z sobre [-1,1]), con la separación justa para ~objetivo bolas."""
    def gen(s):
        p = _hex_lattice(s, R)
        if len(p) == 0:
            return np.zeros((0, 3))
        ok = mask(p[:, 0] / R, p[:, 1] / R)
        p = p[ok]
        out = []
        for c in range(capas):
            y = altura(p[:, 0] / R, p[:, 1] / R) + c * sep
            off = (c % 2) * s * 0.5
            out.append(np.c_[p[:, 0] + off * 0.5, y, p[:, 1] + off * 0.29])
        return np.vstack(out)
    lo, hi = 0.03, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if len(gen(mid)) > objetivo:
            lo = mid
        else:
            hi = mid
    return gen(lo), lo


def _anillos_param(radios_alturas, objetivo):
    """Anillos horizontales (radio, altura): el número de bolas de cada uno, proporcional a su perímetro."""
    per = sum(2 * math.pi * max(r, 0.05) for r, _ in radios_alturas)
    s = per / objetivo
    pts = []
    for k, (r, y) in enumerate(radios_alturas):
        n = max(1, round(2 * math.pi * r / s)) if r > 1e-3 else 1
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (k % 2)) / n
            pts.append((r * math.cos(a), y, r * math.sin(a)))
    return np.array(pts), s


def figura(d: dict) -> tuple[np.ndarray, float]:
    """Devuelve (puntos Nx3, separación) de la figura del día, centrada y escalada a radio_figura."""
    N, R, forma = int(d["bolas"]), float(d["radio_figura"]), d["forma"]
    if forma == "toroide":            # 23 anillos concéntricos alrededor del tubo (el encargo original)
        Rm, rt = 0.66 * R, 0.30 * R
        ra = [(Rm + rt * math.cos(2 * math.pi * k / 23), rt + rt * math.sin(2 * math.pi * k / 23)) for k in range(23)]
        p, s = _anillos_param(ra, N)
    elif forma == "disco_hex":        # red hexagonal en cúpula suave
        p, s = _rellena(lambda x, z: np.ones_like(x, bool), lambda x, z: 0.55 * (1 - (x * x + z * z)), R, N)
    elif forma == "lente":            # esfera achatada (casquete doble de Fibonacci)
        k = np.arange(N) + 0.5
        phi = np.arccos(1 - 2 * k / N)
        th = math.pi * (1 + 5 ** 0.5) * k
        p = np.c_[np.sin(phi) * np.cos(th) * R * 0.92, (np.cos(phi) + 1) * 1.0, np.sin(phi) * np.sin(th) * R * 0.92]
        s = math.sqrt(4 * math.pi * (R * 0.92) ** 2 * 0.55 / N)
    elif forma == "galaxia":
        brazos = int(d.get("brazos", 3))

        def m(x, z):
            r = np.hypot(x, z)
            a = np.arctan2(z, x)
            fase = (a - 3.2 * np.log(r + 0.08)) * brazos / (2 * np.pi)
            return (np.abs(fase - np.round(fase)) < 0.22 + 0.25 * (1 - r)) | (r < 0.22)
        p, s = _rellena(m, lambda x, z: 0.45 * np.exp(-3 * (x * x + z * z)), R, N, capas=2, sep=0.22)
    elif forma == "flor":
        k = int(d.get("petalos", 5))
        p, s = _rellena(lambda x, z: np.hypot(x, z) <= 0.25 + 0.75 * np.abs(np.cos(k * np.arctan2(z, x) / 2)) ** 0.7,
                        lambda x, z: 0.5 * (1 - np.hypot(x, z)) ** 0.8, R, N, capas=2, sep=0.24)
    elif forma == "estrella":
        poly = []
        for k in range(10):
            a = np.pi / 2 + k * np.pi / 5
            rr = 1.0 if k % 2 == 0 else 0.45
            poly.append((rr * np.cos(a), rr * np.sin(a)))
        p, s = _rellena(lambda x, z: _en_poligono(x, z, poly), lambda x, z: 0.0 * x, R, N, capas=3, sep=0.25)
    elif forma == "corazon":
        def m(x, z):
            X, Z = x * 1.25, -z * 1.25 + 0.15
            return (X * X + Z * Z - 0.55) ** 3 - X * X * Z ** 3 * 0.9 <= 0
        p, s = _rellena(m, lambda x, z: 0.0 * x, R, N, capas=3, sep=0.25)
    elif forma == "caracola":         # rampa en espiral (escalera de caracol) sobre una red hexagonal
        p, s = _rellena(lambda x, z: np.hypot(x, z) > 0.12,
                        lambda x, z: 1.5 * ((np.arctan2(z, x) + np.pi) / (2 * np.pi)) * (0.35 + 0.65 * np.hypot(x, z)), R, N)
    elif forma == "piramide":
        p, s = _rellena(lambda x, z: (np.abs(x) < 0.72) & (np.abs(z) < 0.72),
                        lambda x, z: np.round((0.72 - np.maximum(np.abs(x), np.abs(z))) * 6) / 6 * 1.6, R, N)
    elif forma == "ondas":
        p, s = _rellena(lambda x, z: np.ones_like(x, bool),
                        lambda x, z: 0.32 * (1 + np.cos(np.hypot(x, z) * 3.4 * np.pi)) * (1.05 - np.hypot(x, z)), R, N)
    elif forma == "tornado":
        ra = [(R * (0.18 + 0.82 * k / 22), 0.08 + 1.5 * (k / 22) ** 1.4) for k in range(23)]
        p, s = _anillos_param(ra, N)
    else:                              # mandala: anillos con ondulación poligonal alterna (6 y 12 lados)
        radios = [R * (0.06 + 0.94 * k / 22) for k in range(23)]
        per_total = sum(2 * math.pi * r for r in radios)
        s = per_total / N
        pts = []
        for k, r0 in enumerate(radios):
            n = max(6, round(2 * math.pi * r0 / s))
            lados = 6 if k % 2 else 12
            for i in range(n):
                a = 2 * math.pi * (i + 0.5 * (k % 2)) / n
                y = 0.30 + 0.16 * math.sin(k * 0.55) + 0.12 * math.cos(lados * a) * (k / 22)
                pts.append((r0 * math.cos(a), y, r0 * math.sin(a)))
        p = np.array(pts)
    p = np.asarray(p, float)
    rmax = np.hypot(p[:, 0], p[:, 2]).max()
    if rmax > 0:
        f = R / rmax
        p[:, 0] *= f
        p[:, 2] *= f
        s *= f
    p[:, 1] -= p[:, 1].min()
    return p, float(s)


def _vecina(p: np.ndarray) -> float:
    """Distancia a la bola más cercana (percentil 2: las más apretadas mandan) → radio sin solapes."""
    nn = np.full(len(p), np.inf)
    for i in range(0, len(p), 256):
        dd = ((p[i:i + 256, None, :] - p[None, :, :]) ** 2).sum(-1)
        for j in range(dd.shape[0]):
            dd[j, i + j] = np.inf
        nn[i:i + 256] = np.sqrt(dd.min(1))
    return float(np.percentile(nn, 2))


# ============================================================ patrón → grupos
def _q(d: dict, x, z) -> np.ndarray:
    """Coordenada del patrón en [0,1): las bolas con q parecido rebotan juntas (un grupo = una nota)."""
    R = float(d["radio_figura"])
    r = np.clip(np.hypot(x, z) / R, 0, 1)
    a = np.arctan2(z, x)
    pt = d["patron"]
    if pt == "anillos":
        q = r
    elif pt == "espiral":
        q = (r * 1.15 + d.get("brazos", 3) * a / (2 * np.pi)) % 1.0
    elif pt == "petalos":
        k = d.get("petalos", 5)
        q = 0.62 * np.abs(np.sin(k * a / 2)) + 0.38 * r
    elif pt == "diana":
        q = (np.floor(r * 6) % 2) * 0.5 + 0.5 * ((np.cos(4 * a) + 1) / 2) * 0.999
    elif pt == "interferencia":
        d1 = np.hypot(x - 0.45 * R, z)
        d2 = np.hypot(x + 0.45 * R, z)
        q = ((d1 - d2) / (0.9 * R) + 1) / 2
    else:   # remolino
        q = (2 * r + a / (2 * np.pi)) % 1.0
    return np.clip(q, 0, 0.99999)


# ============================================================ coreografía
def _vuelo(h, g):
    return 2.0 * math.sqrt(2.0 * max(h, 1e-4) / g)


def coreografia(d: dict) -> dict:
    """Tabla de impactos por grupo. Cada grupo: impactos t[k] y altura h[k] del salto que empieza en t[k].
    Todas tocan a la vez en t_impacto; la ruptura de simetría empieza DESPUÉS (variedad casi 0 en el 1.er rebote);
    todas vuelven a coincidir en t_final y hacen el mismo eco."""
    g = float(d["gravedad"])
    G = int(d["grupos"])
    t0, tf = float(d["t_impacto"]), float(d["t_final"])
    F, w = float(d["ondas"]), float(d["velocidad_onda"])
    fase2 = _hash01(d["semilla"], "fase") * 2 * math.pi
    grupos = []
    for gi in range(G):
        qg = (gi + 0.5) / G
        ts, hs = [t0], []
        t = t0
        while True:
            p = min(1.0, (t - t0) / (tf - t0))
            base = d["rebote_min"] + (d["rebote_max"] - d["rebote_min"]) * p ** 0.9
            var = d["variedad_min"] + (d["variedad_max"] - d["variedad_min"]) * p ** 0.5
            # al principio manda una rampa por el patrón (cascada ordenada: de dentro a fuera, por el brazo...);
            # después, dos ondas que viajan por la figura y se cruzan (anillos, espirales, flores que aparecen y se deshacen)
            rampa = 2 * qg - 1
            ondas = (0.62 * math.sin(2 * math.pi * (F * qg - w * t))
                     + 0.38 * math.sin(2 * math.pi * (0.5 * F * qg + 0.7 * w * t) + fase2))
            mezcla = min(1.0, p * 2.2)
            onda = (1 - mezcla) * rampa + mezcla * ondas
            h = base * (1 + 0.62 * var * onda) * float(d["elasticidad"])
            h = min(max(h, 0.35), 4.6)
            dur = _vuelo(h, g)
            resto = tf - t
            if t + dur > tf - 0.55:                   # último salto: ajustado para caer justo en t_final
                if resto > 2 * _vuelo(4.6, g):         # (no debería pasar) parte en dos
                    dur = resto / 2
                    hs.append(g * dur * dur / 8)
                    t += dur
                    ts.append(t)
                    resto = tf - t
                if resto < 0.45:                       # demasiado poco: alarga el salto anterior hasta t_final
                    ts.pop()
                    t = ts[-1]
                    hs.pop()
                    resto = tf - t
                hs.append(g * resto * resto / 8)
                ts.append(tf)
                break
            hs.append(h)
            t += dur
            ts.append(t)
        for h in (0.30, 0.10, 0.032):                  # eco: tres saltitos idénticos para todas
            hs.append(h)
            ts.append(ts[-1] + _vuelo(h, g))
        hs.append(0.0)                                 # quieta hasta el final
        grupos.append({"q": qg, "t": [round(x, 5) for x in ts], "h": [round(x, 5) for x in hs]})
    return {"grupos": grupos}


# ============================================================ bolas, colores, curvas
def _hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _degradado(pal, u):
    cols = np.array([_hex2rgb(c) for c in pal])
    u = np.clip(u, 0, 1) * (len(cols) - 1)
    i = np.minimum(np.floor(u).astype(int), len(cols) - 2)
    f = (u - i)[:, None]
    return cols[i] * (1 - f) + cols[i + 1] * f


def curvas(d: dict) -> dict:
    """Expansión radial E(t) y giro S(t) de la figura, muestreados por fotograma (los usa Three.js)."""
    fps, n = int(d["fps"]), int(round(d["segundos"] * d["fps"]))
    t = np.arange(n) / fps
    t0, tf = d["t_impacto"], d["t_final"]
    u = np.clip((t - t0) / (tf - t0), 0, 1)
    sube = u * u * (3 - 2 * u)
    E = d["dispersion"] * sube * (1 - 0.35 * np.clip((t - tf + 2.5) / 2.5, 0, 1) ** 2)
    S = d["giro"] * (sube + 0.08 * np.sin(2 * np.pi * u * 2.0) * u)
    after = t > tf
    S[after] = S[~after][-1] if (~after).any() else S[after]
    E[after] = E[~after][-1] if (~after).any() else E[after]
    return {"E": [round(float(x), 5) for x in E], "S": [round(float(x), 5) for x in S]}


def plan(d: dict) -> dict:
    p, s = figura(d)
    N = len(p)
    rad = float(np.clip(0.47 * _vecina(p), 0.035, 0.095))
    idx = np.arange(N)
    talla = rad * (0.93 + 0.14 * np.array([_hash01(d["semilla"], "t", i) for i in idx]))
    q = _q(d, p[:, 0], p[:, 2])
    G = int(d["grupos"])
    gid = np.minimum((q * G).astype(int), G - 1)
    R = float(d["radio_figura"])
    r = np.hypot(p[:, 0], p[:, 2]) / R
    a = np.arctan2(p[:, 2], p[:, 0])
    # cuánto se aleja cada bola del centro y cuánto gira: función suave de radio y ángulo (nada de azar por bola)
    sep = 0.55 + 0.45 * np.sin(np.pi * r) + 0.18 * np.cos(d.get("petalos", 5) * a)
    gir = (1.0 - 0.6 * r) * (1 + 0.25 * np.sin(2 * a))
    # color: degradado por el patrón y el radio
    u = 0.55 * r + 0.45 * q
    if d["forma"] in ("tornado", "lente", "piramide", "toroide"):
        u = 0.5 * u + 0.5 * p[:, 1] / max(p[:, 1].max(), 1e-3)
    u = (u - u.min()) / max(u.max() - u.min(), 1e-6)    # el degradado entero, de un extremo de la paleta al otro
    col = _degradado(PALETAS[d["paleta"]], u)
    alt = float(d["altura_caida"])
    y0 = p[:, 1] + alt
    core = coreografia(d)
    lim = d["radio_plataforma"] - 0.2
    rmax_fin = (R * (1 + d["dispersion"] * sep.max()))
    if rmax_fin > lim:                                  # que nada se salga de la plataforma
        d["dispersion"] = float((lim / R - 1) / sep.max())
    out = {
        "version": 1, "slug": d["slug"], "marca": MARCA,
        "fps": int(d["fps"]), "frames": int(round(d["segundos"] * d["fps"])), "segundos": d["segundos"],
        "gravedad": d["gravedad"], "t_suelta": d["t_suelta"], "t_impacto": d["t_impacto"], "t_final": d["t_final"],
        "plataforma": {"radio": d["radio_plataforma"], "tipo": d["plataforma"]},
        "camara": d["camara"], "paleta": PALETAS[d["paleta"]], "forma": d["forma"], "patron": d["patron"],
        "bolas": {
            "x": [round(float(v), 4) for v in p[:, 0]], "z": [round(float(v), 4) for v in p[:, 2]],
            "y0": [round(float(v), 4) for v in y0], "r": [round(float(v), 4) for v in talla],
            "g": [int(v) for v in gid], "sep": [round(float(v), 4) for v in sep], "gir": [round(float(v), 4) for v in gir],
            "c": ["#%02x%02x%02x" % tuple(int(round(c * 255)) for c in cc) for cc in col],
        },
        "grupos": core["grupos"],
        "curvas": curvas(d),
        "audio": f"particulas/{d['slug']}/audio.wav",
    }
    return out


# ============================================================ eventos de sonido (desde la MISMA tabla)
def _nota(d: dict, idx: int) -> int:
    grados, tonica = ESCALAS[d["escala"]]
    o, k = divmod(idx, len(grados))
    return tonica + 12 * o + grados[k]


def eventos(d: dict, pl: dict) -> list[dict]:
    """Un evento por impacto de grupo (no por bola). El primero, un único «pip» colectivo."""
    g = pl["gravedad"]
    t0, tf = pl["t_impacto"], pl["t_final"]
    G = len(pl["grupos"])
    gid = np.array(pl["bolas"]["g"])
    xs = np.array(pl["bolas"]["x"])
    cuenta = np.bincount(gid, minlength=G).astype(float)
    media = cuenta[cuenta > 0].mean()
    panx = np.array([xs[gid == k].mean() if cuenta[k] else 0.0 for k in range(G)])
    panx = panx / (np.abs(panx).max() + 1e-6)
    grados = len(ESCALAS[d["escala"]][0])
    centro = 2 * grados + 2                            # ~ Mi6 en pentatónica de Do
    ev = [{"t": t0, "tipo": "pip", "gain": 1.0, "pan": 0.0, "midi": _nota(d, 3 * grados)}]
    for k, gr in enumerate(pl["grupos"]):
        ts, hs = gr["t"], gr["h"]
        for j in range(1, len(ts)):
            t = ts[j]
            if t >= tf - 1e-6:
                break                                   # el final colectivo y el eco van aparte (un solo acorde)
            p = (t - t0) / (tf - t0)
            h_prev = hs[j - 1]
            span = 3 + 11 * p ** 0.8                   # la escala se abre poco a poco
            alto = (h_prev - 1.6) / 1.4                 # saltos más altos → notas más agudas
            ciclo = int((t - t0) / 1.35)               # cascadas que suben y, a partir de la mitad, también bajan
            sentido = -1 if (p > 0.35 and (ciclo // 2) % 2) else 1
            idx = centro + round(sentido * span * (gr["q"] - 0.5)) + round((1 + 2.2 * p) * alto)
            idx = int(min(max(idx, grados), 4 * grados))
            vel = math.sqrt(2 * g * h_prev)
            gain = (cuenta[k] / media) ** 0.3 * (vel / math.sqrt(2 * g * 2.0)) ** 0.7
            ev.append({"t": t, "tipo": "nota", "gain": float(gain), "pan": float(panx[k] * 0.75), "midi": _nota(d, idx)})
    # final: impacto colectivo = acorde arpegiado muy corto; eco = el mismo acorde, más suave y más agudo
    gr0 = pl["grupos"][0]
    i_f = gr0["t"].index(tf) if tf in gr0["t"] else len(gr0["t"]) - 5
    acorde = [0, 2, 4, 5, 7] if grados == 5 else [0, 2, 4, 6, 8]
    for n, (tt, ga) in enumerate(zip(gr0["t"][i_f:i_f + 4], (1.0, 0.55, 0.32, 0.18))):
        for m, a in enumerate(acorde):
            ev.append({"t": tt + 0.018 * m, "tipo": "final", "gain": ga * (0.75 if m else 1.0),
                       "pan": (m - 2) * 0.22, "midi": _nota(d, 2 * grados + a + n)})
    return sorted(ev, key=lambda e: e["t"])


# ============================================================ síntesis
def _voz(midi: float, dur: float, mezcla: dict, brillo: float = 1.0) -> np.ndarray:
    f = 440.0 * 2 ** ((midi - 69) / 12)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    agudo = np.clip((midi - 72) / 36, 0, 1)            # las notas muy agudas, más cortas (como en la realidad)

    def parcial(ratio, amp, dec):
        fr = f * ratio
        if fr > 15500:
            return 0.0
        return amp * np.sin(2 * np.pi * fr * t) * np.exp(-t / dec)
    m = mezcla
    if m.get("marimba"):
        k = 1 - 0.55 * agudo
        out += m["marimba"] * (parcial(1, 1.0, 0.55 * k) + parcial(3.93, 0.32 * brillo, 0.11 * k) + parcial(9.2, 0.06 * brillo, 0.04))
    if m.get("cristal"):
        k = 1 - 0.4 * agudo
        out += m["cristal"] * 0.8 * (parcial(1, 1.0, 1.5 * k) + parcial(2.32, 0.45, 0.8 * k) + parcial(4.25, 0.22 * brillo, 0.42 * k)
                                     + parcial(6.63, 0.10 * brillo, 0.22 * k))
    if m.get("xilo"):
        out += m["xilo"] * (parcial(1, 1.0, 0.28) + parcial(3.0, 0.42 * brillo, 0.08) + parcial(6.0, 0.08, 0.03))
    if m.get("mallet"):                                 # FM tipo «mallet synth»: índice que se apaga rápido
        idx = 2.2 * brillo * np.exp(-t / 0.05)
        out += m["mallet"] * 0.7 * np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t / (0.7 - 0.35 * agudo))
    if m.get("cajag"):                                  # púa de caja de música: fundamental + modos de la lámina (5,4 · 11,6)
        out += m["cajag"] * (parcial(1, 1.0, 1.25) + parcial(2.0, 0.18, 0.5) + parcial(5.4, 0.22 * brillo, 0.09)
                             + parcial(11.6, 0.06 * brillo, 0.03))
    if m.get("madera"):                                 # bloque de madera: modos inarmónicos muy cortos + golpe
        out += m["madera"] * 0.8 * (parcial(1, 1.0, 0.085) + parcial(2.76, 0.42, 0.04) + parcial(5.4, 0.12, 0.018))
        k = min(n, int(0.004 * SR))
        out[:k] += m["madera"] * 0.25 * np.sin(2 * np.pi * 2400 * t[:k]) * np.linspace(1, 0, k)
    at = int(0.0015 * SR)                               # ataque rapidísimo pero sin «clic»
    if at > 1:
        out[:at] *= np.linspace(0, 1, at) ** 0.5
    return out


def _pip(midi: int, dur: float = 1.4) -> np.ndarray:
    """El primer impacto: una sola campanita de cristal, limpia y muy aguda, con un toque de transitorio."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 440.0 * 2 ** ((midi - 69) / 12)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.55) + 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.25)
         + 0.12 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12) + 0.25 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t / 0.35))
    clic = np.zeros(n)
    m = int(0.003 * SR)
    clic[:m] = np.sin(2 * np.pi * 9000 * t[:m]) * np.hanning(2 * m)[m:]
    s = s + 0.25 * clic
    at = int(0.001 * SR)
    s[:at] *= np.linspace(0, 1, at)
    return s


def _reverb_ir(seg: float, semilla: int) -> np.ndarray:
    rng = np.random.default_rng(semilla)
    n = int(seg * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        ruido = rng.standard_normal(n)
        spec = np.fft.rfft(ruido)
        fr = np.fft.rfftfreq(n, 1 / SR)
        spec *= 1 / (1 + (fr / 7000) ** 2) * (fr > 180)          # reverb delicada: sin graves ni siseo
        r = np.fft.irfft(spec, n)
        r *= np.exp(-t / (seg / 6.9))
        pre = int(0.018 * SR)
        r = np.r_[np.zeros(pre), r[:-pre]]
        for d_ms, a in ((11, 0.35), (23, 0.22), (37, 0.15)):     # primeras reflexiones
            k = int(d_ms * (1.0 + 0.13 * c) * SR / 1000)
            r[k] += a
        ir[:, c] = r / np.sqrt((r ** 2).sum())
    return ir


def _convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(x) + len(ir) - 1
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[:len(x)]


def sintetiza(d: dict, ev: list[dict], segundos: float) -> np.ndarray:
    n = int(round(segundos * SR))
    seco = np.zeros((n, 2))
    mezcla = INSTRUMENTOS[d["instrumento"]]
    cache: dict = {}
    for e in ev:
        i0 = int(round(e["t"] * SR))
        if i0 >= n:
            continue
        if e["tipo"] == "pip" and not mezcla.get("grave"):
            s = _pip(e["midi"]) * 0.9
        elif e["tipo"] == "pip":                       # con la caja grave, el primer golpe también es caja (sin cristal)
            s = _voz(e["midi"] - 12, 2.0, mezcla, 1.0) * 0.9
        else:
            key = (e["midi"], e["tipo"])
            if key not in cache:
                cache[key] = _voz(e["midi"] - (12 if mezcla.get("grave") else 0), 2.2 if e["tipo"] == "final" else 1.6, mezcla, 1.0)
            s = cache[key] * e["gain"]
        a = (e["pan"] + 1) * math.pi / 4
        L, Rr = math.cos(a), math.sin(a)
        m = min(len(s), n - i0)
        seco[i0:i0 + m, 0] += s[:m] * L
        seco[i0:i0 + m, 1] += s[:m] * Rr
    # densidad: cuando suenan muchas a la vez, cada una más suave (envolvente lenta de la energía)
    env = np.sqrt(np.convolve((seco ** 2).mean(1), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")) + 1e-4
    ref = np.percentile(env[env > 1e-3], 60) if (env > 1e-3).any() else 1.0
    comp = np.clip(ref / env, 0.35, 1.0) ** 0.6
    seco *= comp[:, None]
    ir = _reverb_ir(2.6, d["semilla"])
    humedo = np.c_[_convolve(seco[:, 0], ir[:, 0]), _convolve(seco[:, 1], ir[:, 1])]
    mix = seco + float(d["reverb"]) * humedo * (np.abs(seco).max() / (np.abs(humedo).max() + 1e-9))
    # final sin corte: el último medio segundo se apaga suave
    fade = int(0.6 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    pico = np.abs(mix).max()
    mix *= (10 ** (-1.0 / 20)) / max(pico, 1e-9) * min(1.0, float(d["volumen"]))
    return mix


def guarda_wav(path: Path, mix: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(mix, -1, 1)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ============================================================ control de calidad (antes de renderizar)
def _y_bola(pl: dict, i: int, t: float) -> float:
    b = pl["bolas"]
    r = b["r"][i]
    g = pl["gravedad"]
    ts, tsu = pl["t_impacto"], pl["t_suelta"]
    if t <= tsu:
        return b["y0"][i]
    if t <= ts:
        gi = 2 * (b["y0"][i] - r) / (ts - tsu) ** 2
        return b["y0"][i] - 0.5 * gi * (t - tsu) ** 2
    gr = pl["grupos"][b["g"][i]]
    k = max(j for j, x in enumerate(gr["t"]) if x <= t)
    h = gr["h"][k]
    if h <= 0:
        return r
    dur = _vuelo(h, g)
    s = min(1.0, (t - gr["t"][k]) / dur)
    return r + 4 * h * s * (1 - s)


def revisa(d: dict, pl: dict, ev: list[dict], mix: np.ndarray) -> list[str]:
    """Las comprobaciones del encargo (sección 9). Devuelve los fallos (vacío = todo bien)."""
    fallos = []
    b = pl["bolas"]
    N = len(b["x"])
    tsu, ti = pl["t_suelta"], pl["t_impacto"]
    # 1 · todas caen a la vez y llegan a la vez
    for t in (tsu - 0.01, ti - 0.0002):
        ys = [_y_bola(pl, i, t) - b["r"][i] for i in range(0, N, 7)]
        if t < tsu and max(abs(_y_bola(pl, i, t) - b["y0"][i]) for i in range(0, N, 7)) > 1e-9:
            fallos.append("alguna bola se mueve antes de soltarse")
        if t > tsu and max(ys) > 0.01:
            fallos.append("no todas tocan la plataforma a la vez")
    # 2 · un solo sonido en el primer impacto
    cerca = [e for e in ev if abs(e["t"] - ti) < 0.05]
    if len(cerca) != 1:
        fallos.append(f"el primer impacto suena {len(cerca)} veces (debe ser 1)")
    # 3 · la dispersión empieza después: en el primer rebote las alturas casi iguales
    h1 = [gr["h"][0] for gr in pl["grupos"]]
    if (max(h1) - min(h1)) / max(h1) > 0.25:
        fallos.append("el primer rebote ya está muy desordenado")
    # 4 · cada nota coincide con un impacto de su grupo (misma tabla) y nada atraviesa la plataforma
    impactos = sorted({round(x, 4) for gr in pl["grupos"] for x in gr["t"]})
    arr = np.array(impactos)
    for e in ev:
        if e["tipo"] == "nota" and np.abs(arr - e["t"]).min() > 1e-3:
            fallos.append(f"nota sin impacto en {e['t']:.3f} s")
            break
    for t in np.arange(0, pl["segundos"], 0.05):
        for i in range(0, N, 61):
            if _y_bola(pl, i, t) < b["r"][i] - 1e-6:
                fallos.append(f"una bola atraviesa la plataforma en {t:.2f} s")
                break
    # 5 · la escala se abre
    notas = [e for e in ev if e["tipo"] == "nota"]
    if notas:
        mitad = pl["t_impacto"] + (pl["t_final"] - pl["t_impacto"]) / 2
        a = [e["midi"] for e in notas if e["t"] < mitad]
        c = [e["midi"] for e in notas if e["t"] >= mitad]
        if a and c and (max(c) - min(c)) <= (max(a) - min(a)):
            fallos.append("la escala no se amplía con el tiempo")
    # 6 · audio: sin clipping, 30 s exactos, sin silencio raro tras el primer impacto
    if np.abs(mix).max() >= 0.999:
        fallos.append("el audio satura (clipping)")
    if abs(len(mix) / SR - pl["segundos"]) > 1e-6:
        fallos.append("el audio no dura exactamente lo que el vídeo")
    if np.abs(mix[: int((ti - 0.02) * SR)]).max() > 1e-4:
        fallos.append("suena algo antes del primer impacto")
    # 7 · que todo quepa en la plataforma
    sep = np.array(b["sep"])
    rr = np.hypot(b["x"], b["z"]) * (1 + max(pl["curvas"]["E"]) * sep)
    if rr.max() + max(b["r"]) > pl["plataforma"]["radio"]:
        fallos.append("hay bolas que se salen de la plataforma")
    return fallos


# ============================================================ publicación
TITULOS = (
    "{n} bolas caen a la vez… y suenan así 🎶",
    "Cada rebote es una nota 🎵",
    "{n} bolas, una sola melodía",
    "Espera al final 🎧",
    "El rebote más satisfactorio que vas a ver",
    "Gravedad + {n} bolas = música",
    "Sube el volumen 🔊",
    "Caos perfectamente ordenado",
)
NOMBRE_FORMA = {"toroide": "anillo", "disco_hex": "disco hexagonal", "lente": "lente", "galaxia": "galaxia", "flor": "flor",
                "estrella": "estrella", "corazon": "corazón", "caracola": "caracola", "piramide": "pirámide", "ondas": "ondas",
                "tornado": "tornado", "mandala": "mandala"}


def publicacion(d: dict, n: int) -> str:
    rng = random.Random(d["slug"])
    tit = rng.choice(TITULOS).format(n=f"{n:,}".replace(",", "."))
    desc = (f"{n:,}".replace(",", ".") + f" bolas en forma de {NOMBRE_FORMA.get(d['forma'], d['forma'])} caen a la vez sobre una "
            "plataforma. Todas tocan al mismo tiempo… y después cada grupo rebota a su ritmo y toca su propia nota. "
            "Física y sonido sincronizados al fotograma. 🎧 Mejor con cascos.")
    tags = "#satisfying #asmr #oddlysatisfying #physics #shorts"
    return f"{tit}\n\n{desc}\n\n{tags}\n"


# ============================================================ todo junto
def preparar(d: dict, log=print) -> tuple[dict, list[str]]:
    """plan.json + audio.wav en motor3d/public/particulas/<slug>/. Devuelve (plan, fallos de calidad)."""
    pl = plan(d)
    ev = eventos(d, pl)
    mix = sintetiza(d, ev, pl["segundos"])
    fallos = revisa(d, pl, ev, mix)
    carpeta = PUBLIC / d["slug"]
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "plan.json").write_text(json.dumps(pl, separators=(",", ":")), encoding="utf-8")
    guarda_wav(carpeta / "audio.wav", mix)
    (carpeta / "diseno.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  {len(pl['bolas']['x'])} bolas · {len(pl['grupos'])} grupos · {sum(1 for e in ev if e['tipo'] == 'nota')} notas · "
        f"pico {20 * math.log10(np.abs(mix).max()):.1f} dBFS")
    return pl, fallos


def _chrome():
    try:                                   # (25-11) en GitHub Actions (Linux) no hay dia.py ni Chrome: Remotion trae el suyo
        from .dia import _chrome_exe
    except Exception:  # noqa: BLE001
        return None
    return _chrome_exe()


def renderizar(d: dict, pl: dict, log=print) -> Path | None:
    slug = d["slug"]
    props = MOTOR3D / "out" / f"{slug}_props.json"
    (MOTOR3D / "out").mkdir(exist_ok=True)
    # Remotion pinta SOLO la imagen (mute): al mezclar el audio él mismo lo desplazaba ~43 ms (2,5 fotogramas).
    # El audio se une después con FFmpeg, muestra a muestra: el «pip» cae en el fotograma exacto del impacto.
    props.write_text(json.dumps({"plan": f"particulas/{slug}/plan.json", "frames": pl["frames"], "fps": pl["fps"], "mute": True}),
                     encoding="utf-8")
    if not (MOTOR3D / "node_modules").is_dir():
        if subprocess.run("npm install --no-audit --no-fund", cwd=MOTOR3D, shell=True).returncode != 0:
            return None
    nav = f' --browser-executable="{_chrome()}"' if _chrome() else ""
    import os
    gl = os.environ.get("PARTICULAS_GL", "angle")          # en el PC, la gráfica (angle); en pruebas sin GPU, swangle
    nav += " " + os.environ.get("PARTICULAS_EXTRA", "")     # solo pruebas (p. ej. --scale=0.2 --frames=0-99)
    mudo = MOTOR3D / "out" / f"{slug}_mudo.mp4"
    mp4 = MOTOR3D / "out" / f"{slug}.mp4"
    cmd = (f'npx remotion render src/index.ts ParticleFlow "out/{slug}_mudo.mp4" --props="out/{slug}_props.json" '
           f'--gl={gl} --timeout=240000 --codec=h264 --crf=16 --muted{nav}')
    r = subprocess.run(cmd, cwd=MOTOR3D, shell=True)
    if r.returncode != 0 or not mudo.is_file():
        return None
    wav = PUBLIC / slug / "audio.wav"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mudo), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                        "-shortest", str(mp4)])
    if r.returncode != 0 or not mp4.is_file():
        log("  ✗  FFmpeg no pudo unir el audio")
        return None
    mudo.unlink(missing_ok=True)
    still = MOTOR3D / "out" / f"{slug}_miniatura.png"
    subprocess.run(f'npx remotion still src/index.ts ParticleFlow "out/{slug}_miniatura.png" --props="out/{slug}_props.json" '
                   f'--frame={int(pl["fps"] * 19.5)} --gl={gl} --timeout=240000{nav}', cwd=MOTOR3D, shell=True)
    return mp4


def comprueba_mp4(mp4: Path, segundos: float) -> list[str]:
    """30 s exactos, 60 fps, 1080x1920, audio estéreo, ningún fotograma negro."""
    fallos = []
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,channels:format=duration",
                            "-of", "json", str(mp4)], capture_output=True, text=True)
        info = json.loads(r.stdout)
        dur = float(info["format"]["duration"])
        if abs(dur - segundos) > 0.05:
            fallos.append(f"dura {dur:.2f} s")
        v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
        if (v["width"], v["height"]) != (1080, 1920):
            fallos.append(f"resolución {v['width']}x{v['height']}")
        a = [s for s in info["streams"] if s["codec_type"] == "audio"]
        if not a or a[0].get("channels") != 2:
            fallos.append("sin audio estéreo")
        r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(mp4), "-vf", "blackdetect=d=0.03:pix_th=0.02", "-an", "-f", "null", "-"],
                           capture_output=True, text=True)
        if "black_start" in r.stderr:
            fallos.append("hay fotogramas negros")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"no se pudo comprobar el mp4 ({e})")
    return fallos


def apunta(d: dict, mp4: str | None) -> None:
    turno = d.get("turno", 1)
    hist = [h for h in _registro() if (h.get("fecha"), h.get("turno", 1)) != (d["fecha"], turno)]
    hist.append({k: d[k] for k in ("fecha", "slug", "forma", "patron", "paleta", "escala", "instrumento", "camara", "plataforma")}
                | {"mecanismo": "rebote", "mp4": mp4} | ({"turno": turno} if turno > 1 else {}))
    REGISTRO.write_text(json.dumps(hist[-120:], ensure_ascii=False, indent=2), encoding="utf-8")


def hecho_hoy(fecha: dt.date, turno: int = 1) -> str | None:
    for h in _registro():
        if h.get("fecha") == fecha.isoformat() and h.get("turno", 1) == turno and h.get("mp4") and Path(h["mp4"]).is_file():
            return h["mp4"]
    return None


def producir(fecha: dt.date | None = None, overrides: dict | None = None, simular=False, solo_plan=False, log=print,
             turno: int = 1) -> int:
    fecha = fecha or dt.date.today()
    d = disenar(fecha, overrides)
    if turno > 1:                                       # 2.º vídeo del día: carpeta y registro propios
        d["slug"] += "-b" if turno == 2 else f"-{turno}"
        d["turno"] = turno
    log("\n" + "=" * 70 + f"\n  PARTICLE FLOW · {MARCA} · {fecha.isoformat()}\n" + "=" * 70)
    log(f"  Figura {d['forma']} · patrón {d['patron']} · paleta {d['paleta']} · escala {d['escala']} · "
        f"instrumento {d['instrumento']} · cámara {d['camara']} · plataforma {d['plataforma']}")
    if simular:
        log("  (Simulación: no se ha generado nada.)")
        return 0
    pl, fallos = preparar(d, log)
    if fallos:
        for f in fallos:
            log(f"  ✗  {f}")
        log("  >> Control de calidad NO superado: no se renderiza (díselo a Claude).")
        return 1
    log("  ✓  Control previo OK: caída sincronizada, un solo pip, dispersión después del impacto, notas = impactos, sin clipping.")
    if solo_plan:
        return 0
    mp4 = renderizar(d, pl, log)
    if not mp4:
        log("  >> FALLÓ el render de partículas (mira el error arriba).")
        return 1
    fallos = comprueba_mp4(mp4, pl["segundos"])
    for f in fallos:
        log(f"  ✗  {f}")
    from .final import organiza
    fin = organiza(CANAL, d["slug"], mp4, prefijo=f"{d['slug']}_")
    (fin / "publicacion.txt").write_text(publicacion(d, len(pl["bolas"]["x"])), encoding="utf-8")
    if fallos:                                          # no se da por hecho: el próximo lote lo repite (no gasta nada)
        log(f"  >> REVISAR: {fin / (d['slug'] + '.mp4')} no pasa el control final (arriba). Díselo a Claude.")
        return 1
    apunta(d, str(fin / f"{d['slug']}.mp4"))
    _limpia(fecha)
    log(f"  >> OK: {fin / (d['slug'] + '.mp4')}")
    return 0


def _limpia(hoy: dt.date, dias: int = 10) -> None:
    """Los planes y audios de trabajo (motor3d/public/particulas) de hace más de 10 días sobran: el vídeo ya está en
    videos-finales/satisfy/. Así la carpeta pública no crece sin fin."""
    import shutil
    for c in PUBLIC.glob("satisfy-*"):
        try:
            f = dt.date.fromisoformat(c.name[8:18])
        except ValueError:
            continue
        if (hoy - f).days > dias:
            shutil.rmtree(c, ignore_errors=True)


MECANISMOS = ("rebote", "galton", "pendulos", "vasos", "espiral", "arena")   # Pol 19-11: nunca el mismo dos días seguidos
# (22-11) «arena»: batalla de colores que se multiplican y tocan una melodía (shorts/arena.py)

# Pol 19-11: «hazme ya los de los próximos días». Estos días ya están decididos (temas aprobados) y el lote los hace
# por adelantado la primera vez que se ejecuta; cuando llegue su día, ya están hechos y no se repiten.
AGENDA = {
    "2026-11-19": ("galton", {}),                        # ya hecho (el primero del Galton)
    "2026-11-20": ("pendulos", {}),
    "2026-11-21": ("vasos", {}),
    "2026-11-22": ("rebote", {"instrumento": "caja_grave_madera", "camara": "cortes"}),
    "2026-11-23": ("espiral", {}),
    "2026-11-24": ("arena", {}),                         # (22-11) mecanismo nuevo: batalla de colores
}


def mecanismo_de(fecha: dt.date, historial: list[dict] | None = None) -> str:
    if fecha.isoformat() in AGENDA:
        return AGENDA[fecha.isoformat()][0]
    hist = historial if historial is not None else _registro()
    previos = sorted([h for h in hist if h.get("fecha", "") < fecha.isoformat()], key=lambda h: h.get("fecha", ""))
    ult = previos[-1].get("mecanismo", "rebote") if previos else "rebote"
    ops = [m for m in MECANISMOS if m != ult]
    return random.Random(f"mecanismo-{fecha.isoformat()}").choice(ops)


def producir_dia(fecha: dt.date, simular=False, log=print) -> int:
    mec = mecanismo_de(fecha)
    extra = AGENDA.get(fecha.isoformat(), (mec, {}))[1] or None
    if mec == "galton":
        from . import galton
        return galton.producir(fecha, extra, simular=simular, log=log)
    if mec in ("pendulos", "vasos", "espiral", "arena"):
        import importlib
        return importlib.import_module(f".{mec}", __package__).producir(fecha, extra, simular=simular, log=log)
    return producir(fecha, extra, simular=simular, log=log)


# Pol 22-11: «2 vídeos diarios por canal». El 2.º Satisfy del día es siempre un Particle Flow (rebote) con otra figura,
# otro patrón, otra paleta, otro instrumento y otra cámara que el 1.º, y sin repetir figura de los últimos 9 días.
POR_DIA = 2


def segundo_del_dia(fecha: dt.date, simular=False, log=print) -> int:
    ya = hecho_hoy(fecha, 2)
    if ya:
        log(f"\n  2.º Satisfy del {fecha.isoformat()} ya hecho: {ya}")
        return 0
    hist = _registro()
    hoy = [h for h in hist if h.get("fecha") == fecha.isoformat()]

    def dias(h):
        try:
            return (fecha - dt.date.fromisoformat(h["fecha"])).days
        except Exception:
            return 999

    rng = random.Random(f"satisfy-b-{fecha.isoformat()}")

    def elige(opciones, clave, extra=()):
        usados = {h.get(clave) for h in hoy} | set(extra)
        return rng.choice([o for o in opciones if o not in usados] or list(opciones))

    vetadas = {h.get("forma") for h in hist if 0 <= dias(h) <= 9}
    combos = {(h.get("forma"), h.get("patron")) for h in hist if 0 <= dias(h) <= 40}
    forma = elige(FORMAS, "forma", vetadas)
    patron = rng.choice([p for p in PATRONES if (forma, p) not in combos and p not in {h.get("patron") for h in hoy}]
                        or list(PATRONES))
    over = dict(forma=forma, patron=patron, paleta=elige(list(PALETAS), "paleta"),
                instrumento=elige(list(INSTRUMENTOS), "instrumento"), camara=elige(CAMARAS, "camara"),
                escala=elige(list(ESCALAS), "escala"))
    log(f"\n  2.º Satisfy del día ({fecha.isoformat()}): {forma} · {patron} · {over['paleta']}")
    return producir(fecha, over, simular=simular, log=log, turno=2)


ESTILO_NUEVO = True   # Pol 22-11: TODOS los Satisfy como sus referencias (pinzas + anillos), ver shorts/satisfy2.py


def diario(simular=False, log=print) -> int:
    """Lo que llama el lote. Desde el 22-11 (ESTILO_NUEVO): los 2 Satisfy del día de shorts/satisfy2.py (pinzas y
    anillos, plano fijo, sonidos graves). Lo de abajo (rebote, galton, péndulos, vasos, espiral, arena) queda como estaba
    por si Pol quiere volver a alguno."""
    if ESTILO_NUEVO:
        from . import satisfy2
        return satisfy2.diario(simular=simular, log=log)
    return diario_antiguo(simular=simular, log=log)


def diario_antiguo(simular=False, log=print) -> int:
    """Lo que llama el lote: el vídeo de hoy de Hush Satisfy Lab y, si hay días adelantados en la AGENDA que aún no
    están hechos, también esos (cada uno una sola vez: si ya existe, no se repite)."""
    hoy = dt.date.today()
    dias = [hoy] + sorted(dt.date.fromisoformat(f) for f in AGENDA if dt.date.fromisoformat(f) > hoy)
    fallos = 0
    for dia in dias:
        ya = hecho_hoy(dia)
        if ya:
            log(f"\n  Satisfy del {dia.isoformat()} ya hecho: {ya}")
            continue
        fallos += 1 if producir_dia(dia, simular=simular, log=log) else 0
    if POR_DIA >= 2:
        fallos += 1 if segundo_del_dia(hoy, simular=simular, log=log) else 0
    return 1 if fallos else 0
