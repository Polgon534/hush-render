"""ANILLOS — Hush Satisfy Lab, estilo nuevo (Pol 22-11, como su vídeo de referencia de los anillos con contador).

Fondo morado muy oscuro. En el centro, un disco oscuro con un CONTADOR grande. Alrededor, decenas de anillos finos de
colores pastel (degradado alrededor del círculo), cada uno con un HUECO y girando a su ritmo. Una bolita blanca rebota
entre el disco y el anillo de dentro; si al llegar al anillo coincide con su hueco, lo atraviesa: el anillo se ROMPE
(se deshace en trocitos que salen volando), el contador baja uno y todos los anillos se acercan un paso (el siguiente
pasa a ser el de dentro). El vídeo acaba cuando se rompe el último: contador a 0.

Sonido (nada agudo): cada anillo roto toca la siguiente nota de una melodía de dominio público en registro medio-grave
(Grieg, Beethoven, Pachelbel, Satie…) con un timbre de marimba/kalimba suave; cada rebote es un «toc» muy suave y grave.

La CÁMARA NO SE MUEVE. Determinista: misma fecha → mismo vídeo.
"""
from __future__ import annotations

import datetime as dt
import math
import random

import numpy as np

from . import satisfy_base as SB

SR = SB.SR
MECANISMO = "anillos"
NOMBRE = "Anillos con contador"
COMPOSICION = "Satisfy2D"

PALETAS = {   # (tono de inicio, tono final) del degradado alrededor del círculo, en grados HSL
    "aurora": (300, 120), "atardecer": (330, 40), "oceano": (180, 280), "menta": (140, 320), "fuego": (0, 60),
    "lima": (70, 160), "galaxia": (250, 330), "coral": (350, 20), "hielo": (190, 230), "tropical": (40, 170),
    "uva": (270, 300), "cielo": (200, 60),
}
FONDOS = {   # (Pol 24-11: «todos distintos») color del fondo + halo del centro
    "noche": ("#0d0913", "rgba(60,30,90,0.35)"), "abismo": ("#05101a", "rgba(20,80,120,0.35)"),
    "carbon": ("#111111", "rgba(90,90,90,0.25)"), "vino": ("#160810", "rgba(120,20,60,0.3)"),
    "bosque": ("#07140c", "rgba(30,110,60,0.3)"), "tinta": ("#0a0a1f", "rgba(50,50,160,0.35)"),
}
MELODIAS = {   # alturas (MIDI) de melodías de dominio público, registro medio-grave
    "rey_montana": [45, 47, 48, 50, 52, 48, 52, 51, 47, 51, 50, 46, 50, 45, 47, 48, 50, 52, 48, 52, 57, 55, 52, 48, 52, 55],
    "himno_alegria": [52, 52, 53, 55, 55, 53, 52, 50, 48, 48, 50, 52, 52, 50, 50, 52, 52, 53, 55, 55, 53, 52, 50, 48, 48, 50, 52, 50, 48, 48],
    "para_elisa": [64, 63, 64, 63, 64, 59, 62, 60, 57, 48, 52, 57, 59, 52, 56, 59, 60, 52, 64, 63, 64, 63, 64, 59, 62, 60, 57, 48, 52, 57, 59, 52, 60, 59, 57],
    "canon": [62, 66, 69, 57, 61, 64, 59, 62, 66, 54, 57, 61, 55, 59, 62, 50, 54, 57, 55, 59, 62, 57, 61, 64],
    "gymnopedie": [66, 69, 67, 66, 61, 59, 61, 62, 57, 66, 69, 67, 66, 61, 59, 61, 62, 64, 66, 69, 67, 66],
    "estrellita": [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60, 67, 67, 65, 65, 64, 64, 62, 67, 67, 65, 65, 64, 64, 62],
    "jingle_bells": [64, 64, 64, 64, 64, 64, 64, 67, 60, 62, 64, 65, 65, 65, 65, 65, 64, 64, 64, 64, 64, 62, 62, 64, 62, 67],
    "nana_brahms": [64, 64, 67, 64, 64, 67, 64, 67, 72, 71, 69, 69, 67, 62, 64, 65, 62, 62, 64, 65, 62, 65, 71, 69, 67, 71, 72],
    "frere_jacques": [60, 62, 64, 60, 60, 62, 64, 60, 64, 65, 67, 64, 65, 67, 67, 69, 67, 65, 64, 60, 67, 69, 67, 65, 64, 60, 60, 55, 60, 60, 55, 60],
}

