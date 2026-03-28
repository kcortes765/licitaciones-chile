# Security Audit Report — IngenIA Licitaciones

**Fecha**: 2026-03-28
**Auditor**: Claude (autonomo feature 15)
**Estado**: PASS

---

## 1. Cobertura .gitignore

| Patrón | Cubierto | Notas |
|--------|----------|-------|
| `.env` | ✅ | Raíz |
| `.env.local` | ✅ | Raíz |
| `.env.bak*` | ✅ | Cubre `.env.bak.20260306_115223` y similares |
| `lead_scoring/.env` | ✅ | Subdirectorio |
| `lead_scoring/.env.bak*` | ✅ | Subdirectorio |
| `lead_scoring/data/raw/` | ✅ | CSVs bulk |
| `lead_scoring/data/filtered/` | ✅ | Parquets procesados |
| `lead_scoring/data/output/` | ✅ | Exports cliente |
| `backups/` | ✅ | Copias de seguridad |

**Resultado**: Todos los archivos sensibles están excluidos de git.

## 2. API Keys y Secretos en Código

### Búsqueda de patrones sensibles
- Prefijos de token Apify en *.py: 0 matches reales (1 falso positivo en test corregido)
- Prefijos de Google API Key en *.py: 0 matches
- Fragmentos de ticket MercadoPúblico en *.py: 0 matches
- `Bearer ` en *.py: 0 matches
- Strings largos (>20 chars) que parecen keys: 0 matches reales

### Gestión de API keys en config.py
| Variable | Método | Seguro |
|----------|--------|--------|
| `APIFY_TOKEN` | `os.getenv("APIFY_TOKEN", "")` | ✅ |
| `MERCADO_PUBLICO_TICKET` | `os.getenv("MERCADO_PUBLICO_TICKET", "")` | ✅ |
| `GOOGLE_MAPS_API_KEY` | `os.getenv("GOOGLE_MAPS_API_KEY", "")` | ✅ |

### monitor_licitaciones.py
- `TICKET = os.getenv("MERCADO_PUBLICO_TICKET", "")` — línea 27 ✅

### .env.example
- Solo contiene `replace_me` como placeholder ✅
- No expone valores reales ✅

**Resultado**: Ningún secreto hardcoded en código fuente.

## 3. Archivos Sensibles en Git

- `git ls-files` para `data/output/`, `data/filtered/`, `data/raw/`: **0 archivos tracked**
- `git ls-files` para `.env*`: solo `.env.example` (placeholder seguro)
- Directorio `audit/`: no tracked previamente

**Resultado**: Ningún archivo con datos sensibles en el repositorio.

## 4. Protección de Secretos en Runtime

| Función | Ubicación | Propósito |
|---------|-----------|-----------|
| `redact_secret()` | config.py:150 | Oculta valores al imprimir |
| `env_value_status()` | config.py:142 | Detecta missing/placeholder/ok |
| `PLACEHOLDER_SECRET_VALUES` | config.py:30 | Set de valores placeholder conocidos |
| `assert_env_vars()` | config.py:171 | Valida vars requeridas antes de ejecutar |

**Resultado**: Framework robusto de protección de secretos en runtime.

## 5. Correcciones Realizadas

| Archivo | Cambio | Razón |
|---------|--------|-------|
| `lead_scoring/tests/test_config.py:315` | Valor fake de test reemplazado por string genérico | Valor de test contenía patrón de token Apify que disparaba grep de seguridad |

## 6. Nota sobre APIFY_GOOGLE_MAPS_ACTOR

`config.py:104` contiene `APIFY_GOOGLE_MAPS_ACTOR = "nwua9Gu5YrADL7ZDj"`. Este es un **ID público** de actor en la plataforma Apify (equivalente a un nombre de paquete), **NO** es un secreto. No requiere ser movido a .env.

## Conclusión

La postura de seguridad del proyecto es **BUENA**:
- Todos los secretos se gestionan via `.env` + `os.getenv()`
- `.gitignore` cubre archivos sensibles comprensivamente
- Framework de redacción de secretos en runtime
- No hay secretos hardcoded en código fuente
- Datos de pipeline (parquets, CSVs, outputs) excluidos de git
