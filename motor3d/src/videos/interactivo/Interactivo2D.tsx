// INTERACTIVOS (Pol 24-11): 2.º vídeo diario de Skin / Football / History, sin voz (texto + sonido). 1080x1920, 30 fps, 30 s.
// El plan (public/particulas/<slug>/plan.json, shorts/interactivo.py) dice el tipo:
//   postimagen · troxler · lilac · encuentra (Skin)  |  quiz (Football / History)
// Todo es determinista: la misma línea de tiempo que el audio. Aquí solo se pinta.
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, delayRender, continueRender, getInputProps } from "remotion";

export type IProps = { plan: string; mute?: boolean };
// (24-11) la duración la manda el plan (los quiz duran ~38 s; las pruebas de Skin, 30 s)
export const metadatosInteractivo = async ({ props }: { props: IProps }) => {
  const ruta = props.plan || (getInputProps() as IProps).plan;
  try {
    const p = await fetch(staticFile(ruta)).then((r) => r.json());
    return { durationInFrames: Math.round((p.segundos || 30) * (p.fps || 30)) };
  } catch { return { durationInFrames: 900 }; }
};
const W = 1080, H = 1920, CX = 540, CY = 1010;
const SANS = "'JakartaX', 'Plus Jakarta Sans', Arial, sans-serif";
const TITULO = "'AntonX', Impact, sans-serif";
const SERIF = "'PlayfairX', Georgia, serif";

const fuentes = (() => {
  if (typeof document === "undefined") return null;
  const h = delayRender("fuentes interactivo");
  Promise.all([
    new FontFace("JakartaX", `url(${staticFile("fuentes/PlusJakartaSans-ExtraBold.ttf")})`, { weight: "800" }),
    new FontFace("JakartaX", `url(${staticFile("fuentes/PlusJakartaSans-Bold.ttf")})`, { weight: "700" }),
    new FontFace("AntonX", `url(${staticFile("fuentes/Anton-Regular.ttf")})`),
    new FontFace("PlayfairX", `url(${staticFile("fuentes/PlayfairDisplay-Bold.ttf")})`, { weight: "700" }),
  ].map((ff) => ff.load().then((x) => { (document as any).fonts.add(x); })))
    .then(() => continueRender(h)).catch(() => continueRender(h));
  return true;
})();

const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = (x: number) => { x = clamp(x); return x * x * (3 - 2 * x); };
const back = (x: number) => { x = clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
function rnd(seed: number) { let s = seed >>> 0 || 1; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

// texto con ajuste de líneas, centrado
function texto(g: CanvasRenderingContext2D, s: string, x: number, y: number, ancho: number, tam: number, fuente: string,
  color = "#fff", peso = "800", sombra = true, alinea: CanvasTextAlign = "center", interl = 1.12) {
  g.save(); g.font = `${peso} ${tam}px ${fuente}`; g.textAlign = alinea; g.textBaseline = "middle"; g.fillStyle = color;
  if (sombra) { g.shadowColor = "rgba(0,0,0,0.55)"; g.shadowBlur = 14; g.shadowOffsetY = 4; }
  const pal = s.split(" "); const lineas: string[] = []; let l = "";
  for (const p of pal) { const t = l ? l + " " + p : p; if (g.measureText(t).width > ancho && l) { lineas.push(l); l = p; } else l = t; }
  if (l) lineas.push(l);
  const y0 = y - ((lineas.length - 1) * tam * interl) / 2;
  lineas.forEach((ln, i) => g.fillText(ln, x, y0 + i * tam * interl));
  g.restore();
  return lineas.length;
}

function pildora(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number, fill: string, borde?: string, lw = 4) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); g.fillStyle = fill; g.fill();
  if (borde) { g.strokeStyle = borde; g.lineWidth = lw; g.stroke(); }
}

function marca(g: CanvasRenderingContext2D, s: string, claro = false) {
  g.save(); g.font = `700 32px ${SANS}`; g.textAlign = "left"; g.textBaseline = "top";
  g.fillStyle = claro ? "rgba(0,0,0,0.45)" : "rgba(255,255,255,0.45)"; g.fillText(s, W * 0.03, H * 0.042 - 16); g.restore();
}

