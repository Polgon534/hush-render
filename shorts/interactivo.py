"""Vídeos INTERACTIVOS (Pol 24-11): el 2.º vídeo diario de Skin, Football y History, hecho por el PC sin gastar límite
de Claude ni créditos de ElevenLabs (texto en pantalla + sonido sintetizado, como Satisfy).

  · Skin    → «Pon a prueba tu cerebro»: postimagen (mira el punto y luego la pared), efecto Troxler (los colores
              desaparecen), «lilac chaser» (aparece un punto verde que no existe) y «encuentra el distinto» (2 rondas).
              Todo programado: no hay datos que puedan estar mal.
  · Football / History → QUIZ de 4 preguntas con cuenta atrás y respuesta. Las preguntas salen de Wikipedia (es/en)
              con el modelo gratis (shorts/guionista_gemini.llamar) y OTRA llamada comprueba cada una contra el texto;
              la que no se pueda comprobar se tira. Si no quedan 4 buenas, ese día no hay quiz (mejor nada que un error).

    python -m shorts.interactivo [AAAA-MM-DD] [skin|football|history]     (sin canal: los 3)

Cada día es distinto: el tipo, la figura, los colores, el tema y la música cambian con la fecha y no se repiten
(registro en stories/interactivos-usados.json). Salen a videos-finales/<canal>/ con publicacion.txt → panel.
Render: composición Remotion «Interactivo2D» (motor3d/src/videos/interactivo/Interactivo2D.tsx), 1080x1920, 30 fps, 30 s.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

from . import particulas as PF
from . import satisfy_base as SB

ROOT = Path(__file__).resolve().parent.parent
REGISTRO = ROOT / "stories" / "interactivos-usados.json"
MECANISMO = "interactivo"
NOMBRE = "Interactivo"
COMPOSICION = "Interactivo2D"
RECORTA_FINAL = False      # (26-11) la ilusión necesita sus segundos tras el último sonido
SR = PF.SR
SEG, FPS = 30.0, 30
MARCAS = {"skin": "Hush Skin Lab", "football": "Hush Football Lab", "history": "Hush History Lab"}
CARPETA = {"skin": "skin", "football": "football", "history": "history"}
TIPOS_SKIN = ["postimagen", "stroop", "troxler", "encuentra", "lilac"]

TEMAS = {   # (Pol 24-11) temas que enganchen al público joven: récords, curiosidades, leyendas, dinero, momentos míticos
    "football": ["Copa Mundial de Fútbol (récords y curiosidades)", "Lionel Messi", "Cristiano Ronaldo", "Balón de Oro",
                 "Fichajes más caros de la historia del fútbol", "Liga de Campeones de la UEFA (récords)", "Pelé",
                 "Diego Armando Maradona", "Selección de fútbol de España (Mundial 2010 y Eurocopas)", "Estadios de fútbol más grandes",
                 "Kylian Mbappé", "Erling Haaland", "Zinedine Zidane", "Ronaldinho", "Clásico Real Madrid-Barcelona",
                 "Porteros de fútbol legendarios", "Remontadas históricas del fútbol", "Neymar", "Premier League (récords)",
                 "Andrés Iniesta"],
    "history": ["Titanic", "Antiguo Egipto y las pirámides", "Piratas famosos", "Gladiadores de Roma", "Vikingos",
                "Leonardo da Vinci", "Napoleón Bonaparte", "Carrera espacial y llegada a la Luna", "Cleopatra", "Inventos accidentales",
                "Espionaje en la Segunda Guerra Mundial", "Alejandro Magno", "Imperio romano", "Samuráis", "Caballeros templarios",
                "Gran Muralla China", "Julio César", "Pompeya", "Marco Polo", "Imperio azteca"],
}


# ============================================================ registro (para no repetir)
def _registro() -> list[dict]:
    try:
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    except Exception:
        return []


def _apunta(fila: dict) -> None:
    h = [x for x in _registro() if not (x.get("fecha") == fila["fecha"] and x.get("canal") == fila["canal"])]
    h.append(fila)
    REGISTRO.write_text(json.dumps(h[-400:], ensure_ascii=False, indent=1), encoding="utf-8")


def hecho(fecha: dt.date, canal: str) -> bool:
    return any(x.get("fecha") == fecha.isoformat() and x.get("canal") == canal and x.get("mp4") for x in _registro())


# ============================================================ diseño
def disenar(fecha: dt.date, canal: str, overrides: dict | None = None) -> dict:
    rng = random.Random(f"interactivo-{canal}-{fecha.isoformat()}")
    usados = [x for x in _registro() if x.get("canal") == canal]
    d = dict(fecha=fecha.isoformat(), canal=canal, segundos=SEG, fps=FPS, semilla=rng.randrange(1 << 30), cama=False,
             marca=MARCAS[canal], escala=rng.choice(["re_menor", "la_menor", "mi_menor", "do_mayor", "sol_mayor"]))
    if canal == "skin":
        ult = usados[-1]["tipo"] if usados else None
        tipos = [t for t in TIPOS_SKIN if t != ult]
        d["tipo"] = TIPOS_SKIN[fecha.toordinal() % len(TIPOS_SKIN)]
        if d["tipo"] == ult:
            d["tipo"] = tipos[fecha.toordinal() % len(tipos)]
        if d["tipo"] == "postimagen":
            d["figura"] = rng.choice(["corazon", "bandera", "atardecer", "bombilla", "estrella", "arcoiris"])
            d["cuenta"] = 20
        elif d["tipo"] == "troxler":
            d["n_manchas"] = rng.choice([8, 10, 12])
            d["paleta"] = rng.choice(["pastel", "vivos", "calidos", "frios"])
            d["cuenta"] = 20
        elif d["tipo"] == "stroop":
            colores = [("ROJO", "#ff3b3b"), ("AZUL", "#3b7bff"), ("VERDE", "#2ecc71"), ("AMARILLO", "#ffd23f"), ("ROSA", "#ff5fb4"), ("NARANJA", "#ff8c2a")]
            pal = []
            for k in range(14):
                w, c = rng.sample(colores, 2)
                pal.append(dict(palabra=w[0], color=c[1], nombre=c[0]))
            d["palabras"] = pal
        elif d["tipo"] == "lilac":
            d["color"] = rng.choice(["lila", "rosa", "azul"])
            d["cuenta"] = 20
        else:
            pares = [("O", "Q"), ("8", "B"), ("N", "M"), ("E", "F"), ("6", "9"), ("V", "U"), ("P", "R"), ("C", "G"), ("I", "l")]
            r1, r2 = rng.sample(pares, 2)
            d["rondas"] = [dict(base=r1[0], raro=r1[1], cols=8, filas=12, i=rng.randrange(96)),
                           dict(base=r2[0], raro=r2[1], cols=10, filas=15, i=rng.randrange(150))]
    else:
        d["tipo"] = "quiz"
        hechos = {x.get("tema") for x in usados}
        libres = [t for t in TEMAS[canal] if t not in hechos] or TEMAS[canal]
        d["tema"] = libres[fecha.toordinal() % len(libres)]
    for k, v in (overrides or {}).items():
        d[k] = v
    d["slug"] = f"{CARPETA[canal]}-{d['fecha']}-interactivo-{d['tipo']}"
    return d


# ============================================================ quiz (modelo gratis + Wikipedia + comprobación)
def preguntas(d: dict, log=print) -> list[dict] | None:
    from . import guionista_gemini as G
    canal, tema = d["canal"], d["tema"]
    fuentes = G.fuentes_wikipedia(tema, canal)
    if len(fuentes) < 1500:
        log(f"  quiz: pocas fuentes para «{tema}»"); return None
    extra = ("Nada de los últimos 10 años; nada violento ni morboso." if canal == "history"
             else "Solo hechos comprobables (años, récords, títulos, estadios, nacionalidades); nada de sueldos ni rumores.")
    for intento in range(3):
        try:
            txt = G.llamar(f"""Crea un QUIZ en español de España para un Short de {'fútbol' if canal == 'football' else 'historia'} sobre «{tema}».
