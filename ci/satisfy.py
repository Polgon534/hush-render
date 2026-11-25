"""Hush Satisfy Lab en GitHub Actions: los 2 Satisfy del día (mismo código que en el PC de Pol).

Uso:  python ci/satisfy.py [--fecha AAAA-MM-DD]
Deja en salida/:  <slug>.mp4, <slug>.txt (publicación) y particulas-usadas.json (registro para que nada se repita).
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

from shorts import particulas as PF  # noqa: E402
from shorts import satisfy2  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=None)
    a = ap.parse_args()
    fecha = dt.date.fromisoformat(a.fecha) if a.fecha else dt.datetime.now(ZoneInfo("Europe/Madrid")).date()
    print(f"Satisfy del {fecha.isoformat()}")
    rc = satisfy2.diario(fecha=fecha)
    sal = ROOT / "salida"
    sal.mkdir(exist_ok=True)
    n = 0
    for c in sorted((ROOT / "videos-finales" / PF.CANAL).glob(f"satisfy-{fecha.isoformat()}-*")):
        mp4 = c / f"{c.name}.mp4"
        if mp4.is_file():
            shutil.copy2(mp4, sal / mp4.name)
            pub = c / "publicacion.txt"
            if pub.is_file():
                shutil.copy2(pub, sal / f"{c.name}.txt")
            n += 1
    shutil.copy2(PF.REGISTRO, sal / "particulas-usadas.json")
    print(f"{n} vídeo(s) en salida/")
    return rc if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