// confeti que estalla desde (x, y) en t0 (determinista)
function confeti(g: CanvasRenderingContext2D, t: number, t0: number, x: number, y: number, cols: string[], n = 46, fuerza = 1) {
  const u = t - t0; if (u < 0 || u > 1.6) return;
  const r = rnd(Math.floor(t0 * 1000) + 3);
  g.save();
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2, v = (420 + r() * 620) * fuerza, rot = r() * 6;
    const px = x + Math.cos(a) * v * u, py = y + Math.sin(a) * v * u + 900 * u * u;
    g.globalAlpha = clamp(1 - u / 1.6); g.fillStyle = cols[i % cols.length];
    g.translate(px, py); g.rotate(rot + u * 8); g.fillRect(-9, -5, 18, 10); g.setTransform(1, 0, 0, 1, 0, 0);
  }
  g.restore();
}
// partículas que flotan (fondo vivo de las pantallas oscuras)
function polvo(g: CanvasRenderingContext2D, t: number, col = "255,255,255", n = 40) {
  const r = rnd(99);
  for (let i = 0; i < n; i++) {
    const x = (r() * W + t * (8 + r() * 20)) % W, y = (r() * H - t * (20 + r() * 40) + H * 10) % H, a = 0.05 + 0.12 * r();
    g.fillStyle = `rgba(${col},${a})`; g.beginPath(); g.arc(x, y, 2 + r() * 4, 0, Math.PI * 2); g.fill();
  }
}
// anillo de cuenta atrás alrededor del número
function anillo(g: CanvasRenderingContext2D, t: number, a: number, b: number, y: number, col: string) {
  if (t < a || t >= b) return;
  const u = (t - a) / (b - a);
  g.save(); g.lineWidth = 12; g.lineCap = "round"; g.strokeStyle = "rgba(127,127,127,0.25)";
  g.beginPath(); g.arc(CX, y, 118, 0, Math.PI * 2); g.stroke();
  g.strokeStyle = col; g.beginPath(); g.arc(CX, y, 118, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (1 - u)); g.stroke(); g.restore();
}

// cuenta atrás grande (número que late cada segundo)
function cuenta(g: CanvasRenderingContext2D, t: number, a: number, b: number, y: number, claro: boolean, acento = "#ff3b5c") {
  if (t < a || t >= b) return;
  const quedan = Math.ceil(b - t), fr = (t - a) % 1, s = 1 + 0.22 * Math.max(0, 1 - fr / 0.25);
  g.save(); g.translate(CX, y); g.scale(s, s);
  g.font = `400 170px ${TITULO}`; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillStyle = quedan <= 3 ? acento : (claro ? "#1b1b22" : "#fff");
  g.shadowColor = claro ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)"; g.shadowBlur = 18;
  g.fillText(String(quedan), 0, 0); g.restore();
}