Usa SOLO datos que estén escritos tal cual en los textos de Wikipedia de abajo. {extra}
8 preguntas SORPRENDENTES para un público joven de TikTok/Shorts (15-30 años): curiosidades, récords, cifras locas, anécdotas
y «esto no lo sabías», que den ganas de comentar. NADA de detalles de examen aburridos (traducciones, fechas de decretos,
nombres secundarios). Mejor: «¿Cuántos goles…?», «¿Qué le pasó a…?», «¿Cuánto costó…?», «¿Qué récord…?», «¿Por qué…?».
Ordénalas de la más fácil a la más difícil y que la respuesta NO se deduzca de la propia pregunta; opciones creíbles.
Cada pregunta tiene que entenderse sola, sin contexto (nada de «en la lista», «entre los citados», «cuántas veces aparece»).
Español de España impecable (revisa cada palabra: nada de palabras inventadas).
Cada pregunta: "q" (máx. 70 caracteres), "opciones" (3, máx. 22 caracteres cada una, plausibles, una correcta),
"correcta" (0, 1 o 2; repártelas), "dato" (curiosidad corta que se enseña al revelar, máx. 60 caracteres) y
"cita" (la frase EXACTA de los textos que lo demuestra).
Responde SOLO JSON: {{"preguntas": [...]}}

