"""PINZAS — Hush Satisfy Lab, estilo nuevo (Pol 22-11, como sus vídeos de referencia de nexusboxlab).

Un círculo blanco fino sobre negro. En el borde, dos (o tres, o cuatro) PINZAS grises montadas en un engranaje: cada
pinza son dos brazos con codo que se abren y se CIERRAN de golpe formando un rombo. Las bolas (esferas de color
brillante) rebotan dentro del círculo y chocan entre sí; cuando una pinza se cierra con bolas dentro, cada bola
atrapada SE DUPLICA y todas cogen el color nuevo de esa pinza. Se empieza con UNA bola y se acaba con cientos que llenan
el círculo de manchas de colores.

Sonido (como las referencias, nada agudo): al cerrarse, un golpe grave y seco («clunk»); al duplicarse, un crujido
satisfactorio hecho de muchos «pops» suaves (uno por bola duplicada: cuantas más, más largo y más denso) y una nota
grave de marimba de la escala del día. Los choques de las bolas no suenan (silencio entre golpe y golpe).

La CÁMARA NO SE MUEVE (Pol: en Satisfy, sin animación de cámara). Todo es determinista: misma fecha → mismo vídeo, y
cada sonido sale de un suceso de la misma simulación que se pinta (Satisfy2D.tsx).
"""
from __future__ import annotations

import base64
import datetime as dt
import math
import random

import numpy as np

from . import satisfy_base as SB

SR = SB.SR
MECANISMO = "pinzas"
NOMBRE = "Pinzas que duplican"
COMPOSICION = "Satisfy2D"

FONDOS = {"negro": "#000000", "noche": "#04050d", "abismo": "#01090e", "vino": "#0b0306", "bosque": "#020905",
          "tinta": "#06040f", "carbon": "#0a0a0a"}   # (25-11) fondos muy oscuros distintos cada día
PALETAS = {   # colores vivos de las bolas (las referencias: rojo, azul, verde, amarillo, cian, magenta, naranja...)
    "arcoiris": ["#ff2d55", "#2f6bff", "#2ee86b", "#ffd60a", "#19d3ff", "#c13bff", "#ff8a00", "#ff4fd8"],
    "caramelo": ["#ff5c8a", "#5ad1ff", "#7dff6a", "#ffe14d", "#b67bff", "#ff9f43", "#3dffc5", "#ff6bd6"],
    "neon": ["#ff1f6b", "#1fa2ff", "#39ff14", "#fff01f", "#00f5d4", "#9b5de5", "#ff7b00", "#f15bb5"],
    "joyas": ["#e0115f", "#0f52ba", "#21c45a", "#ffbf00", "#00b4d8", "#8e44ad", "#ff6f3c", "#d63384"],
}
ESCALAS = {"la_menor": (45, [0, 3, 5, 7, 10]), "re_menor": (50, [0, 3, 5, 7, 10]), "do_mayor": (48, [0, 2, 4, 7, 9]),
           "mi_menor": (40, [0, 3, 5, 7, 10]), "fa_mayor": (41, [0, 2, 4, 7, 9])}
DISPOSICIONES = {2: [math.pi, 0.0], 3: [math.pi / 2 + 2 * math.pi * k / 3 for k in range(3)],
                 4: [math.pi / 4 + math.pi / 2 * k for k in range(4)]}

DEFECTO = dict(segundos=40.0, fps=60, sub=2, R=1.0, r=0.03, v=0.55, tope=520, pinzas=2, brazo=0.3, abre=1.0,
               t_cierra=1.1, t_sujeta=0.25, t_abre=0.7, espera=0.55, forzar=4.4, intervalo=3.3, succion=0.55, fuerza_succion=0.0, reverb=0.22, volumen=1.0,
               cama=False)
# (Pol 24-11) A CÁMARA LENTA: las pinzas se cierran de una en una, despacio (1,1 s), cada 3,3-4,4 s, y se cruzan al final;
# lo que entra en la pinza mientras se cierra se queda atrapado. Pocas bolas casi todo el vídeo y la explosión de bolas
# al final (x2 al principio, x8 en los últimos segundos).


