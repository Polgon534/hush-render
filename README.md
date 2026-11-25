# hush-render

Render nocturno gratis (GitHub Actions) de los vídeos sin voz de Pol: **Hush Satisfy Lab** (pinzas, anillos, notas).

- `.github/workflows/satisfy.yml`: cada noche (01:17 en España) hace los 2 Satisfy del día y los publica como release `satisfy-AAAA-MM-DD`.
- El PC de Pol los descarga solo (`shorts/github_render.py`) y salen en el Panel Shorts para aprobar.
- `stories/particulas-usadas.json`: registro para no repetir nunca paleta, fondo ni melodía.
- Sin claves ni secretos: no hace falta configurar nada.

El código de `shorts/` y `motor3d/` es una copia del proyecto de Pol; se actualiza desde allí.
