# Contexto del Proyecto — IngenIA Licitaciones

## Resumen
Plataforma B2B de inteligencia competitiva para constructoras chilenas que licitan en Mercado Público.
Fundador: Sebastián Cortés, Ing. Civil UCN. Canal principal: WhatsApp cold outreach.

## Estructura de carpetas

```
licitaciones/                          # raíz del proyecto
├── lead_scoring/                      # pipeline principal (26 scripts Python)
│   ├── config.py                      # configuración central
│   ├── utils.py                       # utilidades compartidas
│   ├── pipeline_core.py               # core: scoring, ranking, CRM
│   ├── pipeline_validation.py         # contratos de datos, seguridad cliente
│   ├── 01_download_bulk.py            # descarga CSVs ChileCompra
│   ├── 02_scrape_mop.py              # scraping MOP
│   ├── 03_filter_construction.py      # filtra construcción (UNSPSC 72)
│   ├── 04_build_company_db.py         # company_database.parquet
│   ├── 05_score_leads.py             # scoring 9 dimensiones
│   ├── 05b_ml_scoring.py             # XGBoost + K-Means
│   ├── 06_enrich_contacts.py          # Google Maps enriquecimiento
│   ├── 07_export_output.py            # exporta Excel/CSV/WhatsApp
│   ├── 08_loss_analysis.py            # análisis de derrotas
│   ├── 09_tender_matcher.py           # match licitaciones → leads
│   ├── 10_visualizations.py           # gráficos
│   ├── 11_generate_diagnostic_pdf.py  # PDF por RUT
│   ├── 12_monitor_api.py             # monitor diario
│   ├── 14_operational_preflight.py    # validación entorno
│   ├── 15_env_hygiene.py             # limpieza .env
│   ├── 16_verify_contacts.py          # verificar contactos
│   ├── validate_outputs.py            # validar outputs cliente-safe
│   ├── data/
│   │   ├── raw/                       # CSVs bulk (gitignored)
│   │   ├── filtered/                  # parquets procesados (gitignored)
│   │   │   ├── company_database.parquet
│   │   │   ├── leads_ranked.parquet
│   │   │   ├── leads_ml_ranked.parquet
│   │   │   ├── leads_enriched.parquet
│   │   │   ├── clusters.parquet
│   │   │   ├── tenders_construction.parquet
│   │   │   ├── tenderers_construction.parquet
│   │   │   ├── suppliers_construction.parquet
│   │   │   ├── parties_construction.parquet
│   │   │   └── awards_construction.parquet
│   │   └── output/                    # exports (gitignored)
│   │       ├── leads_final.xlsx / .csv
│   │       ├── leads_verificados.csv / .xlsx
│   │       ├── crm_leads.xlsx / .csv
│   │       ├── loss_analysis.parquet
│   │       ├── mensajes_whatsapp.txt
│   │       ├── mensajes_whatsapp_v2.txt
│   │       ├── mensajes_wsp_v3.txt
│   │       ├── mensajes_wsp_v4.txt
│   │       └── diagnosticos/ graficos/
│   ├── requirements-dev.txt           # deps: -r requirements.txt + pytest
│   └── .env.example
├── generar_mensajes_v3.py             # generador WSP v3
├── generar_mensajes_v4.py             # generador WSP v4
├── verificar_mensajes.py              # verificación v1
├── verificar_mensajes_v2.py           # verificación v2
├── monitor_licitaciones.py            # monitor standalone
├── filter.py                          # filtro básico
├── commercial/                        # docs comerciales
├── audit/                             # auditoría
└── autonomo/                          # este directorio
```

## Configuración clave (config.py)

### Scoring: 9 dimensiones (suman 1.0)
```python
SCORING_WEIGHTS = {
    "actividad":       0.20,  # 5-15 bids/año ideal
    "tamano":          0.14,  # categoría MOP
    "win_rate":        0.12,  # 15-35% ideal, óptimo 25%
    "recencia":        0.12,  # <365 días ideal
    "valor":           0.12,  # $66M-$500M CLP
    "competencia":     0.10,  # 5-10 competidores
    "oportunidad":     0.10,  # más derrotas = más oportunidad
    "especializacion": 0.06,  # LP ratio
    "region":          0.04,  # regiones top
}

IDEAL_RANGES = {
    "actividad": (5, 15),
    "win_rate": (0.15, 0.35),
    "recencia_dias": (0, 365),
    "valor_clp": (66_000_000, 500_000_000),
    "competencia": (5, 10),
}

RECENCIA_MAX_DAYS = 1460
REGIONES_TOP = [RM, Valparaíso, Biobío, Araucanía, Los Lagos]
```

