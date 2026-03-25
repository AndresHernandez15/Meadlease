'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
//  baymax_face.js  —  v4.0
//  Robot Asistente Médico Meadlese
//
//  Modo claro: fondo blanco, ojos negros — fiel al personaje original.
//  Geometría: dos círculos sólidos + línea horizontal. Sin adornos.
//
//  Estados implementados:
//    IDLE       — reposo: respira, parpadea (simple + doble), micro-drift
//    WAKE       — pulso en línea + bloom oscuro + ojos saltones + nod "¿Sí?"
//    LISTENING  — azul + anillo reactivo al micrófono
//    THINKING   — ámbar + cabeceo + punto viajero en la línea
//    SPEAKING   — línea → onda de voz + jiggle en picos de audio
//    MOVING     — bob de caminata (2 frecuencias) — "chill"
//    SEARCHING  — barrido lateral + shimmer + teal si REMINDER activo
//    APPROACHING — scan biométrico vertical → bloom verde (reconocido)
//                                           → glitch + sacudida (rechazado)
//
//  API pública:
//    setState(state, params)
//    setAudioLevel(0–1)       setMicLevel(0–1)
//    setConfidence(0–1)       rejectApproach()
//    setReminderActive(bool)
//
//  Keyboard (desarrollo):
//    1–8 → estados   A → sim audio   D → debug
//    R   → reminder (SEARCHING)   C → ciclar fases (APPROACHING)
// ═══════════════════════════════════════════════════════════════════════════════

const BASE_W = 1366;

// ─── Geometría ────────────────────────────────────────────────────────────────
const G = {
  eyeR:       58,
  eyeSep:    178,
  lineW:       4.5,
  waveAmp:    52,
  ringGap:    14,
  ringW:       2.5,
  dotR:        7,
  wakePulseR: 260,
  textDy:    195,
};

// ─── Springs ──────────────────────────────────────────────────────────────────
const SPRING = {
  EYE_SCALE: { mass: 1.0, stiffness: 180, damping: 14 },
  JIGGLE:    { mass: 0.6, stiffness: 100, damping: 12 },
  REJECT:    { mass: 0.8, stiffness: 220, damping:  8 },
};

// ─── Colores — modo claro, oscuros sobre blanco ───────────────────────────────
// Todos los valores son oscuros porque el fondo es blanco.
const COL = {
  IDLE:       { r:  17, g:  17, b:  17 },   // casi negro
  WAKE:       { r:  17, g:  17, b:  17 },
  LISTENING:  { r:  21, g: 101, b: 192 },   // azul profundo
  THINKING:   { r: 205, g: 105, b:  15 },   // ámbar vivo
  SPEAKING:   { r:  17, g:  17, b:  17 },
  MOVING:     { r:  17, g:  17, b:  17 },
  SEARCHING:  { r:  17, g:  17, b:  17 },
  APPROACHING:{ r:  17, g:  17, b:  17 },
};
const COL_TEAL  = { r: 13, g: 122, b:  90 };
const COL_GREEN = { r: 13, g: 122, b:  90 };

// ─── Duración de transición por par de estados ────────────────────────────────
const TRANS_MS = {
  default:                 320,
  'WAKE>LISTENING':        480,
  'SEARCHING>APPROACHING': 200,
  'APPROACHING>SEARCHING': 380,
};


// ═══════════════════════════════════════════════════════════════════════════════
//  CLASE PRINCIPAL
// ═══════════════════════════════════════════════════════════════════════════════
class BaymaxFace {

  constructor(canvas) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext('2d');

    // ── FSM ───────────────────────────────────────────────────────────────────
    this.state       = 'IDLE';
    this.prevState   = 'IDLE';
    this.transT      = 1;
    this._transMs    = 320;
    this.stateParams = {};

    // ── Escala ────────────────────────────────────────────────────────────────
    this.S  = 1;
    this.W2 = 0;
    this.H2 = 0;
    this._resize();
    window.addEventListener('resize', () => this._resize());

