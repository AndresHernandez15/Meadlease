#!/bin/bash
# Script para resetear la base de datos de RTAB-Map
# Úsalo cuando quieras empezar un mapa nuevo desde cero

echo "=========================================="
echo "  RESETEAR BASE DE DATOS RTAB-MAP"
echo "=========================================="
echo ""

# Ubicación de la base de datos de RTAB-Map
RTABMAP_DB="$HOME/.ros/rtabmap.db"

if [ -f "$RTABMAP_DB" ]; then
    echo "Base de datos encontrada en: $RTABMAP_DB"
    du -h "$RTABMAP_DB"
    echo ""
    echo "¿Estás seguro de borrar el mapa y empezar desde cero? (s/n)"
    read -r response
    
    if [[ "$response" =~ ^[Ss]$ ]]; then
        rm -f "$RTABMAP_DB"
        echo "✓ Base de datos eliminada"
        echo "Al lanzar RTAB-Map nuevamente, creará un mapa nuevo"
    else
        echo "Operación cancelada"
    fi
else
    echo "No se encontró base de datos existente"
    echo "RTAB-Map creará una nueva al iniciar"
fi
