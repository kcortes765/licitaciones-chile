# Progress — IngenIA Licitaciones Audit + Messages v5

## Estado: EN PROGRESO
## Features completadas: 12/20
## Última sesión: 2026-03-28
## Errores encontrados: 3 (corregidos)

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

### Sesión 7 — 2026-03-28 — Feature 7: test_pipeline_core

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_pipeline_core.py`: 80 tests exhaustivos para pipeline_core.py

**Tests por clase** (80 total):
1. `TestCombinedScoreWeights` (6 tests) — suma=1.0, keys score_total/km_score/xgb_score, all positive, score_total dominant
2. `TestLeadSourcePriority` (4 tests) — 3 entries, orden enriched>ml_ranked>ranked
3. `TestClientForbiddenColumns` (10 tests) — 8 columnas, parametrizado por columna esperada
4. `TestFindBestLeadsPath` (5 tests) — prioridad enriched>ml>ranked, None si vacío, custom priority (usa tmp_path)
5. `TestLoadBestLeadsDataframe` (3 tests) — FileNotFoundError si vacío, carga correcta, prioridad
6. `TestRecomputeScoreTotal` (8 tests) — produce score_total [0,100], consistente con weights, missing col→ValueError, no modifica original, all zeros→0, all hundreds→100
7. `TestRecomputeScoreCombined` (7 tests) — con ML signals usa pesos, sin ML→baseline=score_total, NaN ML→fallback, partial ML, missing score_total→ValueError, weights correctos
8. `TestAssignClusterProfile` (5 tests) — 4 categorías BAJO/REGULAR/BUENO/IDEAL, missing score_combined→ValueError, distribución percentiles ~40/30/20/10
9. `TestAssignRank` (5 tests) — empieza en 1, secuencial, descendente por score, custom columns, no modifica original
10. `TestResolveScoreColumn` (3 tests) — score_combined>score_total>ValueError
11. `TestResolveRankColumn` (3 tests) — rank_ml>rank>ValueError
12. `TestBuildCrmDataframe` (10 tests) — columnas esperadas, NO columnas prohibidas, rank_ml/rank/generado para prioridad, canal WhatsApp default/custom, estado Pendiente, tender info, row count
13. `TestContactCoverageSummary` (7 tests) — conteos correctos tel/email/web, columnas faltantes no crashean, DF vacío, todas las keys presentes
14. `TestSeriesOrDefault` (4 tests) — columna existente, missing→default, preserva índice, DF vacío

**Verificación**:
- `python -m pytest tests/test_pipeline_core.py -v --tb=short` → **80 passed in 0.34s** (PASS)

**Decisiones**:
- Se creó helper `_make_scored_df()` para generar DataFrames con todas las 9 columnas score_{dim} + score_total calculado con pesos reales
- Se usó `tmp_path` fixture de pytest para tests de filesystem (find_best_leads_path, load_best_leads_dataframe)
- Tests cubren inmutabilidad (no modifica DF original) en recompute_score_total, recompute_score_combined, assign_cluster_profile, assign_rank
- Cobertura 80 tests supera los ~45 del plan gracias a parametrización y edge cases adicionales

### Sesión 8 — 2026-03-28 — Feature 8: test_validation

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_validation.py`: 129 tests exhaustivos para pipeline_validation.py

