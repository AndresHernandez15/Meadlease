'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
//  baymax_face.js  —  v3.0
//  Robot Asistente Médico Meadlese
//
//  Anatomía fiel al personaje: dos círculos sólidos + línea horizontal.
//  Una sola idea visual por estado — elegante, no sobrecargado.
//
//  Estados implementados:
//    IDLE      — reposo: respira, parpadea (simple + doble), micro-drift
//    WAKE      — pulso en línea + bloom + ojos saltones + nod del "¿Sí?"
//    LISTENING — azul + anillo reactivo al micrófono
//    THINKING  — ámbar + cabeceo + punto viajero en la línea
//    SPEAKING  — línea → onda de voz + jiggle en picos de audio
//    MOVING    — bob de caminata (2 frecuencias) + rotación sutil — "chill"
//    SEARCHING — barrido lateral + shimmer en la línea + teal si REMINDER activo
//    APPROACHING — ? flotando → ✓ verde + ojos entrecerrados (reconocido)
//                             → sacudida horizontal  (no reconocido)
//
//  API pública:
//    setState(state, params)   — cambiar estado
//    setAudioLevel(0-1)        — nivel TTS
//    setMicLevel(0-1)          — nivel micrófono
//    setConfidence(0-1)        — confianza de reconocimiento facial (APPROACHING)
//    rejectApproach()          — dispara la sacudida de "no"
//    setReminderActive(bool)   — activa modo teal en SEARCHING
//
//  Keyboard (oculto, solo desarrollo):
//    1–8 → estados   A → sim audio   D → debug
//    R   → toggle reminder (en SEARCHING)
//    C   → ciclar fases seeking → recognized → rejected (en APPROACHING)
// ═══════════════════════════════════════════════════════════════════════════════

const BASE_W = 1366;

// ─── Geometría base (px a resolución BASE_W) ─────────────────────────────────
const G = {
  eyeR:       58,
  eyeSep:    178,
  lineW:       4.5,
  waveAmp:    58,
  ringGap:    14,
  ringW:       2.5,
  dotR:        7,
  wakePulseR: 260,
  textDy:    195,
  symbolDy:  110,   // distancia sobre el centro de la cara al símbolo ? / ✓
  symbolSz:   28,   // tamaño de referencia del símbolo
};

// ─── Springs ──────────────────────────────────────────────────────────────────
const SPRING = {
  EYE_SCALE: { mass: 1.0, stiffness: 180, damping: 14 }, // ojos saltones WAKE
  JIGGLE:    { mass: 0.6, stiffness: 100, damping: 12 }, // jiggle vertical SPEAKING
  REJECT:    { mass: 0.8, stiffness: 220, damping:  8 }, // sacudida horizontal APPROACHING
};

// ─── Colores RGB por estado ───────────────────────────────────────────────────
const COL = {
  IDLE:       { r: 255, g: 255, b: 255 },
  WAKE:       { r: 255, g: 255, b: 255 },
  LISTENING:  { r:  75, g: 152, b: 220 },
  THINKING:   { r: 202, g: 130, b:  30 },
  SPEAKING:   { r: 255, g: 255, b: 255 },
  MOVING:     { r: 255, g: 255, b: 255 },
  SEARCHING:  { r: 255, g: 255, b: 255 },  // sobrescrito por REMINDER
  APPROACHING:{ r: 255, g: 255, b: 255 },
};
const COL_TEAL  = { r: 29, g: 158, b: 117 };
const COL_GREEN = { r: 29, g: 158, b: 117 };

