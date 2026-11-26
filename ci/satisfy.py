"""Vídeos sin voz del día en GitHub Actions (mismo código que el PC de Pol):
  · Hush Satisfy Lab: los 2 Satisfy (pinzas, anillos, notas).
  · Hush Skin Lab: 1 interactivo (ilusiones: postimagen, troxler, lilac, stroop, encuentra; sin quiz).

Uso:  python ci/satisfy.py [--fecha AAAA-MM-DD]
Deja en salida/: <slug>.mp4, <slug>.txt (publicación) y los registros (para que nada se repita).
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shorts import interactivo  # noqa: E402
from shorts import particulas as PF  # noqa: E402
from shorts import satisfy2  # noqa: E402

CANALES_INTERACTIVO = ("skin",)        # (Pol 26-11) los quiz no funcionan; las ilusiones de Skin sí


def _copia(carpeta: Path, prefijo: str, sal: Path) -> int:
    n = 0
    for c in sorted(carpeta.glob(prefijo)):
        mp4 = c / f"{c.name}.mp4"
        if mp4.is_file():
            shutil.copy2(mp4, sal / mp4.name)
            if (c / "publicacion.txt").is_file():
                shutil.copy2(c / "publicacion.txt", sal / f"{c.name}.txt")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=None)
    a = ap.parse_args()
    fecha = dt.date.fromisoformat(a.fecha) if a.fecha else dt.datetime.now(ZoneInfo("Europe/Madrid")).date()
    F = fecha.isoformat()
    print(f"Vídeos sin voz del {F}")
    satisfy2.diario(fecha=fecha)
    for canal in CANALES_INTERACTIVO:
        try:
            if not interactivo.hecho(fecha, canal):
                interactivo.producir(fecha, canal)
        except Exception as e:  # noqa: BLE001  (un interactivo roto no tumba los Satisfy)
            print(f"  ✗  interactivo {canal}: {e!r}")
    sal = ROOT / "salida"
    sal.mkdir(exist_ok=True)
    vf = ROOT / "videos-finales"
    n = _copia(vf / PF.CANAL, f"satisfy-{F}-*", sal)
    for canal in CANALES_INTERACTIVO:
        n += _copia(vf / interactivo.CARPETA[canal], f"{canal}-{F}-interactivo-*", sal)
    shutil.copy2(PF.REGISTRO, sal / "particulas-usadas.json")
    if interactivo.REGISTRO.is_file():
        shutil.copy2(interactivo.REGISTRO, sal / "interactivos-usados.json")
    print(f"{n} vídeo(s) en salida/")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