**Tests por clase** (129 total):
1. `TestPipelineContracts` (27 tests) — 6 artifacts existen, cada uno tiene required/ranges, columnas específicas por contrato, unique keys, ranges son tuples
2. `TestValidateDataframeContract` (22 tests) — DataFrame válido→vacío para los 6 contratos, columnas faltantes, duplicados, valores fuera de rango, RUT nulos/NaN, contrato desconocido→KeyError, rank sin upper bound, NaN ignorados, múltiples issues
3. `TestAssertDataframeContract` (2 tests) — wrapper que lanza ValueError
4. `TestClientForbiddenPatterns` (20 tests) — score_total/combined/actividad/region matchean, cluster/cluster_perfil matchean, xgb_*/km_* matchean, lead ideal/rank_position matchean, score_digital NO matchea (excepción regex), nombre/empresa/rut NO matchean, case insensitive, embedded en oraciones
5. `TestAssertClientSafeColumns` (10 tests) — columnas limpias OK, score_total/combined/cluster/xgb/km→ValueError, score_digital no bloquea, allowed_columns override, múltiples prohibidas, DF vacío OK
6. `TestAssertClientSafeText` (8 tests) — texto limpio OK (fixture), dirty text raises, score_total/xgb_predicted_wr/cluster/km_score en texto→ValueError, vacío OK, texto normal OK
7. `TestAssertClientSafeJson` (7 tests) — payload limpio/vacío/lista OK, score_total/nested/value/cluster→ValueError
8. `TestAssertClientSafeBinary` (6 tests) — PDF limpio OK, score_total/cluster/xgb en binario→ValueError, vacío OK, binario puro OK
9. `TestWriteRunManifest` (10 tests) — JSON válido, campos requeridos, command/source/outputs almacenados, details default/custom, ISO timestamp, crea directorios padre, sobreescribe existente
10. `TestWriteValidationReport` (5 tests) — JSON válido, preserva estructura, crea directorios, unicode, vacío
11. `TestExtractTextLikeChunks` (5 tests) — extrae texto legible, vacío, binario puro, chunk mínimo 4 chars
12. `TestScanTextForbidden` (5 tests) — retorna lista, vacío, múltiples matches, palabra parcial no matchea, case insensitive

**Verificación**:
- `python -m pytest tests/test_validation.py -v --tb=short` → **129 passed in 0.42s** (PASS)

**Decisiones**:
- Se crearon helpers `_valid_*_df()` para generar DataFrames válidos por cada contrato, reutilizados en múltiples tests
- Se usó `tmp_path` fixture de pytest para tests de filesystem (write_run_manifest, write_validation_report, assert_client_safe_binary)
- Se testearon funciones internas `_scan_text_forbidden` y `_extract_text_like_chunks` para cobertura completa
- Cobertura 129 tests supera ampliamente los ~60 del plan gracias a parametrización y edge cases adicionales

### Sesión 9 — 2026-03-28 — Feature 9: test_data_contracts

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_data_contracts.py`: 57 tests sobre datos reales en parquets

**Tests por clase** (57 total):
1. `TestCompanyDatabase` (12 tests) — columnas requeridas, RUTs únicos, sin RUTs nulos, win_rate [0,1], total_bids>=0, total_wins>=0, total_wins<=total_bids, monto_promedio>=0, dias_desde_ultima>=0, n_LP/n_LE/n_L1>=0, pasa contrato pipeline, >100 filas
2. `TestLeadsRanked` (10 tests) — columnas requeridas, RUTs únicos, score_total [0,100], rank desde 1 secuencial sin huecos, 9 dimensiones de score presentes y en [0,100], win_rate [0,1], pasa contrato, score_total recomputable (tolerancia 0.5)
3. `TestLeadsMlRanked` (11 tests) — columnas requeridas, RUTs únicos, score_combined [0,100], score_total [0,100], rank_ml desde 1 secuencial, xgb_score [0,100], km_score [0,100], pasa contrato, score_combined recomputable, cluster_perfil tiene 4 categorías válidas
4. `TestLeadsEnriched` (9 tests) — columnas requeridas, RUTs únicos, score_digital [0,100], columnas de contacto (telefono/email/web), score_total y score_combined [0,100], pasa contrato, es subconjunto de ml_ranked, al menos algunos contactos existen
5. `TestLossAnalysis` (9 tests) — columnas requeridas, RUTs únicos, loss_rate [0,1], total_participated>=0, total_won>=0, total_won<=total_participated, total_lost_loss>=0, pasa contrato, loss_rate consistente con total_lost_loss/total_participated
6. `TestCrossDatasetConsistency` (6 tests) — ranked⊂company_db, ranked<=company_db en tamaño, ml_ranked==ranked en tamaño, enriched⊂ml_ranked, score_total recomputable desde dims (>=99%), score_combined recomputable (>=99%)

**Verificación**:
- `python -m pytest tests/test_data_contracts.py -v --tb=short` → **57 passed in 0.96s** (PASS)

**Decisiones**:
- Skip markers definidos localmente (no se puede importar directamente de conftest.py por la mecánica especial de pytest)
- Se usaron paths de config.py (FILTERED_DIR, OUTPUT_DIR) para consistencia con el pipeline
- loss_analysis usa `total_lost_loss` como columna de pérdidas (diferente de `total_lost` del dataset base)
- Tests de recomputación usan tolerancia 0.5 para score_total y score_combined, con umbral de >=99% de filas consistentes
- Tests de consistencia cross-dataset verifican que los datasets se encadenan correctamente (company_db → ranked → ml_ranked → enriched)

### Sesión 10 — 2026-03-28 — Feature 11: test_messages

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_messages.py`: 125 tests exhaustivos para generar_mensajes_v4.py y verificar_mensajes_v2.py

