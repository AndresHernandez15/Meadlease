# Seguridad del Repositorio

Este documento explica los cambios de seguridad aplicados al repo y qué implican para cada integrante del equipo.

---

## ¿Los cambios eliminaron archivos de mi máquina? No.

Los comandos usados fueron:

```bash
git rm --cached database/patient.db
git rm -r --cached .idea/
```

`--cached` significa **solo se eliminan del rastreo de git**; los archivos en el disco de tu máquina **no se tocan, no se borran, no se modifican**. Tus datos, tu configuración de IDE y tu base de datos local siguen exactamente donde estaban.

---

## ¿Qué cambia cuando hagas `git pull`?

Cuando jalés estos cambios a tu máquina local:

| Archivo | En tu disco local | En el repo remoto |
|---------|-------------------|-------------------|
| `database/patient.db` | ✅ Sigue intacto | ❌ Ya no se rastrea |
| `.idea/` | ✅ Sigue intacto | ❌ Ya no se rastrea |

Git simplemente dejará de rastrear esos archivos. No los eliminará de tu carpeta local.

---

## ¿Qué debo hacer después de hacer `git pull`?

Nada obligatorio. Pero se recomienda:

### 1. Mover `patient.db` a la carpeta correcta (opcional)

El README de `database/` indica que el archivo debe vivir en `database/data/patient.db`. Si lo tienes en `database/patient.db`, puedes moverlo:

```bash
mv database/patient.db database/data/patient.db
```

El `.gitignore` ya cubre ambas rutas, así que no se subirá de todas formas.

### 2. Tu `.idea/` sigue funcionando normal

PyCharm/IntelliJ seguirán leyendo `.idea/` de tu disco sin problema. Solo dejará de aparecer en `git status`.

---

## ¿Por qué se hicieron estos cambios?

Para que el repositorio pueda hacerse público sin exponer:

| Problema | Archivo |
|----------|---------|
| Datos médicos reales de pacientes (nombre, diagnósticos, medicamentos, signos vitales) | `database/patient.db` |
| IPs internas de los robots del laboratorio (`192.168.1.14`, `192.168.20.42`) | `.idea/deployment.xml` |

---

## ¿Qué sigue siendo privado o seguro?

- ✅ Las API keys (Groq, Azure, Porcupine) ya se cargaban desde variables de entorno — nunca estuvieron en el repo
- ✅ El `.env` ya estaba en el `.gitignore` de `atlas/`
- ✅ El nuevo `.gitignore` raíz protege contra commits accidentales futuros de `*.db`, `.env`, y `.idea/`

---

## Paso adicional recomendado (admin del repo)

Los archivos sensibles todavía existen en los **commits anteriores** del historial de git. Para eliminarlos completamente antes de hacer el repo público:

```bash
# Instalar la herramienta
pip install git-filter-repo

# Borrar del historial completo
git filter-repo --path database/patient.db --invert-paths
git filter-repo --path .idea/ --invert-paths

# Forzar push (requiere permisos de administrador en GitHub)
git push origin --force --all
```

> ⚠️ Esto reescribe el historial. Todos los integrantes deberán clonar el repo de nuevo o hacer `git fetch --all && git reset --hard origin/main` después.
