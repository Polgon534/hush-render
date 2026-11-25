"""Carpeta única de resultados (Pol, 13-11): da igual si el vídeo es 2D o 3D, todos acaban en

    videos-finales/<canal>/<slug>/
        <slug>.mp4
        publicacion.txt        (título + descripción + hashtags, si el storyboard trae el bloque "publicacion")
        miniatura.png          (si el storyboard trae "publicacion.miniatura")
        miniatura_B.png        (versión B para el test A/B de YouTube)
        miniatura_1280.png / miniatura_B_1280.png   (solo si el vídeo es horizontal: largo de Skin)

Antes cada canal se guardaba en un sitio distinto (out/SKIN, out/FOOTBALL, out/HISTORY, motor3d/out) y con
nombres distintos (publicar.txt, <slug>_publicar.txt...). organiza() junta todo eso en un solo sitio, con
el mismo nombre de archivo siempre, para que encontrarlos sea igual de fácil mires el canal que mires.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .config import ROOT

VIDEOS_FINALES = ROOT / "videos-finales"

# qué archivo de origen corresponde a qué nombre final (el primero que exista gana)
_COPIAS = {
    "publicacion.txt": ("publicar.txt",),
    "miniatura.png": ("miniatura.png",),
    "miniatura_B.png": ("miniatura_B.png",),
    "miniatura_1280.png": ("miniatura_1280.png",),
    "miniatura_B_1280.png": ("miniatura_B_1280.png",),
}


def organiza(canal: str, slug: str, mp4: str | Path, prefijo: str = "") -> Path:
    """Copia el mp4 y, si existen junto a él, publicar.txt/miniatura(s) a videos-finales/<canal>/<slug>/.

    `prefijo`: en motor3d/out los archivos se llaman "<slug>_publicar.txt", "<slug>_miniatura.png", etc.
    (varios vídeos comparten la carpeta out/); en out/<CANAL>/<slug>_elevenlabs/ no hay prefijo.
    """
    mp4 = Path(mp4)
    origen = mp4.parent
    destino = VIDEOS_FINALES / canal / slug
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mp4, destino / f"{slug}.mp4")
    for nombre_final, variantes in _COPIAS.items():
        for v in variantes:
            cand = origen / f"{prefijo}{v}"
            if cand.is_file():
                shutil.copy2(cand, destino / nombre_final)
                break
    return destino
