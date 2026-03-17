'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
//  baymax_face.js  —  v2.0
//  Robot Asistente Médico Meadlese
//
//  Anatomía fiel al personaje: dos círculos sólidos + línea horizontal.
//  Una sola idea visual por estado — elegante, no sobrecargado.
//
//  Estados implementados:
//    IDLE      — reposo: respira, parpadea
//    WAKE      — despertar: círculos se abren con spring, anillo de pulso
//    LISTENING — escucha: azul + anillo reactivo al micrófono
//    THINKING  — procesa: ámbar + cabeceo lento + punto que recorre la línea
//    SPEAKING  — habla:  la línea SE CONVIERTE en onda de voz
//
//  Keyboard (oculto para desarrollo):
//    1-5  → cambiar estado   A → simular audio   D → debug overlay
// ═══════════════════════════════════════════════════════════════════════════════

const BASE_W = 1366;
const BASE_H = 768;

// ─── Geometría — valores en px a resolución BASE_W ───────────────────────────
const G = {
  eyeR:       58,    // radio de cada círculo
  eyeSep:    178,    // distancia del centro de la cara al centro de cada círculo
  lineW:       4.5,  // grosor de la línea / onda
  // extremo de la línea = eyeSep - eyeR desde el centro
  get lineX() { return this.eyeSep - this.eyeR; },  // 120 px
  waveAmp:    58,    // amplitud máxima de la onda en SPEAKING
  ringGap:    14,    // distancia entre borde del círculo y el anillo (LISTENING)
  ringW:       2.5,  // grosor del anillo
  dotR:        7,    // radio del punto viajero (THINKING)
  wakePulseR: 260,   // radio máximo del pulso de WAKE
  textDy:    195,    // desplazamiento vertical del texto "Escuchando..."
};

// ─── Física para animaciones con spring (resorte) ──────────────────────────
const PHYSICS = {
  // Configuración para una animación rápida y con rebote (ej. despertar)
  WAKE: { mass: 1, stiffness: 120, damping: 18 },
  // Configuración para una animación más suave (ej. parpadeo)
  BLINK: { mass: 1, stiffness: 180, damping: 20 },
  // Configuración para el movimiento de la pupila o reflejos
  EYE_FOLLOW: { mass: 0.8, stiffness: 120, damping: 15 },
  // Configuración para el "jiggle" ocular en SPEAKING
  JIGGLE: { mass: 0.6, stiffness: 100, damping: 12 },
};