    // ── Audio ─────────────────────────────────────────────────────────────────
    this.audioLevel      = 0;
    this.micLevel        = 0;
    this.smoothAudio     = 0;
    this.smoothMic       = 0;
    this.simAudio        = false;
    this._simPhase       = 0;
    this._prevAudioLevel = 0;

    // ── Springs ───────────────────────────────────────────────────────────────
    this._eyeScaleL = { pos: 1, vel: 0 };
    this._eyeScaleR = { pos: 1, vel: 0 };
    this._jiggleL   = { pos: 0, vel: 0 };
    this._jiggleR   = { pos: 0, vel: 0 };
    this._rejectSpr = { pos: 0, vel: 0 };

    // ── Parpadeo ──────────────────────────────────────────────────────────────
    this._blinkRy     = 1;
    this._blinkPhase  = 'idle';
    this._blinkTimer  = 0;
    this._blinkNext   = this._rand(2800, 5500);
    this._doubleBlink = false;

    // ── Respiración + micro-drift IDLE ────────────────────────────────────────
    this._breathT     = 0;
    this._driftPhaseX = Math.random() * 100;
    this._driftPhaseY = Math.random() * 100;

    // ── WAKE ──────────────────────────────────────────────────────────────────
    this._wakeActive = false;
    this._wakeTs     = 0;
    this._wakeLine   = 0;
    this._wakeBloom  = 0;    // 0→1: expansión del bloom oscuro
    this._wakeNodY   = 0;
    this._wakePulses = [];

    // ── LISTENING ─────────────────────────────────────────────────────────────
    this._ringPulse       = 0;
    this._ringEntryActive = false;
    this._ringEntry       = 0;

    // ── THINKING ─────────────────────────────────────────────────────────────
    this._tiltPhase = 0;
    this._dotPhase  = 0;

    // ── SPEAKING ──────────────────────────────────────────────────────────────
    this._wavePhase = 0;

    // ── MOVING ────────────────────────────────────────────────────────────────
    this._moveBobT = 0;

    // ── SEARCHING ─────────────────────────────────────────────────────────────
    this._searchT        = 0;
    this._reminderActive = false;
    this._reminderBlend  = 0;

    // ── APPROACHING ───────────────────────────────────────────────────────────
    // Tres fases: curious lean → nod yes → shake no
    // Todo con la cara inexpresiva — el movimiento lo dice todo.
    this._approachPhase   = 'seeking';  // 'seeking' | 'recognized' | 'rejected'
    this._curiousLean     = 0;          // ángulo del cabeceo curioso (rad)
    this._curiousLeanT    = 0;          // acumulador de fase
    this._nodSpring       = { pos: 0, vel: 0 };  // spring vertical para el sí
    this._shakeSpring     = { pos: 0, vel: 0 };  // spring horizontal para el no

    // ── Debug ─────────────────────────────────────────────────────────────────
    this._debug = false;

    this._lastTs = 0;
    this._rafId  = null;

    this._setupKeys();
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  API PÚBLICA
  // ═══════════════════════════════════════════════════════════════════════════

  setState(newState, params = {}) {
    if (newState === this.state) return;
    this.prevState   = this.state;
    this.state       = newState;
    this.transT      = 0;
    this.stateParams = params;
    this._transMs    = TRANS_MS[`${this.prevState}>${newState}`] ?? TRANS_MS.default;

    switch (newState) {
      case 'IDLE':
        this._blinkNext  = this._rand(600, 2200);
        this._blinkTimer = 0;
        break;

      case 'WAKE':
        this._eyeScaleL.vel += 5.5;
        this._eyeScaleR.vel += 5.5;
        this._wakeActive = true;
        this._wakeTs     = this._lastTs;
        this._wakeLine   = 0;
        this._wakeBloom  = 0;
        this._wakeNodY   = 0;
        this._wakePulses = [];
        if (this._blinkRy < 0.5) { this._blinkPhase = 'opening'; this._blinkTimer = 0; }
        break;

      case 'LISTENING':
        this._ringEntry       = 0;
        this._ringEntryActive = true;
        break;

      case 'THINKING':
        this._tiltPhase = 0;
        this._dotPhase  = 0;
        break;

      case 'APPROACHING':
        this._approachPhase    = 'seeking';
        this._curiousLeanT     = 0;
        this._nodSpring.pos    = 0;
        this._nodSpring.vel    = 0;
        this._shakeSpring.pos  = 0;
        this._shakeSpring.vel  = 0;
        break;
    }
  }

