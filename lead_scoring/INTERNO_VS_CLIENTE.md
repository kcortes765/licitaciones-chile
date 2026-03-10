# Separacion Datos Internos vs Cliente

## REGLA PRINCIPAL
NUNCA mezclar datos internos con lo que ve el cliente.

---

## DATOS INTERNOS (solo para nosotros)

Estos datos NUNCA deben aparecer en PDFs, mensajes WhatsApp, ni archivos
que puedan llegar al cliente:

| Dato | Variable | Por que es interno |
|------|----------|-------------------|
| Score combinado | `score_combined` | Revela como priorizamos leads |
| Score ML (XGBoost) | `xgb_score`, `xgb_predicted_wr` | Modelo predictivo interno |
| Score K-Means | `km_score` | Clustering interno |
| Cluster/perfil | `cluster_perfil`, `cluster` | Etiquetas tipo "LEAD IDEAL" |
| Ranking interno | `rank_position` | Posicion en nuestro ranking |
| Sub-scores | `score_actividad`, `score_tamano`, etc. | 9 dimensiones de scoring |
| Score digital | `score_digital` | Completitud de datos de contacto |
| Oportunidad | `score_oportunidad` | Score basado en derrotas |

### Donde viven estos datos
- `leads_ml_ranked.parquet` (5,232 empresas con scores)
- `leads_enriched.parquet` (top 100 con scores + contacto)
- `loss_analysis.parquet` (top 100 con loss + scores)

---

## DATOS CLIENTE (ok para mostrar)

Derivados de datos publicos de ChileCompra/Mercado Publico:

| Dato | Variable | Fuente publica |
|------|----------|---------------|
| Win rate | `win_rate` | Bids vs wins en ChileCompra |
| Total licitaciones | `total_bids` | Conteo publico |
| Total adjudicadas | `total_wins` | Conteo publico |
| Monto total/promedio | `monto_total`, `monto_promedio` | Montos de ChileCompra |
| Region | `region` | Dato de registro |
| Rivales | `top_rival_*`, `n_distinct_rivals` | Cruce publico |
| Derrotas | `total_lost`, `loss_rate` | Derivado de datos publicos |
| Tipo licitacion | `n_L1`, `n_LE`, `n_LP` | Clasificacion ChileCompra |
| Categoria MOP | `categoria_mop`, `tipo_mop` | Registro MOP publico |
| Percentil win rate | Calculado vs 4,408 activas | Estadistica de mercado |
| Dias desde ultima | `dias_desde_ultima` | Derivado de fechas publicas |

### Donde se muestran
- **PDF diagnostico** (6 paginas)
- **Mensaje WhatsApp** (solo nombre rival + conteo)
- **notas_ia.json** (datos para personalizar PDF)

---

## RADAR CHART: Percentiles Client-Facing

El radar del PDF muestra 8 dimensiones calculadas como **percentil vs el mercado**
(entre 4,408 constructoras activas), NO scores internos:

| Dimension en radar | Calculo | Significado para el cliente |
|---|---|---|
| Win Rate | Percentil de win_rate | "Gano mas que X% del mercado" |
| Volumen | Percentil de total_bids | "Licito mas que X% del mercado" |
| Adjudicaciones | Percentil de total_wins | "Gane mas contratos que X%" |
| Monto | Percentil de monto_promedio | "Mis obras son mas grandes que X%" |
| Diversificacion | 0/33/66/100 segun tipos usados | "Compito en 1, 2 o 3 segmentos" |
| Competidores | Percentil de n_distinct_rivals | "Enfrento mas rivales que X%" |
| Resiliencia | Inversa de loss_rate vs mercado | "Pierdo menos que X%" |
| Actividad reciente | Percentil de dias_desde_ultima (inv) | "Estoy mas activo que X%" |

---

## ARCHIVOS CLIENT-FACING: Checklist

Antes de enviar cualquier archivo al cliente, verificar:

- [ ] PDF: NO contiene "score", "cluster", "LEAD IDEAL", "ML", "ranking interno"
- [ ] notas_ia.json: NO contiene `score`, `rank`, `total_ranked`, `cluster`
- [ ] FICHA_LEAD.txt: NO contiene "Score ML"
- [ ] mensaje_whatsapp.txt: Solo nombre rival + conteo (ya esta limpio)
- [ ] Carpeta outreach: NO incluir archivos .parquet ni .xlsx internos

---

## HISTORIAL DE CORRECCIONES

- 2026-03-05: Detectado que radar usaba scores internos (score_actividad etc).
  Corregido a percentiles client-facing vs mercado.
- 2026-03-05: Removido score, cluster, rank, total_ranked de notas JSON.
- 2026-03-05: Removido "Score ML" de FICHA_LEAD.txt (3 fichas).