// ------------------------------------------------------------------ SKIN · postimagen
const FIG: Record<string, string[]> = {   // colores INVERTIDOS (la postimagen sale en los de verdad)
  corazon: ["#00e5e5", "#00b3b3"], bandera: ["#00ffff", "#0000ff", "#00ffff"], atardecer: ["#00b4ff", "#ff9a3c", "#2a00ff"],
  bombilla: ["#0000ff", "#5a5aff", "#c0c0c0"], estrella: ["#0000ff", "#00ffff"], arcoiris: ["#00ffff", "#005aff", "#0000ff", "#ff00ff", "#ff7f00", "#7fff00"],
};
function figura(g: CanvasRenderingContext2D, nom: string, alfa: number) {
  const c = FIG[nom] || FIG.corazon; g.save(); g.globalAlpha = alfa;
  if (nom === "corazon") {
    g.translate(CX, CY + 165); g.scale(4.6, 4.6); g.beginPath(); g.moveTo(0, 30);
    g.bezierCurveTo(-90, -40, -60, -120, 0, -70); g.bezierCurveTo(60, -120, 90, -40, 0, 30); g.closePath();
    const gr = g.createLinearGradient(0, -110, 0, 30); gr.addColorStop(0, c[0]); gr.addColorStop(1, c[1]); g.fillStyle = gr; g.fill();
  } else if (nom === "bandera") {
    const w = 900, h = 600, x = CX - w / 2, y = CY - h / 2;
    for (let i = 0; i < 3; i++) { g.fillStyle = c[i]; g.fillRect(x, y + (i * h) / 3, w, h / 3 + 1); }
  } else if (nom === "atardecer") {
    g.fillStyle = c[0]; g.fillRect(90, CY - 420, 900, 520);                       // cielo
    g.fillStyle = c[2]; g.beginPath(); g.arc(CX, CY - 60, 170, 0, Math.PI * 2); g.fill();   // sol
    g.fillStyle = c[1]; g.fillRect(90, CY + 100, 900, 320);                       // mar
  } else if (nom === "bombilla") {
    g.fillStyle = c[0]; g.beginPath(); g.arc(CX, CY - 120, 260, 0, Math.PI * 2); g.fill();
    g.fillStyle = c[2]; g.fillRect(CX - 110, CY + 120, 220, 170);
    g.fillStyle = c[1]; for (let i = 0; i < 4; i++) g.fillRect(CX - 120, CY + 135 + i * 40, 240, 14);
  } else if (nom === "estrella") {
    g.fillStyle = c[0]; g.fillRect(90, CY - 450, 900, 900);
    g.translate(CX, CY); g.fillStyle = c[1]; g.beginPath();
    for (let i = 0; i < 10; i++) { const r = i % 2 ? 150 : 380, a = -Math.PI / 2 + (i * Math.PI) / 5; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    g.closePath(); g.fill();
  } else {
    for (let i = 0; i < 6; i++) { g.strokeStyle = c[i]; g.lineWidth = 62; g.beginPath(); g.arc(CX, CY + 260, 420 - i * 62, Math.PI, 0); g.stroke(); }
  }
  g.restore();
}

function postimagen(g: CanvasRenderingContext2D, P: any, t: number) {
  const [ia, ib] = P.intro, [ma, mb] = P.mira, [ra] = P.revela, [oa] = P.outro;
  const claro = t >= ra;
  g.fillStyle = claro ? "#e9e7e2" : "#101014"; g.fillRect(0, 0, W, H);
  if (!claro) {
    figura(g, P.figura, t < ia + 0.4 ? ease((t - ia) / 0.4) : 1);
    const pul = 1 + 0.12 * Math.sin(t * 6);
    g.fillStyle = "#fff"; g.beginPath(); g.arc(CX, CY, 13 * pul, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#000"; g.beginPath(); g.arc(CX, CY, 5, 0, Math.PI * 2); g.fill();
    if (t < ib) {
      texto(g, "MIRA EL PUNTO", CX, 380, 960, 118, TITULO, "#fff", "400");
      texto(g, `${P.cuenta} segundos sin parpadear`, CX, 500, 900, 54, SANS, "#ffd23f");
    } else {
      texto(g, "No apartes la vista del punto", CX, 330, 900, 46, SANS, "rgba(255,255,255,0.85)", "700");
      anillo(g, t, ma, mb, 1640, "#ffd23f");
      cuenta(g, t, ma, mb, 1640, false);
    }
  } else {
    g.fillStyle = "#222"; g.beginPath(); g.arc(CX, CY, 6, 0, Math.PI * 2); g.fill();
    const u = ease((t - ra) / 0.35);
    if (t < oa) texto(g, "¡AHORA MIRA AQUÍ!", CX, 360 - 30 * (1 - u), 960, 96, TITULO, "#1b1b22", "400", false);
    else {
      confeti(g, t, oa, CX, 330, ["#ff3b5c", "#ffd23f", "#2ecc71", "#3b7bff"]);
      texto(g, "¿LA HAS VISTO EN COLOR?", CX, 330, 960, 88, TITULO, "#1b1b22", "400", false);
      texto(g, "Tus conos se cansan del color y tu cerebro pinta el contrario", CX, 1560, 900, 46, SANS, "#2b2b33", "700", false);
      texto(g, "Dímelo en comentarios", CX, 1720, 900, 46, SANS, "#d11f4b", "800", false);
    }
  }
  marca(g, P.marca_canal, claro);
}

// ------------------------------------------------------------------ SKIN · troxler (manchas borrosas que desaparecen)
const PALS: Record<string, string[]> = {
  pastel: ["#f7a1c4", "#a1d6f7", "#c4f7a1", "#f7e1a1", "#d1a1f7", "#a1f7e6"],
  vivos: ["#ff4d6d", "#4dd2ff", "#7dff4d", "#ffd24d", "#b84dff", "#ff8c4d"],
  calidos: ["#ff6b6b", "#ffa94d", "#ffd43b", "#f783ac", "#e8590c", "#fab005"],
  frios: ["#4dabf7", "#63e6be", "#748ffc", "#3bc9db", "#9775fa", "#38d9a9"],
};
function cruz(g: CanvasRenderingContext2D, col = "#111") {
  g.strokeStyle = col; g.lineWidth = 7; g.beginPath(); g.moveTo(CX - 26, CY); g.lineTo(CX + 26, CY); g.moveTo(CX, CY - 26); g.lineTo(CX, CY + 26); g.stroke();
}
function troxler(g: CanvasRenderingContext2D, P: any, t: number) {
  const [ia, ib] = P.intro, [ma, mb] = P.mira, [ra] = P.revela, [oa] = P.outro;
  g.fillStyle = "#c9c9c9"; g.fillRect(0, 0, W, H);
  const pal = PALS[P.paleta] || PALS.pastel, n = P.n_manchas, r = rnd(P.semilla);
  const sacude = t >= ra && t < ra + 1.2 ? Math.sin((t - ra) * 40) * 14 * (1 - (t - ra) / 1.2) : 0;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + r() * 0.4, d = 250 + r() * 180, x = CX + Math.cos(a) * d + sacude, y = CY + Math.sin(a) * d * 1.15;
    const rad = 130 + r() * 60, gr = g.createRadialGradient(x, y, 0, x, y, rad);
    gr.addColorStop(0, pal[i % pal.length]); gr.addColorStop(1, "rgba(201,201,201,0)");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, rad, 0, Math.PI * 2); g.fill();
  }
  cruz(g);
  if (t < ib) { texto(g, "MIRA LA CRUZ", CX, 360, 960, 118, TITULO, "#111", "400", false); texto(g, "y NO muevas los ojos", CX, 480, 900, 56, SANS, "#c2185b", "800", false); }
  else if (t < mb) { texto(g, "No muevas los ojos…", CX, 330, 900, 46, SANS, "#222", "700", false); anillo(g, t, ma, mb, 1680, "#c2185b"); cuenta(g, t, ma, mb, 1680, true); }
  else if (t < oa) { texto(g, "¿HAN DESAPARECIDO?", CX, 340, 960, 96, TITULO, "#111", "400", false); texto(g, "Muévelos un poco… ¡y vuelven!", CX, 1640, 900, 50, SANS, "#c2185b", "800", false); }
  else { confeti(g, t, oa, CX, 330, pal); texto(g, "EFECTO TROXLER", CX, 330, 960, 96, TITULO, "#111", "400", false);
    texto(g, "Tu cerebro deja de ver lo que no cambia", CX, 1590, 900, 48, SANS, "#222", "700", false);
    texto(g, "¿A ti se te han borrado?", CX, 1730, 900, 48, SANS, "#c2185b", "800", false); }
  marca(g, P.marca_canal, true);
}

