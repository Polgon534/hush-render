"""(Pol 25-11) Los Satisfy se renderizan en GitHub (repo público hush-render, minutos gratis) y el PC solo los descarga.

Cada noche GitHub publica una «release» satisfy-AAAA-MM-DD con <slug>.mp4, <slug>.txt (publicación) y el registro
particulas-usadas.json. traer(fecha) los deja en videos-finales/satisfy/<slug>/ como si se hubieran hecho aquí y
actualiza el registro local. Si GitHub falló, satisfy2.diario los hace en el PC como siempre (respaldo).

Se activa con encargos/noche/satisfy-github.flag (si no existe, todo sigue como antes).
"""
from __future__ import annotations

import datetime as dt
import json
import ssl
import urllib.request
from pathlib import Path

from .config import ROOT

REPO = "Polgon534/hush-render"
FLAG = ROOT / "encargos" / "noche" / "satisfy-github.flag"
REGISTRO = ROOT / "stories" / "particulas-usadas.json"
REGISTRO_INT = ROOT / "stories" / "interactivos-usados.json"   # (26-11) interactivos de Skin
DESTINO = ROOT / "videos-finales" / "satisfy"


def _destino(slug: str) -> Path:
    """satisfy-… → videos-finales/satisfy · skin-/football-/history-… → la carpeta de ese canal."""
    pref = slug.split("-", 1)[0]
    return ROOT / "videos-finales" / (pref if pref in ("skin", "football", "history") else "satisfy")


def activo() -> bool:
    return FLAG.is_file()


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def _get(url: str, binario: bool = False, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "hush-render-pc", "Accept": "application/octet-stream" if binario
                                               else "application/vnd.github+json"})
    last = None
    for ctx in (_ctx(), None):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read()
        except urllib.error.HTTPError:
            raise
        except Exception as e:  # noqa: BLE001  (certificados de Windows: se prueba otro contexto)
            last = e
    raise last  # type: ignore[misc]


def traer(fecha: dt.date | None = None, log=print) -> int:
    """Descarga los Satisfy de `fecha` desde GitHub. Devuelve cuántos vídeos nuevos ha dejado en videos-finales."""
    fecha = fecha or dt.date.today()
    tag = f"satisfy-{fecha.isoformat()}"
    try:
        rel = json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"))
    except urllib.error.HTTPError as e:
        log(f"  GitHub: aún no hay {tag} ({e.code}); se hará en el PC si hace falta")
        return 0
    except Exception as e:  # noqa: BLE001
        log(f"  GitHub no responde ({e!r}); se hará en el PC si hace falta")
        return 0
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    nuevos = 0
    reg_remoto = None
    if "particulas-usadas.json" in assets:
        try:
            reg_remoto = json.loads(_get(assets["particulas-usadas.json"], binario=True))
        except Exception as e:  # noqa: BLE001
            log(f"  ✗  registro de GitHub: {e!r}")
    for nombre, url in sorted(assets.items()):
        if not nombre.endswith(".mp4"):
            continue
        slug = nombre[:-4]
        c = _destino(slug) / slug
        mp4 = c / nombre
        if mp4.is_file() and mp4.stat().st_size > 100_000:
            continue
        c.mkdir(parents=True, exist_ok=True)
        tmp = mp4.with_suffix(".part")
        tmp.write_bytes(_get(url, binario=True, timeout=600))
        tmp.replace(mp4)
        if f"{slug}.txt" in assets:
            (c / "publicacion.txt").write_bytes(_get(assets[f"{slug}.txt"], binario=True))
        nuevos += 1
        log(f"  >> OK (GitHub): {mp4}")
    if "interactivos-usados.json" in assets:          # registro de interactivos: el de GitHub manda
        try:
            ri = json.loads(_get(assets["interactivos-usados.json"], binario=True))
            for h in ri:
                s_ = h.get("slug")
                if s_ and (_destino(s_) / s_ / f"{s_}.mp4").is_file():
                    h["mp4"] = str(_destino(s_) / s_ / f"{s_}.mp4")
            REGISTRO_INT.write_text(json.dumps(ri, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            log(f"  ✗  registro de interactivos de GitHub: {e!r}")
    if reg_remoto is not None:                     # el registro de GitHub manda; las rutas apuntan a este PC
        for h in reg_remoto:
            s = h.get("slug")
            if s and (DESTINO / s / f"{s}.mp4").is_file():
                h["mp4"] = str(DESTINO / s / f"{s}.mp4")
        try:
            local = json.loads(REGISTRO.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            local = []
        vistos = {(h.get("fecha"), h.get("slug")) for h in reg_remoto}
        extra = [h for h in local if (h.get("fecha"), h.get("slug")) not in vistos]   # lo hecho solo en el PC
        REGISTRO.write_text(json.dumps((reg_remoto + extra)[-160:], ensure_ascii=False, indent=2), encoding="utf-8")
    return nuevos