DEFECTO = dict(segundos=30.0, fps=60, sub=4, r_in=0.15, r_out=1.08, n=30, rb=0.021, g=3.2, hueco=70.0, w0=1.1, dw=0.035,
               reverb=0.3, volumen=1.0, cama=False)


def disenar(fecha: dt.date, overrides: dict | None = None, historial: list[dict] | None = None, turno: int = 1) -> dict:
    ult = SB.ultimo(fecha, historial)
    rng = random.Random(f"anillos-{fecha.isoformat()}-{turno}")
    d = dict(DEFECTO)
    # (Pol 24-11: «no repitas nada nunca») la combinación paleta + melodía + fondo no se ha usado antes
    usadas = {(h.get("paleta"), h.get("melodia"), h.get("fondo")) for h in (historial or [])}
    recientes = [h.get("paleta") for h in (historial or [])][-4:] + [h.get("melodia") for h in (historial or [])][-3:]
    for _ in range(200):
        pal, mel, fon = rng.choice(list(PALETAS)), rng.choice(list(MELODIAS)), rng.choice(list(FONDOS))
        if (pal, mel, fon) not in usadas and pal not in recientes and mel not in recientes:
            break
    d.update(fecha=fecha.isoformat(), mecanismo=MECANISMO, paleta=pal, melodia=mel, fondo=fon,
             grosor=rng.choice([2.4, 3.0, 3.8]), n=rng.choice([22, 24, 28, 32, 36]),
             w0=round(rng.uniform(0.8, 1.3), 3) * rng.choice([1, -1]), semilla=rng.randrange(1 << 30))
    for k, v in (overrides or {}).items():
        if v is not None:
            d[k] = v
    d["slug"] = f"satisfy-{d['fecha']}-anillos-{d['paleta']}"
    return d


