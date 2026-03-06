# Base de Datos — Meadlease

> SQLite local · No se sube `patient.db` al repo (datos reales de pacientes)

## Esquema

5 tablas: `pacientes`, `medicamentos`, `horarios_medicacion`, `signos_vitales`, `registros_dispensacion`

Ver [DOCUMENTACION_CONVERSACIONAL.md](../docs/DOCUMENTACION_CONVERSACIONAL.md#7-base-de-datos-medica) para el esquema completo.

## Crear y poblar base de datos de prueba

```bash
python scripts/populate_test_db.py
# Genera: data/patient.db con datos ficticios para pruebas
```

## Privacidad

- `data/patient.db` está en `.gitignore` — **nunca se sube al repo**
- Los datos reales de pacientes son confidenciales
- Solo se versiona el script de creación del esquema y datos de prueba ficticios

## Estructura

```
database/
├── README.md
├── scripts/
│   ├── populate_test_db.py     # Datos ficticios para pruebas
│   └── create_schema.py        # Solo el esquema vacío
└── data/
    └── .gitkeep                # Carpeta versionada, .db ignorado
```