**Archivos modificados** (bug fix):
- `generar_mensajes_v4.py`: Corregido regex en humanizar() y limpiar_rival() — `\b` trailing impedía match de E.I.R.L. y S.A.
- `generar_mensajes_v3.py`: Misma corrección de regex

**Tests por clase** (125 total):
1. `TestHumanizar` (15 tests) — title case, removes SPA/LTDA/LIMITADA/EIRL/E.I.R.L./S.A., pipe→comercial, None/NaN/empty/numeric→str, whitespace
2. `TestLimpiarRival` (9 tests) — cleaning, pipe, empty/None/whitespace/NaN→"", removes suffixes, title case
3. `TestPct` (8 tests) — 0.22→"22%", 0→"0%", 1.0→"100%", rounding up/down, format
4. `TestMeses` (9 tests) — 180→6, 365→12, 30→1, 0→0, rounding, float/string input, returns int
5. `TestElegirInsightRivalFuerte` (5 tests) — cnt≥3, body contains rival name and count, has CTA
6. `TestElegirInsightRivalRecurrente` (3 tests) — cnt≥2, not fuerte, body mentions rival
7. `TestElegirInsightWinRateGapLP` (5 tests) — n_LP≥5 AND wr<0.20, boundary, gap points, LP count
8. `TestElegirInsightLpAlto` (4 tests) — n_LP≥5 with wr≥0.20, above/at/below industry, body
9. `TestElegirInsightInactivo` (5 tests) — dias≥180, boundary, body has months, priority over wr_bajo_lp
10. `TestElegirInsightWrBajoLp` (3 tests) — wr<0.20 AND n_LP≥3, high LP, not if LP<3
11. `TestElegirInsightLossConcentrado` (3 tests) — loss_rate≥0.40 AND total_lost≥5, boundary
12. `TestElegirInsightWrBajo` (3 tests) — wr<0.19, boundary, body has stats
13. `TestElegirInsightRivalUnico` (3 tests) — rival AND total_lost≥3, body mentions rival, not if few losses
14. `TestElegirInsightDefault` (3 tests) — fallback case, has stats and CTA
15. `TestInsightPriority` (5 tests) — rival_fuerte>all, recurrente>LP, gap>lp_alto, inactivo>wr_bajo_lp, zero→default
16. `TestInsightEdgeCases` (5 tests) — NaN win_rate, None rival, zero everything, missing fields, all insights have required keys
17. `TestForbiddenTerms` (3 tests) — no score/cluster/ML/modelo/pipeline/algoritmo/ranking in any message/cuerpo/CTA
18. `TestGenerarMensaje` (8 tests) — with/without contact, empty/short name, firma, CTA question, multiword name
19. `TestGenerarWspLink` (7 tests) — +56 prefix, without prefix, float phone, URL encoding, leading zero
20. `TestGetRivalAliases` (5 tests) — basic, pipe, empty, None, "nan"
21. `TestNameMatches` (6 tests) — exact, partial both ways, no match, case insensitive, empty aliases
22. `TestConstants` (4 tests) — INDUSTRY_WR_MEDIAN=0.22, type float, FIRMA has name and company
23. `TestIntegrationRealData` (4 tests) — 10 leads insight consistent, no forbidden terms, CTA question, ≥3 insight types