def _envolver(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _radios(d: dict) -> list[float]:
    n = d["n"]
    return [d["r_in"] + (d["r_out"] - d["r_in"]) * j / (n - 1) for j in range(n)]


def _simula(d: dict, semilla: int, hueco: float, dw: float, paso_fase: float = 0.9) -> dict:
    """(Pol 23-11) Con GRAVEDAD y anillos FIJOS: la bola cae y rebota dentro del anillo de dentro que queda; si llega por
    el hueco, SALE de verdad (sigue cayendo hacia el siguiente) y ese anillo se rompe. Si los huecos de varios anillos
    coinciden, atraviesa varios pisos seguidos. Tras el último, se escapa del todo."""
    rng = random.Random(semilla)
    fps, sub = d["fps"], d["sub"]
    dt_ = 1.0 / (fps * sub)
    rb, g = d["rb"], d["g"]
    R = _radios(d)
    hw = math.radians(hueco) / 2
    # todos los huecos empiezan casi alineados abajo y giran a velocidades un poco distintas: espiral que se abre y se
    # vuelve a alinear (los momentos en que coinciden = caída por varios pisos)
    g0 = [-math.pi / 2 + rng.uniform(-0.25, 0.25) + paso_fase * j for j in range(d["n"])]
    om = [d["w0"] + dw * j * (1 if j % 2 == 0 else 1) for j in range(d["n"])]
    x, y = rng.uniform(-0.03, 0.03), 0.0
    vx, vy = rng.uniform(-0.5, 0.5), 0.8
    k = 0
    F = int(round(d["segundos"] * fps))
    tray, ev, t_rot = [], [], []
    fuera = None
    for f in range(F):
        for s in range(sub):
            t = (f * sub + s) * dt_
            vy -= g * dt_
            x += vx * dt_
            y += vy * dt_
            if k < d["n"]:
                rr = math.hypot(x, y)
                lim = R[k] - rb - 0.004
                if rr > lim:
                    nx, ny = x / rr, y / rr
                    vn = vx * nx + vy * ny
                    if vn > 0:
                        ang = math.atan2(y, x)
                        hueco_k = g0[k] + om[k] * t
                        if abs(_envolver(ang - hueco_k)) < hw - math.asin(min(1, rb / rr)):
                            ev.append(dict(t=t, tipo="rompe", k=k, x=x, y=y))
                            t_rot.append(t)
                            k += 1
                            if k == d["n"]:
                                fuera = t
                        else:
                            vx -= 2 * vn * nx
                            vy -= 2 * vn * ny
                            # energía: rebota siempre con alegría (sin perder altura) y un pelín de azar
                            sp = math.hypot(vx, vy)
                            obj = max(sp, 2.1)
                            da = rng.uniform(-0.05, 0.05)
                            c, s_ = math.cos(da), math.sin(da)
                            vx, vy = (c * vx - s_ * vy) * obj / sp, (s_ * vx + c * vy) * obj / sp
                            x, y = nx * lim, ny * lim
                            ev.append(dict(t=t, tipo="toc", x=x, y=y, k=k))
        tray += [round(x, 4), round(y, 4)]
    return dict(tray=tray, ev=ev, rotos=k, t_rotura=t_rot, F=F, g0=g0, om=om, fuera=fuera)


def _cadenas(t_rot: list[float]) -> list[int]:
    """tamaños de las cadenas (roturas separadas < 0,12 s = la bola atraviesa varios pisos seguidos)"""
    out, c = [], 1
    for a, b in zip(t_rot, t_rot[1:]):
        if b - a < 0.12:
            c += 1
        else:
            out.append(c)
            c = 1
    if t_rot:
        out.append(c)
    return out


def plan(d: dict, log=print) -> dict:
    # busca la combinación que acaba bien: se rompen TODOS los anillos entre el segundo 24 y el 28,3 (da tiempo a ver la
    # bola escaparse), nunca más de 2,6 s sin romper ninguno, y con al menos 3 caídas de varios pisos seguidos
    mejor = None
    rng = random.Random(d["semilla"])
    for _ in range(400):
        sem = rng.randrange(1 << 30)
        hueco = rng.choice([72.0, 80.0, 90.0, 100.0])
        dw = rng.choice([0.0, 0.012, 0.025, 0.04])
        d["g"] = rng.choice([3.2, 4.2, 5.2])
        pf = rng.choice([0.3, 0.45, 0.6, 0.9])
        sim = _simula(d, sem, hueco, dw, pf)
        tr = [0.0] + sim["t_rotura"]
        hueco_max = max(b - a for a, b in zip(tr, tr[1:])) if len(tr) > 1 else 99
        cad = sum(1 for c in _cadenas(sim["t_rotura"]) if c >= 2)
        cad3 = sum(1 for c in _cadenas(sim["t_rotura"]) if c >= 3)
        fin = sim["fuera"] or 99
        nota = -abs(min(fin, 40) - 26.5) * 3 - 4 * max(0, hueco_max - 3.5) + min(cad, 6) + 3 * min(cad3, 4) - 5 * (d["n"] - sim["rotos"])
        if mejor is None or nota > mejor[0]:
            mejor = (nota, sim, hueco, dw, d["g"])
        if sim["rotos"] == d["n"] and 24.0 <= fin <= 28.3 and hueco_max <= 3.5 and cad >= 3 and cad3 >= 3:
            break
    _, sim, hueco, dw, d["g"] = mejor
    d["_sim"], d["hueco"], d["dw"] = sim, hueco, dw
    h0, h1 = PALETAS[d["paleta"]]
    return dict(fps=d["fps"], frames=int(round(d["segundos"] * d["fps"])), segundos=d["segundos"], estilo="anillos",
                radios=[round(r, 4) for r in _radios(d)], rb=d["rb"], g=d["g"], hueco=hueco, tray=sim["tray"], total=d["n"],
                g0=[round(a, 5) for a in sim["g0"]], om=[round(w, 5) for w in sim["om"]],
                t_rotura=[round(t, 5) for t in sim["t_rotura"]], tonos=[h0, h1], fuera=sim["fuera"],
                cadenas=_cadenas(sim["t_rotura"]), fondo=FONDOS[d.get("fondo", "noche")][0],
                halo=FONDOS[d.get("fondo", "noche")][1], grosor=d.get("grosor", 3.0))


def eventos(d: dict, pl: dict) -> list[dict]:
    mel = MELODIAS[d["melodia"]]
    ev, k = [], 0
    n_toc = 0
    for e in d["_sim"]["ev"]:
        pan = max(-0.7, min(0.7, e["x"] / 0.5 * 0.6))
        if e["tipo"] == "rompe":
            ev.append(dict(t=e["t"], tipo="nota", midi=mel[k % len(mel)], pan=pan, gain=1.0))
            ev.append(dict(t=e["t"], tipo="cristal", midi=mel[k % len(mel)] + 12, pan=pan, gain=0.5))
            k += 1
        else:
            n_toc += 1
            ev.append(dict(t=e["t"], tipo="toc", midi=0, pan=pan, gain=0.9 if e["tipo"] == "toc" else 0.6))
    # final: acorde grave cuando el contador llega a 0
    tf = d["_sim"]["t_rotura"][-1] if d["_sim"]["t_rotura"] else d["segundos"] - 2
    base = min(mel)
    for j, a in enumerate((0, 7, 12, 16 if base % 12 in (0, 5, 7) else 15)):
        ev.append(dict(t=tf + 0.12 + 0.05 * j, tipo="nota", midi=base + a, pan=(j - 1.5) * 0.25, gain=0.75))
    return sorted(ev, key=lambda e: e["t"])


def _kalimba(midi: float, rng) -> np.ndarray:
    """marimba/kalimba suave: fundamental larga, un parcial inarmónico corto y casi nada de agudos"""
    f = SB.midi_hz(midi)
    n = int(1.8 * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7) + 0.22 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.3)
         + 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.05) + 0.3 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t / 0.4))
    a = int(0.004 * SR)
    s[:a] *= np.linspace(0, 1, a)
    return s / np.abs(s).max()