// ------------------------------------------------------------------ SKIN · lilac chaser
function lilac(g: CanvasRenderingContext2D, P: any, t: number) {
  const [ia, ib] = P.intro, [ma, mb] = P.mira, [ra] = P.revela, [oa] = P.outro;
  g.fillStyle = "#c4c4c4"; g.fillRect(0, 0, W, H);
  const col = ({ lila: "#c25fd6", rosa: "#e8609f", azul: "#6f7ee8" } as any)[P.color] || "#c25fd6";
  const n = 12, hueco = Math.floor((t * 10) % n);
  for (let i = 0; i < n; i++) {
    if (i === hueco && t < oa) continue;
    const a = (i / n) * Math.PI * 2 - Math.PI / 2, x = CX + Math.cos(a) * 330, y = CY + Math.sin(a) * 330;
    const gr = g.createRadialGradient(x, y, 0, x, y, 95); gr.addColorStop(0, col); gr.addColorStop(0.35, col); gr.addColorStop(1, "rgba(196,196,196,0)");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, 95, 0, Math.PI * 2); g.fill();
  }
  cruz(g);
  if (t < ib) { texto(g, "MIRA LA CRUZ", CX, 360, 960, 118, TITULO, "#111", "400", false); texto(g, "20 segundos, sin mover los ojos", CX, 480, 900, 54, SANS, "#6a1b9a", "800", false); }
  else if (t < mb) { texto(g, "¿Qué color ves girando?", CX, 330, 900, 48, SANS, "#222", "700", false); anillo(g, t, ma, mb, 1680, "#6a1b9a"); cuenta(g, t, ma, mb, 1680, true); }
  else if (t < oa) { texto(g, "¿HAS VISTO UN PUNTO VERDE?", CX, 340, 960, 86, TITULO, "#111", "400", false);
    texto(g, "No existe: solo hay puntos de color y un hueco", CX, 1640, 900, 46, SANS, "#6a1b9a", "800", false); }
  else { confeti(g, t, oa, CX, 330, ["#2ecc71", "#c25fd6", "#ffd23f"]); texto(g, "TU CEREBRO LO INVENTA", CX, 330, 960, 92, TITULO, "#111", "400", false);
    texto(g, "Cada hueco deja una postimagen verde y la ves girar", CX, 1590, 900, 46, SANS, "#222", "700", false);
    texto(g, "¿Lo has visto?", CX, 1730, 900, 48, SANS, "#6a1b9a", "800", false); }
  marca(g, P.marca_canal, true);
}