TEXTOS:
{fuentes[:40000]}""", G.MODELOS_ESCRIBIR, json_out=True, temp=0.5, calidad=True)
            qs = G._json(txt).get("preguntas", [])
        except Exception as e:
            log(f"  quiz: el modelo no respondió ({str(e)[:120]})"); continue
        buenas = []
        for q in qs:
            ops = [str(o).strip() for o in q.get("opciones", [])]
            if (len(ops) != 3 or len(set(o.lower() for o in ops)) != 3 or not isinstance(q.get("correcta"), int)
                    or not 0 <= q["correcta"] <= 2 or len(str(q.get("q", ""))) > 80 or max(len(o) for o in ops) > 26
                    or len(str(q.get("dato", ""))) > 72):
                continue
            cita = str(q.get("cita", ""))
            if len(cita) < 15 or cita[:40].lower() not in fuentes.lower():   # la cita tiene que estar de verdad en el texto
                continue
            buenas.append(dict(q=str(q["q"]).strip(), opciones=ops, correcta=q["correcta"], dato=str(q.get("dato", "")).strip(), cita=cita))
        if len(buenas) < 4:
            log(f"  quiz: solo {len(buenas)} preguntas con cita literal (intento {intento + 1})"); continue
        # segunda comprobación, independiente: ¿la respuesta marcada es la correcta según la cita?
        try:
            lista = "\n".join(f"{i}. {b['q']} → «{b['opciones'][b['correcta']]}» (otras: {', '.join(o for j, o in enumerate(b['opciones']) if j != b['correcta'])}). Cita: {b['cita']}"
                              for i, b in enumerate(buenas))
            r = G._json(G.llamar(f"""Eres un verificador muy estricto. Para cada pregunta, di si la respuesta marcada es CORRECTA y la
