// SATISFY 2D · Hush Satisfy Lab, estilo nuevo (Pol 22-11, como sus vídeos de referencia). 1080x1920 a 60 fps, sin voz.
// Plano FIJO (Pol: en Satisfy, sin movimiento de cámara). El plan (public/particulas/<slug>/plan.json) dice el estilo:
//   «pinzas»  (shorts/pinzas.py): círculo blanco, pinzas en el borde que se cierran y DUPLICAN las bolas atrapadas.
//   «anillos» (shorts/anillos.py): anillos con hueco alrededor de un contador; la bolita los rompe uno a uno.
// Todo sale de la MISMA simulación que el audio: aquí solo se pinta.
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, delayRender, continueRender, getInputProps } from "remotion";

export type S2Props = { plan: string; mute?: boolean };
// (24-11) la duración la manda el plan (pinzas ~40 s, notas según la canción)
export const metadatosSatisfy = async ({ props }: { props: S2Props }) => {
  const ruta = props.plan || (getInputProps() as S2Props).plan;
  try {
    const p = await fetch(staticFile(ruta)).then((r) => r.json());
    return { durationInFrames: Math.round((p.segundos || 30) * (p.fps || 60)) };
  } catch { return { durationInFrames: 1800 }; }
};
const W = 1080, H = 1920, CX = 540;
const FUENTE = "'Jakarta', 'Plus Jakarta Sans', Arial, sans-serif";

const fuentes = (() => {
  if (typeof document === "undefined") return null;
  const h = delayRender("fuentes-s2");
  new FontFace("Jakarta", `url(${staticFile("fuentes/PlusJakartaSans-Bold.ttf")})`, { weight: "700" }).load()
    .then((ff) => { (document as any).fonts.add(ff); continueRender(h); }).catch(() => continueRender(h));
  return h;
})();
void fuentes;

