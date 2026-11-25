"""Hush Satisfy Lab · ESTILO NUEVO (Pol 22-11): todos los Satisfy son ya como sus vídeos de referencia.

Cada día salen DOS, distintos entre sí:
  · PINZAS  (shorts/pinzas.py):  círculo blanco, pinzas que se cierran y duplican las bolas; de 1 bola a cientos.
  · ANILLOS (shorts/anillos.py): anillos con hueco alrededor de un contador; la bolita los rompe uno a uno hasta 0.
El orden se alterna por días y cada vídeo cambia paleta, número de pinzas, tamaño de bolas, huecos, velocidad, escala y
melodía (y nunca repite la paleta del anterior de su estilo). Plano fijo (Pol: en Satisfy, sin movimiento de cámara) y
sonidos graves y satisfactorios (nada agudo). Lo llama particulas.diario() (el lote de cada noche).
"""
from __future__ import annotations

import datetime as dt
import json
import random

from . import particulas as PF
from . import satisfy_base as SB

ESTILOS = ("pinzas", "anillos", "notas")   # (Pol 24-11) + notas: el cuadrado que toca una canción


def _modulo(estilo: str):
    import importlib
    return importlib.import_module(f".{estilo}", __package__)


def _registro_estilo(estilo: str) -> list[dict]:
    return [h for h in PF._registro() if h.get("mecanismo") == estilo]


def hecho(fecha: dt.date, turno: int) -> str | None:
    """Ya hecho si está en el registro (aunque el mp4 ya no exista: al programarlo se manda a la Papelera)."""
    for h in PF._registro():
        if h.get("fecha") == fecha.isoformat() and h.get("turno", 1) == turno and h.get("estilo2") and h.get("mp4"):
            return h["mp4"]
    return None


def estilo_de(fecha: dt.date, turno: int) -> str:
    """2 al día de 3 estilos, rotando: (pinzas, notas) · (anillos, pinzas) · (notas, anillos)… cada estilo 2 de cada 3 días"""
    pares = [("notas", "anillos"), ("pinzas", "notas"), ("anillos", "pinzas")]
    return pares[fecha.toordinal() % 3][0 if turno == 1 else 1]


def _apunta(M, d: dict, mp4: str, turno: int) -> None:
    hist = [h for h in PF._registro() if not ((h.get("fecha"), h.get("turno", 1)) == (d["fecha"], turno) and h.get("estilo2"))]
    fila = {"fecha": d["fecha"], "slug": d["slug"], "mecanismo": M.MECANISMO, "mp4": mp4, "turno": turno, "estilo2": True}
    for k in ("paleta", "escala", "melodia", "pinzas", "fondo"):
        if k in d:
            fila[k] = d[k]
    hist.append(fila)
    PF.REGISTRO.write_text(json.dumps(hist[-160:], ensure_ascii=False, indent=2), encoding="utf-8")


def producir(fecha: dt.date, turno: int, simular=False, log=print, sufijo: str = "", estilo: str | None = None) -> tuple[int, str | None]:
    estilo = estilo or estilo_de(fecha, turno)
    M = _modulo(estilo)
    d = M.disenar(fecha, None, _registro_estilo(estilo), turno=turno)
    d["turno"] = turno
    d["slug"] += sufijo
    log("\n" + "=" * 70 + f"\n  {M.NOMBRE.upper()} · {PF.MARCA} · {fecha.isoformat()} · vídeo {turno}\n" + "=" * 70)
    if simular:
        log(f"  {d['slug']} (simulación: no se ha generado nada)")
        return 0, None
    pl, fallos = SB.preparar(M, d, log)
    for intento in range(10):                      # (24-11) si la simulación no cumple, otra semilla (mismo diseño)
        if not fallos:
            break
        log(f"  (intento {intento + 1}: {'; '.join(fallos)[:160]} → otra semilla)")
        d["semilla"] = int(d.get("semilla", 1)) + 7919
        pl, fallos = SB.preparar(M, d, log)
    if fallos:
        for f in fallos:
            log(f"  ✗  {f}")
        log("  >> Control de calidad NO superado: no se renderiza (díselo a Claude).")
        return 1, None
    log("  ✓  Control previo OK: cada sonido = un suceso de la imagen, nada se sale, sin saturar.")
    mp4 = SB.renderizar(M, d, pl, log)
    if not mp4:
        log(f"  >> FALLÓ el render de {M.NOMBRE} (mira el error arriba).")
        return 1, None
    fallos = PF.comprueba_mp4(mp4, pl["segundos"])
    for f in fallos:
        log(f"  ✗  {f}")
    return (1 if fallos else 0), str(mp4) if not fallos else None, d, M, pl  # type: ignore[return-value]


def diario(simular=False, log=print, fecha: dt.date | None = None) -> int:
    hoy = fecha or dt.date.today()
    fallos = 0
    try:                                            # (Pol 25-11) primero lo que ya ha hecho GitHub (minutos gratis)
        from . import github_render
        if github_render.activo() and not simular:
            github_render.traer(hoy, log=log)
    except Exception as e:  # noqa: BLE001  (si falla, se hacen aquí como siempre)
        log(f"  GitHub: {e!r}")
    for turno in (1, 2):
        ya = hecho(hoy, turno)
        if ya:
            log(f"\n  Satisfy {turno} del {hoy.isoformat()} ya hecho: {ya}")
            continue
        r = producir(hoy, turno, simular=simular, log=log)
        if simular:
            continue
        codigo, mp4 = r[0], r[1]
        if codigo or not mp4:
            fallos += 1
            continue
        _, _, d, M, pl = r
        from .final import organiza
        fin = organiza(PF.CANAL, d["slug"], mp4, prefijo=f"{d['slug']}_")
        (fin / "publicacion.txt").write_text(M.publicacion(d, pl), encoding="utf-8")
        _apunta(M, d, str(fin / f"{d['slug']}.mp4"), turno)
        log(f"  >> OK: {fin / (d['slug'] + '.mp4')}")
    PF._limpia(hoy)
    return 1 if fallos else 0