def _toc(rng) -> np.ndarray:
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.018) + 0.4 * SB.ruido_filtrado(n, rng, 200, 1500) * np.exp(-t / 0.005)
    return s / np.abs(s).max()


def _cristal_suave(midi: float, rng) -> np.ndarray:
    """el anillo que se deshace: un «shhh» granulado corto, apagado"""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    s = SB.ruido_filtrado(n, rng, 400, 3000) * np.exp(-t / 0.08) * (1 + 0.6 * (rng.random(n) < 0.01))
    s += 0.3 * np.sin(2 * np.pi * SB.midi_hz(midi) * t) * np.exp(-t / 0.15)
    return s / np.abs(s).max()


def sintetiza(d: dict, ev: list[dict], segundos: float) -> np.ndarray:
    n = int(round(segundos * SR))
    seco = np.zeros((n, 2))
    rng = np.random.default_rng(d["semilla"])
    cache = {}
    tocs = [_toc(rng) for _ in range(6)]
    for j, e in enumerate(ev):
        if e["tipo"] == "nota":
            if e["midi"] not in cache:
                cache[e["midi"]] = _kalimba(e["midi"], rng)
            SB.mezcla_en(seco, cache[e["midi"]], e["t"], e["pan"], 0.5 * e["gain"])
        elif e["tipo"] == "cristal":
            SB.mezcla_en(seco, _cristal_suave(e["midi"], rng), e["t"], e["pan"], 0.12 * e["gain"])
        else:
            SB.mezcla_en(seco, tocs[j % 6], e["t"], e["pan"], 0.1 * e["gain"])
    for c in (0, 1):
        sp = np.fft.rfft(seco[:, c])
        fr = np.fft.rfftfreq(n, 1 / SR)
        sp *= 1 / (1 + (fr / 3500) ** 4)
        seco[:, c] = np.fft.irfft(sp, n)
    return SB.acaba(seco, d["semilla"], d["reverb"], d["volumen"], ir_seg=2.4, fade=0.6)