const ease = (x: number) => { const u = Math.min(1, Math.max(0, x)); return u * u * (3 - 2 * u); };
const wrap = (a: number) => ((a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;

// ======================================================================== PINZAS
type EstadoP = { f: number; k: number; col: Int16Array };

function cierre(P: any, t: number, t0: number) {
  const tc = P.t_cierra, ts = P.t_sujeta, ta = P.t_abre, u = t - t0;
  if (u < 0) return 0;
  if (u < tc) return ease(u / tc);
  if (u < tc + ts) return 1;
  if (u < tc + ts + ta) return 1 - ease((u - tc - ts) / ta);
  return 0;
}

function brazos(P: any, k: number, s: number): [number, number][][] {
  const th = P.angulos[k], ux = Math.cos(th), uy = Math.sin(th), nx = -uy, ny = ux;
  const px = ux * (P.R - 0.005), py = uy * (P.R - 0.005), a = P.brazo, b = P.brazo;
  const al = ((48 * Math.PI) / 180) * (1 - 0.82 * s), a2 = al * s + ((16 * Math.PI) / 180) * s * s * s;   // (Pol 24-11) se cierra del todo y las puntas se cruzan
  const out: [number, number][][] = [];
  for (const lado of [1, -1]) {
    const ex = px + a * (-ux * Math.cos(al) + lado * nx * Math.sin(al)), ey = py + a * (-uy * Math.cos(al) + lado * ny * Math.sin(al));
    const tx = ex + b * (-ux * Math.cos(a2) - lado * nx * Math.sin(a2)), ty = ey + b * (-uy * Math.cos(a2) - lado * ny * Math.sin(a2));
    out.push([[px, py], [ex, ey], [tx, ty]]);
  }
  return out;
}

function sprites(colores: string[], radio: number): HTMLCanvasElement[] {
  return colores.map((c) => {
    const cv = document.createElement("canvas");
    const d = Math.ceil(radio * 2 + 4);
    cv.width = cv.height = d;
    const g = cv.getContext("2d")!;
    const r = radio, o = d / 2;
    const grad = g.createRadialGradient(o - r * 0.35, o - r * 0.4, r * 0.1, o, o, r);
    grad.addColorStop(0, "rgba(255,255,255,0.95)");
    grad.addColorStop(0.18, c);
    grad.addColorStop(0.75, c);
    grad.addColorStop(1, "rgba(0,0,0,0.55)");
    g.fillStyle = grad;
    g.beginPath(); g.arc(o, o, r, 0, Math.PI * 2); g.fill();
    // sombreado de esfera: oscurece el borde de abajo a la derecha
    const sh = g.createRadialGradient(o + r * 0.3, o + r * 0.35, r * 0.2, o, o, r * 1.05);
    sh.addColorStop(0, "rgba(0,0,0,0)"); sh.addColorStop(1, "rgba(0,0,0,0.35)");
    g.fillStyle = sh; g.beginPath(); g.arc(o, o, r, 0, Math.PI * 2); g.fill();
    return cv;
  });
}

function engranaje(g: CanvasRenderingContext2D, x: number, y: number, r: number, giro: number) {
  g.save(); g.translate(x, y); g.rotate(giro);
  g.fillStyle = "#9aa0a8"; g.strokeStyle = "#5f646b"; g.lineWidth = 2;
  g.beginPath();
  const dientes = 10;
  for (let i = 0; i < dientes * 2; i++) {
    const a = (i / (dientes * 2)) * Math.PI * 2, rr = i % 2 ? r : r * 1.28;
    const a2 = ((i + 1) / (dientes * 2)) * Math.PI * 2;
    g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); g.lineTo(Math.cos(a2) * rr, Math.sin(a2) * rr);
  }
  g.closePath(); g.fill(); g.stroke();
  g.fillStyle = "#2b2e33"; g.beginPath(); g.arc(0, 0, r * 0.38, 0, Math.PI * 2); g.fill();
  g.restore();
}

function pintaPinzas(g: CanvasRenderingContext2D, P: any, f: number, est: EstadoP, pos: Int16Array, inicio: number[], spr: HTMLCanvasElement[]) {
  const S = 470, CY = 960, t = f / P.fps;
  g.fillStyle = P.fondo || "#000"; g.fillRect(0, 0, W, H);
  // colores: se aplican los cambios hasta f (incremental; si se va hacia atrás, desde el principio)
  if (f < est.f) { est.col.fill(0); est.k = 0; }
  while (est.k < P.recolor.length && P.recolor[est.k][0] <= f) {
    const [, c, atr, n0, n1] = P.recolor[est.k];
    for (const i of atr) est.col[i] = c;
    for (let i = n0; i < n1; i++) est.col[i] = c;
    est.k++;
  }
  est.f = f;
  // aro blanco fino
  g.strokeStyle = "rgba(255,255,255,0.92)"; g.lineWidth = 3.2;
  g.beginPath(); g.arc(CX, CY, P.R * S, 0, Math.PI * 2); g.stroke();
  // bolas (claves cada 2 fotogramas, interpoladas)
  const kf = f / P.paso_claves, k0 = Math.min(Math.floor(kf), P.cuantas.length - 1), k1 = Math.min(k0 + 1, P.cuantas.length - 1);
  const u = Math.min(1, kf - k0);
  const n0 = P.cuantas[k0], n1 = P.cuantas[k1];
  const off0 = inicio[k0], off1 = inicio[k1];
  const rpx = P.r * S, d = spr[0].width;
  // (Pol 23-11) las atrapadas se aplastan mientras la pinza se cierra y salen disparadas con una mini explosión
  const escala = new Map<number, number>();
  const explos: [number, number, number, number][] = [];
  for (const ev of P.recolor) {
    const fe = ev[0], t0 = ev[5], te = fe / P.fps;
    if (t0 === undefined || t < t0 || t > te + 0.5) continue;
    const atr: number[] = ev[2];
    if (t < te) {
      const q = 1 - 0.7 * ease((t - t0) / Math.max(0.01, te - t0));
      for (const i of atr) escala.set(i, q);
    } else {
      const q = 0.35 + 0.65 * ease((t - te) / 0.12) + 0.15 * Math.sin(Math.min(1, (t - te) / 0.2) * Math.PI);
      for (const i of atr) escala.set(i, q);
      for (let i = ev[3]; i < ev[4]; i++) escala.set(i, q);
      explos.push([t - te, ev[6], ev[7], ev[1]]);
    }
  }
  for (const [e, ox, oy, c] of explos) {                  // destello + chispas del color nuevo
    const sx = CX + ox * S, sy = CY - oy * S, u = e / 0.5, uf = Math.min(1, e / 0.18);
    g.save();
    g.globalAlpha = Math.max(0, 0.9 * (1 - uf) * (1 - uf));   // destello corto (0,18 s)
    {                                                       // (24-11) destello con degradado: blanco → color → transparente (nada de mancha gris)
      const rf = 14 + 60 * ease(uf), gr = g.createRadialGradient(sx, sy, 0, sx, sy, rf);
      gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.35, P.colores[c]); gr.addColorStop(1, "rgba(0,0,0,0)");
      g.globalCompositeOperation = "lighter"; g.fillStyle = gr; g.beginPath(); g.arc(sx, sy, rf, 0, Math.PI * 2); g.fill();
      g.globalCompositeOperation = "source-over";
    }
    g.globalAlpha = Math.max(0, 0.85 * (1 - u));             // (Pol 24-11) onda de choque del color nuevo
    g.strokeStyle = P.colores[c]; g.lineWidth = 7 * (1 - u) + 1;
    g.beginPath(); g.arc(sx, sy, 18 + 190 * ease(u), 0, Math.PI * 2); g.stroke();
    g.globalAlpha = Math.max(0, 1 - u);
    g.lineWidth = 4;
    for (let q = 0; q < 22; q++) {
      const a = (q / 22) * Math.PI * 2 + c, r0 = 20 + (140 + 50 * ((q * 7) % 3)) * ease(u), r1 = r0 + 30 * (1 - u);
      g.beginPath(); g.moveTo(sx + Math.cos(a) * r0, sy + Math.sin(a) * r0); g.lineTo(sx + Math.cos(a) * r1, sy + Math.sin(a) * r1); g.stroke();
    }
    g.fillStyle = P.colores[c];
    for (let q = 0; q < 12; q++) {                          // confeti redondo que sale despedido y cae un poco
      const a = (q / 12) * Math.PI * 2 + 0.26 + c, r = 30 + 230 * ease(u);
      g.beginPath(); g.arc(sx + Math.cos(a) * r, sy + Math.sin(a) * r + 60 * u * u, 6 * (1 - u) + 1.5, 0, Math.PI * 2); g.fill();
    }
    g.restore();
  }
  for (let i = 0; i < n1; i++) {
    let x: number, y: number;
    if (i < n0) {
      x = pos[off0 + 2 * i] + (pos[off1 + 2 * i] - pos[off0 + 2 * i]) * u;
      y = pos[off0 + 2 * i + 1] + (pos[off1 + 2 * i + 1] - pos[off0 + 2 * i + 1]) * u;
    } else { if (u < 0.5) continue; x = pos[off1 + 2 * i]; y = pos[off1 + 2 * i + 1]; }
    const sx = CX + (x / 10000) * S, sy = CY - (y / 10000) * S;
    const q = escala.get(i) ?? 1;
    if (q === 1) g.drawImage(spr[est.col[i]], sx - d / 2, sy - d / 2);
    else g.drawImage(spr[est.col[i]], sx - (d * q) / 2, sy - (d * q) / 2, d * q, d * q);
  }
  void rpx;
  // pinzas (por encima de las bolas, como en la referencia)
  P.angulos.forEach((th: number, k: number) => {
    let s = 0;
    for (const [t0, kk] of P.cierres) if (kk === k && t0 <= t) s = Math.max(s, cierre(P, t, t0));
    const br = brazos(P, k, s);
    g.lineCap = "round"; g.lineJoin = "round";
    for (const [w, c] of [[0.034 * S, "#5c6168"], [0.024 * S, "#a9aeb5"]] as [number, string][]) {
      g.strokeStyle = c; g.lineWidth = w;
      for (const tramo of br) {
        g.beginPath();
        tramo.forEach(([x, y], j) => { const sx = CX + x * S, sy = CY - y * S; if (j) g.lineTo(sx, sy); else g.moveTo(sx, sy); });
        g.stroke();
      }
    }
    const gx = CX + Math.cos(th) * (P.R + 0.02) * S, gy = CY - Math.sin(th) * (P.R + 0.02) * S;
    engranaje(g, gx, gy, 0.045 * S, s * 1.4 + k);
  });
}

