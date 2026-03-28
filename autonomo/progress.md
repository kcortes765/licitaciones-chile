# Progress — IngenIA Licitaciones Audit + Messages v5

## Estado: EN PROGRESO
## Features completadas: 6/20
## Última sesión: 2026-03-28
## Errores encontrados: 0

---

## Log de sesiones

### Sesión 1 — 2026-03-28 — Feature 1: fix_hardcoded_paths

**Estado**: COMPLETADA

**Cambios realizados**:
- `filter.py`: `C:\Seba\Nueva carpeta (2)\licitaciones_hoy.json` → `Path(__file__).parent / "licitaciones_hoy.json"`
- `generar_mensajes_v3.py`: `C:/Seba/Nueva carpeta (2)/lead_scoring/data` → `Path(__file__).parent / "lead_scoring" / "data"` (+ 7 path vars)
- `generar_mensajes_v4.py`: Misma corrección que v3 (+ 7 path vars)
- `verificar_mensajes.py`: 2 paths hardcoded → `Path(__file__).parent / "lead_scoring" / "data"` base
- `verificar_mensajes_v2.py`: 2 paths hardcoded → misma corrección
- `monitor_licitaciones.py`: `C:\Seba\Nueva carpeta (2)\\` → `Path(__file__).parent / filename`
- `lead_scoring/COMMERCIAL_PLAYBOOK.md`: 6 links `C:\Seba\Nueva carpeta (2)\commercial\...` → `../commercial/...`

**Verificación**:
- `grep -r 'C:/Seba\|C:\\Seba\|Nueva carpeta' *.py lead_scoring/COMMERCIAL_PLAYBOOK.md` → **0 matches** (PASS)
- Nota: la verificación original del plan (`grep 'Seba'`) da 5 matches por el nombre "Sebastián Cortés" en firmas/templates de mensajes — son referencias legítimas al fundador, NO paths hardcoded.

**Decisiones**:
- Se usó `Path(__file__).parent` en todos los scripts Python (no config.py) para mantener independencia — cada script funciona standalone.
- Links en COMMERCIAL_PLAYBOOK.md convertidos a paths relativos (`../commercial/...`).

### Sesión 2 — 2026-03-28 — Feature 2: create_requirements_txt

**Estado**: COMPLETADA

**Cambios realizados**:
- `lead_scoring/requirements.txt`: Actualizado con 18 dependencias con version constraints adecuadas (>=min,<next_major). El archivo existía con versiones incompletas (numpy pinned a <1.25, mayoría sin versión).

**Dependencias incluidas** (18 paquetes):
- Core: pandas, numpy, pyarrow, python-dotenv
- Data I/O: openpyxl, lxml
- HTTP & Scraping: requests, beautifulsoup4, tqdm
- ML: scikit-learn, xgboost, joblib
- Viz: matplotlib, seaborn
- PDF: fpdf2
- Analysis: scipy, networkx
- Enrichment: apify-client

**Verificación**:
- `pkg_resources.require()` contra todas las líneas → sin errores (PASS)
- `requirements-dev.txt` (-r requirements.txt + pytest) → OK (PASS)

**Decisiones**:
- Se usaron rangos compatibles (>=installed_major.minor, <next_major) para equilibrar estabilidad y flexibilidad.
- Todas las dependencias opcionales (xgboost, scipy, networkx, apify-client) incluidas ya que están importadas en el código aunque con try/except — requirements.txt debe garantizar instalación completa.