  setAudioLevel(l) { this.audioLevel = Math.max(0, Math.min(1, l)); }
  setMicLevel(l)   { this.micLevel   = Math.max(0, Math.min(1, l)); }

  setConfidence(val) {
    if (this.state !== 'APPROACHING' || this._approachPhase !== 'seeking') return;
    if (val >= 0.75) {
      this._approachPhase = 'recognized';
      // Kick hacia arriba — 2-3 nods naturales con spring underdamped
      this._nodSpring.pos = 0;
      this._nodSpring.vel = -this._s(420);
    }
  }

  rejectApproach() {
    if (this.state !== 'APPROACHING') return;
    this._approachPhase   = 'rejected';
    // Kick lateral — 3 oscilaciones con spring underdamped
    this._shakeSpring.pos = 0;
    this._shakeSpring.vel = this._s(380);
  }

  setReminderActive(active) { this._reminderActive = !!active; }

  start() {
    if (this._rafId) return;
    this._rafId = requestAnimationFrame(ts => this._loop(ts));
  }

  stop() {
    if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = null; }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  LOOP
  // ═══════════════════════════════════════════════════════════════════════════

  _loop(ts) {
    const dt = Math.min(ts - (this._lastTs || ts), 80);
    this._lastTs = ts;
    this._update(ts, dt);
    this._render(ts);
    this._rafId = requestAnimationFrame(nts => this._loop(nts));
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  UPDATE
  // ═══════════════════════════════════════════════════════════════════════════

  _update(ts, dt) {
    if (this.transT < 1)
      this.transT = Math.min(1, this.transT + dt / this._transMs);

    const dtS = dt / 1000;

    this._breathT     += (dt / 4500) * Math.PI * 2;
    this._driftPhaseX += dt * 0.0002;
    this._driftPhaseY += dt * 0.00025;
    this._moveBobT    += dtS;
    this._searchT     += dtS;

    this._updateSpring(this._eyeScaleL,  1, SPRING.EYE_SCALE, dtS);
    this._updateSpring(this._eyeScaleR,  1, SPRING.EYE_SCALE, dtS);
    this._updateSpring(this._jiggleL,    0, SPRING.JIGGLE,    dtS);
    this._updateSpring(this._jiggleR,    0, SPRING.JIGGLE,    dtS);
    this._updateSpring(this._nodSpring,  0, { mass: 0.7, stiffness: 140, damping: 9  }, dtS);
    this._updateSpring(this._shakeSpring,0, { mass: 0.7, stiffness: 160, damping: 8  }, dtS);

    this._updateBlink(dt);
    if (this._wakeActive) this._updateWake(ts, dt);

    this._ringPulse += dt * 0.0025;
    if (this._ringEntryActive) {
      this._ringEntry = Math.min(1, this._ringEntry + dt / 500);
      if (this._ringEntry >= 1) this._ringEntryActive = false;
    }

    if (this.state === 'THINKING' || this.prevState === 'THINKING') {
      this._tiltPhase += dt * 0.00078;
      this._dotPhase  += dt * 0.00175;
    }

    this._wavePhase += dt * 0.0032;
    if (this.state === 'SPEAKING') {
      const peak = this.audioLevel - this._prevAudioLevel;
      if (peak > 0.35) {
        const kick = this._s(peak * 1.2);
        this._jiggleL.vel += kick;
        this._jiggleR.vel += kick;
      }
    }
    this._prevAudioLevel = this.audioLevel;

    const remTarget      = this._reminderActive ? 1 : 0;
    this._reminderBlend += (remTarget - this._reminderBlend) * Math.min(1, dt * 0.003);

    // APPROACHING — lean curioso solo en seeking
    if (this.state === 'APPROACHING' && this._approachPhase === 'seeking') {
      this._curiousLeanT += dtS;
    }

    if (this.simAudio && this.state === 'SPEAKING') {
      this._simPhase += dt * 0.001;
      const env   = Math.max(0, Math.sin(this._simPhase * 2.3) * 0.5 + 0.55);
      const fast  = Math.abs(Math.sin(this._simPhase * 15) * Math.sin(this._simPhase * 7 + 1));
      const pause = Math.max(0, Math.sin(this._simPhase * 0.85));
      this.audioLevel = Math.min(1, env * fast * pause * 0.95);
    } else if (!this.simAudio) {
      this.audioLevel = 0;
    }

    this.smoothAudio = this.smoothAudio * 0.55 + this.audioLevel * 0.45;
    this.smoothMic   = this.smoothMic   * 0.65 + this.micLevel   * 0.35;
  }

  _updateBlink(dt) {
    this._blinkTimer += dt;
    switch (this._blinkPhase) {
      case 'idle':
        if (this._blinkTimer >= this._blinkNext) { this._blinkPhase = 'closing'; this._blinkTimer = 0; }
        break;
      case 'closing': {
        const p = Math.min(1, this._blinkTimer / 115);
        this._blinkRy = 1 - this._easeInQuad(p);
        if (this._blinkTimer >= 115) { this._blinkPhase = 'opening'; this._blinkTimer = 0; }
        break;
      }
      case 'opening': {
        const p = Math.min(1, this._blinkTimer / 160);
        this._blinkRy = this._easeOutCubic(p);
        if (this._blinkTimer >= 160) {
          this._blinkRy = 1; this._blinkPhase = 'idle'; this._blinkTimer = 0;
          if (!this._doubleBlink && Math.random() < 0.15) {
            this._doubleBlink = true;
            this._blinkNext   = this._rand(100, 180);
          } else {
            this._doubleBlink = false;
            this._blinkNext   = this._rand(3000, 7500);
          }
        }
        break;
      }
    }
  }

  _updateWake(ts, dt) {
    const e = ts - this._wakeTs;
    this._wakeLine = Math.min(1, e / 220);
    if (e >= 180) {
      const t = Math.min(1, (e - 180) / 300);
      this._wakeBloom = t < 0.35 ? t / 0.35 : 1 - (t - 0.35) / 0.65;
    }
    if (e >= 200 && this._wakePulses.length === 0) {
      this._wakePulses = [
        { offset:   0, maxR: G.wakePulseR * 0.8 },
        { offset: 180, maxR: G.wakePulseR * 0.5 },
      ];
    }
    const NOD_PX = 18;
    if (e <= 600) {
      const t = e / 600;
      this._wakeNodY = -this._s(NOD_PX) * (1 - Math.pow(1 - t, 4));
    } else if (e <= 1200) {
      const t = (e - 600) / 600;
      this._wakeNodY = -this._s(NOD_PX) * (1 - this._easeInOutCubic(t));
    } else {
      this._wakeNodY = 0; this._wakeBloom = 0;
      this._wakeLine = 1; this._wakeActive = false;
    }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  _render(ts) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // ── Fondo blanco ──────────────────────────────────────────────────────────
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const t = this._easeInOutCubic(this.transT);

    // Color base
    let baseCol = this._lerpRGB(COL[this.prevState] ?? COL.IDLE, COL[this.state] ?? COL.IDLE, t);
    if (this.state === 'SEARCHING' || this.prevState === 'SEARCHING') {
      const tb = this._reminderBlend * ((this.state === 'SEARCHING') ? t : (1 - t));
      baseCol = this._lerpRGB(baseCol, COL_TEAL, tb);
    }
    const colStr  = `rgb(${baseCol.r},${baseCol.g},${baseCol.b})`;
    const alphaStr = (a) => `rgba(${baseCol.r},${baseCol.g},${baseCol.b},${a})`;

    const breathRy = 1 + Math.sin(this._breathT) * 0.015;

    // Cabeceo THINKING
    const tiltBlend = (this.state==='THINKING') ? t : (this.prevState==='THINKING' ? 1-t : 0);
    const tiltAngle = Math.sin(this._tiltPhase) * 0.11 * tiltBlend;

    // Bob MOVING
    const movingBlend = (this.state==='MOVING') ? t : (this.prevState==='MOVING' ? 1-t : 0);
    const slowBob = Math.sin(this._moveBobT * 2 * Math.PI * 1.2);
    const fastBob = Math.sin(this._moveBobT * 2 * Math.PI * 2.4);
    const bobY    = this._s(slowBob * 6 + fastBob * 2.5) * movingBlend;
    const bobRot  = slowBob * 0.022 * movingBlend;

    // Drift IDLE
    const driftBlend = (this.state==='IDLE') ? t : (this.prevState==='IDLE' ? 1-t : 0);
    const driftX = Math.sin(this._driftPhaseX) * this._s(1.5) * driftBlend;
    const driftY = Math.cos(this._driftPhaseY) * this._s(1.5) * driftBlend;

    // Barrido SEARCHING
    const searchBlend = (this.state==='SEARCHING') ? t : (this.prevState==='SEARCHING' ? 1-t : 0);
    const sweepX = Math.sin(this._searchT * 2 * Math.PI / 2.5) * this._s(42) * searchBlend;

    // Lean curioso APPROACHING (seeking) — inclinación sinusoidal lenta
    // Nod yes — spring vertical
    // Shake no — spring horizontal
    const approachBlend = (this.state==='APPROACHING') ? t : (this.prevState==='APPROACHING' ? 1-t : 0);

    // Lean: oscilación sinusoidal de ~8° con período 2.2 s, solo en seeking
    const leanAngle = Math.sin(this._curiousLeanT * 2 * Math.PI / 2.2) * 0.14 * approachBlend
                    * (this._approachPhase === 'seeking' ? 1 : 0);

    // Nod: desplazamiento vertical del spring (positivo = abajo)
    const nodY   = this._nodSpring.pos   * approachBlend;

    // Shake: desplazamiento horizontal del spring
    const shakeX = this._shakeSpring.pos * approachBlend;

    ctx.save();
    ctx.translate(this.W2 + shakeX, this.H2 + this._wakeNodY + bobY + nodY);
    ctx.rotate(tiltAngle + bobRot + leanAngle);

    const lx = -this._s(G.eyeSep) + driftX + sweepX;
    const rx =  this._s(G.eyeSep) + driftX + sweepX;
    const r  =  this._s(G.eyeR);
    const rL = r * Math.max(0.1, this._eyeScaleL.pos);
    const rR = r * Math.max(0.1, this._eyeScaleR.pos);

    // Anillos LISTENING
    const ringBlend = (this.state==='LISTENING') ? t : (this.prevState==='LISTENING' ? 1-t : 0);
    if (ringBlend > 0.01) {
      this._drawRing(lx, driftY, rL, ringBlend, baseCol, alphaStr);
      this._drawRing(rx, driftY, rR, ringBlend, baseCol, alphaStr);
    }

    // Línea / onda
    const waveBlend = (this.state==='SPEAKING') ? t : (this.prevState==='SPEAKING' ? 1-t : 0);
    this._drawLineOrWave(lx, rx, driftY, rL, rR, colStr, alphaStr, waveBlend);

    // Pulso WAKE sobre la línea
    if (this._wakeActive && this._wakeLine < 1)
      this._drawLinePulse(lx, rx, driftY, rL, rR, this._wakeLine, baseCol);

    // Shimmer SEARCHING
    if (searchBlend > 0.01)
      this._drawLineShimmer(lx, rx, driftY, rL, rR, searchBlend, baseCol);

    this._drawCircle(lx, driftY, rL, breathRy, this._jiggleL.pos,
                     colStr, alphaStr, this._wakeBloom);
    this._drawCircle(rx, driftY, rR, breathRy, this._jiggleR.pos,
                     colStr, alphaStr, this._wakeBloom);

    // Punto viajero THINKING
    const dotBlend = (this.state==='THINKING') ? t : (this.prevState==='THINKING' ? 1-t : 0);
    if (dotBlend > 0.01)
      this._drawTravelingDot(lx, rx, driftY, rL, rR, dotBlend, baseCol);

    // Texto "Escuchando..."
    const textBlend = (this.state==='LISTENING') ? t : (this.prevState==='LISTENING' ? 1-t : 0);
    if (textBlend > 0.01)
      this._drawListeningText(textBlend, baseCol);

    ctx.restore();

    // Pulsos WAKE (coordenadas absolutas)
    if (this._wakePulses.length > 0) this._drawWakePulses(ts);

    if (this._debug) this._drawDebug();
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  MÉTODOS DE DIBUJO
  // ═══════════════════════════════════════════════════════════════════════════

  _drawCircle(x, y, r, breathRy, jiggle, colStr, alphaStr, bloom = 0) {
    if (r < 1) return;
    const ctx   = this.ctx;
    const ryEff = r * Math.max(0.02, this._blinkRy * breathRy) + jiggle;
    if (ryEff < 0.5) return;

    ctx.save();
    // Sombra sutil — en modo claro, los ojos se elevan del fondo
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = this._s(2 + bloom * 4);
    ctx.shadowBlur    = this._s(8 + bloom * 20);
    ctx.shadowColor   = `rgba(0,0,0,${0.12 + bloom * 0.18})`;

    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.fillStyle = colStr;
    ctx.fill();

    // Highlight sutil: reflejo muy tenue en la esquina superior izquierda
    ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.clip();
    const hGrd = ctx.createRadialGradient(
      x - r * 0.28, y - ryEff * 0.32, 0,
      x - r * 0.28, y - ryEff * 0.32, r * 0.5
    );
    hGrd.addColorStop(0,   'rgba(255,255,255,0.18)');
    hGrd.addColorStop(1,   'rgba(255,255,255,0)');
    ctx.fillStyle = hGrd;
    ctx.fillRect(x - r, y - ryEff, r * 2, ryEff * 2);
    ctx.restore();
  }

  _drawLineOrWave(lx, rx, y, rL, rR, colStr, alphaStr, waveBlend) {
    const ctx = this.ctx;
    const x1 = lx + rL, x2 = rx - rR;
    if (x2 <= x1 + 2) return;
    const span = x2 - x1;
    const amp  = this.smoothAudio * this._s(G.waveAmp) * waveBlend;
    ctx.save();
    ctx.strokeStyle = colStr;
    ctx.lineWidth   = this._s(G.lineW);
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.shadowBlur    = this._s(3);
    ctx.shadowColor   = alphaStr(0.12);
    ctx.shadowOffsetY = this._s(1);
    ctx.beginPath();
    for (let i = 0; i <= 140; i++) {
      const f  = i / 140;
      const px = x1 + f * span;
      const py = y + Math.sin(f * Math.PI) * Math.sin(f * Math.PI * 4 + this._wavePhase) * amp;
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();
  }

  _drawLinePulse(lx, rx, y, rL, rR, progress, col) {
    const ctx  = this.ctx;
    const x1 = lx + rL, x2 = rx - rR;
    const mid = (x1 + x2) / 2, half = (x2 - x1) / 2;
    const reachL = mid - half * progress;
    const reachR = mid + half * progress;

    // En modo claro: el pulso es oscuro con sombra sutil
    const makeGrad = (x0, x1) => {
      const g = ctx.createLinearGradient(x0, y, x1, y);
      g.addColorStop(0,   `rgba(${col.r},${col.g},${col.b},0)`);
      g.addColorStop(0.5, `rgba(${col.r},${col.g},${col.b},0.35)`);
      g.addColorStop(1,   `rgba(${col.r},${col.g},${col.b},0.9)`);
      return g;
    };
    ctx.save();
    ctx.lineWidth   = this._s(G.lineW * 1.8);
    ctx.lineCap     = 'round';
    ctx.shadowBlur  = this._s(8);
    ctx.shadowColor = `rgba(${col.r},${col.g},${col.b},0.25)`;
    ctx.beginPath(); ctx.moveTo(mid, y); ctx.lineTo(reachL, y);
    ctx.strokeStyle = makeGrad(mid, reachL); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(mid, y); ctx.lineTo(reachR, y);
    ctx.strokeStyle = makeGrad(mid, reachR); ctx.stroke();
    ctx.restore();
  }

  _drawLineShimmer(lx, rx, y, rL, rR, blend, col) {
    const ctx = this.ctx;
    const x1  = lx + rL, x2 = rx - rR;
    if (x2 <= x1) return;
    const shimX = x1 + ((this._searchT / 1.8) % 1) * (x2 - x1);
    ctx.save();
    const grad = ctx.createRadialGradient(shimX, y, 0, shimX, y, this._s(28));
    grad.addColorStop(0,    `rgba(${col.r},${col.g},${col.b},${blend * 0.55})`);
    grad.addColorStop(0.4,  `rgba(${col.r},${col.g},${col.b},${blend * 0.12})`);
    grad.addColorStop(1,    `rgba(${col.r},${col.g},${col.b},0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.ellipse(shimX, y, this._s(28), this._s(7), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  _drawRing(x, y, circR, blend, col, alphaStr) {
    const ctx = this.ctx;
    let extraR = 0, entryOpacity = 1;
    if (this._ringEntryActive) {
      const eased  = this._easeOutCubic(this._ringEntry);
      extraR        = this._s(55) * (1 - eased);
      entryOpacity  = 0.3 + eased * 0.7;
    }
    const rr    = circR + this._s(G.ringGap) + this.smoothMic * this._s(26) + extraR;
    const pulse = (Math.sin(this._ringPulse) * 0.15 + 0.85) * blend * entryOpacity;
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, rr, 0, Math.PI * 2);
    ctx.strokeStyle = alphaStr(pulse * (0.32 + this.smoothMic * 0.45));
    ctx.lineWidth   = this._s(G.ringW);
    ctx.shadowBlur  = this._s(8);
    ctx.shadowColor = alphaStr(pulse * 0.2);
    ctx.stroke();
    ctx.restore();
  }

  _drawTravelingDot(lx, rx, y, rL, rR, blend, col) {
    const ctx = this.ctx;
    const x1 = lx + rL, x2 = rx - rR;
    if (x2 <= x1) return;
    const px = x1 + ((Math.sin(this._dotPhase) + 1) / 2) * (x2 - x1);
    ctx.save();
    ctx.beginPath();
    ctx.arc(px, y, this._s(G.dotR), 0, Math.PI * 2);
    ctx.fillStyle   = `rgba(${col.r},${col.g},${col.b},${blend * 0.88})`;
    ctx.shadowBlur  = this._s(6);
    ctx.shadowColor = `rgba(${col.r},${col.g},${col.b},${blend * 0.25})`;
    ctx.fill();
    ctx.restore();
  }

  _drawListeningText(blend, col) {
    const ctx = this.ctx;
    ctx.save();
    ctx.font         = `300 ${this._s(13)}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
    ctx.fillStyle    = `rgba(${col.r},${col.g},${col.b},${blend * 0.38})`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('E S C U C H A N D O', 0, this._s(G.textDy));
    ctx.restore();
  }

  _drawWakePulses(ts) {
    const ctx  = this.ctx;
    const elap = ts - this._wakeTs - 200;
    if (elap < 0) return;
    const lx = this.W2 - this._s(G.eyeSep);
    const rx = this.W2 + this._s(G.eyeSep);
    let alive = false;
    this._wakePulses.forEach(p => {
      const t = (elap - p.offset) / 900;
      if (t < 0)  { alive = true; return; }
      if (t >= 1) return;
      alive = true;
      const radius  = this._s(G.eyeR + 8 + t * (p.maxR - G.eyeR - 8));
      const opacity = Math.pow(1 - t, 1.8) * 0.18;  // más sutil en modo claro
      [lx, rx].forEach(ex => {
        ctx.save();
        ctx.beginPath();
        ctx.arc(ex, this.H2, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(17,17,17,${opacity})`;
        ctx.lineWidth   = this._s(1.6);
        ctx.stroke();
        ctx.restore();
      });
    });
    if (!alive) this._wakePulses = [];
  }

  _drawDebug() {
    const ctx = this.ctx;
    const W = this.canvas.width, H = this.canvas.height;
    ctx.save();
    ctx.font      = `${this._s(11)}px monospace`;
    ctx.fillStyle = 'rgba(0,0,0,0.25)';
    ctx.textAlign = 'right';
    ctx.fillText(`${this.prevState} → ${this.state}  t=${this.transT.toFixed(2)}`, W-16, H-68);
    ctx.fillText(`audio ${this.smoothAudio.toFixed(2)}  mic ${this.smoothMic.toFixed(2)}  sim ${this.simAudio?'ON':'off'}`, W-16, H-51);
    ctx.fillText(`blink:${this._blinkPhase}  ry=${this._blinkRy.toFixed(2)}  scaleL=${this._eyeScaleL.pos.toFixed(3)}`, W-16, H-34);
    ctx.fillText(`approach:${this._approachPhase}  lean=${this._curiousLeanT.toFixed(1)}  nodY=${this._nodSpring.pos.toFixed(1)}  shakeX=${this._shakeSpring.pos.toFixed(1)}`, W-16, H-17);
    ctx.restore();
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  UTILIDADES
  // ═══════════════════════════════════════════════════════════════════════════

  _updateSpring(spring, target, cfg, dtS) {
    const acc   = (-cfg.stiffness * (spring.pos - target) - cfg.damping * spring.vel) / cfg.mass;
    spring.vel += acc * dtS;
    spring.pos += spring.vel * dtS;
  }

  _resize() {
    this.canvas.width  = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.S  = this.canvas.width / BASE_W;
    this.W2 = this.canvas.width  / 2;
    this.H2 = this.canvas.height / 2;
  }

  _s(v)         { return v * this.S; }
  _rand(a, b)   { return a + Math.random() * (b - a); }
  _lerp(a, b, t){ return a + (b - a) * t; }

  _easeInOutCubic(t) { return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; }
  _easeInOutSine(t)  { return -(Math.cos(Math.PI * t) - 1) / 2; }
  _easeInQuad(t)     { return t * t; }
  _easeOutCubic(t)   { return 1 - Math.pow(1 - t, 3); }

  _lerpRGB(a, b, t) {
    return {
      r: Math.round(a.r + (b.r - a.r) * t),
      g: Math.round(a.g + (b.g - a.g) * t),
      b: Math.round(a.b + (b.b - a.b) * t),
    };
  }

  _setupKeys() {
    const MAP = {
      '1':'IDLE','2':'WAKE','3':'LISTENING','4':'THINKING','5':'SPEAKING',
      '6':'MOVING','7':'SEARCHING','8':'APPROACHING',
    };
    window.addEventListener('keydown', e => {
      if (MAP[e.key]) this.setState(MAP[e.key]);
      if (e.key==='a'||e.key==='A') {
        this.simAudio = !this.simAudio;
        console.log('[BaymaxFace] sim audio:', this.simAudio ? 'ON' : 'off');
      }
      if (e.key==='d'||e.key==='D') this._debug = !this._debug;
      if ((e.key==='r'||e.key==='R') && this.state==='SEARCHING') {
        this.setReminderActive(!this._reminderActive);
        console.log('[BaymaxFace] reminder:', this._reminderActive ? 'ON' : 'off');
      }
      if ((e.key==='c'||e.key==='C') && this.state==='APPROACHING') {
        if (this._approachPhase === 'seeking') {
          this.setConfidence(0.85);
          console.log('[BaymaxFace] → recognized');
        } else if (this._approachPhase === 'recognized') {
          this.rejectApproach();
          console.log('[BaymaxFace] → rejected');
        }
      }
    });
  }
}

window.BaymaxFace = BaymaxFace;