### Score combinado (pipeline_core.py)
```python
COMBINED_SCORE_WEIGHTS = {
    "score_total": 0.70,
    "km_score": 0.15,
    "xgb_score": 0.15,
}
# Si falta km_score o xgb_score, se usa score_total como baseline neutral
```

### Columnas prohibidas para cliente
```python
CLIENT_FORBIDDEN_COLUMNS = {
    "score_total", "score_combined", "cluster", "cluster_perfil",
    "km_score", "xgb_score", "xgb_predicted_wr", "score_digital",
}
```

### Contratos de datos (pipeline_validation.py)
```python
PIPELINE_CONTRACTS = {
    "company_database": {
        "required": ["rut", "total_bids", "total_wins", "win_rate",
                      "monto_promedio", "dias_desde_ultima", "n_LP", "n_LE", "n_L1"],
        "unique": ["rut"],
        "ranges": {"win_rate": (0, 1)},
    },
    "leads_ranked": {
        "required": ["rut", "score_total", "rank"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "rank": (1, None), "win_rate": (0, 1)},
    },
    "leads_ml_ranked": {
        "required": ["rut", "score_total", "score_combined", "rank_ml"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "score_combined": (0, 100), "rank_ml": (1, None)},
    },
    "leads_enriched": {
        "required": ["rut", "score_total", "score_combined"],
        "unique": ["rut"],
        "ranges": {"score_total": (0, 100), "score_combined": (0, 100), "score_digital": (0, 100)},
    },
    "loss_analysis": {
        "required": ["rut", "total_participated", "total_won", "loss_rate"],
        "unique": ["rut"],
        "ranges": {"loss_rate": (0, 1)},
    },
}
```

## Bugs conocidos que DEBEN corregirse

1. **PATHS HARDCODED**: 6 archivos usan `C:/Seba/Nueva carpeta (2)/` — deben usar paths relativos o config.py:
   - generar_mensajes_v3.py (línea 20)
   - generar_mensajes_v4.py (línea 28)
   - verificar_mensajes.py (líneas 6, 13)
   - verificar_mensajes_v2.py (líneas 6, 13)
   - filter.py (línea 3)
   - monitor_licitaciones.py (línea 164)

2. **CSV EXPORT LEAK**: `07_export_output.py` línea 228 hace `df.to_csv(csv_path, index=False)` — exporta TODAS las columnas incluyendo scores internos. La versión Excel filtra columnas correctamente pero la CSV no.

3. **10_visualizations.py**: pesos mencionados en RETOMAR.md difieren de config.py (14%→15%, falta score_oportunidad). Verificar que use SCORING_WEIGHTS directamente.

4. **INDUSTRY_WR_MEDIAN = 0.22**: hardcoded en generar_mensajes_v3.py y v4.py. Debería venir de config o calcularse.

5. **requirements.txt**: No existe en lead_scoring/ (requirements-dev.txt hace `-r requirements.txt`).