### Sesión 3 — 2026-03-28 — Feature 3: test_infrastructure

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/__init__.py`: Módulo de tests
- `lead_scoring/tests/conftest.py`: 11 fixtures reutilizables
- `lead_scoring/pyproject.toml`: Configuración pytest (testpaths, markers, addopts)

**Fixtures en conftest.py**:
1. `sample_company_row` — pd.Series con los 22 campos de company_database (datos sintéticos realistas)
2. `sample_leads_df` — DataFrame 5 filas con leads rankeados + 9 score_{dim} + score_total + rank
3. `sample_enriched_df` — Extiende sample_leads_df con contacto, teléfono, email, web, scores ML, cluster_perfil, score_digital
4. `sample_loss_df` — DataFrame 3 filas para loss_analysis con rival1/rival1_cnt
5. `clean_text` — Mensaje WhatsApp seguro sin términos internos
6. `dirty_text` — Texto con score_total, xgb_score, km_score, cluster, pipeline (para tests de seguridad)
7. `real_company_db` — Carga parquet real, skip si no existe
8. `real_leads_ranked` — Carga parquet real, skip si no existe
9. `real_leads_ml_ranked` — Carga parquet real, skip si no existe
10. `real_leads_enriched` — Carga parquet real, skip si no existe
11. `real_loss_analysis` — Carga parquet real, skip si no existe

**Constantes exportadas**:
- `FILTERED_DIR`, `OUTPUT_DIR` — paths a directorios de datos
- `COMPANY_DB_PATH`, `LEADS_RANKED_PATH`, etc. — paths a parquets individuales
- `skip_no_company_db`, `skip_no_leads_ranked`, etc. — marcadores pytest.mark.skipif

**Verificación**:
- 7 smoke tests pasaron validando todas las fixtures y paths
- `python -m pytest tests/conftest.py --co -q` ejecuta sin errores
- pyproject.toml con testpaths=["tests"], addopts="-v --tb=short"

**Decisiones**:
- Se usó pyproject.toml en vez de pytest.ini (formato moderno, más extensible)
- sys.path se inserta en conftest.py para que `import config`, `import utils` etc. funcionen desde tests/
- Fixtures reales usan pytest.skip() dentro del fixture (más flexible que skipif en decorador para fixtures)
- Datos sintéticos modelados con columnas reales verificadas contra los parquets existentes

### Sesión 4 — 2026-03-28 — Feature 4: test_config

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_config.py`: 79 tests exhaustivos para config.py y constantes de pipeline_core.py

**Tests por clase** (79 total):
1. `TestScoringWeights` (14 tests) — suma=1.0, 9 dimensiones, pesos (0,1), tipos float, parametrizado por dimensión
2. `TestIdealRanges` (6 tests) — min<max, actividad>=0, win_rate en [0,1], valor_clp positivo, competencia>0, recencia=0
3. `TestConstants` (12 tests) — RECENCIA_MAX_DAYS>365, REGIONES_TOP sin duplicados, TIPOS_LICITACION L1/LE/LP/LR, BULK_YEARS>=4, ENRICH_TOP_N>0, PLACEHOLDER_SECRET_VALUES, CONSTRUCTION_UNSPSC_PREFIX="72"
4. `TestPaths` (7 tests) — BASE_DIR/DATA_DIR/RAW_DIR/FILTERED_DIR/OUTPUT_DIR existen, config.py existe
5. `TestPythonVersion` (7 tests) — PYTHON_BASELINE/TARGET son tuples (3,x), target>=baseline
6. `TestPythonRuntimeLabel` (3 tests) — formato "major.minor", valor actual, custom version_info
7. `TestRuntimeSupportStatus` (4 tests) — baseline/target/unverified/default
8. `TestEnvValueStatus` (8 tests) — missing ("", None, whitespace), placeholder (replace_me, case insensitive, todo), ok (real values)
9. `TestRedactSecret` (5 tests) — <missing>, <placeholder>, <configured:N chars>, no leak, None
10. `TestMissingEnvVars` (5 tests) — set vars, unset vars, placeholder vars, empty list, mix
11. `TestPipelineCoreConstants` (8 tests) — COMBINED_SCORE_WEIGHTS suma=1.0, keys, positivos; CLIENT_FORBIDDEN_COLUMNS no vacío, tiene score_total/combined/cluster/ml_scores

**Verificación**:
- `python -m pytest tests/test_config.py -v --tb=short` → **79 passed in 0.14s** (PASS)

**Decisiones**:
- Se incluyeron tests de pipeline_core (COMBINED_SCORE_WEIGHTS, CLIENT_FORBIDDEN_COLUMNS) por ser constantes de configuración relacionadas
- Se usó `unittest.mock.patch.dict` para tests de env vars sin contaminar el entorno real
- Tests parametrizados con `@pytest.mark.parametrize` para las 9 dimensiones de scoring