def revisa(d: dict, pl: dict, ev: list[dict], mix: np.ndarray) -> list[str]:
    sim = d.pop("_sim", None)
    fallos = []
    if np.abs(mix).max() > 0.95:
        fallos.append("el audio satura")
    if sim["rotos"] < d["n"]:
        fallos.append(f"solo rompe {sim['rotos']} de {d['n']} anillos (no se escapa)")
    if sim["fuera"] and not (22.0 <= sim["fuera"] <= 28.6):
        fallos.append(f"se escapa a los {sim['fuera']:.1f} s (tiene que ser hacia el final)")
    tr = [0.0] + sim["t_rotura"]
    if max(b - a for a, b in zip(tr, tr[1:])) > 4.8:
        fallos.append(f"{max(b - a for a, b in zip(tr, tr[1:])):.1f} s sin romper ningún anillo")
    if sum(1 for c in pl["cadenas"] if c >= 2) < 2:
        fallos.append("ninguna caída por varios pisos a la vez (lo más satisfactorio)")
    # coherencia: mientras quede un anillo, la bola está dentro de él (nunca atraviesa una parte sin hueco)
    xy = np.array(sim["tray"]).reshape(-1, 2)
    R = pl["radios"]
    k = 0
    for f in range(len(xy)):
        t = (f + 1) / d["fps"]                            # la posición guardada es la del final del fotograma
        while k < len(pl["t_rotura"]) and pl["t_rotura"][k] <= t:
            k += 1
        if k < len(R) and math.hypot(*xy[f]) > R[k] - d["rb"] + 0.012:
            fallos.append(f"la bola atraviesa el anillo {k} por donde no hay hueco ({t:.2f} s)")
            break
    return fallos


TITULOS = ("¿Llegará a 0? 🤯", "Cada anillo que rompe toca una nota 🎹", "Rompe todos los anillos… uno a uno",
           "No puedes dejar de mirarlo 👀")
NOMBRE_MELODIA = {"rey_montana": "En la gruta del rey de la montaña (Grieg)", "himno_alegria": "Himno de la alegría (Beethoven)",
                  "para_elisa": "Para Elisa (Beethoven)", "canon": "Canon (Pachelbel)", "gymnopedie": "Gymnopédie n.º 1 (Satie)", "estrellita": "Estrellita, ¿dónde estás?", "jingle_bells": "Jingle Bells", "nana_brahms": "la Nana de Brahms", "frere_jacques": "Frère Jacques"}


def publicacion(d: dict, pl: dict) -> str:
    rng = random.Random(d["slug"])
    desc = (f"Una bolita atrapada en {pl['total']} anillos que giran: cuando cae por un hueco, el anillo se rompe y suena la "
            f"siguiente nota de «{NOMBRE_MELODIA[d['melodia']]}». ¿Llegará a escaparse? 🎧 Mejor con cascos.")
    return f"{rng.choice(TITULOS)}\n\n{desc}\n\n#satisfying #asmr #oddlysatisfying #satisfyingvideo #shorts\n"


def resumen(d: dict, pl: dict, ev: list[dict]) -> str:
    return (f"{pl['total']} anillos · hueco {pl['hueco']:.0f}° · se escapa a los {pl['fuera'] or 0:.1f} s · cadenas "
            f"{[c for c in pl['cadenas'] if c > 1]} · melodía {d['melodia']} · paleta {d['paleta']}")