// ------------------------------------------------------------------ SKIN · encuentra el distinto
function encuentra(g: CanvasRenderingContext2D, P: any, t: number) {
  g.fillStyle = "#0f1220"; g.fillRect(0, 0, W, H); polvo(g, t, "120,170,255");
  const fase = P.fases.find((f: any) => t >= f.t0 && t < f.t1);
  if (t < 2.2) {
    texto(g, "ENCUENTRA", CX, 760, 960, 150, TITULO, "#fff", "400"); texto(g, "EL DISTINTO", CX, 920, 960, 150, TITULO, "#ffd23f", "400");
    texto(g, "2 rondas · 10 segundos cada una", CX, 1100, 900, 52, SANS, "rgba(255,255,255,0.85)", "700");
  } else if (fase) {
    const R = P.rondas[fase.r], cw = 900 / R.cols, ch = 1100 / R.filas, x0 = CX - 450, y0 = 470;
    const tam = Math.min(cw, ch) * 0.78, ent = ease((t - fase.t0) / 0.3);
    g.save(); g.globalAlpha = fase.revela ? 1 : ent; g.font = `800 ${tam}px ${SANS}`; g.textAlign = "center"; g.textBaseline = "middle";
    for (let k = 0; k < R.cols * R.filas; k++) {
      const c = k % R.cols, f = Math.floor(k / R.cols), x = x0 + cw * (c + 0.5), y = y0 + ch * (f + 0.5);
      const raro = k === R.i;
      g.fillStyle = fase.revela ? (raro ? "#ffd23f" : "rgba(255,255,255,0.25)") : "#fff";
      g.fillText(raro ? R.raro : R.base, x, y);
      if (raro && fase.revela) {
        const u = back((t - fase.t0) / 0.45); g.strokeStyle = "#ff3b5c"; g.lineWidth = 9;
        g.beginPath(); g.arc(x, y, tam * 0.9 * u + 4, 0, Math.PI * 2); g.stroke();
      }
    }
    g.restore();
    texto(g, `RONDA ${fase.r + 1}`, CX, 330, 900, 72, TITULO, fase.r ? "#ff8c4d" : "#4dd2ff", "400");
    if (!fase.revela) cuenta(g, t, fase.t0, fase.t1, 1720, false);
    else { texto(g, "¡AQUÍ ESTABA!", CX, 1720, 900, 76, TITULO, "#ffd23f", "400"); confeti(g, t, fase.t0, CX, 1000, ["#ffd23f", "#ff3b5c", "#4dd2ff"], 36, 0.8); }
  } else {
    texto(g, "¿HAS ENCONTRADO", CX, 800, 960, 110, TITULO, "#fff", "400"); texto(g, "LAS DOS?", CX, 930, 960, 130, TITULO, "#ffd23f", "400");
    texto(g, "Dímelo en comentarios", CX, 1120, 900, 54, SANS, "rgba(255,255,255,0.9)", "800");
  }
  marca(g, P.marca_canal);
}