ÚNICA correcta según su cita (y según lo que sabes), si la pregunta es clara, se entiende sola, es interesante para un
público joven y está escrita en un español correcto (pregunta y opciones). Si falla cualquiera de esas cosas: false.
{lista}
Responde SOLO JSON: {{"ok": [true/false, ...]}} (una entrada por pregunta, en orden).""", G.MODELOS_RAPIDOS, json_out=True, temp=0.0, calidad=True))
            oks = r.get("ok", [])
            buenas = [b for b, ok in zip(buenas, oks) if ok is True]
        except Exception as e:
            log(f"  quiz: no se pudo verificar ({str(e)[:100]})"); continue
        if len(buenas) >= 4:
            # de fácil a difícil tal cual las dio; las 4 primeras verificadas
            return buenas[:4]
        log(f"  quiz: solo {len(buenas)} preguntas verificadas (intento {intento + 1})")
    return None


# ============================================================ línea de tiempo (la pinta Interactivo2D y suena igual)
def plan(d: dict) -> dict:
    pl = dict(tipo=d["tipo"], canal=d["canal"], segundos=SEG, fps=FPS, marca_canal=d["marca"], semilla=d["semilla"])
    for k in ("figura", "cuenta", "n_manchas", "paleta", "color", "rondas", "tema", "palabras"):
        if k in d:
            pl[k] = d[k]
    if "tema" in pl:
        pl["tema"] = pl["tema"].split(" (")[0]
    if d["tipo"] == "quiz":
        T0, TQ, TR = 2.4, 6.5, 2.0          # (Pol 24-11) más tiempo para pensar: 6,5 s por pregunta; 4 preguntas (~38 s)
        pl["intro"] = [0.0, T0]
        pl["bloques"] = []
        t = T0
        for i, q in enumerate(d["_preguntas"]):
            pl["bloques"].append(dict(n=i + 1, t0=round(t, 3), tr=round(t + TQ, 3), t1=round(t + TQ + TR, 3),
                                      q=q["q"], opciones=q["opciones"], correcta=q["correcta"], dato=q["dato"]))
            t += TQ + TR
        pl["segundos"] = round(t + 2.6, 3)
        pl["outro"] = [round(t, 3), pl["segundos"]]
    elif d["tipo"] == "stroop":
        pl["fases"] = [dict(t0=2.6, t1=14.0, nivel=1), dict(t0=14.6, t1=26.0, nivel=2)]
        pl["outro"] = [26.4, SEG]
    elif d["tipo"] == "encuentra":
        pl["fases"] = [dict(t0=2.2, t1=12.2, r=0), dict(t0=12.2, t1=14.2, r=0, revela=True),
                       dict(t0=14.2, t1=24.2, r=1), dict(t0=24.2, t1=26.4, r=1, revela=True)]
        pl["outro"] = [26.4, SEG]
    else:
        c = d.get("cuenta", 20)
        pl["intro"] = [0.0, 2.4]
        pl["mira"] = [2.4, 2.4 + c]
        pl["revela"] = [2.4 + c, 27.0]
        pl["outro"] = [27.0, SEG]
    return pl


def eventos(d: dict, pl: dict) -> list[dict]:
    ev = []
    if d["tipo"] == "quiz":
        ev.append(dict(t=0.05, tipo="whoosh"))
        for b in pl["bloques"]:
            ev.append(dict(t=b["t0"], tipo="whoosh"))
            for s in range(1, int(b["tr"] - b["t0"]) + 1):
                ev.append(dict(t=b["t0"] + s, tipo="tic", fuerte=(b["tr"] - b["t0"] - s) < 3))
            ev.append(dict(t=b["tr"], tipo="acierto"))
        ev.append(dict(t=pl["outro"][0], tipo="final"))
    elif d["tipo"] == "stroop":
        ev.append(dict(t=0.05, tipo="whoosh"))
        for f in pl["fases"]:
            ev.append(dict(t=f["t0"], tipo="whoosh"))
            n = 7
            for k in range(n):
                ev.append(dict(t=f["t0"] + k * (f["t1"] - f["t0"]) / n, tipo="tic", fuerte=k == n - 1))
            ev.append(dict(t=f["t1"], tipo="acierto"))
        ev.append(dict(t=pl["outro"][0], tipo="final"))
    elif d["tipo"] == "encuentra":
        ev.append(dict(t=0.05, tipo="whoosh"))
        for f in pl["fases"]:
            if f.get("revela"):
                ev.append(dict(t=f["t0"], tipo="acierto"))
            else:
                ev.append(dict(t=f["t0"], tipo="whoosh"))
                for s in range(1, 10):
                    ev.append(dict(t=f["t0"] + s, tipo="tic", fuerte=s >= 7))
        ev.append(dict(t=pl["outro"][0], tipo="final"))
    else:
        ev.append(dict(t=0.05, tipo="whoosh"))
        a, b = pl["mira"]
        for s in range(1, int(b - a)):
            ev.append(dict(t=a + s, tipo="tic", fuerte=(b - a - s) <= 3))
        ev.append(dict(t=b, tipo="revela"))
        ev.append(dict(t=pl["outro"][0], tipo="final"))
    return sorted(ev, key=lambda e: e["t"])


# ============================================================ sonido (grave y suave, nada agudo: como Satisfy)
def _env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)


def sintetiza(d: dict, ev: list[dict], segundos: float) -> np.ndarray:
    rng = np.random.default_rng(d["semilla"])
    n = int(segundos * SR)
    seco = np.zeros((n, 2))
    raiz = {"re_menor": 50, "la_menor": 45, "mi_menor": 52, "do_mayor": 48, "sol_mayor": 43}[d["escala"]]
    menor = "menor" in d["escala"]
    t = np.arange(n) / SR
    # cama: acorde grave que respira (tensión durante la cuenta atrás)
    acorde = [raiz, raiz + (3 if menor else 4), raiz + 7, raiz + 12]
    cama = sum(np.sin(2 * np.pi * SB.midi_hz(m - 12) * t + i) * (0.5 if i == 0 else 0.22) for i, m in enumerate(acorde))
    cama *= (0.55 + 0.45 * np.sin(2 * np.pi * t / 7.5)) * 0.055
    fade = np.minimum(1, np.minimum(t / 1.2, (segundos - t) / 1.5))
    seco += (cama * fade)[:, None] * 0.6
    seco += musica(d, segundos, raiz, menor) * fade[:, None]
    for e in ev:
        if e["tipo"] == "tic":
            m = int(0.06 * SR)
            s = SB.ruido_filtrado(m, rng, 600, 2400) * _env(m, 0.001, 0.012) * (0.5 if e.get("fuerte") else 0.32)
            s += np.sin(2 * np.pi * (220 if e.get("fuerte") else 160) * np.arange(m) / SR) * _env(m, 0.001, 0.03) * 0.3
            SB.mezcla_en(seco, s, e["t"], 0.0, 1.0)
        elif e["tipo"] == "whoosh":
            m = int(0.7 * SR)
            env = np.sin(np.linspace(0, np.pi, m)) ** 2
            s = SB.ruido_filtrado(m, rng, 200, 1500) * env * 0.22
            SB.mezcla_en(seco, s, max(0.0, e["t"] - 0.35), 0.0, 1.0)
        elif e["tipo"] in ("acierto", "revela", "final"):
            notas = [raiz + 12, raiz + 19, raiz + 24] if e["tipo"] != "final" else [raiz + 12, raiz + 16 - menor, raiz + 19, raiz + 24]
            for j, mm in enumerate(notas):
                m = int(1.6 * SR)
                tt = np.arange(m) / SR
                s = (np.sin(2 * np.pi * SB.midi_hz(mm) * tt) + 0.25 * np.sin(2 * np.pi * SB.midi_hz(mm) * 2.01 * tt)) * _env(m, 0.004, 0.45) * 0.22
                SB.mezcla_en(seco, s, e["t"] + 0.07 * j, (-0.3, 0.0, 0.3, 0.0)[j % 4], 1.0)
    mix = SB.acaba(seco, d["semilla"], 0.25)
    pico = float(np.abs(mix).max()) or 1.0
    return mix * (0.89 / pico)


def musica(d: dict, segundos: float, raiz: int, menor: bool) -> np.ndarray:
    """(Pol 24-11) musiquita de fondo propia (sintetizada aquí: gratis y sin derechos): bombo suave, charles, bajo y un
    arpegio pegadizo sobre una progresión que cambia cada día; más intensa en el último tercio."""
    rng = np.random.default_rng(d["semilla"] + 11)
    bpm = float(rng.choice([100, 106, 112, 118]))
    beat = 60.0 / bpm
    n = int(segundos * SR)
    out = np.zeros((n, 2))
    prog = [[0, 8, 3, 10], [0, 5, 8, 7], [0, 10, 8, 7], [0, 3, 8, 10]][int(rng.integers(4))] if menor else \
           [[0, 7, 9, 5], [0, 5, 9, 7], [0, 9, 5, 7], [0, 4, 9, 5]][int(rng.integers(4))]
    tercera = 3 if menor else 4
    patron = [0, 2, 1, 2, 0, 2, 1, 3][: 8] if rng.random() < 0.5 else [0, 1, 2, 1, 3, 2, 1, 2]
    nb = int(segundos / beat) + 1

    def nota(hz, dur, a, r, amp, armonicos=(1.0, 0.3, 0.1)):
        m = int(dur * SR)
        tt = np.arange(m) / SR
        w = sum(h * np.sin(2 * np.pi * hz * (i + 1) * tt) for i, h in enumerate(armonicos))
        return w * _env(m, a, r) * amp

    for b in range(nb):
        t0 = b * beat
        if t0 >= segundos:
            break
        compas = int(b // 4)
        grado = prog[compas % 4]
        sube = 1.0 if t0 < segundos * 0.62 else 1.35
        # bombo (grave y redondo) en cada pulso; charles en las corcheas a contratiempo
        m = int(0.25 * SR)
        tt = np.arange(m) / SR
        kick = np.sin(2 * np.pi * (48 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * 0.32 * sube
        SB.mezcla_en(out, kick, t0, 0.0, 1.0)
        m = int(0.05 * SR)
        hat = SB.ruido_filtrado(m, rng, 5000, 11000) * _env(m, 0.001, 0.012) * 0.045 * sube
        SB.mezcla_en(out, hat, t0 + beat / 2, 0.25, 1.0)
        # bajo: la fundamental del acorde en el pulso 1 y 3
        if b % 2 == 0:
            SB.mezcla_en(out, nota(SB.midi_hz(raiz - 12 + grado), beat * 1.9, 0.01, 0.35, 0.16, (1.0, 0.45, 0.15)), t0, 0.0, 1.0)
        # arpegio pegadizo (corcheas) con las notas del acorde
        acorde = [raiz + 12 + grado, raiz + 12 + grado + tercera, raiz + 12 + grado + 7, raiz + 24 + grado]
        for k2 in range(2):
            mm = acorde[patron[(b * 2 + k2) % len(patron)]]
            SB.mezcla_en(out, nota(SB.midi_hz(mm), beat * 0.6, 0.004, 0.16, 0.075 * sube, (1.0, 0.18, 0.05)),
                         t0 + k2 * beat / 2, (-0.35, 0.35)[k2], 1.0)
    return out


def revisa(d: dict, pl: dict, ev: list[dict], mix: np.ndarray) -> list[str]:
    f = []
    if np.abs(mix).max() > 0.95:
        f.append("el audio satura")
    if d["tipo"] == "quiz":
        if len(pl.get("bloques", [])) != 4:
            f.append("el quiz no tiene 4 preguntas")
        for b in pl.get("bloques", []):
            if len(b["q"]) > 80 or max(len(o) for o in b["opciones"]) > 26:
                f.append(f"texto demasiado largo en la pregunta {b['n']}")
    if not 20 <= pl["segundos"] <= 45:
        f.append(f"dura {pl['segundos']} s")
    return f


def resumen(d: dict, pl: dict, ev: list[dict]) -> str:
    return f"{d['canal']} · {d['tipo']} · " + (f"tema «{d['tema']}»" if d["tipo"] == "quiz" else
                                              f"{d.get('figura') or d.get('paleta') or d.get('color') or ('palabras' if 'palabras' in d else 'rondas')}")


# ============================================================ publicación
def publicacion(d: dict, pl: dict) -> str:
    rng = random.Random(d["slug"])
    if d["tipo"] == "postimagen":
        tit = rng.choice(["Mira el punto 20 s y verás COLORES que no existen", "Tu cerebro PINTA esta imagen: mira el punto",
                          "Este truco ENGAÑA a tus ojos en 20 segundos"])
        desc = ("👁️ Mira el punto 20 segundos sin parpadear y luego la pantalla clara.\n"
                "🧠 Los conos de tu retina se cansan de un color y tu cerebro pinta el contrario: es una postimagen.\n"
                "¿La has visto en color? Dímelo en comentarios 👇")
    elif d["tipo"] == "troxler":
        tit = rng.choice(["Mira la cruz y los colores DESAPARECEN", "Tu cerebro BORRA estos colores en 20 s",
                          "No muevas los ojos: los colores se van a ESFUMAR"])
        desc = ("👁️ Mira la cruz fijamente sin mover los ojos.\n"
                "🧠 Efecto Troxler: tu cerebro deja de ver lo que no cambia y está borroso.\n¿Han desaparecido? 👇")
    elif d["tipo"] == "lilac":
        tit = rng.choice(["Mira la cruz: aparece un punto VERDE que no existe", "Este punto VERDE no existe… pero lo vas a ver",
                          "Ilusión ÓPTICA: mira la cruz 20 segundos"])
        desc = ("👁️ Mira la cruz y no muevas los ojos.\n"
                "🧠 Es el «lilac chaser»: cada hueco deja una postimagen verde y tu cerebro la ve girar.\n¿Lo has visto? 👇")
    elif d["tipo"] == "stroop":
        tit = rng.choice(["Di el COLOR, no la palabra: ¿lo consigues?", "Tu cerebro FALLA en este test de colores",
                          "Test de colores: casi nadie llega al final SIN FALLAR"])
        desc = ("🎨 Di en voz alta el COLOR de cada palabra, no lo que pone. Nivel 1 y nivel 2 (más rápido).\n"
                "🧠 Es el efecto Stroop: leer es tan automático que tu cerebro se pelea consigo mismo.\n¿Has fallado alguna? 👇")
    elif d["tipo"] == "encuentra":
        tit = rng.choice(["Encuentra la letra DISTINTA en 10 segundos", "Solo los de vista de LINCE encuentran las dos",
                          "¿Encuentras el carácter DISTINTO? 2 rondas"])
        desc = "👀 Dos rondas, 10 segundos cada una. ¿Las has encontrado las dos? Dímelo en comentarios 👇"
    else:
        tema = d["tema"]
        tema = tema.split(" (")[0]
        tit = rng.choice([f"Quiz de {tema}: ¿aciertas las 4?", f"4 PREGUNTAS sobre {tema}", f"¿Sabes tanto de {tema}? QUIZ"])
        if len(tit) > 60:
            tit = "QUIZ: ¿aciertas las 4 preguntas?"
        desc = (f"🧠 Quiz de {tema}: 4 preguntas con cuenta atrás.\n"
                "¿Cuántas has acertado? Dímelo en comentarios 👇 (datos de Wikipedia)")
    tags = {"skin": "#cerebro #ilusionoptica #curiosidades #shorts", "football": "#futbol #quiz #football #shorts",
            "history": "#historia #quiz #curiosidades #shorts"}[d["canal"]]
    return f"{tit}\n\n{desc}\n\n{tags}\n"


# ============================================================ producción
def producir(fecha: dt.date, canal: str, log=print) -> str | None:
    d = disenar(fecha, canal)
    log("\n" + "=" * 70 + f"\n  INTERACTIVO · {MARCAS[canal]} · {fecha.isoformat()} · {d['tipo']}\n" + "=" * 70)
    if d["tipo"] == "quiz":
        qs = preguntas(d, log)
        if not qs:
            log("  >> Sin 4 preguntas comprobadas: hoy no hay quiz (mejor nada que un dato mal).")
            return None
        d["_preguntas"] = qs
    import sys as _s
    M = _s.modules[__name__]
    pl, fallos = SB.preparar(M, d, log)
    if fallos:
        for f in fallos:
            log(f"  ✗  {f}")
        return None
    mp4 = SB.renderizar(M, d, pl, log)
    if not mp4:
        log("  >> FALLÓ el render del interactivo."); return None
    fallos = PF.comprueba_mp4(mp4, pl["segundos"])
    fallos = [f for f in fallos if "negros" not in f]          # (el fondo oscuro del quiz no es un fotograma negro)
    if fallos:
        for f in fallos:
            log(f"  ✗  {f}")
        return None
    from .final import organiza
    fin = organiza(CARPETA[canal], d["slug"], mp4, prefijo=f"{d['slug']}_")
    (fin / "publicacion.txt").write_text(publicacion(d, pl), encoding="utf-8")
    if d["tipo"] == "quiz":
        (fin / "preguntas.json").write_text(json.dumps(d["_preguntas"], ensure_ascii=False, indent=1), encoding="utf-8")
    _apunta(dict(fecha=d["fecha"], canal=canal, tipo=d["tipo"], tema=d.get("tema"), slug=d["slug"], mp4=str(fin / f"{d['slug']}.mp4")))
    log(f"  >> OK: {fin / (d['slug'] + '.mp4')}")
    return str(fin)


def diario(fecha: dt.date | None = None, log=print) -> int:
    hoy = fecha or dt.date.today()
    mal = 0
    for canal in ("skin", "football", "history"):
        if hecho(hoy, canal):
            log(f"  Interactivo de {canal} del {hoy} ya hecho"); continue
        try:
            if not producir(hoy, canal, log):
                mal += 1
        except Exception as e:      # nunca tumba el lote
            log(f"  ✗  interactivo {canal}: {e!r}"); mal += 1
    return 1 if mal else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    f = dt.date.fromisoformat(a[0]) if a and a[0][:2] == "20" else dt.date.today()
    c = [x for x in a if x in MARCAS]
    if c:
        print(producir(f, c[0]))
    else:
        print(diario(f))