**Bug encontrado y corregido**:
- **Regex `\b` trailing en humanizar/limpiar_rival**: La regex `\b(SPA|LTDA|...|E\.I\.R\.L\.|S\.A\.|SA)\b\.?$` no matcheaba `E.I.R.L.` ni `S.A.` porque `\b` requiere transición word↔non-word, pero `.` es non-word y al final de string `\b` falla. Fix: remover `\b` trailing → `\b(...)\.?$`. Corregido en v3 y v4.

**Verificación**:
- `python -m pytest tests/test_messages.py -v --tb=short` → **125 passed in 0.18s** (PASS)

**Decisiones**:
- Funciones de verificar_mensajes_v2.py (get_rival_aliases, name_matches) copiadas localmente al test para evitar ejecución del módulo completo que hace I/O a nivel de módulo
- Paths definidos localmente en el test (no importados de conftest.py por la mecánica de pytest)
- Test `test_zero_everything` ajustado: wr=0 < 0.19 → wr_bajo es correcto (no default)
- Cobertura 125 tests supera ampliamente los ~80 del plan gracias a edge cases y tests de prioridad

### Sesión 11 — 2026-03-28 — Feature 12: test_integration

**Estado**: COMPLETADA

**Archivos creados**:
- `lead_scoring/tests/test_integration.py`: 39 tests de integración end-to-end con datos reales

**Tests por clase** (39 total):
1. `TestCalculateScoresOnRealData` (4 tests) — score_total [0,100], 9 dims creadas y en rango, suma ponderada correcta, row count preservado
2. `TestRecomputeScoreTotalConsistency` (3 tests) — recompute ≈ original (tolerancia 0.5, ≥99%), recomputado en [0,100], dims en [0,100]
3. `TestRecomputeScoreCombinedConsistency` (2 tests) — recompute combined ≈ original, en [0,100]
4. `TestDatasetSizeRelationships` (4 tests) — ranked > enriched, ranked == ml_ranked, ranked ⊂ company_db, enriched ⊂ ml_ranked
5. `TestCrmExportSafety` (4 tests) — CRM sin columnas prohibidas, columnas esperadas, pasa client-safe, ml_ranked→CRM limpio
6. `TestFullScoreFlow` (2 tests) — cadena completa scores→combined→cluster→rank, sin ML combined≈score_total
7. `TestScoreTotalFromDims` (1 test) — suma ponderada almacenada == recalculada (≥99% filas)
8. `TestAssignRankOnRealData` (5 tests) — rank empieza en 1, secuencial sin huecos, mayor score→menor rank, rank_ml idem
9. `TestPipelineContracts` (5 tests) — company_db/leads_ranked/ml_ranked/enriched/loss_analysis pasan contratos
10. `TestCoverageReport` (5 tests) — keys esperadas, total=len(df), conteos ≥0, conteos ≤ total, no crashea con ranked
11. `TestResolveColumnsOnRealData` (4 tests) — resolve score/rank en ml_ranked y ranked

**Verificación**:
- `python -m pytest tests/test_integration.py -v --tb=short` → **39 passed in 0.96s** (PASS)

**Decisiones**:
- Todos los tests usan `@pytest.mark.skipif` para saltar si los parquets no existen
- Se usan datos reales completos (no solo head) para tests de consistencia y contratos
- Para tests de calculate_scores se usa head(50-100) para mantener velocidad razonable
- Tolerancia de 0.5 puntos y ≥99% de filas para recompute tests (consistente con test_data_contracts)
- 39 tests superan los ~30 del plan gracias a cobertura adicional en ranking y resolve columns
