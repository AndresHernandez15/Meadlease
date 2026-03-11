#!/bin/bash
# Script maestro para lanzar sistema completo de SLAM con RTAB-Map + Kinect V2
# Verifica condiciones, detecta OpenCL, y lanza todo el sistema

set -e  # Salir si hay error

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuración
WORKSPACE_DIR="$HOME/ros2_ws"
KINECT_USB_ID="045e:02c4"
MIN_RAM_GB=3
RESET_DB=false

# Banner
clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}ROBOT MÉDICO - SISTEMA SLAM 3D CON RTAB-MAP + KINECT V2${NC}  ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Función para imprimir con formato
print_step() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# ============================================
# FASE 1: VERIFICACIÓN DE PREREQUISITOS
# ============================================
print_step "FASE 1: Verificando prerequisitos del sistema..."
echo ""

# 1.1 Verificar que estamos en el workspace correcto
print_info "Verificando workspace..."
if [ ! -d "$WORKSPACE_DIR" ]; then
    print_error "Workspace no encontrado: $WORKSPACE_DIR"
    exit 1
fi
cd "$WORKSPACE_DIR"
print_success "Workspace encontrado: $WORKSPACE_DIR"

# 1.2 Verificar Kinect conectado
print_info "Verificando Kinect V2..."
if ! lsusb | grep -q "$KINECT_USB_ID"; then
    print_error "Kinect V2 no detectado en USB"
    print_error "Verifica que esté conectado y con alimentación"
    exit 1
fi
KINECT_BUS=$(lsusb | grep "$KINECT_USB_ID" | awk '{print $2, $4}' | sed 's/://')
print_success "Kinect V2 detectado en Bus $KINECT_BUS"

# 1.3 Verificar RAM disponible
print_info "Verificando RAM disponible..."
RAM_FREE=$(free -g | awk '/^Mem:/{print $7}')
if [ "$RAM_FREE" -lt "$MIN_RAM_GB" ]; then
    print_warning "RAM libre: ${RAM_FREE}GB (mínimo recomendado: ${MIN_RAM_GB}GB)"
    print_warning "Considera cerrar aplicaciones innecesarias"
else
    print_success "RAM libre: ${RAM_FREE}GB (suficiente)"
fi

# 1.4 Verificar si libfreenect2 tiene OpenCL
print_info "Verificando soporte OpenCL en libfreenect2..."
OPENCL_ENABLED=false
if [ -f "$WORKSPACE_DIR/src/libfreenect2/build/CMakeCache.txt" ]; then
    if grep -q "ENABLE_OPENCL:BOOL=ON" "$WORKSPACE_DIR/src/libfreenect2/build/CMakeCache.txt"; then
        OPENCL_ENABLED=true
        print_success "OpenCL HABILITADO (rendimiento óptimo)"
    else
        print_warning "OpenCL DESHABILITADO (solo CPU)"
        print_warning "Rendimiento será 100x más lento"
        print_info "Para mejorar: ejecuta ./recompile_libfreenect2_opencl.sh"
    fi
else
    print_warning "No se pudo verificar OpenCL (archivo CMakeCache.txt no encontrado)"
fi

# 1.5 Source del workspace
print_info "Cargando entorno ROS2..."
if [ -f "$WORKSPACE_DIR/install/setup.bash" ]; then
    source "$WORKSPACE_DIR/install/setup.bash"
    print_success "Entorno ROS2 cargado"
else
    print_error "No se encontró install/setup.bash"
    print_error "Ejecuta: colcon build"
    exit 1
fi

# 1.6 Verificar que los paquetes estén compilados
print_info "Verificando paquetes compilados..."
PACKAGES_OK=true
for pkg in kinect2_bridge robot_medical; do
    if [ ! -d "$WORKSPACE_DIR/install/$pkg" ]; then
        print_error "Paquete no compilado: $pkg"
        PACKAGES_OK=false
    fi
done

if [ "$PACKAGES_OK" = false ]; then
    print_error "Compila primero: colcon build"
    exit 1