// ------------------------------------------------------------------ SKIN · Stroop (di el COLOR, no la palabra)
function stroop(g: CanvasRenderingContext2D, P: any, t: number) {
  const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, "#151a2e"); gr.addColorStop(1, "#0a0d18");
  g.fillStyle = gr; g.fillRect(0, 0, W, H); polvo(g, t);
  if (t < P.fases[0].t0) {
    const u = back(t / 0.5); g.save(); g.translate(CX, 760); g.scale(u, u);
    texto(g, "DI EL COLOR", 0, 0, 980, 150, TITULO, "#fff", "400"); g.restore();
    texto(g, "no la palabra", CX, 900, 900, 70, SANS, "#ffd23f", "800");
    texto(g, "En voz alta y sin parar", CX, 1040, 900, 50, SANS, "rgba(255,255,255,0.8)", "700");
    return;
  }
  const f = P.fases.find((x: any) => t >= x.t0 && t < x.t1);
  if (f) {
    const n = 7, dur = (f.t1 - f.t0) / n, k = Math.floor((t - f.t0) / dur), u = (t - f.t0 - k * dur) / dur;
    const w = P.palabras[(f.nivel - 1) * 7 + k];
    texto(g, `NIVEL ${f.nivel}`, CX, 330, 900, 70, TITULO, f.nivel === 1 ? "#4dd2ff" : "#ff8c4d", "400");
    texto(g, f.nivel === 1 ? "Di el COLOR" : "Más rápido…", CX, 420, 900, 46, SANS, "rgba(255,255,255,0.75)", "700");
    for (let i = 0; i < n; i++) pildora(g, CX - 230 + i * 70, 500, 44, 12, 6, i < k ? "#2ecc71" : i === k ? "#fff" : "rgba(255,255,255,0.18)");
    const s = back(u / 0.18) * (f.nivel === 2 ? 1 + 0.04 * Math.sin(t * 20) : 1);
    const dx = f.nivel === 2 ? Math.sin(t * 3 + k) * 60 : 0;
    g.save(); g.translate(CX + dx, 960); g.scale(s, s);
    g.font = `400 210px ${TITULO}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = w.color;
    g.shadowColor = w.color; g.shadowBlur = 30; g.fillText(w.palabra, 0, 0); g.restore();
    if (u > 0.7) {
      const v = ease((u - 0.7) / 0.15);
      g.save(); g.globalAlpha = v;
      pildora(g, CX - 260, 1190, 520, 120, 60, "rgba(255,255,255,0.1)", w.color, 5);
      texto(g, `ERA ${w.nombre}`, CX, 1252, 500, 66, TITULO, w.color, "400", false);
      g.restore();
    }
  } else if (t >= P.outro[0]) {
    confeti(g, t, P.outro[0], CX, 800, ["#ff3b3b", "#3b7bff", "#2ecc71", "#ffd23f", "#ff5fb4"]);
    texto(g, "¿HAS FALLADO", CX, 780, 960, 130, TITULO, "#fff", "400"); texto(g, "ALGUNA?", CX, 920, 960, 150, TITULO, "#ffd23f", "400");
    texto(g, "Efecto Stroop: leer es tan automático que tu cerebro se pelea consigo mismo", CX, 1130, 900, 46, SANS, "rgba(255,255,255,0.85)", "700");
    texto(g, "Dímelo en comentarios", CX, 1330, 900, 52, SANS, "#ff5fb4", "800");
  } else {
    texto(g, "NIVEL 2", CX, 900, 900, 160, TITULO, "#ff8c4d", "400");
  }
  marca(g, P.marca_canal);
}

// ------------------------------------------------------------------ QUIZ (Football / History)
function fondoQuiz(g: CanvasRenderingContext2D, P: any, t: number) {
  if (P.canal === "football") {
    const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, "#0b3d1f"); gr.addColorStop(1, "#06210f"); g.fillStyle = gr; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? "rgba(255,255,255,0.025)" : "rgba(0,0,0,0.04)"; g.fillRect(0, i * 240, W, 240); }
    g.strokeStyle = "rgba(255,255,255,0.12)"; g.lineWidth = 6; g.beginPath(); g.arc(CX, H / 2, 230, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.moveTo(0, H / 2); g.lineTo(W, H / 2); g.stroke();
    g.fillStyle = "rgba(255,255,255,0.12)"; g.beginPath(); g.arc(CX, H / 2, 12, 0, Math.PI * 2); g.fill();
  } else {
    const gr = g.createRadialGradient(CX, H / 2, 200, CX, H / 2, 1200); gr.addColorStop(0, "#3a2a17"); gr.addColorStop(1, "#140d06");
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
    const r = rnd(7); g.strokeStyle = "rgba(230,200,140,0.05)"; g.lineWidth = 2;
    for (let i = 0; i < 70; i++) { const y = r() * H; g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(300, y + 20 * r(), 700, y - 20 * r(), W, y + 10 * r()); g.stroke(); }
    g.strokeStyle = "rgba(230,190,110,0.35)"; g.lineWidth = 4; g.strokeRect(40, 150, W - 80, H - 300);
  }
  void t;
}
function quiz(g: CanvasRenderingContext2D, P: any, t: number) {
  fondoQuiz(g, P, t); polvo(g, t, P.canal === "football" ? "255,255,255" : "240,210,150", 30);
  const foot = P.canal === "football", acento = foot ? "#ffd23f" : "#e8c27a", fq = foot ? SANS : SERIF;
  const tarjeta = foot ? "rgba(255,255,255,0.08)" : "rgba(245,225,185,0.08)";
  if (t < P.intro[1]) {
    const u = back(t / 0.5);
    g.save(); g.translate(CX, 800); g.scale(u, u);
    texto(g, "QUIZ", 0, -40, 960, 220, TITULO, acento, "400"); g.restore();
    texto(g, P.tema, CX, 1010, 900, 66, fq, "#fff", "800");
    texto(g, `¿Aciertas las ${P.bloques.length}?`, CX, 1180, 900, 60, SANS, "rgba(255,255,255,0.9)", "800");
  } else if (t < P.outro[0]) {
    const b = P.bloques.find((x: any) => t >= x.t0 && t < x.t1);
    if (b) {
      const ent = ease((t - b.t0) / 0.35), rev = t >= b.tr, ur = ease((t - b.tr) / 0.3);
      // contador de preguntas
      for (let i = 0; i < P.bloques.length; i++) {
        const x = CX - 45 * (P.bloques.length - 1) + i * 90; pildora(g, x - 30, 250, 60, 16, 8, i + 1 < b.n ? acento : i + 1 === b.n ? "#fff" : "rgba(255,255,255,0.18)");
      }
      texto(g, `PREGUNTA ${b.n}`, CX, 345, 900, 54, TITULO, acento, "400");
      g.save(); g.globalAlpha = ent; g.translate(0, 40 * (1 - ent));
      pildora(g, 70, 430, W - 140, 400, 36, tarjeta, foot ? "rgba(255,255,255,0.15)" : "rgba(230,190,110,0.35)", 3);
      texto(g, b.q, CX, 630, W - 220, 64, fq, "#fff", "800");
      g.restore();
      const letras = ["A", "B", "C"];
      b.opciones.forEach((o: string, i: number) => {
        const e2 = ease((t - b.t0 - 0.25 - i * 0.12) / 0.35), y = 940 + i * 190;
        const ok = i === b.correcta;
        let fill = "rgba(255,255,255,0.1)", borde = "rgba(255,255,255,0.35)", col = "#fff";
        if (rev && ok) { fill = "rgba(46,204,113,0.92)"; borde = "#2ecc71"; }
        if (rev && !ok) { fill = "rgba(255,255,255,0.05)"; borde = "rgba(255,255,255,0.12)"; col = "rgba(255,255,255,0.35)"; }
        g.save(); g.globalAlpha = e2; const s = rev && ok ? 1 + 0.06 * Math.sin(clamp(ur) * Math.PI) : 1;
        g.translate(CX, y + 70); g.scale(s, s); g.translate(-CX, -(y + 70));
        pildora(g, 110, y, W - 220, 140, 70, fill, borde, 5);
        pildora(g, 130, y + 20, 100, 100, 50, rev && ok ? "#fff" : acento);
        texto(g, letras[i], 180, y + 72, 100, 60, TITULO, rev && ok ? "#1e8449" : "#111", "400", false);
        texto(g, o, CX + 60, y + 72, W - 440, 54, SANS, col, "800", false);
        if (rev && ok) texto(g, "✓", W - 190, y + 72, 100, 80, SANS, "#fff", "800", false);
        g.restore();
      });
      if (!rev) {   // barra de tiempo
        const u = clamp((t - b.t0) / (b.tr - b.t0));
        pildora(g, 110, 1560, W - 220, 26, 13, "rgba(255,255,255,0.12)");
        pildora(g, 110, 1560, Math.max(26, (W - 220) * (1 - u)), 26, 13, u > 0.7 ? "#ff3b5c" : acento);
        anillo(g, t, b.t0, b.tr, 1740, u > 0.7 ? "#ff3b5c" : acento);
        cuenta(g, t, b.t0, b.tr, 1740, false, "#ff3b5c");
      } else if (b.dato) {
        g.save(); g.globalAlpha = ur; texto(g, b.dato, CX, 1660, W - 200, 48, SANS, acento, "700"); g.restore();
        confeti(g, t, b.tr, CX, 940 + b.correcta * 190 + 70, [acento, "#2ecc71", "#ffffff", "#ff3b5c"], 40, 0.7);
      }
    }
  } else {
    const u = back((t - P.outro[0]) / 0.5);
    g.save(); g.translate(CX, 830); g.scale(u, u); texto(g, "¿CUÁNTAS", 0, -80, 960, 150, TITULO, "#fff", "400");
    texto(g, "HAS ACERTADO?", 0, 80, 960, 130, TITULO, acento, "400"); g.restore();
    texto(g, "Dímelo en comentarios", CX, 1110, 900, 56, SANS, "rgba(255,255,255,0.92)", "800");
  }
  marca(g, P.marca_canal);
}

// ======================================================================== composición
const cache: Record<string, any> = {};
const Lienzo: React.FC<{ plan: any }> = ({ plan }) => {
  void fuentes;
  const f = useCurrentFrame();
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const g = ref.current?.getContext("2d");
    if (!g) return;
    const t = f / (plan.fps || 30);
    g.clearRect(0, 0, W, H);
    ({ postimagen, troxler, lilac, encuentra, stroop, quiz } as any)[plan.tipo](g, plan, t);
  }, [f, plan]);
  return <canvas ref={ref} width={W} height={H} style={{ width: W, height: H }} />;
};

export const Interactivo2D: React.FC<IProps> = (props) => {
  const ruta = props.plan || (getInputProps() as IProps).plan;
  const [plan, setPlan] = useState<any>(cache[ruta] ?? null);
  const [h] = useState(() => (cache[ruta] ? null : delayRender(`plan ${ruta}`)));
  useEffect(() => {
    if (plan) return;
    fetch(staticFile(ruta)).then((r) => r.json()).then((p) => { cache[ruta] = p; setPlan(p); if (h !== null) continueRender(h); });
  }, [ruta, plan, h]);
  if (!plan) return <AbsoluteFill style={{ background: "#111" }} />;
  return (
    <AbsoluteFill style={{ background: "#111" }}>
      <Lienzo plan={plan} />
      {!props.mute && <Audio src={staticFile(plan.audio)} />}
    </AbsoluteFill>
  );
};
