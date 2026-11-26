"""Base común de los mecanismos nuevos de Hush Satisfy Lab (20-11): péndulos, vasos y espiral.

Cada mecanismo es un módulo con:
    MECANISMO, NOMBRE, COMPOSICION (id de Remotion)
    disenar(fecha, overrides, historial) -> d        (determinista: misma fecha → mismo vídeo)
    plan(d) -> pl                                     (la tabla que pinta Three.js; incluye «planos»)
    eventos(d, pl) -> [ {t, ...} ]                    (cada sonido sale de un suceso de esa MISMA tabla)
    sintetiza(d, ev, segundos) -> mix estéreo
    revisa(d, pl, ev, mix) -> [fallos]
    publicacion(d, pl) -> texto
    resumen(d, pl, ev) -> línea de log
Este módulo hace el resto igual que el Galton: plan.json + audio.wav → Remotion mudo → FFmpeg une el audio exacto →
control final → videos-finales/satisfy/ → registro.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import subprocess
from pathlib import Path

import numpy as np

from . import particulas as PF

SR = PF.SR


# ============================================================ utilidades de diseño
def ultimo(fecha: dt.date, historial: list[dict] | None) -> dict:
    hist = historial if historial is not None else PF._registro()
    previos = sorted([h for h in hist if h.get("fecha", "") < fecha.isoformat()], key=lambda h: h.get("fecha", ""))
    return previos[-1] if previos else {}


def elige(rng: random.Random, opciones, evita=None):
    ops = [o for o in opciones if o != evita] or list(opciones)
    return rng.choice(ops)


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def escala_notas(grados: list[int], tonica: int, n: int) -> list[int]:
    return [tonica + 12 * (i // len(grados)) + grados[i % len(grados)] for i in range(n)]


# ============================================================ utilidades de sonido
def mezcla_en(seco: np.ndarray, s: np.ndarray, t: float, pan: float, gain: float = 1.0) -> None:
    n = len(seco)
    i0 = int(round(t * SR))
    if i0 >= n or i0 < 0:
        return
    a = (max(-1.0, min(1.0, pan)) + 1) * math.pi / 4
    m = min(len(s), n - i0)
    seco[i0:i0 + m, 0] += s[:m] * math.cos(a) * gain
    seco[i0:i0 + m, 1] += s[:m] * math.sin(a) * gain


def ruido_filtrado(n: int, rng: np.random.Generator, lo: float, hi: float) -> np.ndarray:
    x = rng.standard_normal(n)
    sp = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    sp *= ((fr > lo) & (fr < hi)) * 1.0
    y = np.fft.irfft(sp, n)
    return y / (np.abs(y).max() + 1e-9)


def acaba(seco: np.ndarray, semilla: int, reverb: float, volumen: float = 1.0, ir_seg: float = 2.8,
          comprime: bool = True, fade: float = 0.6) -> np.ndarray:
    """Compresión suave de densidad + reverb + fundido final + pico a −1 dBFS (igual que el Particle Flow)."""
    if comprime:
        w = int(0.25 * SR)
        env = np.sqrt(np.convolve((seco ** 2).mean(1), np.ones(w) / w, "same")) + 1e-4
        ref = np.percentile(env[env > 1e-3], 60) if (env > 1e-3).any() else 1.0
        seco = seco * (np.clip(ref / env, 0.35, 1.0) ** 0.6)[:, None]
    ir = PF._reverb_ir(ir_seg, semilla)
    hum = np.c_[PF._convolve(seco[:, 0], ir[:, 0]), PF._convolve(seco[:, 1], ir[:, 1])]
    mix = seco + reverb * hum * (np.abs(seco).max() / (np.abs(hum).max() + 1e-9))
    if fade > 0:
        k = int(fade * SR)
        mix[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    mix *= (10 ** (-1.0 / 20)) / max(np.abs(mix).max(), 1e-9) * min(1.0, volumen)
    return mix


# ============================================================ cama armónica (Pol 22-11: «más satisfactorio al oído»)
CAMAS = ("calida", "cristal", "coro")


def cama(ev: list[dict], segundos: float, semilla: int, ref: np.ndarray, nivel_db: float = -19.0) -> np.ndarray:
    """Un «pad» muy suave con las notas que más suenan en el vídeo (las mismas de los golpes, una octava o dos más
    graves), que respira despacio y se agacha un poco con cada golpe. Rellena los huecos sin tapar nada y hace que todo
    suene a una pieza. En BUCLE: el final empalma con el principio sin clic (fundido cruzado)."""
    midis = [int(e["midi"]) for e in ev if e.get("midi")]
    n = int(segundos * SR)
    if not midis or n <= 0:
        return np.zeros((n, 2), np.float32)
    from collections import Counter
    pcs = [pc for pc, _ in Counter(m % 12 for m in midis).most_common(3)]
    base = min(midis)
    notas = sorted({48 + ((pc - 48) % 12) for pc in pcs})                 # do3..si3
    if base % 12 not in pcs:
        notas.insert(0, 36 + base % 12)
    else:
        notas.insert(0, 36 + pcs[0])                                       # la mas frecuente, abajo (raiz)
    rng = random.Random(semilla * 7 + 3)
    tipo = CAMAS[semilla % len(CAMAS)]
    extra = int(2.0 * SR)
    m = n + extra
    t = np.arange(m) / SR
    out = np.zeros((m, 2), np.float32)
    parciales = {"calida": [(1, 1.0), (2, 0.35), (3, 0.12)], "cristal": [(1, 0.8), (2, 0.25), (4, 0.2), (6, 0.08)],
                 "coro": [(1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15), (5, 0.08)]}[tipo]
    for i, nm in enumerate(notas):
        f0 = midi_hz(nm)
        for lado in (0, 1):
            det = 2 ** ((rng.uniform(-4, 4)) / 1200)
            fase = rng.uniform(0, 2 * math.pi)
            s = sum(a * np.sin(2 * math.pi * f0 * k * det * t + fase * k) for k, a in parciales)
            ciclos = max(1, round(segundos * rng.uniform(0.06, 0.12)))     # respiracion lenta (ciclos enteros: bucle)
            lfo = 0.75 + 0.25 * np.sin(2 * math.pi * ciclos * t / segundos + rng.uniform(0, 6.28))
            out[:, lado] += (s * lfo / (1.6 + i * 0.4)).astype(np.float32)
    # suaviza arriba (pasa bajos por FFT) para que sea cama y no melodia
    for lado in (0, 1):
        sp = np.fft.rfft(out[:, lado]); fr = np.fft.rfftfreq(m, 1 / SR)
        sp *= 1 / (1 + (fr / (1400 if tipo != "cristal" else 2600)) ** 4)
        out[:, lado] = np.fft.irfft(sp, m).astype(np.float32)
    # bucle: los 2 s extra se funden sobre el principio
    k = np.linspace(0, 1, extra, dtype=np.float32)[:, None]
    out[:extra] = out[:extra] * k + out[n:n + extra] * (1 - k)
    out = out[:n]
    # se agacha con cada golpe (respira con el ritmo, «sidechain» suave)
    env = np.ones(n, np.float32)
    for e in ev:
        i0 = int(e["t"] * SR)
        if 0 <= i0 < n:
            L = min(int(0.35 * SR), n - i0)
            env[i0:i0 + L] = np.minimum(env[i0:i0 + L], 1 - 0.35 * np.exp(-np.arange(L) / (0.12 * SR)))
    out *= env[:, None]
    r_ref = math.sqrt(float((ref ** 2).mean()) + 1e-12)
    r_out = math.sqrt(float((out ** 2).mean()) + 1e-12)
    return out * (r_ref / r_out * 10 ** (nivel_db / 20))


def revisa_audio(ev: list[dict], mix: np.ndarray, segundos: float) -> list[str]:
    fallos = []
    if np.abs(mix).max() > 0.95:
        fallos.append("el audio satura")
    if not ev:
        fallos.append("no hay sonidos")
        return fallos
    if any(e["t"] < 0 or e["t"] > segundos for e in ev):
        fallos.append("hay sonidos fuera del vídeo")
    # ningún hueco de silencio de más de 1,2 s (que no se quede «muerto»)
    ts = sorted(e["t"] for e in ev)
    huecos = np.diff([0.0] + ts)
    if (huecos > 1.6).any():
        fallos.append(f"hueco de {huecos.max():.1f} s sin ningún sonido")
    return fallos


# ============================================================ producción
COLA_FINAL = 1.3      # segundos que se deja sonar después del último golpe


def _carpeta(d: dict) -> Path:
    return PF.PUBLIC / d["slug"]


def preparar(M, d: dict, log=print) -> tuple[dict, list[str]]:
    pl = M.plan(d)
    ev = M.eventos(d, pl)
    # (Pol 25-11) nada de segundos muertos al final: el vídeo acaba ~1,3 s después del último sonido (lo justo para que
    # se apague la reverb), así la gente lo ve hasta el final y no desliza en un plano quieto.
    if ev and getattr(M, "RECORTA_FINAL", True):
        corte = round(max(e["t"] for e in ev) + COLA_FINAL, 3)
        if corte < pl["segundos"] - 0.25:
            log(f"  final recortado: {pl['segundos']:.1f} s -> {corte:.1f} s (sin plano quieto)")
            pl["segundos"] = corte
            pl["frames"] = int(round(corte * pl["fps"]))
    mix = M.sintetiza(d, ev, pl["segundos"])
    if d.get("cama", True):                                   # (22-11) cama armonica suave debajo de los golpes
        pico = float(np.abs(mix).max()) or 1.0
        mix = mix + cama(ev, pl["segundos"], int(d.get("semilla", 1)), mix)[: len(mix)]
        mix *= pico / max(float(np.abs(mix).max()), 1e-9)
        log(f"  cama armonica: {CAMAS[int(d.get('semilla', 1)) % len(CAMAS)]}")
    fallos = M.revisa(d, pl, ev, mix)
    c = _carpeta(d)
    c.mkdir(parents=True, exist_ok=True)
    pl["audio"] = f"particulas/{d['slug']}/audio.wav"
    pl["marca"] = PF.MARCA
    pl["mecanismo"] = M.MECANISMO
    publico = {k: v for k, v in pl.items() if not k.startswith("_")}      # lo interno (con «_») no va al plan
    (c / "plan.json").write_text(json.dumps(publico, separators=(",", ":")), encoding="utf-8")
    PF.guarda_wav(c / "audio.wav", mix)
    (c / "diseno.json").write_text(json.dumps({k: v for k, v in d.items() if not k.startswith("_")}, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    log("  " + M.resumen(d, pl, ev) + f" · pico {20 * math.log10(np.abs(mix).max() + 1e-12):.1f} dBFS")
    return pl, fallos


def renderizar(M, d: dict, pl: dict, log=print) -> Path | None:
    slug = d["slug"]
    MM = PF.MOTOR3D
    (MM / "out").mkdir(exist_ok=True)
    props = MM / "out" / f"{slug}_props.json"
    props.write_text(json.dumps({"plan": f"particulas/{slug}/plan.json", "mute": True}), encoding="utf-8")
    if not (MM / "node_modules").is_dir():
        if subprocess.run("npm install --no-audit --no-fund", cwd=MM, shell=True).returncode != 0:
            return None
    nav = f' --browser-executable="{PF._chrome()}"' if PF._chrome() else ""
    gl = os.environ.get("PARTICULAS_GL", "angle")
    nav += " " + os.environ.get("PARTICULAS_EXTRA", "")
    mudo, mp4 = MM / "out" / f"{slug}_mudo.mp4", MM / "out" / f"{slug}.mp4"
    r = subprocess.run(f'npx remotion render src/index.ts {M.COMPOSICION} "out/{slug}_mudo.mp4" --props="out/{slug}_props.json" '
                       f'--gl={gl} --timeout=240000 --codec=h264 --crf=16 --muted{nav}', cwd=MM, shell=True)
    if r.returncode != 0 or not mudo.is_file():
        return None
    wav = _carpeta(d) / "audio.wav"
    # (Pol 23-11: en el panel «se para todo el rato») se recomprime a un bitrate que cualquier navegador/móvil reproduce
    # fluido (antes iba a CRF 16 sin tope: picos enormes con tantas líneas finas a 60 fps)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mudo), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
                        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
                        "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                        "-shortest", str(mp4)])
    if r.returncode != 0 or not mp4.is_file():
        log("  ✗  FFmpeg no pudo unir el audio")
        return None
    mudo.unlink(missing_ok=True)
    return mp4


def apunta(M, d: dict, mp4: str) -> None:
    hist = [h for h in PF._registro() if h.get("fecha") != d["fecha"]]
    fila = {"fecha": d["fecha"], "slug": d["slug"], "mecanismo": M.MECANISMO, "mp4": mp4}
    for k in ("paleta", "escala", "variante"):
        if k in d:
            fila[k] = d[k]
    hist.append(fila)
    PF.REGISTRO.write_text(json.dumps(hist[-120:], ensure_ascii=False, indent=2), encoding="utf-8")


def producir(M, fecha: dt.date | None = None, overrides: dict | None = None, simular=False, solo_plan=False, log=print) -> int:
    fecha = fecha or dt.date.today()
    d = M.disenar(fecha, overrides)
    log("\n" + "=" * 70 + f"\n  {M.NOMBRE.upper()} · {PF.MARCA} · {fecha.isoformat()}\n" + "=" * 70)
    if simular:
        log(f"  {d['slug']} (simulación: no se ha generado nada)")
        return 0
    pl, fallos = preparar(M, d, log)
    if fallos:
        for f in fallos:
            log(f"  ✗  {f}")
        log("  >> Control de calidad NO superado: no se renderiza (díselo a Claude).")
        return 1
    log("  ✓  Control previo OK: cada sonido = un suceso de la imagen, bucle limpio, sin saturar.")
    if solo_plan:
        return 0
    mp4 = renderizar(M, d, pl, log)
    if not mp4:
        log(f"  >> FALLÓ el render de {M.NOMBRE} (mira el error arriba).")
        return 1
    fallos = PF.comprueba_mp4(mp4, pl["segundos"])
    for f in fallos:
        log(f"  ✗  {f}")
    from .final import organiza
    fin = organiza(PF.CANAL, d["slug"], mp4, prefijo=f"{d['slug']}_")
    (fin / "publicacion.txt").write_text(M.publicacion(d, pl), encoding="utf-8")
    if fallos:
        log(f"  >> REVISAR: {fin / (d['slug'] + '.mp4')} no pasa el control final (arriba). Díselo a Claude.")
        return 1
    apunta(M, d, str(fin / f"{d['slug']}.mp4"))
    PF._limpia(dt.date.today())
    log(f"  >> OK: {fin / (d['slug'] + '.mp4')}")
    return 0