fi
print_success "Todos los paquetes compilados"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ VERIFICACIÓN COMPLETA - SISTEMA LISTO${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================
# FASE 2: CONFIGURACIÓN Y OPCIONES
# ============================================
print_step "FASE 2: Configuración del mapeo..."
echo ""

# Preguntar si resetear base de datos
if [ -f "$HOME/.ros/rtabmap.db" ]; then
    DB_SIZE=$(du -h "$HOME/.ros/rtabmap.db" | cut -f1)
    print_info "Base de datos RTAB-Map existente encontrada (${DB_SIZE})"
    echo -e "${YELLOW}¿Deseas resetear el mapa y empezar desde cero? (s/N):${NC} "
    read -r -t 10 response || response="n"
    if [[ "$response" =~ ^[Ss]$ ]]; then
        rm -f "$HOME/.ros/rtabmap.db"
        print_success "Base de datos eliminada - mapa nuevo"
        RESET_DB=true
    else
        print_info "Continuando con mapa existente"
    fi
else
    print_info "No hay mapa previo - creando nuevo mapa"
    RESET_DB=true
fi

echo ""

# ============================================
# FASE 3: LANZAMIENTO DEL SISTEMA
# ============================================
print_step "FASE 3: Lanzando sistema SLAM..."
echo ""

# 3.1 Lanzar kinect2_bridge en background
print_info "Iniciando kinect2_bridge..."
gnome-terminal --title="Kinect2 Bridge" -- bash -c "
    cd $WORKSPACE_DIR
    source install/setup.bash
    echo -e '${CYAN}═══════════════════════════════════════${NC}'
    echo -e '${CYAN}  KINECT2 BRIDGE${NC}'
    echo -e '${CYAN}═══════════════════════════════════════${NC}'
    echo ''
    ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
    echo ''
    echo -e '${RED}kinect2_bridge finalizado${NC}'
    read -p 'Presiona Enter para cerrar...'
" &
KINECT_PID=$!
sleep 3  # Dar tiempo para que inicie

# Verificar que kinect2_bridge esté corriendo
print_info "Verificando que kinect2_bridge esté publicando..."
sleep 2
if timeout 5 ros2 topic list | grep -q "kinect2"; then
    print_success "kinect2_bridge está publicando topics"
else
    print_error "kinect2_bridge no está publicando topics"
    print_error "Verifica la ventana de kinect2_bridge"
    exit 1
fi

# 3.2 Lanzar RTAB-Map en background
print_info "Iniciando RTAB-Map..."
sleep 2
gnome-terminal --title="RTAB-Map SLAM" -- bash -c "
    cd $WORKSPACE_DIR
    source install/setup.bash
    echo -e '${CYAN}═══════════════════════════════════════${NC}'
    echo -e '${CYAN}  RTAB-MAP SLAM 3D${NC}'
    echo -e '${CYAN}═══════════════════════════════════════${NC}'
    echo ''
    if [ '$OPENCL_ENABLED' = true ]; then
        echo -e '${GREEN}✓ OpenCL habilitado - Rendimiento óptimo${NC}'
    else
        echo -e '${YELLOW}⚠ Solo CPU - Rendimiento limitado${NC}'
    fi
    echo ''
    ros2 launch robot_medical slam_real_kinect.launch.py
    echo ''
    echo -e '${RED}RTAB-Map finalizado${NC}'
    read -p 'Presiona Enter para cerrar...'
" &
RTABMAP_PID=$!
sleep 5  # Dar tiempo para que inicie

# Verificar que RTAB-Map esté corriendo
print_info "Verificando que RTAB-Map esté corriendo..."
sleep 2
if timeout 5 ros2 node list | grep -q "rtabmap"; then
    print_success "RTAB-Map está corriendo"
else
    print_warning "RTAB-Map puede no estar completamente iniciado"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ SISTEMA SLAM COMPLETAMENTE INICIADO${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================
# FASE 4: MONITOREO Y ESTADO
# ============================================
print_step "FASE 4: Monitoreando sistema..."
echo ""

# Lanzar terminal de monitoreo
gnome-terminal --title="Monitor SLAM" --geometry=100x30 -- bash -c "
    cd $WORKSPACE_DIR
    source install/setup.bash
    
    echo -e '${CYAN}╔════════════════════════════════════════════════════════════╗${NC}'
    echo -e '${CYAN}║${NC}               ${BOLD}MONITOR DE RTAB-MAP EN VIVO${NC}                  ${CYAN}║${NC}'
    echo -e '${CYAN}╚════════════════════════════════════════════════════════════╝${NC}'
    echo ''
    
    echo -e '${YELLOW}Esperando que RTAB-Map publique datos...${NC}'
    sleep 10
    
    while true; do
        clear
        echo -e '${CYAN}╔════════════════════════════════════════════════════════════╗${NC}'
        echo -e '${CYAN}║${NC}               ${BOLD}MONITOR DE RTAB-MAP EN VIVO${NC}                  ${CYAN}║${NC}'
        echo -e '${CYAN}╠════════════════════════════════════════════════════════════╣${NC}'
        echo -e '${CYAN}║${NC} Actualización: \$(date +%H:%M:%S)                                ${CYAN}║${NC}'
        echo -e '${CYAN}╚════════════════════════════════════════════════════════════╝${NC}'
        echo ''
        
        # Estado de nodos
        echo -e '${BOLD}NODOS ACTIVOS:${NC}'
        ros2 node list | grep -E 'kinect|rtabmap' | sed 's/^/  /'
        echo ''
        
        # Rendimiento topics
        echo -e '${BOLD}RENDIMIENTO TOPICS:${NC}'
        echo -n '  Kinect RGB:   '
        timeout 2 ros2 topic hz /kinect2/sd/image_color_rect 2>/dev/null | grep 'average' | awk '{print \$3 \" Hz\"}' || echo 'N/A'
        
        echo -n '  Kinect Depth: '
        timeout 2 ros2 topic hz /kinect2/sd/image_depth_rect 2>/dev/null | grep 'average' | awk '{print \$3 \" Hz\"}' || echo 'N/A'
        
        echo -n '  RTAB-Map:     '
        timeout 2 ros2 topic hz /rtabmap/info 2>/dev/null | grep 'average' | awk '{print \$3 \" Hz\"}' || echo 'N/A'
        echo ''
        
        # Estadísticas RTAB-Map
        echo -e '${BOLD}ESTADÍSTICAS MAPA:${NC}'
        if timeout 2 ros2 topic echo /rtabmap/info --once 2>/dev/null > /tmp/rtabmap_info.txt; then
            NODES=\$(grep -A1 'local_map_size:' /tmp/rtabmap_info.txt | tail -1 | awk '{print \$2}')
            LOOP_ID=\$(grep -A1 'loop_closure_id:' /tmp/rtabmap_info.txt | tail -1 | awk '{print \$2}')
            
            echo \"  Nodos en mapa: \$NODES\"
            if [ \"\$LOOP_ID\" != \"-1\" ]; then
                echo -e \"  ${GREEN}✓ Loop closure detectado (ID: \$LOOP_ID)${NC}\"
            else
                echo \"  Loop closure: No detectado aún\"
            fi
        else
            echo '  Esperando datos...'
        fi
        
        echo ''
        echo -e '${CYAN}═══════════════════════════════════════════════════════════${NC}'
        echo -e '${YELLOW}Presiona Ctrl+C para detener el monitor${NC}'
        echo ''
        
        sleep 5
    done
" &
MONITOR_PID=$!

# ============================================
# INFORMACIÓN FINAL Y RECOMENDACIONES
# ============================================
echo ""
echo -e "${BOLD}VENTANAS ABIERTAS:${NC}"
echo "  1. Kinect2 Bridge (publicando imágenes RGB-D)"
echo "  2. RTAB-Map SLAM (mapeando en 3D)"
echo "  3. RTAB-Map Viz (visualización 3D - ventana gráfica)"
echo "  4. Monitor en vivo (estadísticas en tiempo real)"
echo ""

echo -e "${BOLD}INSTRUCCIONES DE USO:${NC}"
echo -e "${CYAN}┌────────────────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│${NC} ${BOLD}TÉCNICA DE MAPEO:${NC}                                      ${CYAN}│${NC}"
echo -e "${CYAN}├────────────────────────────────────────────────────────┤${NC}"
echo -e "${CYAN}│${NC} 1. Muévete MUY LENTO (5-10 cm/segundo)            ${CYAN}│${NC}"
echo -e "${CYAN}│${NC} 2. PAUSA 2-3 segundos cada 20-30cm                ${CYAN}│${NC}"
echo -e "${CYAN}│${NC} 3. Apunta a zonas con TEXTURA (evita paredes)     ${CYAN}│${NC}"
echo -e "${CYAN}│${NC} 4. Observa rtabmap_viz: VERDE=OK, ROJO=perdió     ${CYAN}│${NC}"
echo -e "${CYAN}│${NC} 5. Cierra LOOPS volviendo al punto inicial        ${CYAN}│${NC}"
echo -e "${CYAN}└────────────────────────────────────────────────────────┘${NC}"
echo ""

echo -e "${BOLD}MONITOREO:${NC}"
echo "  • Ventana 'Monitor SLAM': Estado en tiempo real"
echo "  • Ventana 'RTAB-Map Viz': Visualización 3D del mapa"
echo "  • Busca color VERDE (tracking OK) en rtabmap_viz"
echo ""

echo -e "${BOLD}PARA DETENER EL SISTEMA:${NC}"
echo "  • Ctrl+C en cada ventana de terminal"
echo "  • O cierra las ventanas directamente"
echo ""

if [ "$OPENCL_ENABLED" = false ]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠ RECOMENDACIÓN: ACTIVAR OPENCL PARA MEJOR RENDIMIENTO${NC}  ${YELLOW}║${NC}"
    echo -e "${YELLOW}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║${NC}  Ejecuta: ./recompile_libfreenect2_opencl.sh       ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Mejora: 100-300x más rápido                        ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Tiempo: ~10-15 minutos                             ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
fi

echo -e "${GREEN}Sistema completamente iniciado y monitoreando.${NC}"
echo -e "${GREEN}¡Comienza a mapear tu entorno!${NC}"
echo ""

# Mantener script vivo
print_info "Script maestro corriendo... Presiona Ctrl+C para salir"
echo ""

# Trap para limpieza
cleanup() {
    echo ""
    print_info "Deteniendo sistema..."
    # No matamos los procesos, dejamos que el usuario los cierre manualmente
    print_success "Saliendo del script maestro"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Loop infinito para mantener script vivo
while true; do
    sleep 10
done
