# 🗺️ GUÍA DE MAPEO CON RTAB-MAP Y KINECT V2

## 🎯 Objetivo: Crear un Mapa Estable sin Perder Tracking

---

## ⚠️ INDICADORES EN RTABMAP_VIZ

### Colores de Estado:
- 🟢 **VERDE:** ✅ Tracking correcto, mapeando bien
- 🔴 **ROJO:** ❌ Perdió tracking (odometría visual falló)
- 🟡 **AMARILLO:** ⚠️ Warning, pocas features pero aún funcionando

### Si la Pantalla se Pone Roja:
1. **DETENTE** - No muevas la cámara
2. Apunta a una zona con textura (pared con cuadros, muebles, etc.)
3. Espera a que vuelva a verde
4. Continúa moviendo **MÁS LENTO**

---

## 📋 TÉCNICA CORRECTA PARA MAPEAR

### 1️⃣ Preparación
```bash
# Resetear mapa viejo (si es necesario)
cd ~/ros2_ws
./reset_rtabmap_db.sh

# Lanzar Kinect
source install/setup.bash
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
```

**En otra terminal:**
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robot_medical slam_real_kinect.launch.py
```

---

### 2️⃣ Inicio del Mapeo

1. **Coloca el Kinect** apuntando a una zona con **buena textura** (no pared blanca)
   - ✅ Bueno: Pósters, cuadros, muebles con detalles, libros
   - ❌ Malo: Pared blanca lisa, ventanas, espejos

2. **Espera 3-5 segundos** sin mover
   - Observa que rtabmap_viz esté en **VERDE**
   - Verifica que aparezcan puntos 3D en la nube

---

### 3️⃣ Movimiento (MUY IMPORTANTE)

#### Velocidad: **LENTO Y SUAVE**
- ⏱️ **Rotación:** Máximo 10-15°/segundo (muy lento)
- 📏 **Traslación:** Máximo 10-20 cm/segundo (muy lento)
- ⏸️ **Pausas:** Cada 30-45° de rotación o 30-50cm de movimiento

#### Patrón Recomendado:
```
1. Mueve 20cm → PAUSA 2 segundos
2. Rota 30° → PAUSA 2 segundos
3. Mueve 20cm → PAUSA 2 segundos
4. Repite...
```

#### ❌ NUNCA HAGAS:
- Movimientos bruscos
- Girar rápido (>20°/seg)
- Mover sin pausar
- Apuntar al cielo o suelo solo
- Apuntar a espejos o ventanas

---

### 4️⃣ Mapeo de una Habitación

**Proceso Paso a Paso:**

```
[Inicio: Esquina A]
   |
   v
1. Apunta a la pared con textura → ESPERA verde
   |
   v
2. Gira 30° lentamente → PAUSA 2 seg
   |
   v
3. Avanza 30cm hacia esquina B → PAUSA 2 seg
   |
   v
4. Repite hasta cubrir toda la habitación
   |
   v
5. CIERRA EL LOOP: Vuelve a esquina A (muy importante)
```

**Loop Closure (Muy Importante):**
- Al final, vuelve a la posición inicial
- Cuando RTAB-Map reconozca el lugar (verás línea verde en el grafo)
- Esto corrige errores acumulados

---

### 5️⃣ Monitoreo Durante Mapeo

**Terminal de Diagnóstico:**
```bash
source ~/ros2_ws/install/setup.bash

# Ver rendimiento odometría
ros2 topic hz /odom

# Ver info RTAB-Map
ros2 topic echo /rtabmap/info --once

# Buscar estos valores:
# - loop_closure_id: -1 (sin loop) o >0 (loop detectado)
# - local_map_size: número de nodos locales
# - working_mem_size: nodos en memoria de trabajo
```

---

## 🎬 FLUJO COMPLETO DE MAPEO

### Escenario: Mapear Apartamento

```
TERMINAL 1: Kinect
  ros2 launch kinect2_bridge kinect2_bridge_launch.yaml

TERMINAL 2: RTAB-Map
  ros2 launch robot_medical slam_real_kinect.launch.py

TERMINAL 3: Monitoreo
  watch -n 1 'ros2 topic hz /odom'
```

**Proceso:**
1. **Sala (5 min):**
   - Inicio en esquina SW
   - Avanza lentamente por perímetro
   - Pausa cada 30cm
   - Vuelve a inicio (loop closure)

2. **Pasillo (2 min):**
   - Desde sala hacia cocina
   - Movimiento muy lento
   - Muchas pausas

3. **Cocina (5 min):**
   - Igual que sala
   - Cerrar loop volviendo al pasillo

4. **Habitaciones (10 min cada una):**
   - Una a la vez
   - Siempre cerrar loops

**TOTAL:** ~30-45 minutos para apartamento completo

---

## 💾 GUARDAR MAPA

**Una vez terminado:**
```bash
# Ver tamaño del mapa
ls -lh ~/.ros/rtabmap.db

# Exportar mapa 2D para Nav2 (próximo paso)
# (Se hará en tutorial siguiente)
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Problema: Se Pone Rojo Constantemente

**Causa:** Movimiento muy rápido o escena sin textura

**Solución:**
1. Reduce velocidad a la mitad
2. Aumenta pausas a 3-4 segundos
3. Busca áreas con más textura
4. Verifica iluminación (evita contraluces)

---

### Problema: No Detecta Loop Closures

**Causa:** Cambió mucho el punto de vista

**Solución:**
1. Vuelve **exactamente** al mismo lugar y ángulo inicial
2. Mantén la cámara ahí 5-10 segundos
3. Observa en rtabmap_viz si aparece línea verde en el grafo

---

### Problema: Mapa se Deforma

**Causa:** Error acumulado sin loop closures

**Solución:**
1. Haz loops pequeños frecuentes (cada habitación)
2. No hagas trayectorias muy largas sin cerrar
3. Aumenta `Kp/MaxFeatures` si detecta pocos loops

---

## 📊 PARÁMETROS ACTUALES OPTIMIZADOS

```yaml
DetectionRate: 1.5 Hz         # Procesa cada frame lentamente
Vis/MaxFeatures: 400          # Muchas features para tracking robusto
Vis/MinInliers: 10            # Tolerante a pocas coincidencias
RGBD/LinearUpdate: 0.1m       # Actualiza cada 10cm (tolerante)
RGBD/AngularUpdate: 0.1rad    # Actualiza cada ~6° (tolerante)
```

---

## 🎯 CHECKLIST PRE-MAPEO

- [ ] Kinect conectado y funcionando (Protonect OK)
- [ ] Iluminación adecuada (ni muy oscuro ni contraluces)
- [ ] Escena con textura visible (no paredes blancas)
- [ ] Batería laptop cargada (proceso largo)
- [ ] Base de datos reseteada (si mapa nuevo)
- [ ] 3 terminales abiertas (Kinect, RTAB, Monitor)

---

## 🚀 SIGUIENTE PASO

Una vez tengas un mapa completo y estable:
1. Exportar OccupancyGrid para Nav2
2. Configurar localización (sin SLAM)
3. Probar navegación autónoma

**Archivo siguiente:** `NAVIGATION_SETUP.md` (próximo tutorial)

---

**Actualizado:** 26 Febrero 2026  
**Optimizado para:** Hardware limitado (12GB RAM, 4 cores)