// ─── Colores por estado — como arrays RGB para interpolación suave ────────────
const COL = {
  IDLE:      { r: 255, g: 255, b: 255 },
  WAKE:      { r: 255, g: 255, b: 255 },
  LISTENING: { r:  75, g: 152, b: 220 },
  THINKING:  { r: 202, g: 130, b:  30 },
  SPEAKING:  { r: 255, g: 255, b: 255 },
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
    this.TRANS_MS    = 450; // Aumentamos la duración para dar tiempo a las físicas
    this.stateParams = {};

    // ── Animaciones con Física (Springs) ─────────────────────────────────────
    this.eyeScale = {
      left:  { pos: 1, vel: 0 },
      right: { pos: 1, vel: 0 }
    };
    this.pupilPos = {
      left:  { x: 0, y: 0, vx: 0, vy: 0 },
      right: { x: 0, y: 0, vx: 0, vy: 0 }
    };
    this.eyeJiggleY = {
      left:  { pos: 0, vel: 0 },
      right: { pos: 0, vel: 0 }
    };

    // ── Escala ────────────────────────────────────────────────────────────────
    this.S  = 1;
    this.W2 = 0;
    this.H2 = 0;
    this._resize();
    window.addEventListener('resize', () => this._resize());

    // ── Audio ─────────────────────────────────────────────────────────────────
    this.audioLevel  = 0;
    this.micLevel    = 0;
    this.smoothAudio = 0;
    this.smoothMic   = 0;
    this.simAudio    = false;
    this._simPhase   = 0;

    // ── Parpadeo ──────────────────────────────────────────────────────────────
    this._blinkRy    = 1;
    this._blinkPhase = 'idle';
    this._blinkTimer = 0;
    this._blinkNext  = this._rand(5800, 8500);
    this._isDoubleBlink = false;

    // ── Respiración y micro-movimientos IDLE ──────────────────────────────────
    this._breathT    = 0;
    this._idleDriftX = 0;
    this._idleDriftY = 0;
    this._idleDriftPhaseX = Math.random() * 100;
    this._idleDriftPhaseY = Math.random() * 100;

    // ── WAKE — activación orgánica ────────────────────────────────────────────
    // El pulso viaja por la línea desde el centro hacia los ojos,
    // luego cada ojo hace bloom, luego salen los anillos expansivos.
    this._wakeActive  = false;
    this._wakeTs      = 0;
    this._wakePulses  = [];   // anillos expansivos desde cada ojo
    // Los círculos SIEMPRE existen — no se escalan desde cero
    this._wakeBloom   = 0;    // 0→1: intensidad extra de glow en los ojos
    this._wakeLine    = 0;    // 0→1: progreso del pulso sobre la línea (centro→ojos)
    this._wakeNodY    = 0;    // px: desplazamiento vertical — sube con el "¿Sí?" y baja al LISTENING

    // ── LISTENING ─────────────────────────────────────────────────────────────
    this._ringPulse  = 0;
    this._ringEntry  = 0;   // 0→1: el ring "aterriza" desde el bloom del WAKE
    this._ringEntryActive = false;

    // ── THINKING ─────────────────────────────────────────────────────────────
    this._tiltPhase  = 0;
    this._dotPhase   = 0;
    this._thinkingPupilPhase = 0;

    // ── SPEAKING ──────────────────────────────────────────────────────────────
    this._wavePhase  = 0;
    this._lastAudioLevel = 0;

    // ── Debug ─────────────────────────────────────────────────────────────────
    this._debug      = false;

    this._lastTs     = 0;
    this._rafId      = null;

    this._setupKeys();
  }


  // ─── API pública ─────────────────────────────────────────────────────────────

  setState(newState, params = {}) {
    if (newState === this.state) return;
    this.prevState   = this.state;
    this.state       = newState;
    this.transT      = 0;
    this.stateParams = params;

    // Aplicar un "empujón" al resorte de escala de los ojos al despertar
    if (newState === 'WAKE') {
      this.eyeScale.left.vel += 8;
      this.eyeScale.right.vel += 8;
    }

    if (newState === 'WAKE') {
      this._wakeActive = true;
      this._wakeTs     = this._lastTs;
      this._wakeBloom  = 0;
      this._wakeLine   = 0;
      this._wakeNodY   = 0;
      this._wakePulses = [];   // se añaden más adelante cuando el pulso llega a los ojos

      // Si los ojos estaban cerrados (parpadeo), abrirlos suavemente
      if (this._blinkRy < 0.5) {
        this._blinkPhase = 'opening';
        this._blinkTimer = 0;
      }
    }

    if (newState === 'IDLE') {
      this._blinkNext  = this._rand(600, 2200);
      this._blinkTimer = 0;
    }

    // Al entrar a LISTENING desde WAKE, el bloom se convierte en el ring
    if (newState === 'LISTENING') {
      this._ringEntry       = 0;
      this._ringEntryActive = true;
      // Si venimos de WAKE y el bloom aún tiene energía, acortamos la transición
      // de color para que el azul aparezca junto con el ring, no después
      if (this.prevState === 'WAKE' && this._wakeBloom > 0.05) {
        this.TRANS_MS = 480;   // más lento — el color "se tiñe" gradualmente
      } else {
        this.TRANS_MS = 450;   // transición normal
      }
    } else {
      this.TRANS_MS = 450;
    }

    if (newState === 'THINKING') {
      this._tiltPhase = 0;
      this._dotPhase  = 0;
      this._thinkingPupilPhase = 0;
    }
  }

  setAudioLevel(l) { this.audioLevel = Math.max(0, Math.min(1, l)); }
  setMicLevel(l)   { this.micLevel   = Math.max(0, Math.min(1, l)); }

  start() {
    if (this._rafId) return;
    this._rafId = requestAnimationFrame(ts => this._loop(ts));
  }

  stop() {
    if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = null; }
  }


  // ─── Loop ────────────────────────────────────────────────────────────────────

  _loop(ts) {
    const dt = Math.min(ts - (this._lastTs || ts), 80);
    this._lastTs = ts;
    this._update(ts, dt);
    this._render(ts);
    this._rafId = requestAnimationFrame(nts => this._loop(nts));
  }


  // ─── Update ──────────────────────────────────────────────────────────────────

  _update(ts, dt) {
    if (this.transT < 1)
      this.transT = Math.min(1, this.transT + dt / this.TRANS_MS);

    // Normalizar dt a segundos para los cálculos de física
    const dtSec = dt / 1000;

    // Actualizar la física de los resortes
    const isThinking = this.state === 'THINKING';
    this._updateSpring(this.eyeScale.left,  isThinking ? 0.95 : 1, PHYSICS.WAKE, dtSec);
    this._updateSpring(this.eyeScale.right, isThinking ? 0.95 : 1, PHYSICS.WAKE, dtSec);
    this._updateSpring(this.eyeJiggleY.left, 0, PHYSICS.JIGGLE, dtSec);
    this._updateSpring(this.eyeJiggleY.right, 0, PHYSICS.JIGGLE, dtSec);

    // Micro-movimientos y respiración en IDLE
    this._breathT += (dt / 4500) * Math.PI * 2;
    this._idleDriftPhaseX += dt * 0.0002;
    this._idleDriftPhaseY += dt * 0.00025;
    this._idleDriftX = Math.sin(this._idleDriftPhaseX) * this._s(1.5);
    this._idleDriftY = Math.cos(this._idleDriftPhaseY) * this._s(1.5);

    this._updateBlink(dt);
    if (this._wakeActive) this._updateWakeAnim(ts, dt);

    this._ringPulse += dt * 0.0025;

    // Ring entry: el bloom del WAKE aterriza como ring de LISTENING (~500 ms)
    if (this._ringEntryActive) {
      this._ringEntry = Math.min(1, this._ringEntry + dt / 500);
      if (this._ringEntry >= 1) this._ringEntryActive = false;
    }

    if (this.state === 'THINKING' || this.prevState === 'THINKING') {
      this._tiltPhase += dt * 0.00078;
      this._dotPhase  += dt * 0.00175;
      this._thinkingPupilPhase += dt * 0.001;
    }

    this._wavePhase += dt * 0.0032;

    // Detección de picos de audio para el "jiggle" de los ojos
    const audioDelta = this.audioLevel - this._lastAudioLevel;
    if (this.state === 'SPEAKING' && audioDelta > 0.35) {
      this.eyeJiggleY.left.vel  += this._s(audioDelta * 1.2);
      this.eyeJiggleY.right.vel += this._s(audioDelta * 1.2);
    }
    this._lastAudioLevel = this.audioLevel;

    // Audio simulado
    if (this.simAudio && this.state === 'SPEAKING') {
      this._simPhase += dt * 0.001;
      const env  = Math.max(0, Math.sin(this._simPhase * 2.3) * 0.5 + 0.55);
      const fast = Math.abs(Math.sin(this._simPhase * 15) * Math.sin(this._simPhase * 7 + 1));
      const pause= Math.max(0, Math.sin(this._simPhase * 0.85));
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
        if (this._blinkTimer >= this._blinkNext) {
          this._blinkPhase = 'closing';
          this._blinkTimer = 0;
        }
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
          this._blinkRy    = 1;
          this._blinkPhase = 'idle';
          this._blinkTimer = 0;

          // Posibilidad de un parpadeo doble
          if (!this._isDoubleBlink && Math.random() < 0.15) {
            this._isDoubleBlink = true;
            this._blinkNext = this._rand(100, 180); // Siguiente parpadeo muy rápido
          } else {
            this._isDoubleBlink = false;
            this._blinkNext = this._rand(3000, 7500); // Siguiente parpadeo normal
          }
        }
        break;
      }
    }
  }

  _updateWakeAnim(ts, dt) {
    const elapsed = ts - this._wakeTs;

    // ── Fase 1 (0→220 ms): pulso viaja por la línea centro → ojos ─────────────
    this._wakeLine = Math.min(1, elapsed / 220);

    // ── Nod vertical sincronizado con el "¿Sí?" (~1200 ms total) ──────────────
    const NOD_PEAK_MS  = 600;
    const NOD_TOTAL_MS = 1200;
    const NOD_PX       = 18;

    if (elapsed <= NOD_PEAK_MS) {
      const t = elapsed / NOD_PEAK_MS;
      this._wakeNodY = -this._s(NOD_PX) * (1 - Math.pow(1 - t, 4)); // easeOutQuart
    } else if (elapsed <= NOD_TOTAL_MS) {
      const t = (elapsed - NOD_PEAK_MS) / (NOD_TOTAL_MS - NOD_PEAK_MS);
      this._wakeNodY = -this._s(NOD_PX) * (1 - this._easeInOutCubic(t));
    } else {
      this._wakeNodY = 0;
    }

    // ── Fase 2 (180→480 ms): bloom de glow en los ojos ───────────────────────
    if (elapsed >= 180) {
      const bloomT = Math.min(1, (elapsed - 180) / 300);
      // Sube rápido a 1, luego decae suavemente a 0
      this._wakeBloom = bloomT < 0.35
        ? bloomT / 0.35                          // sube en los primeros 35%
        : 1 - ((bloomT - 0.35) / 0.65);         // decae el resto
    }

    // ── Fase 3 (200 ms): disparar anillos desde cada ojo (una sola vez) ───────
    if (elapsed >= 200 && this._wakePulses.length === 0) {
      this._wakePulses = [
        { fromEye: true, offset:   0, maxR: G.wakePulseR * 0.8 },
        { fromEye: true, offset: 180, maxR: G.wakePulseR * 0.5 },
      ];
    }

    // Animación completa ≈ 1200 ms (sincronizado con duración del "¿Sí?")
    if (elapsed >= 1200) {
      this._wakeActive = false;
      this._wakeBloom  = 0;
      this._wakeLine   = 1;
      this._wakeNodY   = 0;
    }
  }


  // ─── Render ──────────────────────────────────────────────────────────────────

  _render(ts) {
    const ctx = this.ctx;
    const W   = this.canvas.width;
    const H   = this.canvas.height;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);

    // Color interpolado
    const t   = this._easeInOutCubic(this.transT);
    const col = this._lerpRGB(COL[this.prevState] || COL.IDLE, COL[this.state] || COL.IDLE, t);
    const colStr  = `rgb(${col.r},${col.g},${col.b})`;
    const glowStr = `rgba(${col.r},${col.g},${col.b},`;

    // Respiración — afecta la altura de los ojos
    const breathY = 1 + Math.sin(this._breathT) * 0.015;

    // THINKING: cabeceo — rotación de toda la cara
    const tiltBlend  = (this.state === 'THINKING') ? t : (this.prevState === 'THINKING' ? 1 - t : 0);
    const tiltAngle  = Math.sin(this._tiltPhase) * 0.11 * tiltBlend;

    // Nod vertical del WAKE
    const nodY = this._wakeNodY;

    ctx.save();
    ctx.translate(this.W2, this.H2 + nodY);
    ctx.rotate(tiltAngle);
    // La respiración ya no es un scale global
    // ctx.scale(breath, breath);

    // Posición de los ojos — con micro-movimientos en IDLE
    const idleDriftBlend = (this.state === 'IDLE') ? this._easeInOutCubic(this.transT) : (this.prevState === 'IDLE' ? 1 - this._easeInOutCubic(this.transT) : 0);
    const driftX = this._idleDriftX * idleDriftBlend;
    const driftY = this._idleDriftY * idleDriftBlend;

    const lx = -this._s(G.eyeSep) + driftX;
    const rx =  this._s(G.eyeSep) + driftX;
    const y_offset = driftY; // Usaremos esto para los ojos y el reflejo

    const r  =  this._s(G.eyeR);

    // Aplicar la escala del resorte a cada ojo
    const rLeft = r * this.eyeScale.left.pos;
    const rRight = r * this.eyeScale.right.pos;

    // Anillo LISTENING (detrás de los círculos)
    const ringBlend = (this.state === 'LISTENING') ? t : (this.prevState === 'LISTENING' ? 1 - t : 0);
    if (ringBlend > 0.01) {
      this._drawRing(lx, y_offset, rLeft, ringBlend, col, glowStr);
      this._drawRing(rx, y_offset, rRight, ringBlend, col, glowStr);
    }

    // Línea / onda — con pulso de WAKE superpuesto
    const waveBlend = (this.state === 'SPEAKING') ? t : (this.prevState === 'SPEAKING' ? 1 - t : 0);
    this._drawLineOrWave(lx, rx, y_offset, r, colStr, glowStr, waveBlend);

    // Pulso viajando sobre la línea (WAKE)
    if (this._wakeActive && this._wakeLine < 1) {
      this._drawLinePulse(lx, rx, y_offset, r, this._wakeLine);
    }

    // Círculos — con bloom extra en WAKE, teñido hacia azul al entrar en LISTENING
    let bloom = this._wakeBloom;
    // Si ya entramos en LISTENING, el bloom residual se tiñe hacia el azul del estado
    const bloomCol = (this.state === 'LISTENING' && bloom > 0)
      ? `rgba(${Math.round(255 - (255-75)*this.transT)},${Math.round(255 - (255-152)*this.transT)},${Math.round(255 - (255-220)*this.transT)},`
      : glowStr;
    this._drawCircle(lx, y_offset, rLeft, breathY, colStr, bloomCol, bloom);
    this._drawCircle(rx, y_offset, rRight, breathY, colStr, bloomCol, bloom);

    // Punto viajero THINKING
    const dotBlend = (this.state === 'THINKING') ? t : (this.prevState === 'THINKING' ? 1 - t : 0);
    if (dotBlend > 0.01) this._drawTravelingDot(lx, rx, y_offset, r, dotBlend, col);

    // Texto LISTENING
    const textBlend = (this.state === 'LISTENING') ? t : (this.prevState === 'LISTENING' ? 1 - t : 0);
    if (textBlend > 0.01) this._drawListeningText(textBlend, col);

    ctx.restore();

    // Pulsos WAKE (en coordenadas absolutas, no rotan)
    if (this._wakePulses.length > 0) this._drawWakePulses(ts);

    if (this._debug) this._drawDebug();
  }


  // ─── Métodos de dibujo ───────────────────────────────────────────────────────

  _drawCircle(x, y, r, breathY, colStr, glowStr, bloomExtra = 0) {
    if (r < 1) return;
    const ctx   = this.ctx;
    // Aplicar "jiggle" y respiración a la escala vertical
    const jiggleY = (this.state === 'SPEAKING') ? this.eyeJiggleY[x < 0 ? 'left' : 'right'].pos : 0;
    const ryEff = r * Math.max(0.02, this._blinkRy * breathY) + jiggleY;
    if (ryEff < 0.5) return;

    ctx.save();
    // Glow normal + bloom extra durante WAKE
    ctx.shadowBlur  = this._s(24 + bloomExtra * 55);
    ctx.shadowColor = bloomExtra > 0.01
      ? `rgba(255,255,255,${0.4 + bloomExtra * 0.5})`
      : glowStr + '0.4)';

    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.fillStyle = colStr;
    ctx.fill();

    // Highlight interno
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.ellipse(x, y, r, ryEff, 0, 0, Math.PI * 2);
    ctx.clip();

    // Corrección del reflejo: se calcula desde la posición final en pantalla
    const finalY = this.H2 + this._wakeNodY + y;
    const hx   = x - r * 0.26;
    const hy   = y - ryEff * 0.28; // Posición relativa dentro del canvas transformado

    // Dilatación de pupila en THINKING
    const thinkingBlend = (this.state === 'THINKING') ? this._easeInOutCubic(this.transT) : (this.prevState === 'THINKING' ? 1 - this._easeInOutCubic(this.transT) : 0);
    const pupilSize = 0.55 + (Math.sin(this._thinkingPupilPhase) * 0.5 + 0.5) * 0.15 * thinkingBlend;

    const hGrd = ctx.createRadialGradient(hx, hy, 0, hx, hy, r * pupilSize);
    hGrd.addColorStop(0,   `rgba(255,255,255,${0.5 + bloomExtra * 0.4})`);
    hGrd.addColorStop(0.5, `rgba(255,255,255,${0.12 + bloomExtra * 0.2})`);
    hGrd.addColorStop(1,   'rgba(255,255,255,0)');
    ctx.fillStyle = hGrd;
    ctx.fillRect(x - r, y - ryEff, r * 2, ryEff * 2);

    ctx.restore();
  }

  /**
   * Pulso que viaja desde el centro de la línea hacia ambos ojos. (WAKE)
   * Se dibuja como dos segmentos de línea brillante que crecen desde el centro.
   */
  _drawLinePulse(lx, rx, y, r, progress) {
    const ctx = this.ctx;
    // Los extremos de la línea
    const x1  = lx + r;   // extremo izquierdo
    const x2  = rx - r;   // extremo derecho
    const mid = (x1 + x2) / 2;
    const half = (x2 - x1) / 2;

    // El pulso cubre desde mid hacia afuera según 'progress'
    const reachL = mid - half * progress;
    const reachR = mid + half * progress;

    // Gradiente: brillante en la punta, desvanece hacia el centro
    ctx.save();

    // Línea izquierda (mid → reachL)
    const gradL = ctx.createLinearGradient(mid, y, reachL, y);
    gradL.addColorStop(0, 'rgba(255,255,255,0)');
    gradL.addColorStop(0.6, 'rgba(255,255,255,0.3)');
    gradL.addColorStop(1, 'rgba(255,255,255,0.9)');

    ctx.beginPath();
    ctx.moveTo(mid, y);
    ctx.lineTo(reachL, y);
    ctx.strokeStyle = gradL;
    ctx.lineWidth   = this._s(G.lineW * 1.8);
    ctx.lineCap     = 'round';
    ctx.shadowBlur  = this._s(16);
    ctx.shadowColor = 'rgba(255,255,255,0.8)';
    ctx.stroke();

    // Línea derecha (mid → reachR)
    const gradR = ctx.createLinearGradient(mid, y, reachR, y);
    gradR.addColorStop(0, 'rgba(255,255,255,0)');
    gradR.addColorStop(0.6, 'rgba(255,255,255,0.3)');
    gradR.addColorStop(1, 'rgba(255,255,255,0.9)');

    ctx.beginPath();
    ctx.moveTo(mid, y);
    ctx.lineTo(reachR, y);
    ctx.strokeStyle = gradR;
    ctx.stroke();

    // Punto de impacto en las puntas — pequeño flash cuando llega al ojo
    if (progress > 0.88) {
      const impactOpacity = (progress - 0.88) / 0.12;
      ctx.beginPath();
      ctx.arc(reachL, y, this._s(5), 0, Math.PI * 2);
      ctx.fillStyle  = `rgba(255,255,255,${impactOpacity * 0.9})`;
      ctx.shadowBlur = this._s(20);
      ctx.shadowColor= 'rgba(255,255,255,0.9)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(reachR, y, this._s(5), 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  _drawLineOrWave(lx, rx, y, r, colStr, glowStr, waveBlend) {
    const ctx = this.ctx;
    const x1  = lx + r;
    const x2  = rx - r;
    if (x2 <= x1 + 2) return;

    const span  = x2 - x1;
    const amp   = this.smoothAudio * this._s(G.waveAmp) * waveBlend;
    const STEPS = 140;

    ctx.save();
    ctx.strokeStyle = colStr;
    ctx.lineWidth   = this._s(G.lineW);
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.shadowBlur  = this._s(12);
    ctx.shadowColor = glowStr + '0.45)';

    ctx.beginPath();
    for (let i = 0; i <= STEPS; i++) {
      const frac = i / STEPS;
      const px   = x1 + frac * span;
      const env  = Math.sin(frac * Math.PI);  // Hanning — cero en extremos
      const wave = Math.sin(frac * Math.PI * 4 + this._wavePhase);
      const py   = y + wave * amp * env;
      if (i === 0) ctx.moveTo(px, py);
      else         ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();
  }

  _drawRing(x, y, circR, blend, col, glowStr) {
    const ctx   = this.ctx;

    // Si el ring está "aterrizando" desde el bloom del WAKE,
    // parte de un radio grande y se asienta al radio normal con easeOutCubic
    let extraRadius = 0;
    let entryOpacityMult = 1;
    if (this._ringEntryActive) {
      const eased   = this._easeOutCubic(this._ringEntry);
      // Radio extra: empieza en el tamaño del bloom (~55px) y llega a 0
      extraRadius      = this._s(55) * (1 - eased);
      // La opacidad sube con el entry para que el ring "aparezca" desde el bloom
      entryOpacityMult = 0.3 + eased * 0.7;
    }

    const extra = this._s(G.ringGap) + this.smoothMic * this._s(26);
    const rr    = circR + extra + extraRadius;
    const pulse = (Math.sin(this._ringPulse) * 0.15 + 0.85) * blend * entryOpacityMult;

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

  _drawTravelingDot(lx, rx, y, r, blend, col) {
    const ctx = this.ctx;
    const x1  = lx + r;
    const x2  = rx - r;
    if (x2 <= x1) return;

    // Movimiento sinusoidal suavizado
    const eased = (Math.sin(this._dotPhase) + 1) / 2;
    const px    = x1 + eased * (x2 - x1);

    ctx.save();
    ctx.beginPath();
    ctx.arc(px, y, this._s(G.dotR), 0, Math.PI * 2);
    ctx.fillStyle   = `rgba(${col.r},${col.g},${col.b},${blend * 0.88})`;
    ctx.shadowBlur  = this._s(14);
    ctx.shadowColor = `rgba(${col.r},${col.g},${col.b},${blend * 0.55})`;
    ctx.fill();
    ctx.restore();
  }

  _drawListeningText(blend, col) {
    const ctx  = this.ctx;
    const size = this._s(13);
    ctx.save();
    ctx.font         = `300 ${size}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
    ctx.fillStyle    = `rgba(${col.r},${col.g},${col.b},${blend * 0.38})`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('E S C U C H A N D O', 0, this._s(G.textDy));
    ctx.restore();
  }

  _drawWakePulses(ts) {
    const ctx    = this.ctx;
    const elap   = ts - this._wakeTs - 200;   // los pulsos arrancan 200 ms después
    if (elap < 0) return;
    const maxDur = 900;
    let   alive  = false;

    // Centros de los ojos en coordenadas absolutas del canvas
    const lx = this.W2 - this._s(G.eyeSep);
    const rx = this.W2 + this._s(G.eyeSep);
    const cy = this.H2;

    this._wakePulses.forEach(p => {
      const t = (elap - p.offset) / maxDur;
      if (t < 0)  { alive = true; return; }
      if (t >= 1) return;
      alive = true;

      const radius  = this._s(G.eyeR + 8 + t * (p.maxR - G.eyeR - 8));
      const opacity = Math.pow(1 - t, 1.8) * 0.28;

      // Emitir desde ojo izquierdo
      ctx.save();
      ctx.beginPath();
      ctx.arc(lx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255,255,255,${opacity})`;
      ctx.lineWidth   = this._s(1.6);
      ctx.stroke();
      ctx.restore();

      // Emitir desde ojo derecho
      ctx.save();
      ctx.beginPath();
      ctx.arc(rx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255,255,255,${opacity})`;
      ctx.lineWidth   = this._s(1.6);
      ctx.stroke();
      ctx.restore();
    });

    if (!alive) this._wakePulses = [];
  }

  _drawDebug() {
    const ctx = this.ctx;
    const W   = this.canvas.width;
    const H   = this.canvas.height;
    ctx.save();
    ctx.font      = `${this._s(11)}px monospace`;
    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    ctx.textAlign = 'right';
    ctx.fillText(`${this.prevState} → ${this.state}  t=${this.transT.toFixed(2)}`, W - 16, H - 52);
    ctx.fillText(`audio ${this.smoothAudio.toFixed(2)}  mic ${this.smoothMic.toFixed(2)}  sim ${this.simAudio?'ON':'off'}`, W - 16, H - 35);
    ctx.fillText(`blink:${this._blinkPhase}  ry=${this._blinkRy.toFixed(2)}  nodY=${this._wakeNodY.toFixed(2)}`, W - 16, H - 18);
    ctx.restore();
  }


  // ─── Utilidades ──────────────────────────────────────────────────────────────

  /**
   * Actualiza una propiedad usando un modelo de resorte-amortiguador.
   * @param {object} spring - El objeto con { pos, vel }.
   * @param {number} targetPos - La posición objetivo a la que el resorte quiere llegar.
   * @param {object} physics - La configuración con { mass, stiffness, damping }.
   * @param {number} dt - Delta time en segundos.
   */
  _updateSpring(spring, targetPos, physics, dt) {
    const { mass, stiffness, damping } = physics;
    const displacement = spring.pos - targetPos;
    const springForce = -stiffness * displacement;
    const dampingForce = -damping * spring.vel;
    const totalForce = springForce + dampingForce;
    const acceleration = totalForce / mass;

    spring.vel += acceleration * dt;
    spring.pos += spring.vel * dt;
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
    const MAP = { '1':'IDLE','2':'WAKE','3':'LISTENING','4':'THINKING','5':'SPEAKING' };
    window.addEventListener('keydown', e => {
      if (MAP[e.key]) this.setState(MAP[e.key]);
      if (e.key==='a'||e.key==='A') {
        this.simAudio = !this.simAudio;
        console.log('[BaymaxFace] sim audio:', this.simAudio ? 'ON' : 'off');
      }
      if (e.key==='d'||e.key==='D') this._debug = !this._debug;
    });
  }
}

window.BaymaxFace = BaymaxFace;