### Sesión 5 — 2026-03-28 — Feature 5: test_utils

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_utils.py`: 87 tests exhaustivos para utils.py

**Tests por clase** (87 total):
1. `TestNormalizarRut` (20 tests) — con/sin puntos, con/sin guión, K mayúscula/minúscula, espacios, vacío, None, tipo incorrecto, límites de longitud (5-10 dígitos), RUTs reales
2. `TestExtraerRutDeId` (10 tests) — formato OCDS CL-RUT, directo, sin guión, texto random, vacío, None, k minúscula, números cortos, RUT embebido
3. `TestTipoLicitacion` (11 tests) — LP/LE/L1/LR/LQ, Otro, minúsculas, mixed case, paréntesis, None, numérico
4. `TestIsPersonaNatural` (18 tests) — empresas (CONSTRUCTORA, SERVICIOS, SPA, EIRL, S.A., INVERSIONES), personas (1-4 palabras), pipe con empresa/persona, 5 palabras=False, vacío, NaN, None, acentos empresa/persona, pipe con muchas palabras
5. `TestFormatoClp` (13 tests) — billones, millones, miles, cero, NaN, None, np.nan, negativo, montos típicos
6. `TestSafeGet` (12 tests) — valor numérico/string, NaN con/sin default, np.nan, None, columna inexistente, cero, False (numpy.bool_), string vacío, lista
7. `TestPrintHeader` (3 tests) — output contiene texto, separadores, vacío no crashea

**Verificación**:
- `python -m pytest tests/test_utils.py -v --tb=short` → **87 passed in 0.15s** (PASS)

**Decisiones**:
- Test `test_false_no_es_none` usa `==` en vez de `is` porque pandas Series retorna `numpy.bool_` que no es el singleton Python `False` — bug lógico corregido en test
- Cobertura supera los ~50 tests del plan (87 total) para cubrir todos los edge cases relevantes

### Sesión 6 — 2026-03-28 — Feature 6: test_scoring_functions

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_scoring.py`: 202 tests exhaustivos para 05_score_leads.py

**Tests por clase** (202 total):
1. `TestScoreInRangeNoOptimal` (14 tests) — inside/edges/below/above gradient, NaN/None→0, lower/upper_bound=None, negative clipped, zero-width range
2. `TestScoreInRangeWithOptimal` (27 tests incl. parametrized) — optimal→100, edges→85, midway gradient, below/above decay, clipped optimal, div/0, non-negative sweep, max-100 sweep
3. `TestScoreActividad` (8 tests) — 0→0, 1→low, 5→≥85, 10→mid, 15→100, 25→mid, 50→0, NaN→0
4. `TestScoreTamano` (14 tests) — MOP mayor 2da/segunda→100, 3ra/tercera→80, 1ra/primera→60, unknown→70, menor→50, monto in range, optimal 500M, adjudicado fallback, no data→20, NaN→20, case insensitive
5. `TestScoreWinRate` (9 tests) — <2 bids→30, optimal 0.25→100, wr=0→0, 0.5→<85, 0.8→0, 0.15→≥85, 0.35→≥85, NaN→0
6. `TestScoreRecencia` (8 tests) — 0→100, 100→>90, 365→≥85, 730→<85, 1460→0, 9999→0, NaN→0, missing col→0
7. `TestScoreValor` (7 tests) — 0→20, NaN→20, 66M→≥85, 500M→100, 5B→0, 200M→mid, 1M→0
8. `TestScoreCompetencia` (7 tests) — 0→30, NaN→30, 5→≥85, 10→100, 30→0, 7→mid, 1→0 (at lower_bound)
9. `TestScoreOportunidad` (8 tests) — no data→30, high→100, moderate→50, zero bids→safe, NaN lost/rivals, only rivals→25, capped 100
10. `TestScoreEspecializacion` (7 tests) — all LP→100, all L1→20, all LE→70, mix→85, zero→30, NaN→30, capped 100
11. `TestScoreRegion` (11 tests) — RM→100, Valparaíso→90, Biobío→80, Araucanía→70, Los Lagos→60, other→40, empty→50, NaN→50, None→50, partial match, case insensitive
12. `TestScoreDigital` (11 tests) — web+email→30, web→50, email→50, phone→60, nothing→70, gm_web/ocds_email/gm_telefono, combinations, missing fields→70
13. `TestCalculateScores` (9 tests) — produces score_total, range [0,100], all dim columns, weighted sum verification, preserves columns, row count, single row, dims match config
14. `TestAllScoresBounded` (55 parametrized tests) — sweep de valores extremos para 8 funciones
15. `TestWeightsConsistency` (6 tests) — sum=1.0, 9 dims, scorer functions exist, ideal ranges consistent, recencia max, regiones top

**Verificación**:
- `python -m pytest tests/test_scoring.py -v --tb=short` → **202 passed in 0.44s** (PASS)

**Decisiones**:
- Se usó `import_module("05_score_leads")` por el nombre de archivo numérico que no es importable directo
- Helpers `_row()` y `_drow()` para crear datos de test rápidamente con defaults razonables
- Tests paramétricos en `TestAllScoresBounded` barren valores extremos y NaN para cada scoring function
- Se corrigió expectativa de `test_1_at_lower_bound` (competencia): lower_bound=1 da score=0, no >0
- Cobertura 202 tests supera los ~120 del plan gracias a parametrización exhaustiva