// ======================================================================== ANILLOS (Pol 23-11: con gravedad; la bola SALE
// de verdad por el hueco y, si los huecos coinciden, atraviesa varios anillos seguidos; anillos fijos, plano fijo)
function pintaAnillos(g: CanvasRenderingContext2D, P: any, f: number) {
  const S = 480, CY = 1010, t = f / P.fps;
  g.fillStyle = P.fondo || "#0d0913"; g.fillRect(0, 0, W, H);
  const vg = g.createRadialGradient(CX, CY, 100, CX, CY, 1100);
  vg.addColorStop(0, P.halo || "rgba(60,30,90,0.35)"); vg.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
  const rot = P.t_rotura as number[];
  let k = 0;
  while (k < rot.length && rot[k] <= t + 1 / P.fps) k++;   // como la simulación: posición del final del fotograma
  const hw = ((P.hueco * Math.PI) / 180) / 2;
  const [h0, h1] = P.tonos;
  const tono = (a: number) => h0 + (h1 - h0) * (0.5 - 0.5 * Math.cos(a));
  // anillos que quedan: cada uno con su hueco donde dice la simulación
  for (let j = k; j < P.total; j++) {
    const rr = P.radios[j] * S;
    const hueco = P.g0[j] + P.om[j] * t;
    const cg = (g as any).createConicGradient(0, CX, CY);
    for (let q = 0; q <= 8; q++) cg.addColorStop(q / 8, `hsla(${tono((q / 8) * Math.PI * 2)}, 80%, ${64 + 8 * Math.sin(j * 0.9)}%, 0.95)`);
    const gw = P.grosor || 3; g.strokeStyle = cg; g.lineWidth = j === k ? gw * 1.4 : gw; g.lineCap = "round";
    if (j === k) { g.save(); g.shadowColor = `hsla(${tono(j)}, 90%, 70%, 0.9)`; g.shadowBlur = 14; }
    g.beginPath();
    g.arc(CX, CY, rr, -(hueco + hw), -(hueco - hw + Math.PI * 2), true);   // en pantalla el ángulo va al revés
    g.stroke();
    if (j === k) g.restore();
  }
  // anillos rotos: se parten en trozos que caen con la gravedad y se apagan (1,1 s)
  for (let j = 0; j < k; j++) {
    const e = t - rot[j];
    if (e > 1.1 || e < 0) continue;
    const hueco = P.g0[j] + P.om[j] * rot[j];
    const n = 22, rr = P.radios[j];
    for (let q = 0; q < n; q++) {
      const a0 = hueco + hw + ((q + 0.5) / n) * (Math.PI * 2 - 2 * hw), da = ((Math.PI * 2 - 2 * hw) / n) * 0.42;
      const vx = Math.cos(a0) * 0.55, vy = Math.sin(a0) * 0.55 + 0.6;
      const x = Math.cos(a0) * rr + vx * e, y = Math.sin(a0) * rr + vy * e - 0.5 * P.g * 0.6 * e * e;
      g.save(); g.translate(CX + x * S, CY - y * S); g.rotate(-a0 + e * (q % 2 ? 4 : -4));
      g.strokeStyle = `hsla(${tono(a0)}, 90%, 72%, ${Math.max(0, 1 - e / 1.1)})`; g.lineWidth = 3.4;
      g.beginPath(); g.arc(-Math.cos(0) * rr * S, 0, rr * S, -da, da); g.stroke(); g.restore();
    }
    // destello en el punto por donde ha salido
    if (e < 0.25) {
      const fx = Math.round(rot[j] * P.fps);
      const bx = CX + P.tray[2 * fx] * S, by = CY - P.tray[2 * fx + 1] * S;
      g.fillStyle = `rgba(255,255,255,${0.5 * (1 - e / 0.25)})`;
      g.beginPath(); g.arc(bx, by, 10 + 60 * e, 0, Math.PI * 2); g.fill();
    }
  }
  // contador arriba: los anillos que quedan
  const quedan = P.total - k;
  const pulso = k ? Math.max(0, 1 - (t - rot[k - 1]) / 0.3) : 0;
  g.save(); g.translate(CX, 300); const es = 1 + 0.18 * pulso; g.scale(es, es);
  g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
  g.shadowColor = `hsla(${tono(k * 0.7)}, 90%, 65%, ${0.5 + 0.5 * pulso})`; g.shadowBlur = 25 + 25 * pulso;
  g.font = `700 150px ${FUENTE}`; g.fillText(String(quedan), 0, 0); g.restore();
  // la bola con estela (si ya se ha escapado, sigue cayendo hasta salir de la pantalla)
  const tr = P.tray as number[];
  for (let q = 12; q >= 1; q--) {
    const ff = Math.max(0, f - q);
    g.fillStyle = `rgba(255,255,255,${0.3 * (1 - q / 13)})`;
    g.beginPath(); g.arc(CX + tr[2 * ff] * S, CY - tr[2 * ff + 1] * S, P.rb * S * (1 - q / 16), 0, Math.PI * 2); g.fill();
  }
  g.save(); g.shadowColor = "rgba(255,255,255,0.95)"; g.shadowBlur = 20; g.fillStyle = "#fff";
  g.beginPath(); g.arc(CX + tr[2 * f] * S, CY - tr[2 * f + 1] * S, P.rb * S, 0, Math.PI * 2); g.fill(); g.restore();
}