6. **COMMERCIAL_PLAYBOOK.md**: Tiene paths `C:\Seba\Nueva carpeta (2)\` en links de documentos.

## Fórmulas de scoring (05_score_leads.py)

Cada dimensión devuelve 0-100. `score_in_range(value, ideal_min, ideal_max, lower_bound, upper_bound, optimal)`:
- Dentro del rango ideal: 100 (sin optimal) o 85-100 (con optimal, gradiente al pico)
- Fuera: decae linealmente hacia 0

Fórmulas específicas:
- `score_actividad`: score_in_range(bids, 5, 15, 0, 50, optimal=15)
- `score_tamano`: MOP categoría o monto proxy
- `score_win_rate`: score_in_range(wr, 0.15, 0.35, 0, 0.8, optimal=0.25), mín 30 si <2 bids
- `score_recencia`: invertido (score_in_range(-dias, -365, 0, -1460, 0, optimal=0))
- `score_valor`: score_in_range(monto, 66M, 500M, 1M, 5B, optimal=500M)
- `score_competencia`: score_in_range(comp, 5, 10, 1, 30, optimal=10)
- `score_oportunidad`: min(100, min(70, loss_rate×140) + min(30, n_rivals×5))
- `score_especializacion`: min(100, ratio_lp×100 + ratio_le×50 + 20)
- `score_region`: 100-90-80-70-60 para top5, 40 para resto, 50 sin dato

`score_total = Σ(score_dim × peso)`, clipped [0,100], rounded 1 decimal.
`score_combined = 0.70×score_total + 0.15×km_score + 0.15×xgb_score`

## Datos de leads (para mensajes v4)

Insight types v4 por prioridad:
1. rival_fuerte (rival ganó 3+)
2. rival_recurrente (rival ganó 2)
3. win_rate_gap_LP (n_LP>=5 AND WR<20%)
4. lp_alto (n_LP>=5)
5. inactivo (>=180 días)
6. wr_bajo_lp (WR<20% AND n_LP>=3)
7. loss_concentrado (loss_rate>=40% AND total_lost>=5)
8. wr_bajo (WR<19%)
9. rival_unico (rival>0 AND total_lost>=3)
10. default

`INDUSTRY_WR_MEDIAN = 0.22`

## Convenciones de testing

- Framework: pytest (ya en requirements-dev.txt)
- Tests en: `lead_scoring/tests/`
- Ejecutar: `cd lead_scoring && python -m pytest tests/ -v`
- Los tests verifican el CÓDIGO, no los datos. Si un test falla, el bug está en el código pipeline, no en el test.
- Usar datos reales de los parquets cuando sea posible para tests de integración
- Usar DataFrames sintéticos para tests unitarios
- No mockear la base de datos — usar datos reales filtrados
- Cada scoring function debe probarse con: valor ideal (100), valor mínimo (0), NaN (0 o default), edge cases

## Estrategia de cold outreach (para Phase B)

### Principios de conversión WhatsApp B2B Chile
1. **IMPACTO PRIMERO**: La primera línea debe causar una reacción emocional. No "soy X y hago Y" sino "encontré Z sobre su empresa".
2. **DATO CONCRETO**: Mencionar algo que el prospecto NO puede ver fácilmente en Mercado Público (rival dominante, patrón de pérdida, brecha de WR vs industria).
3. **BREVEDAD**: Máximo 4-6 líneas antes del CTA. Si necesitan scroll, no lo leen.
4. **CTA PREGUNTA**: Terminar con pregunta abierta que invite respuesta, no con "contáctenos".
5. **SIN VENTA**: No mencionar precio, servicio, ni "diagnóstico" en el primer mensaje. Solo el insight.
6. **TONO**: Profesional pero cercano. Tuteo con "usted" (Chile formal). Sin emojis. Sin "estimado/a".
7. **PERSONALIZACIÓN**: Cada mensaje debe tener al menos 2 datos específicos de la empresa.

### Estructura ganadora del mensaje (max 5 líneas + firma)
```
[Saludo con nombre], soy Sebastián de IngenIA Licitaciones.

[GOLPE: 1-2 líneas con dato concreto e impactante sobre su empresa]

[CONTEXTO: 1 línea que explica por qué esto importa]

[CTA: Pregunta abierta]

Sebastián Cortés
IngenIA Licitaciones
```

### Mensajes por tipo de insight — guía para v5

**rival_fuerte**: "{Rival} les ganó {N} de las últimas {M} que no se adjudicaron. Hay un patrón claro en cómo estructura propuestas. ¿Le interesa saber exactamente qué es?"

**rival_recurrente**: Similar pero con 2 victorias, tono de "patrón emergente".

**win_rate_gap_LP**: Enfatizar brecha en $ — "con {N} postulaciones LP a más de $66M y tasa de {X}%, están dejando contratos por valor de ${Y}M en manos de la competencia cada año."

**lp_alto**: Ángulo positivo si WR≥rubro, ángulo de mejora si WR<rubro.

**inactivo**: Urgencia — "sus rivales directos siguen postulando y ganando en su región."

**wr_bajo_lp/wr_bajo**: Cuantificar la brecha en puntos vs industria (22%).

**loss_concentrado**: "Hay un patrón común en esas pérdidas."

### Reglas absolutas
- NUNCA mencionar: score, cluster, ML, modelo, pipeline, ranking, algoritmo
- NUNCA usar lenguaje causal: "usted pierde porque..." → "los datos sugieren..."
- NUNCA enviar PDF gratis — el valor gratuito es texto en chat
- NUNCA llamar sin que el cliente lo pida
- SI hay nombre de contacto, usar primer nombre en saludo
- SI no hay nombre, usar "Hola," sin "estimado/a"

## NO TOCAR
- Archivos en data/raw/ (datos fuente, no modificar)
- .git/ (no manipular directamente)
- .env (contiene secretos reales — solo verificar, no exponer)
