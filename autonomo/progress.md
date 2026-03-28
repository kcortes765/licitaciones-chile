# Progress — IngenIA Licitaciones Audit + Messages v5

## Estado: EN PROGRESO
## Features completadas: 4/20
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