// ======================================================================== NOTAS (Pol 24-11): el cuadrado que excava y toca una canción
function posNotas(P: any, t: number): [number, number, number] {
  const v = P.verts as number[][];
  let i = 0;
  while (i < v.length - 2 && v[i + 1][0] <= t) i++;
  const [t0, x0, y0] = v[i], [t1, x1, y1] = v[i + 1];
  const u = t1 > t0 ? Math.max(0, Math.min(1.2, (t - t0) / (t1 - t0))) : 0;
  return [x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, i];
}
function pintaNotas(g: CanvasRenderingContext2D, P: any, f: number) {
  const t = f / P.fps, L = P.lado, cols: string[] = P.colores;
  // cámara: sigue al cuadrado con suavidad (media de los últimos 0,7 s)
  let cx = 0, cy = 0; const N = 8;
  for (let k = 0; k < N; k++) { const [x, y] = posNotas(P, Math.max(0, t - (k * 0.7) / N)); cx += x / N; cy += y / N; }
  const SX = (x: number) => 540 + (x - cx), SY = (y: number) => 930 - (y - cy);
  g.fillStyle = P.fondo || "#77777e"; g.fillRect(0, 0, W, H);
  // textura sutil del bloque
  g.fillStyle = "rgba(0,0,0,0.05)";
  for (let k = 0; k < 40; k++) { const gx = ((k * 211 - cx * 0.5) % 1300 + 1300) % 1300 - 100, gy = ((k * 383 + cy * 0.5) % 2100 + 2100) % 2100 - 100; g.fillRect(gx, gy, 180, 120); }
  const [px, py, iseg] = posNotas(P, t);
  const v = P.verts as number[][], golpes = P.golpes as any[];
  // (Pol 24-11) el pasillo ENTERO se ve desde el principio (como la referencia); el color se pinta al pasar
  g.lineJoin = "miter"; g.lineCap = "square";
  g.strokeStyle = "#0d0d12"; g.lineWidth = L * 1.9;
  g.beginPath(); v.forEach((q: number[], k: number) => (k ? g.lineTo(SX(q[1]), SY(q[2])) : g.moveTo(SX(q[1]), SY(q[2])))); g.stroke();
  for (const gp of golpes) {                       // las paredes, apagadas hasta que las toca
    if (gp.t <= t) continue;
    const off = L * 0.95, bar = L * 1.3; let x0 = gp.x, y0 = gp.y, x1 = gp.x, y1 = gp.y;
    if (gp.pared === "der" || gp.pared === "izq") { x0 = x1 = gp.x + (gp.pared === "der" ? off : -off); y0 = gp.y - bar / 2; y1 = gp.y + bar / 2; }
    else { y0 = y1 = gp.y + (gp.pared === "arriba" ? off : -off); x0 = gp.x - bar / 2; x1 = gp.x + bar / 2; }
    g.strokeStyle = "rgba(255,255,255,0.22)"; g.lineWidth = 6; g.lineCap = "round";
    g.beginPath(); g.moveTo(SX(x0), SY(y0)); g.lineTo(SX(x1), SY(y1)); g.stroke();
  }
  const camino: [number, number][] = [];
  for (let i = 0; i <= iseg; i++) camino.push([v[i][1], v[i][2]]);
  camino.push([px, py]);
  // chevrones de color dentro del pasillo (cada tramo, el color del choque que lo empezó)
  for (let i = 0; i < camino.length - 1; i++) {
    const [ax, ay] = camino[i], [bx, by] = camino[i + 1], dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
    if (len < 1) continue;
    const ux = dx / len, uy = dy / len, nx = -uy, ny = ux, col = cols[i === 0 ? 0 : golpes[i - 1].c % cols.length];
    g.strokeStyle = col; g.lineWidth = 5; g.shadowColor = col; g.shadowBlur = 10;
    for (let s = 14; s < len; s += 24) {
      const qx = ax + ux * s, qy = ay + uy * s, w = L * 0.55;
      g.beginPath(); g.moveTo(SX(qx - ux * 8 + nx * w), SY(qy - uy * 8 + ny * w)); g.lineTo(SX(qx + ux * 6), SY(qy + uy * 6));
      g.lineTo(SX(qx - ux * 8 - nx * w), SY(qy - uy * 8 - ny * w)); g.stroke();
    }
    g.shadowBlur = 0;
  }
  // paredes encendidas donde chocó (+ destello y chispas al chocar)
  for (const gp of golpes) {
    if (gp.t > t) break;
    const e = t - gp.t, col = cols[gp.c % cols.length];
    const off = L * 0.95, bar = L * 1.3;
    let x0 = gp.x, y0 = gp.y, x1 = gp.x, y1 = gp.y;
    if (gp.pared === "der") { x0 = x1 = gp.x + off; y0 = gp.y - bar / 2; y1 = gp.y + bar / 2; }
    if (gp.pared === "izq") { x0 = x1 = gp.x - off; y0 = gp.y - bar / 2; y1 = gp.y + bar / 2; }
    if (gp.pared === "arriba") { y0 = y1 = gp.y + off; x0 = gp.x - bar / 2; x1 = gp.x + bar / 2; }
    if (gp.pared === "abajo") { y0 = y1 = gp.y - off; x0 = gp.x - bar / 2; x1 = gp.x + bar / 2; }
    const brillo = 0.55 + 0.45 * Math.exp(-e / 0.25);
    g.save(); g.globalAlpha = brillo; g.strokeStyle = col; g.lineWidth = 9; g.lineCap = "round"; g.shadowColor = col; g.shadowBlur = 22 + 30 * Math.exp(-e / 0.2);
    g.beginPath(); g.moveTo(SX(x0), SY(y0)); g.lineTo(SX(x1), SY(y1)); g.stroke(); g.restore();
    if (e < 0.6) {
      const u = e / 0.6;
      g.save(); g.fillStyle = col; g.globalAlpha = 1 - u;
      for (let q = 0; q < 14; q++) {
        const a = q * 2.399 + gp.t * 7, r = 12 + 90 * Math.sqrt(u) * (0.5 + ((q * 37) % 10) / 20);
        g.beginPath(); g.arc(SX((x0 + x1) / 2) + Math.cos(a) * r, SY((y0 + y1) / 2) + Math.sin(a) * r + 40 * u * u, 3.5 * (1 - u) + 1, 0, Math.PI * 2); g.fill();
      }
      g.restore();
    }
  }
  // el cuadrado (rebota un poco al chocar)
  const ult = golpes.filter((x) => x.t <= t).pop(), eh = ult ? t - ult.t : 9, sq = 1 + 0.25 * Math.exp(-eh / 0.07);
  const colAct = cols[ult ? ult.c % cols.length : 0];
  g.save(); g.translate(SX(px), SY(py)); g.scale(sq, 2 - sq);
  g.shadowColor = colAct; g.shadowBlur = 35; g.fillStyle = "#ffffff";
  g.fillRect(-L / 2, -L / 2, L, L); g.shadowBlur = 0; g.strokeStyle = colAct; g.lineWidth = 4; g.strokeRect(-L / 2 + 3, -L / 2 + 3, L - 6, L - 6);
  g.restore();
}

