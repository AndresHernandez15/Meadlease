#!/bin/bash
# Script para verificar condiciones óptimas de mapeo con RTAB-Map

echo "=========================================="
echo "  DIAGNÓSTICO DE CONDICIONES DE MAPEO"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar Kinect conectado
echo -e "${YELLOW}[1/6] Verificando Kinect...${NC}"
if lsusb | grep -q "045e:02c4"; then
    echo -e "${GREEN}✓ Kinect V2 conectado${NC}"
else
    echo -e "${RED}✗ Kinect NO detectado${NC}"
    exit 1
fi

# 2. Verificar resolución de topics
echo ""
echo -e "${YELLOW}[2/6] Verificando configuración topics Kinect...${NC}"
source ~/ros2_ws/install/setup.bash
timeout 3 ros2 topic info /kinect2/sd/image_color_rect &>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Topics SD configurados correctamente${NC}"
else
    echo -e "${RED}✗ Topics SD no disponibles. ¿Está corriendo kinect2_bridge?${NC}"
fi

# 3. Verificar Hz del Kinect
echo ""
echo -e "${YELLOW}[3/6] Midiendo rendimiento Kinect (5 segundos)...${NC}"
FPS_COLOR=$(timeout 5 ros2 topic hz /kinect2/sd/image_color_rect 2>/dev/null | grep "average rate" | awk '{print $3}')
if [ ! -z "$FPS_COLOR" ]; then
    FPS_INT=${FPS_COLOR%.*}
    if [ "$FPS_INT" -gt 20 ]; then
        echo -e "${GREEN}✓ Kinect RGB: ${FPS_COLOR} Hz (Excelente)${NC}"
    elif [ "$FPS_INT" -gt 10 ]; then
        echo -e "${YELLOW}⚠ Kinect RGB: ${FPS_COLOR} Hz (Aceptable, considera OpenCL)${NC}"
    else
        echo -e "${RED}✗ Kinect RGB: ${FPS_COLOR} Hz (Lento - RECOMENDADO: recompilar con OpenCL)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No se pudo medir FPS (¿kinect2_bridge corriendo?)${NC}"
fi

# 4. Verificar RAM disponible
echo ""
echo -e "${YELLOW}[4/6] Verificando RAM disponible...${NC}"
RAM_FREE=$(free -g | awk '/^Mem:/{print $7}')
if [ "$RAM_FREE" -gt 4 ]; then
    echo -e "${GREEN}✓ RAM libre: ${RAM_FREE}GB (Suficiente)${NC}"
elif [ "$RAM_FREE" -gt 2 ]; then
    echo -e "${YELLOW}⚠ RAM libre: ${RAM_FREE}GB (Justo, cierra apps innecesarias)${NC}"
else
    echo -e "${RED}✗ RAM libre: ${RAM_FREE}GB (Insuficiente - cierra Chrome/Firefox)${NC}"
fi

# 5. Verificar CPU idle
echo ""
echo -e "${YELLOW}[5/6] Verificando carga CPU...${NC}"
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | cut -d'.' -f1)
if [ "$CPU_IDLE" -gt 60 ]; then
    echo -e "${GREEN}✓ CPU idle: ${CPU_IDLE}% (Buen rendimiento esperado)${NC}"
elif [ "$CPU_IDLE" -gt 40 ]; then
    echo -e "${YELLOW}⚠ CPU idle: ${CPU_IDLE}% (Rendimiento moderado)${NC}"
else
    echo -e "${RED}✗ CPU idle: ${CPU_IDLE}% (Sistema sobrecargado)${NC}"
fi

# 6. Verificar OpenCL disponible
echo ""
echo -e "${YELLOW}[6/6] Verificando soporte OpenCL...${NC}"
if command -v clinfo &> /dev/null; then
    if clinfo 2>/dev/null | grep -q "Device Name"; then
        echo -e "${GREEN}✓ OpenCL disponible en el sistema${NC}"
        echo -e "${YELLOW}  → RECOMENDADO: Recompilar libfreenect2 con OpenCL (100x mejora)${NC}"
        echo -e "${YELLOW}  → Ejecuta: ~/ros2_ws/recompile_libfreenect2_opencl.sh${NC}"
    else
        echo -e "${YELLOW}⚠ OpenCL instalado pero sin dispositivos${NC}"
    fi
else
    echo -e "${YELLOW}⚠ clinfo no instalado (OpenCL puede estar disponible)${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}  DIAGNÓSTICO COMPLETO${NC}"
echo "=========================================="
echo ""
echo "RECOMENDACIONES:"
echo "1. Si Kinect < 15 Hz → Recompilar con OpenCL (mejora 100x)"
echo "2. Muévete LENTO: 10cm/seg, pausas de 2 seg cada 30cm"
echo "3. Apunta a zonas con textura (evita paredes blancas)"
echo "4. Buena iluminación (evita contraluces)"
echo ""
