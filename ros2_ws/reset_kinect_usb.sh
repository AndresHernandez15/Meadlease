#!/bin/bash
# Script para resetear el dispositivo USB del Kinect

echo "Reseteando dispositivo Kinect USB..."

# Encontrar el dispositivo Kinect
KINECT_DEVICE=$(lsusb | grep "045e:02c4" | awk '{print "/dev/bus/usb/" $2 "/" $4}' | sed 's/://g')

if [ -z "$KINECT_DEVICE" ]; then
    echo "Error: No se encontró el Kinect"
    exit 1
fi

echo "Kinect encontrado en: $KINECT_DEVICE"

# Usar usbreset si está disponible, sino usar bind/unbind
if command -v usbreset &> /dev/null; then
    sudo usbreset "$KINECT_DEVICE"
else
    # Método alternativo usando bind/unbind
    BUS=$(echo $KINECT_DEVICE | cut -d'/' -f5)
    DEV=$(echo $KINECT_DEVICE | cut -d'/' -f6)
    
    # Encontrar el bus USB del dispositivo
    USB_DEVICE=$(readlink -f /sys/bus/usb/devices/$BUS-* 2>/dev/null | head -1)
    
    if [ ! -z "$USB_DEVICE" ]; then
        sudo sh -c "echo 0 > $USB_DEVICE/authorized"
        sleep 1
        sudo sh -c "echo 1 > $USB_DEVICE/authorized"
    fi
fi

echo "Dispositivo reseteado. Espera 2 segundos..."
sleep 2

echo "Verificando dispositivo:"
lsusb | grep Microsoft

echo ""
echo "Ahora puedes ejecutar: ./Protonect"