// ─── Duración de transición por par de estados ────────────────────────────────
const TRANS_MS = {
  default:                 320,
  'WAKE>LISTENING':        480,
  'SEARCHING>APPROACHING': 200,  // rápido — robot ve a alguien
  'APPROACHING>SEARCHING': 380,  // más lento — fade tras el rechazo
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
    this._eyeScaleL = { pos: 1, vel: 0 };  // ojos saltones WAKE
    this._eyeScaleR = { pos: 1, vel: 0 };
    this._jiggleL   = { pos: 0, vel: 0 };  // jiggle vertical SPEAKING
    this._jiggleR   = { pos: 0, vel: 0 };
    this._rejectSpr = { pos: 0, vel: 0 };  // sacudida horizontal APPROACHING

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
    this._wakeBloom  = 0;
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

    // ── MOVING — bob de caminata ──────────────────────────────────────────────
    this._moveBobT = 0;   // siempre avanza, se modula por blend en render

    // ── SEARCHING ─────────────────────────────────────────────────────────────
    this._searchT        = 0;     // siempre avanza
    this._reminderActive = false;
    this._reminderBlend  = 0;     // 0=blanco, 1=teal (transición suave)

    // ── APPROACHING ───────────────────────────────────────────────────────────
    this._approachPhase      = 'seeking';  // 'seeking' | 'recognized' | 'rejected'
    this._approachConfidence = 0;
    this._recognizedT        = 0;          // 0→1: animación de reconocimiento
    this._approachSquint     = 1;          // 1→0.55: entrecierre de ojos
    this._approachNodY       = 0;          // px: bajada de cabeza al reconocer

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
        this._eyeScaleL.vel += 5.5;   // kick → ojos saltones con rebote
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
        this._approachPhase      = 'seeking';
        this._approachConfidence = params.confidence ?? 0;
        this._recognizedT        = 0;
        this._approachSquint     = 1;
        this._approachNodY       = 0;
        this._rejectSpr.pos      = 0;
        this._rejectSpr.vel      = 0;
        break;
    }
  }

  setAudioLevel(l) { this.audioLevel = Math.max(0, Math.min(1, l)); }
  setMicLevel(l)   { this.micLevel   = Math.max(0, Math.min(1, l)); }

  /** Actualizar confianza del reconocimiento facial en APPROACHING (0–1). */
  setConfidence(val) {
    this._approachConfidence = Math.max(0, Math.min(1, val));
    if (this._approachPhase === 'seeking' && this._approachConfidence >= 0.75) {
      this._approachPhase = 'recognized';
      this._recognizedT   = 0;
    }
  }

  /** Disparar animación de rechazo — robot no reconoció el rostro. */
  rejectApproach() {
    if (this.state !== 'APPROACHING') return;
    this._approachPhase = 'rejected';
    this._rejectSpr.pos = 0;
    this._rejectSpr.vel = this._s(340);  // kick → spring underdamped → 3-4 oscilaciones
  }

  /** Activar/desactivar modo REMINDER en SEARCHING (ojos → teal). */
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

    // Timers globales (siempre avanzan)
    this._breathT     += (dt / 4500) * Math.PI * 2;
    this._driftPhaseX += dt * 0.0002;
    this._driftPhaseY += dt * 0.00025;
    this._moveBobT    += dtS;
    this._searchT     += dtS;

    // Springs — siempre activos
    this._updateSpring(this._eyeScaleL, 1, SPRING.EYE_SCALE, dtS);
    this._updateSpring(this._eyeScaleR, 1, SPRING.EYE_SCALE, dtS);
    this._updateSpring(this._jiggleL,   0, SPRING.JIGGLE,    dtS);
    this._updateSpring(this._jiggleR,   0, SPRING.JIGGLE,    dtS);
    this._updateSpring(this._rejectSpr, 0, SPRING.REJECT,    dtS);

    this._updateBlink(dt);
    if (this._wakeActive) this._updateWake(ts, dt);

    // LISTENING
    this._ringPulse += dt * 0.0025;
    if (this._ringEntryActive) {
      this._ringEntry = Math.min(1, this._ringEntry + dt / 500);
      if (this._ringEntry >= 1) this._ringEntryActive = false;
    }

    // THINKING
    if (this.state === 'THINKING' || this.prevState === 'THINKING') {
      this._tiltPhase += dt * 0.00078;
      this._dotPhase  += dt * 0.00175;
    }

    // SPEAKING — onda + jiggle en picos de audio
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

    // SEARCHING — blend de color hacia teal si REMINDER activo
    const remTarget      = this._reminderActive ? 1 : 0;
    this._reminderBlend += (remTarget - this._reminderBlend) * Math.min(1, dt * 0.003);

    // APPROACHING — animación de reconocimiento (fase 'recognized')
    if (this._approachPhase === 'recognized') {
      this._recognizedT    = Math.min(1, this._recognizedT + dt / 600);
      this._approachSquint = 1 - this._recognizedT * 0.45;
      this._approachNodY   = this._s(12) * this._easeOutCubic(this._recognizedT);
    }

    // Audio simulado
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
    const elapsed = ts - this._wakeTs;
    this._wakeLine = Math.min(1, elapsed / 220);
    if (elapsed >= 180) {
      const t = Math.min(1, (elapsed - 180) / 300);
      this._wakeBloom = t < 0.35 ? t / 0.35 : 1 - (t - 0.35) / 0.65;
    }
    if (elapsed >= 200 && this._wakePulses.length === 0) {
      this._wakePulses = [
        { offset:   0, maxR: G.wakePulseR * 0.8 },
        { offset: 180, maxR: G.wakePulseR * 0.5 },
      ];
    }
    const NOD_PX = 18;
    if (elapsed <= 600) {
      const t = elapsed / 600;
      this._wakeNodY = -this._s(NOD_PX) * (1 - Math.pow(1 - t, 4));
    } else if (elapsed <= 1200) {
      const t = (elapsed - 600) / 600;
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
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const t = this._easeInOutCubic(this.transT);

    // ── Color base — con teal de REMINDER en SEARCHING ────────────────────────
    let baseCol = this._lerpRGB(COL[this.prevState] ?? COL.IDLE, COL[this.state] ?? COL.IDLE, t);
    if (this.state === 'SEARCHING' || this.prevState === 'SEARCHING') {
      const tealBlend = this._reminderBlend *
        ((this.state === 'SEARCHING') ? t : (1 - t));
      baseCol = this._lerpRGB(baseCol, COL_TEAL, tealBlend);
    }
    const colStr  = `rgb(${baseCol.r},${baseCol.g},${baseCol.b})`;
    const glowStr = `rgba(${baseCol.r},${baseCol.g},${baseCol.b},`;

    const breathRy = 1 + Math.sin(this._breathT) * 0.015;

    // Cabeceo THINKING
    const tiltBlend = (this.state === 'THINKING') ? t : (this.prevState === 'THINKING' ? 1 - t : 0);
    const tiltAngle = Math.sin(this._tiltPhase) * 0.11 * tiltBlend;

    // Bob de caminata MOVING (dos frecuencias superpuestas)
    const movingBlend = (this.state === 'MOVING') ? t : (this.prevState === 'MOVING' ? 1 - t : 0);
    const slowBob  = Math.sin(this._moveBobT * 2 * Math.PI * 1.2);
    const fastBob  = Math.sin(this._moveBobT * 2 * Math.PI * 2.4);
    const bobY     = this._s(slowBob * 6 + fastBob * 2.5) * movingBlend;
    const bobRot   = slowBob * 0.022 * movingBlend;

    // Micro-drift IDLE
    const driftBlend = (this.state === 'IDLE') ? t : (this.prevState === 'IDLE' ? 1 - t : 0);
    const driftX = Math.sin(this._driftPhaseX) * this._s(1.5) * driftBlend;
    const driftY = Math.cos(this._driftPhaseY) * this._s(1.5) * driftBlend;

    // Barrido lateral SEARCHING
    const searchBlend = (this.state === 'SEARCHING') ? t : (this.prevState === 'SEARCHING' ? 1 - t : 0);
    const sweepX = Math.sin(this._searchT * 2 * Math.PI / 2.5) * this._s(42) * searchBlend;

    // Sacudida + bajada de cabeza APPROACHING
    const approachBlend = (this.state === 'APPROACHING') ? t : (this.prevState === 'APPROACHING' ? 1 - t : 0);
    const rejectX    = this._rejectSpr.pos * approachBlend;
    const approachY  = this._approachNodY  * approachBlend;
    const squintMult = (this.state === 'APPROACHING')
      ? 1 - (1 - this._approachSquint) * t
      : 1;

    ctx.save();
    ctx.translate(this.W2 + rejectX, this.H2 + this._wakeNodY + bobY + approachY);
    ctx.rotate(tiltAngle + bobRot);

    // Posición de los ojos: centro ± sep + drift + sweep
    const lx = -this._s(G.eyeSep) + driftX + sweepX;
    const rx =  this._s(G.eyeSep) + driftX + sweepX;
    const r  =  this._s(G.eyeR);
    const rL = r * Math.max(0.1, this._eyeScaleL.pos);
    const rR = r * Math.max(0.1, this._eyeScaleR.pos);

    // Anillos LISTENING
    const ringBlend = (this.state === 'LISTENING') ? t : (this.prevState === 'LISTENING' ? 1 - t : 0);
    if (ringBlend > 0.01) {
      this._drawRing(lx, driftY, rL, ringBlend, baseCol, glowStr);
      this._drawRing(rx, driftY, rR, ringBlend, baseCol, glowStr);
    }

    // Línea / onda SPEAKING
    const waveBlend = (this.state === 'SPEAKING') ? t : (this.prevState === 'SPEAKING' ? 1 - t : 0);
    this._drawLineOrWave(lx, rx, driftY, rL, rR, colStr, glowStr, waveBlend);

    // Pulso WAKE sobre la línea
    if (this._wakeActive && this._wakeLine < 1)
      this._drawLinePulse(lx, rx, driftY, rL, rR, this._wakeLine);

    // Shimmer SEARCHING sobre la línea
    if (searchBlend > 0.01)
      this._drawLineShimmer(lx, rx, driftY, rL, rR, searchBlend);

    // Círculos (bloom del WAKE se tiñe de azul al entrar en LISTENING)
    const bloomGlow = (this.state === 'LISTENING' && this._wakeBloom > 0)
      ? `rgba(${Math.round(255-(255-75)*t)},${Math.round(255-(255-152)*t)},${Math.round(255-(255-220)*t)},`
      : glowStr;
    this._drawCircle(lx, driftY, rL, breathRy * squintMult, this._jiggleL.pos, colStr, bloomGlow, this._wakeBloom);
    this._drawCircle(rx, driftY, rR, breathRy * squintMult, this._jiggleR.pos, colStr, bloomGlow, this._wakeBloom);

    // Punto viajero THINKING
    const dotBlend = (this.state === 'THINKING') ? t : (this.prevState === 'THINKING' ? 1 - t : 0);
    if (dotBlend > 0.01)
      this._drawTravelingDot(lx, rx, driftY, rL, rR, dotBlend, baseCol);

    // Símbolo APPROACHING (? → ✓)
    if (approachBlend > 0.01)
      this._drawApproachSymbol(driftY, approachBlend);

    // Texto "Escuchando..."
    const textBlend = (this.state === 'LISTENING') ? t : (this.prevState === 'LISTENING' ? 1 - t : 0);
    if (textBlend > 0.01)
      this._drawListeningText(textBlend, baseCol);

    ctx.restore();

    // Anillos expansivos WAKE (coordenadas absolutas)
    if (this._wakePulses.length > 0) this._drawWakePulses(ts);

    if (this._debug) this._drawDebug();
  }


  // ═══════════════════════════════════════════════════════════════════════════
  //  MÉTODOS DE DIBUJO
  // ═══════════════════════════════════════════════════════════════════════════

  _drawCircle(x, y, r, breathRy, jiggle, colStr, glowStr, bloom = 0) {
    if (r < 1) return;
    const ctx   = this.ctx;
    const ryEff = r * Math.max(0.02, this._blinkRy * breathRy) + jiggle;
    if (ryEff < 0.5) return;

    ctx.save();
    ctx.shadowBlur  = this._s(24 + bloom * 55);
    ctx.shadowColor = bloom > 0.01
      ? `rgba(255,255,255,${0.4 + bloom * 0.5})`
      : glowStr + '0.4)';
    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.fillStyle = colStr;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.clip();
    const hx   = x - r * 0.26;
    const hy   = y - ryEff * 0.28;
    const hGrd = ctx.createRadialGradient(hx, hy, 0, hx, hy, r * 0.55);
    hGrd.addColorStop(0,   `rgba(255,255,255,${0.5 + bloom * 0.4})`);
    hGrd.addColorStop(0.5, `rgba(255,255,255,${0.12 + bloom * 0.2})`);
    hGrd.addColorStop(1,   'rgba(255,255,255,0)');
    ctx.fillStyle = hGrd;
    ctx.fillRect(x - r, y - ryEff, r * 2, ryEff * 2);
    ctx.restore();
  }

  _drawLineOrWave(lx, rx, y, rL, rR, colStr, glowStr, waveBlend) {
    const ctx = this.ctx;
    const x1 = lx + rL, x2 = rx - rR;
    if (x2 <= x1 + 2) return;
    const span = x2 - x1;
    const amp  = this.smoothAudio * this._s(G.waveAmp) * waveBlend;
    ctx.save();
    ctx.strokeStyle = colStr;
    ctx.lineWidth   = this._s(G.lineW);
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.shadowBlur  = this._s(12);
    ctx.shadowColor = glowStr + '0.45)';
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

  _drawLinePulse(lx, rx, y, rL, rR, progress) {
    const ctx  = this.ctx;
    const x1 = lx + rL, x2 = rx - rR;
    const mid = (x1 + x2) / 2, half = (x2 - x1) / 2;
    const reachL = mid - half * progress;
    const reachR = mid + half * progress;
    const makeGrad = (x0, x1) => {
      const g = ctx.createLinearGradient(x0, y, x1, y);
      g.addColorStop(0,   'rgba(255,255,255,0)');
      g.addColorStop(0.6, 'rgba(255,255,255,0.3)');
      g.addColorStop(1,   'rgba(255,255,255,0.9)');
      return g;
    };
    ctx.save();
    ctx.lineWidth = this._s(G.lineW * 1.8);
    ctx.lineCap   = 'round';
    ctx.shadowBlur  = this._s(16);
    ctx.shadowColor = 'rgba(255,255,255,0.8)';
    ctx.beginPath(); ctx.moveTo(mid, y); ctx.lineTo(reachL, y);
    ctx.strokeStyle = makeGrad(mid, reachL); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(mid, y); ctx.lineTo(reachR, y);
    ctx.strokeStyle = makeGrad(mid, reachR); ctx.stroke();
    if (progress > 0.88) {
      const a = (progress - 0.88) / 0.12;
      ctx.fillStyle = `rgba(255,255,255,${a * 0.9})`;
      ctx.shadowColor = 'rgba(255,255,255,0.9)';
      ctx.shadowBlur  = this._s(20);
      [reachL, reachR].forEach(px => {
        ctx.beginPath(); ctx.arc(px, y, this._s(5), 0, Math.PI * 2); ctx.fill();
      });
    }
    ctx.restore();
  }

  /**
   * Shimmer: punto brillante que recorre la línea de conexión. (SEARCHING)
   * Período: 1.8 s — efecto de ping de sonar.
   */
  _drawLineShimmer(lx, rx, y, rL, rR, blend) {
    const ctx = this.ctx;
    const x1  = lx + rL, x2 = rx - rR;
    if (x2 <= x1) return;
    const shimX = x1 + ((this._searchT / 1.8) % 1) * (x2 - x1);
    ctx.save();
    const grad = ctx.createRadialGradient(shimX, y, 0, shimX, y, this._s(28));
    grad.addColorStop(0,    `rgba(255,255,255,${blend * 0.75})`);
    grad.addColorStop(0.35, `rgba(255,255,255,${blend * 0.18})`);
    grad.addColorStop(1,    'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.ellipse(shimX, y, this._s(28), this._s(7), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  _drawRing(x, y, circR, blend, col, glowStr) {
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
    ctx.strokeStyle = `rgba(${col.r},${col.g},${col.b},${pulse * (0.28 + this.smoothMic * 0.52)})`;
    ctx.lineWidth   = this._s(G.ringW);
    ctx.shadowBlur  = this._s(12);
    ctx.shadowColor = glowStr + `${pulse * 0.45})`;
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
    ctx.shadowBlur  = this._s(14);
    ctx.shadowColor = `rgba(${col.r},${col.g},${col.b},${blend * 0.55})`;
    ctx.fill();
    ctx.restore();
  }

  /**
   * Símbolo flotante encima de la cara. (APPROACHING)
   * ? se desvanece con scale-down mientras ✓ aparece con scale-up.
   * _recognizedT: 0 = solo ?, 1 = solo ✓.
   */
  _drawApproachSymbol(driftY, blend) {
    const cy = driftY - this._s(G.symbolDy);
    const sz = this._s(G.symbolSz);
    const rt = this._recognizedT;

    if (rt < 0.98) {
      const qAlpha = (1 - this._easeInOutCubic(rt)) * blend;
      this._drawQuestionMark(0, cy, sz * (1 - rt * 0.25), qAlpha);
    }
    if (rt > 0.02) {
      const cAlpha = this._easeOutCubic(rt) * blend;
      this._drawCheckMark(0, cy, sz * (0.5 + rt * 0.5), cAlpha);
    }
  }

  /** Signo de interrogación como Canvas path. Centro (cx, cy), tamaño sz. */
  _drawQuestionMark(cx, cy, sz, alpha) {
    if (alpha < 0.01 || sz < 1) return;
    const ctx = this.ctx;
    ctx.save();
    ctx.strokeStyle = `rgba(255,255,255,${alpha})`;
    ctx.fillStyle   = `rgba(255,255,255,${alpha})`;
    ctx.lineWidth   = sz * 0.18;
    ctx.lineCap     = 'round';
    ctx.shadowBlur  = sz * 0.4;
    ctx.shadowColor = `rgba(255,255,255,${alpha * 0.4})`;

    // Arco superior + cola curvada hacia el centro
    ctx.beginPath();
    ctx.arc(cx, cy - sz * 0.38, sz * 0.28, Math.PI * 0.5, Math.PI * 2.15, false);
    ctx.bezierCurveTo(
      cx + sz * 0.30, cy - sz * 0.06,
      cx + sz * 0.08, cy + sz * 0.06,
      cx,             cy + sz * 0.12
    );
    ctx.stroke();

    // Punto inferior
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.arc(cx, cy + sz * 0.42, sz * 0.10, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  /** Checkmark en verde. Centro (cx, cy), tamaño sz. */
  _drawCheckMark(cx, cy, sz, alpha) {
    if (alpha < 0.01 || sz < 1) return;
    const ctx = this.ctx;
    ctx.save();
    ctx.strokeStyle = `rgba(${COL_GREEN.r},${COL_GREEN.g},${COL_GREEN.b},${alpha})`;
    ctx.lineWidth   = sz * 0.22;
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.shadowBlur  = sz * 0.55;
    ctx.shadowColor = `rgba(${COL_GREEN.r},${COL_GREEN.g},${COL_GREEN.b},${alpha * 0.6})`;
    ctx.beginPath();
    ctx.moveTo(cx - sz * 0.42, cy + sz * 0.02);
    ctx.lineTo(cx - sz * 0.06, cy + sz * 0.40);
    ctx.lineTo(cx + sz * 0.48, cy - sz * 0.38);
    ctx.stroke();
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
      const opacity = Math.pow(1 - t, 1.8) * 0.28;
      [lx, rx].forEach(ex => {
        ctx.save();
        ctx.beginPath();
        ctx.arc(ex, this.H2, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255,255,255,${opacity})`;
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
    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    ctx.textAlign = 'right';
    ctx.fillText(`${this.prevState} → ${this.state}  t=${this.transT.toFixed(2)}`, W-16, H-68);
    ctx.fillText(`audio ${this.smoothAudio.toFixed(2)}  mic ${this.smoothMic.toFixed(2)}  sim ${this.simAudio?'ON':'off'}`, W-16, H-51);
    ctx.fillText(`blink:${this._blinkPhase}  ry=${this._blinkRy.toFixed(2)}  scaleL=${this._eyeScaleL.pos.toFixed(3)}`, W-16, H-34);
    ctx.fillText(`approach:${this._approachPhase}  conf=${this._approachConfidence.toFixed(2)}  recT=${this._recognizedT.toFixed(2)}  rejectX=${this._rejectSpr.pos.toFixed(1)}`, W-16, H-17);
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

  _s(v)       { return v * this.S; }
  _rand(a, b) { return a + Math.random() * (b - a); }
  _easeInOutCubic(t) { return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; }
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

      // SEARCHING: toggle reminder
      if ((e.key==='r'||e.key==='R') && this.state === 'SEARCHING') {
        this.setReminderActive(!this._reminderActive);
        console.log('[BaymaxFace] reminder:', this._reminderActive ? 'ON' : 'off');
      }

      // APPROACHING: ciclar fases para testear
      if ((e.key==='c'||e.key==='C') && this.state === 'APPROACHING') {
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