def disenar(fecha: dt.date, overrides: dict | None = None, historial: list[dict] | None = None, turno: int = 1) -> dict:
    ult = SB.ultimo(fecha, historial)
    rng = random.Random(f"pinzas-{fecha.isoformat()}-{turno}")
    d = dict(DEFECTO)
    previos = [h for h in (historial or []) if h.get("fecha", "") < fecha.isoformat()]   # (25-11) nada repetido de cerca
    evita_p = {h.get("paleta") for h in previos[-4:]}
    evita_f = {h.get("fondo") for h in previos[-3:]}
    d.update(fecha=fecha.isoformat(), mecanismo=MECANISMO,
             paleta=rng.choice([p for p in PALETAS if p not in evita_p] or list(PALETAS)),
             fondo=rng.choice([f for f in FONDOS if f not in evita_f] or list(FONDOS)),
             escala=SB.elige(rng, list(ESCALAS), ult.get("escala")), pinzas=2,
             r=rng.choice([0.031, 0.033, 0.035]), v=round(rng.uniform(0.66, 0.78), 3), semilla=rng.randrange(1 << 30))
    d["tope"] = int(0.45 * (1.0 / d["r"]) ** 2)         # tope de bolas (el final llena casi medio círculo)
    d["brazo"] = {2: 0.46, 3: 0.4, 4: 0.34}[d["pinzas"]]   # (24-11) pinzas grandes: atrapan sin imán
    for k, v in (overrides or {}).items():
        if v is not None:
            d[k] = v
    d["slug"] = f"satisfy-{d['fecha']}-pinzas-{d['paleta']}"
    return d


# ============================================================ geometría de las pinzas
def _brazos(d: dict, k: int, s: float) -> list[tuple]:
    """Segmentos de la pinza k con cierre s (0 abierta → 1 cerrada). Cada brazo: pivote → codo → punta.
    Cerrada: las dos puntas se juntan en el eje y forman un rombo."""
    th = DISPOSICIONES[d["pinzas"]][k]
    u = np.array([math.cos(th), math.sin(th)])            # hacia fuera
    n = np.array([-u[1], u[0]])                           # lateral
    P = u * (d["R"] - 0.005)                              # pivote en el aro
    a = b = d["brazo"]
    al = math.radians(48) * (1 - 0.82 * s)                # (Pol 23-11) se cierra DEL TODO: los brazos acaban casi juntos
    a2 = al * s + math.radians(16) * s ** 3               # (Pol 24-11) y al final las puntas se CRUZAN (tijera)
    segs = []
    for lado in (1, -1):
        E = P + a * (-u * math.cos(al) + lado * n * math.sin(al))
        T = E + b * (-u * math.cos(a2) - lado * n * math.sin(a2))
        segs += [(P, E), (E, T)]
    return segs


def _bolsa(d: dict, k: int) -> np.ndarray:
    """polígono del rombo cerrado (zona donde una bola queda atrapada)"""
    th = DISPOSICIONES[d["pinzas"]][k]
    u = np.array([math.cos(th), math.sin(th)])
    n = np.array([-u[1], u[0]])
    P = u * (d["R"] - 0.005)
    a = d["brazo"]
    al = math.radians(48)                                 # la zona que atrapa: el rombo con la pinza a medio cerrar
    E1, E2 = P + a * (-u * math.cos(al) + n * math.sin(al)), P + a * (-u * math.cos(al) - n * math.sin(al))
    T = P - u * 2 * a * math.cos(al)
    return np.array([P, E1, T, E2])


def _bolsa_actual(d: dict, k: int, s: float) -> np.ndarray:
    """(Pol 24-11) el hueco que dejan los brazos AHORA (se va estrechando al cerrar): solo lo que está aquí se atrapa"""
    (P, E1), (_, T1), (_, E2), (_, T2) = _brazos(d, k, s)
    return np.array([P, E1, T1, T2, E2])


def _punta(d: dict, k: int) -> np.ndarray:
    """punto justo delante de la punta de la pinza cerrada (de ahí salen las bolas al explotar)"""
    th = DISPOSICIONES[d["pinzas"]][k]
    u = np.array([math.cos(th), math.sin(th)])
    al = math.radians(48) * 0.18
    return u * (d["R"] - 0.005) - u * (2 * d["brazo"] * math.cos(al) + 2.2 * d["r"])


