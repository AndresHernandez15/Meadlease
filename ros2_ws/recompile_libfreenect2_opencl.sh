#!/bin/bash
# Script para recompilar libfreenect2 con aceleración OpenCL para máximo rendimiento

set -e

echo "=============================================="
echo "  Recompilación de libfreenect2 con OpenCL"
echo "=============================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio de trabajo
LIBFREENECT2_DIR="$HOME/ros2_ws/src/libfreenect2"
BUILD_DIR="$LIBFREENECT2_DIR/build"

# Verificar si OpenCL está instalado
echo -e "${YELLOW}[1/6] Verificando dependencias de OpenCL...${NC}"
if ! dpkg -l | grep -q "ocl-icd-libopencl1"; then
    echo -e "${RED}Error: OpenCL no está instalado. Instalando...${NC}"
    sudo apt-get update
    sudo apt-get install -y ocl-icd-libopencl1 opencl-headers ocl-icd-opencl-dev
else
    echo -e "${GREEN}✓ OpenCL ya está instalado${NC}"
fi

# Instalar dependencias adicionales para compilación
echo -e "${YELLOW}[2/6] Instalando dependencias de compilación...${NC}"
sudo apt-get install -y \
    libturbojpeg0-dev \
    libglfw3-dev \
    libopengl-dev \
    mesa-common-dev \
    libusb-1.0-0-dev \
    cmake \
    pkg-config

# Limpiar build anterior
echo -e "${YELLOW}[3/6] Limpiando compilación anterior...${NC}"
cd "$LIBFREENECT2_DIR"
rm -rf build
mkdir -p build
cd build

# Configurar con CMake habilitando OpenCL
echo -e "${YELLOW}[4/6] Configurando con CMake (OpenCL habilitado)...${NC}"
cmake .. \
    -DENABLE_CXX11=ON \
    -DBUILD_OPENNI2_DRIVER=OFF \
    -DENABLE_OPENCL=ON \
    -DENABLE_CUDA=OFF \
    -DENABLE_OPENGL=OFF \
    -DENABLE_VAAPI=OFF \
    -DENABLE_TEGRAJPEG=OFF \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DCMAKE_BUILD_TYPE=Release

# Compilar en paralelo
echo -e "${YELLOW}[5/6] Compilando libfreenect2 (esto puede tardar varios minutos)...${NC}"
make -j$(nproc)

# Instalar
echo -e "${YELLOW}[6/6] Instalando libfreenect2...${NC}"
sudo make install

# Configurar ldconfig
echo -e "${YELLOW}Configurando librerías...${NC}"
sudo ldconfig

echo ""
echo -e "${GREEN}=============================================="
echo -e "  ✓ Compilación completada exitosamente"
echo -e "==============================================${NC}"
echo ""
echo -e "${YELLOW}SIGUIENTES PASOS:${NC}"
echo "1. Recompilar kinect2_bridge en ROS2:"
echo "   cd ~/ros2_ws"
echo "   colcon build --packages-select kinect2_registration kinect2_bridge --cmake-clean-cache"
echo ""
echo "2. Usar el launch file optimizado:"
echo "   source ~/ros2_ws/install/setup.bash"
echo "   ros2 launch kinect2_bridge kinect2_bridge_optimized.yaml"
echo ""
echo "3. Editar el launch file y cambiar:"
echo "   depth_method: 'opencl'"
echo "   reg_method: 'opencl'"
echo ""