// ======================================================================== composición
const cache: Record<string, any> = {};

const Lienzo: React.FC<{ plan: any }> = ({ plan }) => {
  const f = useCurrentFrame();
  const ref = useRef<HTMLCanvasElement>(null);
  const datos = useMemo(() => {
    if (plan.estilo !== "pinzas") return null;
    const bin = atob(plan.pos);
    const buf = new ArrayBuffer(bin.length);
    const u8 = new Uint8Array(buf);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    const pos = new Int16Array(buf);
    const inicio: number[] = [];
    let o = 0;
    for (const c of plan.cuantas) { inicio.push(o); o += 2 * c; }
    return { pos, inicio, spr: sprites(plan.colores, plan.r * 470), est: { f: -1, k: 0, col: new Int16Array(plan.max_bolas + 8) } as EstadoP };
  }, [plan]);
  useLayoutEffect(() => {
    const g = ref.current?.getContext("2d");
    if (!g) return;
    if (plan.estilo === "pinzas" && datos) pintaPinzas(g, plan, f, datos.est, datos.pos, datos.inicio, datos.spr);
    else if (plan.estilo === "notas") pintaNotas(g, plan, f);
    else pintaAnillos(g, plan, f);
    // marca de agua (como en los demás vídeos del canal)
    g.font = `700 32px ${FUENTE}`; g.textAlign = "left"; g.textBaseline = "top";
    g.fillStyle = "rgba(255,255,255,0.45)"; g.fillText(plan.marca || "Hush Satisfy Lab", 1080 * 0.03, 1920 * 0.042 - 16);
  }, [f, plan, datos]);
  return <canvas ref={ref} width={W} height={H} style={{ width: W, height: H }} />;
};

export const Satisfy2D: React.FC<S2Props> = (props) => {
  const ruta = props.plan || (getInputProps() as S2Props).plan;
  const [plan, setPlan] = useState<any>(cache[ruta] ?? null);
  const [h] = useState(() => (cache[ruta] ? null : delayRender(`plan ${ruta}`)));
  useEffect(() => {
    if (plan) return;
    fetch(staticFile(ruta)).then((r) => r.json()).then((p) => { cache[ruta] = p; setPlan(p); if (h !== null) continueRender(h); });
  }, [ruta, plan, h]);
  if (!plan) return <AbsoluteFill style={{ background: "#000" }} />;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Lienzo plan={plan} />
      {!props.mute && <Audio src={staticFile(plan.audio)} />}
    </AbsoluteFill>
  );
};