def _dentro(poly: np.ndarray, P: np.ndarray) -> np.ndarray:
    x, y = P[:, 0], P[:, 1]
    res = np.zeros(len(P), bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
        res ^= c
        j = i
    return res


def _cierre(d: dict, t: float, t0: float) -> float:
    """curva de cierre de una pinza que empezó a cerrarse en t0"""
    tc, ts, ta = d["t_cierra"], d["t_sujeta"], d["t_abre"]
    u = t - t0
    if u < 0:
        return 0.0
    if u < tc:
        x = u / tc
        return x * x * (3 - 2 * x)
    if u < tc + ts:
        return 1.0
    if u < tc + ts + ta:
        x = (u - tc - ts) / ta
        return 1 - x * x * (3 - 2 * x)
    return 0.0


# ============================================================ simulación
def _simula(d: dict) -> dict:
    rng = np.random.default_rng(d["semilla"])
    fps, sub = d["fps"], d["sub"]
    dt_ = 1.0 / (fps * sub)
    R, r, v = d["R"], d["r"], d["v"]
    cap = d["tope"]
    pos = np.zeros((cap, 2))
    vel = np.zeros((cap, 2))
    col = np.zeros(cap, int)
    n = 1
    a0 = rng.uniform(0, 2 * math.pi)
    pos[0] = (0.15 * math.cos(a0), 0.15 * math.sin(a0))
    K0 = int(rng.integers(d["pinzas"]))                    # la primera bola sale hacia una pinza: arranca rápido
    obj = _bolsa(d, K0).mean(0)
    dv = obj - pos[0]
    vel[0] = dv / np.linalg.norm(dv) * v
    K = d["pinzas"]
    ncol = len(PALETAS[d["paleta"]])
    color_pinza = [(1 + k) % ncol for k in range(K)]
    inicio = [-99.0] * K                                  # cuándo empezó a cerrarse cada pinza
    presas = [np.array([], int) for _ in range(K)]
    turbo = np.zeros(cap)                                 # hasta cuándo va «disparada» cada bola tras una explosión
    ultima = [0.0] * K
    ult_global, turno_k, union_t = -1.0, K0, [0.0] * K
    bolsas = [_bolsa(d, k) for k in range(K)]
    dur = d["t_cierra"] + d["t_sujeta"] + d["t_abre"]
    F = int(round(d["segundos"] * fps))
    claves, recolor, ev = [], [], []
    for f in range(F):
        for s_ in range(sub):
            t = (f * sub + s_) * dt_
            # --- las pinzas deciden si cierran (si tienen alguna bola en la bolsa, o si llevan mucho sin cerrar)
            ocupada = any(0 <= t - inicio[j] < dur for j in range(K))
            if not ocupada and 0.5 < t < d["segundos"] - 2.4 and (t - ult_global >= d["intervalo"] or ult_global < 0):
                cand = []
                k = turno_k % K                          # (Pol 24-11) se cierran POR TURNOS: una, luego la otra
                ya = int(_dentro(bolsas[k], pos[:n]).sum())
                luego = int(_dentro(bolsas[k], pos[:n] + vel[:n] * 0.35).sum())
                if ya and luego:
                    cand.append((ya + luego, k))
                forzada = ult_global >= 0 and t - ult_global >= d["forzar"]
                if cand or forzada:
                    turno_k = k + 1
                    inicio[k] = t
                    ult_global = t
                    presas[k] = np.nonzero(_dentro(bolsas[k], pos[:n]))[0]
                    union_t[k] = t
                    ev.append(dict(t=t, tipo="cierra", k=k, m=len(presas[k])))
            # --- mientras se cierra (despacio), la pinza SUCCIONA las bolas cercanas y lo que entra se queda atrapado
            for k in range(K):
                u_ = t - inicio[k]
                if d["fuerza_succion"] > 0 and 0 <= u_ < d["t_cierra"] * 0.75:
                    cen = bolsas[k].mean(0)
                    dd_ = cen - pos[:n]
                    dist_ = np.maximum(np.hypot(dd_[:, 0], dd_[:, 1]), 1e-6)
                    m_ = dist_ < d["succion"]
                    if m_.any():
                        vel[:n][m_] += (dd_[m_] / dist_[m_][:, None]) * d["fuerza_succion"] * dt_
                if 0 <= u_ < d["t_cierra"] * 0.8:
                    otras = set()
                    for j in range(K):
                        if j != k:
                            otras |= set(presas[j].tolist())
                    hueco = _bolsa_actual(d, k, _cierre(d, t, inicio[k]))
                    nuevo = [i for i in np.nonzero(_dentro(hueco, pos[:n]))[0] if i not in otras and i not in set(presas[k].tolist())]
                    if nuevo:
                        presas[k] = np.concatenate([presas[k], np.array(nuevo, int)])
                        union_t[k] = t
            # --- (Pol 23-11) mientras se cierra, lo atrapado se aplasta hacia el centro del rombo; al cerrarse del todo
            #     ¡mini explosión!: salen por la punta las aplastadas y sus copias, disparadas hacia dentro del círculo
            for k in range(K):
                if inicio[k] < 0 or not len(presas[k]):
                    continue
                u_ = t - inicio[k]
                if 0 <= u_ < d["t_cierra"]:
                    cen = bolsas[k].mean(0)
                    pos[presas[k]] += (cen - pos[presas[k]]) * min(1.0, dt_ * 6)
                    vel[presas[k]] = 0
                if abs(u_ - d["t_cierra"]) < dt_ / 2:
                    atrapadas = presas[k]
                    c = color_pinza[k]
                    nuevas = []
                    fr = t / d["segundos"]                                       # (Pol 24-11) pocas bolas hasta el final
                    mult = 4 if fr < 0.5 else 5 if fr < 0.7 else 8 if fr < 0.85 else 14
                    origen = _punta(d, k)
                    th = DISPOSICIONES[K][k]
                    haciadentro = math.atan2(-math.sin(th), -math.cos(th))
                    todas = list(atrapadas)
                    for i in atrapadas:
                        for _ in range(mult - 1):
                            if n >= cap:
                                break
                            todas.append(n)
                            nuevas.append(n)
                            n += 1
                    nt = len(todas)
                    sig = bolsas[(k + 1) % K].mean(0) - origen        # (Pol 24-11) el abanico apunta a la SIGUIENTE pinza:
                    haciadentro = math.atan2(sig[1], sig[0])          # las bolas viajan hacia ella y esa es la que se cierra
                    abre = min(0.75, 0.25 + 0.05 * nt)
                    for j, i in enumerate(todas):     # abanico ordenado: cada bola sale en su dirección, se ve clara
                        ang = haciadentro + (-abre + 2 * abre * (j + 0.5) / nt if nt > 1 else 0.0)
                        sp = v * (1.35 + 0.25 * (j % 3) / 2)
                        pos[i] = origen + np.array([math.cos(ang), math.sin(ang)]) * (1.2 * r + 2.1 * r * (j % 3))
                        vel[i] = (sp * math.cos(ang), sp * math.sin(ang))
                        turbo[i] = t + 0.9
                    if len(atrapadas):
                        col[todas] = c
                        recolor.append([f, c, [int(x) for x in atrapadas], (nuevas[0] if nuevas else n), n,
                                        round(min(max(inicio[k], union_t[k]), t - 0.35), 4), round(float(origen[0]), 4), round(float(origen[1]), 4)])
                        ev.append(dict(t=t, tipo="duplica", k=k, m=len(atrapadas), nuevas=len(nuevas),
                                       x=float(origen[0]), y=float(origen[1])))
                        ultima[k] = t
                    presas[k] = np.array([], int)
                    color_pinza[k] = (c + K) % ncol if ncol > K else (c + 1) % ncol
            P = pos[:n]
            V = vel[:n]
            P += V * dt_
            libres = np.ones(n, bool)                         # las que se están aplastando no chocan con nada
            for k in range(K):
                if len(presas[k]):
                    libres[presas[k][presas[k] < n]] = False
            # --- brazos de las pinzas (sólidos: las bolas no los atraviesan)
            for k in range(K):
                sc = _cierre(d, t, inicio[k])
                for A, B in _brazos(d, k, sc):
                    AB = B - A
                    L2 = AB @ AB
                    u = np.clip(((P - A) @ AB) / L2, 0, 1)
                    C = A + u[:, None] * AB
                    D = P - C
                    dist = np.hypot(D[:, 0], D[:, 1])
                    lim = r + 0.012
                    m = (dist < lim) & libres
                    if m.any():
                        nr = D[m] / np.maximum(dist[m], 1e-9)[:, None]
                        P[m] = C[m] + nr * lim
                        vn = (V[m] * nr).sum(1)
                        V[m] -= (2 * np.minimum(vn, 0))[:, None] * nr
            # --- aro
            rr = np.hypot(P[:, 0], P[:, 1])
            m = rr > R - r
            if m.any():
                nr = P[m] / rr[m][:, None]
                vn = (V[m] * nr).sum(1)
                V[m] -= (2 * np.maximum(vn, 0))[:, None] * nr
                P[m] = nr * (R - r)
            # --- choques entre bolas (elásticos) + separación
            if n > 1:
                dx = P[:, None, :] - P[None, :, :]
                d2 = (dx ** 2).sum(2)
                ii, jj = np.nonzero(np.triu(d2 < (2 * r) ** 2, 1))
                ok_ = libres[ii] & libres[jj]
                ii, jj = ii[ok_], jj[ok_]
                if len(ii):
                    dd = P[ii] - P[jj]
                    dn = np.maximum(np.hypot(dd[:, 0], dd[:, 1]), 1e-9)
                    nn = dd / dn[:, None]
                    sep = ((2 * r - dn) / 2)[:, None] * nn * 0.9
                    np.add.at(P, ii, sep)
                    np.add.at(P, jj, -sep)
                    rv = ((V[ii] - V[jj]) * nn).sum(1)
                    q = rv < 0
                    imp = (rv * q)[:, None] * nn
                    np.add.at(V, ii, -imp)
                    np.add.at(V, jj, imp)
            # --- y al final otra vez el aro (el empujón entre bolas no puede sacar a ninguna)
            rr = np.hypot(P[:, 0], P[:, 1])
            m = rr > R - r
            if m.any():
                P[m] = P[m] / rr[m][:, None] * (R - r)
            # --- todas a la misma velocidad (vivas pero sin explotar)
            sp = np.maximum(np.hypot(V[:, 0], V[:, 1]), 1e-9)
            vt = v * (1 - 0.72 * (n / cap) ** 1.3)              # cuanto más lleno, más despacio: se ven las manchas de color
            ex = np.where(turbo[:n] > t, 0.012, 0.15)           # tras la explosión frenan poco a poco
            V *= ((vt / sp) ** ex)[:, None]
        if f % 2 == 0:
            claves.append(np.round(pos[:n] * 10000).astype(np.int16).ravel())
    cierres = [[e["t"], e["k"]] for e in ev if e["tipo"] == "cierra"]
    return dict(claves=claves, recolor=recolor, ev=ev, n=n, cierres=cierres, F=F)


def plan(d: dict, log=print) -> dict:
    sim = _simula(d)
    d["_sim"] = sim
    cuantas = [len(c) // 2 for c in sim["claves"]]
    blob = np.concatenate(sim["claves"]).astype("<i2").tobytes()
    return dict(fps=d["fps"], frames=int(round(d["segundos"] * d["fps"])), segundos=d["segundos"], estilo="pinzas",
                R=d["R"], r=d["r"], colores=PALETAS[d["paleta"]], cuantas=cuantas, pos=base64.b64encode(blob).decode(),
                paso_claves=2, recolor=sim["recolor"], pinzas=d["pinzas"], brazo=d["brazo"],
                angulos=DISPOSICIONES[d["pinzas"]], cierres=sim["cierres"], t_cierra=d["t_cierra"], t_sujeta=d["t_sujeta"],
                t_abre=d["t_abre"], max_bolas=sim["n"], fondo=FONDOS.get(d.get("fondo", "negro"), "#000000"))


# ============================================================ sonido
def eventos(d: dict, pl: dict) -> list[dict]:
    raiz, grados = ESCALAS[d["escala"]]
    notas = [raiz + 12 * (i // len(grados)) + grados[i % len(grados)] for i in range(10)]
    ev, k = [], 0
    for e in d["_sim"]["ev"]:
        pan = 0.0 if e["tipo"] == "cierra" else max(-0.7, min(0.7, e["x"] * 0.6))
        if e["tipo"] == "cierra":
            lado = 0.6 * math.cos(pl["angulos"][e["k"]])
            ev.append(dict(t=e["t"], tipo="clunk", midi=raiz - 12, pan=lado, gain=1.0))
            if e.get("m"):
                ev.append(dict(t=e["t"] + 0.02, tipo="aplasta", midi=0, m=e["m"], pan=lado, gain=1.0))
        else:
            m = e["m"]
            ev.append(dict(t=e["t"], tipo="crujido", midi=notas[k % len(notas)], m=m, pan=pan,
                           gain=min(1.0, 0.45 + 0.12 * math.log2(1 + m))))
            ev.append(dict(t=e["t"] + 0.005, tipo="nota", midi=notas[k % len(notas)], pan=pan, gain=0.7))
            ev.append(dict(t=e["t"], tipo="boom", midi=raiz - 24, pan=pan, gain=min(1.0, 0.55 + 0.1 * math.log2(1 + m))))
            k += 1
    return sorted(ev, key=lambda e: e["t"])


def _clunk(midi: float, rng) -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = SB.midi_hz(midi) * (1 + 0.6 * np.exp(-t / 0.02))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)
    s += 0.35 * SB.ruido_filtrado(n, rng, 150, 1400) * np.exp(-t / 0.012)          # el «clac» metálico, apagado
    return s / np.abs(s).max()


def _pop(rng) -> np.ndarray:
    """un «pop» blandito de bola (como burbuja de plástico): grave-medio, sin agudos"""
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    f0 = rng.uniform(260, 620)
    f = f0 * (1 + 0.5 * np.exp(-t / 0.006))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.012)
    s += 0.25 * SB.ruido_filtrado(n, rng, 200, 2400) * np.exp(-t / 0.004)
    return s / np.abs(s).max()


def _aplasta(rng, dur: float) -> np.ndarray:
    """el «crrrr» de las bolas apretándose mientras la pinza se cierra (grave, apagado)"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / (dur * 0.7)) * np.exp(-np.maximum(0, t - dur * 0.7) / 0.03)
    s = SB.ruido_filtrado(n, rng, 120, 1300) * env * (1 + 0.8 * (rng.random(n) < 0.004))
    return s / (np.abs(s).max() + 1e-9)


def _boom(midi: float, rng) -> np.ndarray:
    """mini explosión: golpe grave redondo + soplo corto (nada agudo)"""
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    f = SB.midi_hz(midi) * (1 + 1.2 * np.exp(-t / 0.03))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    s += 0.45 * SB.ruido_filtrado(n, rng, 80, 1800) * np.exp(-t / 0.06)
    return s / np.abs(s).max()


def _marimba_grave(midi: float) -> np.ndarray:
    f = SB.midi_hz(midi)
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.55) + 0.25 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.08)
         + 0.35 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t / 0.35))
    a = int(0.003 * SR)
    s[:a] *= np.linspace(0, 1, a)
    return s / np.abs(s).max()


def sintetiza(d: dict, ev: list[dict], segundos: float) -> np.ndarray:
    n = int(round(segundos * SR))
    seco = np.zeros((n, 2))
    rng = np.random.default_rng(d["semilla"])
    pops = [_pop(rng) for _ in range(24)]
    for e in ev:
        if e["tipo"] == "clunk":
            SB.mezcla_en(seco, _clunk(e["midi"], rng), e["t"], e["pan"], 0.55)
        elif e["tipo"] == "aplasta":
            SB.mezcla_en(seco, _aplasta(rng, d["t_cierra"]), e["t"], e["pan"], 0.22 * min(1.0, 0.5 + 0.1 * e["m"]))
        elif e["tipo"] == "boom":
            SB.mezcla_en(seco, _boom(e["midi"], rng), e["t"], e["pan"], 0.6 * e["gain"])
        elif e["tipo"] == "nota":
            SB.mezcla_en(seco, _marimba_grave(e["midi"]), e["t"], e["pan"], 0.42 * e["gain"])
        elif e["tipo"] == "crujido":                        # tantos pops como bolas duplicadas, más largo si son más
            m = max(1, e["m"])
            largo = min(0.55, 0.06 + 0.035 * math.sqrt(m) * 3)
            for j in range(min(m * 2, 160)):
                tt = e["t"] + largo * (rng.random() ** 1.6)
                SB.mezcla_en(seco, pops[int(rng.integers(len(pops)))], tt, e["pan"] + rng.uniform(-0.25, 0.25),
                             0.16 * e["gain"] / math.sqrt(1 + j * 0.02))
    # pasa-bajos suave: nada chillón (Pol: «no tan agudos»)
    for c in (0, 1):
        sp = np.fft.rfft(seco[:, c])
        fr = np.fft.rfftfreq(n, 1 / SR)
        sp *= 1 / (1 + (fr / 3800) ** 4)
        seco[:, c] = np.fft.irfft(sp, n)
    return SB.acaba(seco, d["semilla"], d["reverb"], d["volumen"], ir_seg=1.8, fade=0.8)


# ============================================================ control
def revisa(d: dict, pl: dict, ev: list[dict], mix: np.ndarray) -> list[str]:
    sim = d.pop("_sim", None)
    fallos = []
    if np.abs(mix).max() > 0.95:
        fallos.append("el audio satura")
    dup = [e for e in sim["ev"] if e["tipo"] == "duplica"]
    if not dup or dup[0]["t"] > 3.5:
        fallos.append("la primera duplicación llega tarde (más de 3,5 s sin nada)")
    if sim["n"] < 110:
        fallos.append(f"solo llegan a {sim['n']} bolas (el final tiene que ser una explosión de bolas)")
    n60 = 1 + sum(e["nuevas"] for e in dup if e["t"] < 0.6 * d["segundos"])
    if n60 > 0.3 * sim["n"]:
        fallos.append(f"a los {0.6 * d['segundos']:.0f} s ya hay {n60} bolas: tienen que ser pocas hasta el final")
    if len(dup) < 5:
        fallos.append(f"solo {len(dup)} cierres con bolas dentro")
    ts = [e["t"] for e in sim["ev"] if e["tipo"] == "cierra"]
    huecos = np.diff([0.0] + ts + [d["segundos"]])
    if (huecos[1:] > 4.8).any():
        fallos.append(f"hueco de {huecos.max():.1f} s sin que pase nada")
    # coherencia: ninguna bola fuera del círculo ni metida dentro de un brazo (se mira en las claves)
    R, r = d["R"], d["r"]
    for kf in range(0, len(sim["claves"]), 15):
        P = sim["claves"][kf].reshape(-1, 2) / 10000
        if (np.hypot(P[:, 0], P[:, 1]) > R - r + 0.01).any():
            fallos.append(f"una bola se sale del círculo ({kf * 2 / d['fps']:.1f} s)")
            break
    # bolas muy metidas unas en otras (se ve feo): como mucho un 3 %
    P = sim["claves"][-1].reshape(-1, 2) / 10000
    dd = np.hypot(*(P[:, None] - P[None]).transpose(2, 0, 1))
    np.fill_diagonal(dd, 9)
    if (dd.min(1) < 1.2 * r).mean() > 0.03:
        fallos.append("demasiadas bolas solapadas al final")
    return fallos


TITULOS = ("Cada vez que la pinza se cierra… se DUPLICAN 🤯", "De 1 bola a cientos 🔴🔵🟢", "¿Qué color se queda el círculo?",
           "La pinza que multiplica bolas 😮‍💨")


def publicacion(d: dict, pl: dict) -> str:
    rng = random.Random(d["slug"])
    desc = ("Empieza con una sola bola. Cada vez que una pinza se cierra con bolas dentro, se duplican y cambian de color. "
            "🎧 Mejor con cascos.")
    return f"{rng.choice(TITULOS)}\n\n{desc}\n\n#satisfying #asmr #oddlysatisfying #satisfyingvideo #shorts\n"


def resumen(d: dict, pl: dict, ev: list[dict]) -> str:
    return (f"{pl['max_bolas']} bolas · {d['pinzas']} pinzas · {len(pl['cierres'])} cierres · "
            f"{sum(1 for e in ev if e['tipo'] == 'crujido')} duplicaciones · paleta {d['paleta']} · escala {d['escala']}")
