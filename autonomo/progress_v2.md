# Progress — Output Layer Modo Dios

## Estado: EN PROGRESO
## Features completadas: 8/11
## Ultima sesion: 2026-03-28
## Errores encontrados: 0

---

## Log de sesiones

### Sesion 1 — 2026-03-28
**Feature 1: design_system** — COMPLETADA

Creado `lead_scoring/pdf_design.py` con sistema de diseno premium:
- Paleta de 21 colores premium (navy, blue, gold/copper accents, grises elegantes, semantic colors)
- MCOLORS dict para matplotlib (0-1 range)
- 10 estilos tipograficos (H1/H2/H3/body/body_b/small/caption/metric/metric_label/metric_sub)
- Layout grid A4 con 23 constantes (margins, columns, spacing, card dimensions)
- Clase PremiumPDF(FPDF) con 14 componentes reutilizables:
  - header_bar: barra navy full-width con titulo, subtitulo, detalle, branding
  - section_title: numero en circulo + titulo + linea dorada decorativa
  - metric_card / metric_cards_row: cards compactas con valor grande + label + subtexto
  - insight_callout: caja con borde izquierdo grueso, 4 estilos (info/warning/success/danger)
  - comparison_table: tabla con header navy, highlight column, filas alternas
  - simple_table: tabla liviana sin highlight
  - professional_footer: linea + branding + confidencial + paginacion
  - text_block: texto multi-linea con estilo
  - divider: separador horizontal (light/gold/navy)
  - spacer: espacio vertical configurable
  - cta_card: card navy+dorado para CTA/servicios
  - embed_chart: insertar graficos matplotlib con caption
  - pricing_tier: card de tier con features
  - badge: etiqueta pequena estilo tag
- Helpers: _s() (Latin-1 safe), _name(), _money(), _pct()
- Verificacion: `from pdf_design import *` OK, todos los componentes testeados

Archivos creados: `lead_scoring/pdf_design.py`

### Sesion 2 — 2026-03-28
**Feature 2: pdf_charts_premium** — COMPLETADA

Creado `lead_scoring/pdf_charts.py` con 7 funciones de graficos premium publicacion-ready:
- `gen_win_rate_gauge`: gauge semicircular con zonas rojo/amarillo/verde, aguja, marker promedio rubro
- `gen_radar_premium`: radar 8 ejes con relleno semi-transparente, linea P50, valores en cada punto
- `gen_competitor_bars`: barras horizontales degradado rojo->naranja, mini-barra gris contexto, conteo + %
- `gen_timeline`: linea temporal participaciones (fecha vs monto, color gano/perdio), linea tendencia (NUEVO)
- `gen_market_position`: scatter WR vs total_bids, empresa destacada punto grande+borde dorado, cuadrantes
- `gen_opportunity_waterfall`: waterfall ingresos actuales -> +5pp -> prom rubro -> top10% -> potencial
- `gen_tipo_donut`: donut LP/LE/L1 con total en centro, leyenda debajo

Caracteristicas:
- DPI 200, fondo blanco, tipografia consistente
- Usa MCOLORS y COLORS de pdf_design.py
- _style_ax() helper para estilo base consistente
- Manejo robusto de datos faltantes (fallbacks elegantes)
- 7/7 charts testeados OK con datos sinteticos

Archivos creados: `lead_scoring/pdf_charts.py`

### Sesion 3 — 2026-03-28
**Feature 3: pdf_generator_v2_pages_1_3** — COMPLETADA

Creado `lead_scoring/generate_pdf_v2.py` con las 3 primeras paginas del PDF diagnostico premium:

**PAGE 1 — Portada:**
- header_bar navy full-width con nombre empresa, RUT, region, fecha
- Badge "Diagnostico Competitivo Premium"
- 5 metric cards en fila: Licitaciones, Adjudicadas, Win Rate (con color semantico), Monto Total Op., Rivales Unicos
- Resumen ejecutivo personalizado (4-5 lineas con datos reales: WR vs rubro, rival dominante o inactividad, escala operacion)
- Indice del informe (4 secciones con numeros en circulo + descripcion)

**PAGE 2 — Desempeno vs Mercado:**
- Section title con numero + linea dorada
- Win rate gauge semicircular (gen_win_rate_gauge) + texto interpretativo a la derecha
  - Comparacion con promedio y top 10%, gap en puntos, estimacion de licitaciones extra
  - Percentil exacto (posicion X de Y empresas)
- Radar chart 8 dimensiones (gen_radar_premium) + texto interpretativo
  - Mayor fortaleza y mayor debilidad identificadas automaticamente
  - Top 4 dimensiones con indicador +/- y color semantico
- Market position scatter (gen_market_position) full-width con caption

**PAGE 3 — Inteligencia Competitiva:**
- Competitor bars chart (gen_competitor_bars) con degradado y contexto
- Detalle por rival: nombre, veces ganadas, % de derrotas
- NUEVO: tabla detallada de licitaciones perdidas vs rival principal
  - Cruza tenderers, suppliers, tenders, awards parquets
  - Muestra: codigo, fecha, tipo (LP/LE/L1), monto, titulo
  - Hasta 6 licitaciones mas recientes
- Hallazgo clave en insight_callout (danger si rival>=3, warning si>=1)
- Tabla comparativa: Tu empresa vs Promedio rubro vs Top 10% (WR, licitaciones, monto, rivales)

**Funciones principales:**
- `load_data(rut)`: carga company, loss, industry, percentiles, wr_distribution, lost_tender_details
- `_load_lost_tender_details(rut, data)`: cruza 4 parquets para encontrar licitaciones perdidas vs rival
- `_generate_executive_summary(data)`: genera resumen ejecutivo personalizado segun datos
- `_build_page_1/2/3(pdf, data, tmp_dir)`: constructores de cada pagina
- `generate_diagnostic_v2(data, output_path)`: orquestador principal

**Verificacion:**
- `from generate_pdf_v2 import *` OK
- PDF generado para GUERCUT (132385-4): 213KB, 3 paginas con graficos
- Client-safe: sin score_total, score_combined, cluster, xgb_score, km_score, pipeline, algoritmo
- Usa pdf_design.py (componentes) y pdf_charts.py (graficos premium)
- Texto sanitizado con _s() para compatibilidad Latin-1

Archivos creados: `lead_scoring/generate_pdf_v2.py`

### Sesion 4 — 2026-03-28
**Feature 4: pdf_generator_v2_pages_4_6** — COMPLETADA

Agregadas paginas 4-6 a `lead_scoring/generate_pdf_v2.py`:

**PAGE 4 — Analisis Temporal y Sectorial:**
- Timeline chart (gen_timeline) con historial de participaciones (gano/perdio) full-width
- Texto interpretativo automatico segun dias de inactividad (activo/intermitente/inactivo)
- Donut chart (gen_tipo_donut) de distribucion LP/LE/L1 a la izquierda
- Texto interpretativo a la derecha: tipo dominante, implicancia estrategica
- Presencia regional con region principal de operacion
- Escala de operacion: monto promedio vs promedio rubro

**PAGE 5 — Costo de Oportunidad:**
- Waterfall chart (gen_opportunity_waterfall) full-width con caption
- Tabla de escenarios: +5pp WR, Promedio rubro, Top 10% — con adjudicaciones extra y monto CLP
- Callout prominente "$": "Cada punto de Win Rate = $XMM anuales para su empresa"
- Market position scatter reutilizado mostrando "donde esta vs donde podria estar"

**PAGE 6 — Recomendaciones y Siguiente Paso:**
- _generate_recommendations(): genera 4-5 recomendaciones ESPECIFICAS basadas en datos:
  - Rival dominante → analizar propuestas del rival
  - WR bajo promedio → cerrar brecha de X puntos
  - Inactividad → reactivar con monitoreo
  - Concentracion tipo → optimizar LP o diversificar a LP
  - Tasa perdida alta → analizar patrones de no adjudicacion
  - Siempre: monitoreo proactivo de oportunidades
- 3 pricing tiers con pricing_tier component (Diagnostico $190K, Competitivo $250K, Mensual $490K)
- CTA card navy+dorado con firma: Sebastian Cortes, Ing. Civil UCN
- Disclaimer legal al pie

**Funcion main() CLI:**
- `python generate_pdf_v2.py <RUT> [--dry-run] [--output PATH]`
- --dry-run: carga datos, valida, no genera PDF
- Muestra empresa, WR, licitaciones, fuente, tamanio PDF

**Verificacion:**
- `from generate_pdf_v2 import *` OK
- dry-run para GUERCUT (132385-4): DRY RUN EXITOSO
- PDF generado: 375 KB, 6 paginas con graficos premium
- Client-safe: 0 terminos prohibidos encontrados (score_total, cluster, km_score, etc.)
- Texto sanitizado con _s() para Latin-1

Archivos modificados: `lead_scoring/generate_pdf_v2.py`

### Sesion 5 — 2026-03-28
**Feature 5: generate_test_pdfs** — COMPLETADA

Generados 4 PDFs de prueba para empresas con diagnosticos existentes:

| Empresa | RUT | Size | Paginas | Client-Safe |
|---------|-----|------|---------|-------------|
| GUERCUT | 132385-4 | 384 KB | 6 | PASS |
| CONSTRUCTORA SYNEL SPA | 121265-9 | 387 KB | 6 | PASS |
| Mecvalves Ltda | 105243-8 | 387 KB | 6 | PASS |
| CONSTRUCCIONES HERRERA SPA | 137981-3 | 385 KB | 6 | PASS |

**Bug encontrado y corregido:**
- `_extract_text_like_chunks` en `pipeline_validation.py` extraia texto de bloques
  `stream...endstream` comprimidos (imagenes/fonts), causando falso positivo
  `km_w` en GUERCUT PDF (secuencia random en datos comprimidos de imagen).
- Fix: agregar `_STREAM_BLOCK_PATTERN` que elimina bloques stream antes de extraer
  chunks de texto. 129/129 tests de validation siguen pasando.

**Verificacion:**
- 4 PDFs generados en `data/output/diagnosticos_v2/`
- Todos >200KB (indica graficos incluidos correctamente)
- Todos con 6 paginas
- Todos pasan `assert_client_safe_binary`
- 864/864 tests del suite completo pasan

Archivos creados: `lead_scoring/data/output/diagnosticos_v2/*.pdf` (4 PDFs)
Archivos modificados: `lead_scoring/pipeline_validation.py` (fix falso positivo en binary scanner)

### Sesion 6 — 2026-03-28
**Feature 6: commercial_templates_premium** — COMPLETADA

Reescritos desde cero los 6 documentos comerciales en `commercial/` a nivel consultoria de elite:

**OFERTA_SERVICIO.md (7.7 KB, antes 2.2 KB):**
- Estructura: Problema (3 pain points sector construccion) → Solucion (con datos: 1.8M registros) → Metodologia (4 pasos: dato→analisis→insight→accion) → 3 tiers detallados con entregables, plazos y precios → Equipo (Sebastian Cortes, Ing. Civil UCN) → Casos de uso reales (4 ejemplos anonimizados) → Exclusiones
- Tono: consultoria de ingenieria, no freelancer

**PROPUESTA_BASE.md (6.1 KB, antes 2.2 KB):**
- Propuesta formal con: Resumen ejecutivo con placeholders [EMPRESA], Alcance detallado por tier (A/B/C), Tabla de entregables con formatos y frecuencia, Metodologia 4 pasos, SLA (tiempos de respuesta por tier), Exclusiones, Pricing, Condiciones de pago (permanencia minima 3 meses), Confidencialidad, Aceptacion

**TARIFARIO.md (3.0 KB, antes 0.5 KB):**
- Tabla comparativa de tiers con checkmarks (✓) por caracteristica
- 5 categorias: Analisis, Entregables, Soporte, Plazos
- Condiciones de pago en tabla
- Seccion "Valor agregado del Servicio Mensual" con ROI

**FOLLOWUP_SEQUENCE.md (5.3 KB, antes 1.8 KB):**
- 5 touchpoints: D0 WhatsApp, D2 Email, D5 Seguimiento, D10 Cierre, D30 Reactivacion
- Copy EXACTO listo para copiar-pegar en bloques de codigo
- Variables: [NOMBRE], [EMPRESA], [HALLAZGO], [DATO_CONCRETO], [RIVAL], [REGION]
- Manejo de respuestas: "Cuanto cuesta?", "Mandame info", "No me interesa"
- 6 reglas de la secuencia

**ANALISIS_GRATIS_TEMPLATE.md (2.9 KB, antes 0.7 KB):**
- Estructura narrativa: hallazgo → implicancia → pregunta
- Mini-diagnostico con: contexto cuantificado, hallazgo principal en narrativa (no lista), cuantificacion en pesos, 3 preguntas que el diagnostico completo responde, CTA con precio y plazo

**NDA_SIMPLE.md (4.7 KB, antes 1.9 KB):**
- Formato profesionalizado: partes con RUT y representante
- 9 secciones formales: Objeto, Definicion, Obligaciones (5 incisos), Exclusiones (5 incisos), Vigencia, Devolucion, Responsabilidad, Jurisdiccion, Firmas con campos completos
- Terminologia juridica chilena apropiada

**Verificacion:**
- 6 archivos OK, todos >500 bytes
- Promedio 4943 bytes (3.3x el tamano original promedio)
- Sin mencion de scores, clusters, ML, pipeline, algoritmos
- Tono consistente: consultoria de ingenieria de elite
- Pricing consistente: $190K/$250K/$490K en todos los documentos

Archivos modificados: `commercial/OFERTA_SERVICIO.md`, `commercial/PROPUESTA_BASE.md`, `commercial/TARIFARIO.md`, `commercial/FOLLOWUP_SEQUENCE.md`, `commercial/ANALISIS_GRATIS_TEMPLATE.md`, `commercial/NDA_SIMPLE.md`

### Sesion 7 — 2026-03-28
**Feature 7: guion_whatsapp_v2** — COMPLETADA

Reescrito desde cero `GUION-WHATSAPP.md` a nivel consultoria de elite (17,451 chars, antes ~5,200):

**Estructura del funnel (6 pasos):**

**PASO 1 — Mensaje cold:** No se toca. Viene del generador automatico (mensajes_wsp_v6.txt).

**PASO 2 — Enganche (3 casos):**
- Caso A (interes directo): Dato concreto de rival + patron + oferta de ejemplo puntual. Tono de ingeniero que encontro un patron, no vendedor.
- Caso B (curioso/esceptico): Presentacion como ingeniero civil UCN + escala de datos (1.8M registros) + hallazgo breve + oferta de ejemplo.
- Caso C (respuesta corta): Directo al Paso 3 sin pedir permiso.

**PASO 3 — Mini-analisis por chat (demo):**
- Estructura fija de 6-8 bullets verificados contra datos reales
- Campos: Tipo/Region/Monto | Adjudicador | Participantes | Criterio dominante | Factor decisivo | Patron rival | Oportunidad
- Cierre con ancla: "Esto es 1 licitacion. El diagnostico cubre las [N] donde han participado."
- NO incluir precio aqui — esperar que pregunten

**PASO 4 — Cierre y pricing:**
- Escenario A: Pregunta precio → $190K base con descripcion detallada del entregable (PDF 6 paginas, radar, rivales, costo oportunidad, recomendaciones)
- Escenario B: Acepta → datos de transferencia con monto IVA incluido ($226.100)
- Escenario C: Confirmacion de pago → mensaje corto profesional
- Escenario D: Tier avanzado → $250K para empresas grandes con extras (benchmark top 10%, estrategia por tipo)

**PASO 5 — Entrega PDF:**
- 3 hallazgos principales resumidos (ni mas ni menos)
- Apuntar a pagina especifica (p.5 costo oportunidad) para engagement
- No ofrecer llamada, no pedir feedback inmediato

**PASO 6 — Upsell mensual:**
- Timing: 24-48h despues de entrega (no inmediato)
- Copy: transicion natural de "foto fija" a "monitoreo continuo"
- 4 entregables semanales detallados: oportunidades, rivales, recomendacion, soporte
- $490K/mes sin permanencia
- Sub-respuesta para "que incluye exactamente?"

**OBJECIONES (6 reescritas con sofisticacion):**
1. "Es caro" → Contextualizar vs monto promedio de licitaciones del prospecto
2. "Lo veo despues" → Fijar fecha concreta en 2 semanas
3. "Es una IA?" → Analogia con herramientas de ingenieria (SAP2000/Presto), 1.8M registros
4. "Ya lo hacemos" → Diferencia entre leer bases propias vs cruzar todos los competidores
5. "No licitamos mucho" → Argumento inverso: mas razon para elegir bien donde participar
6. "Que garantia?" → Anclar en el mini-analisis ya entregado como prueba de calidad

**FOLLOW-UP (4 touchpoints con dato concreto):**
1. 48h: Win rate vs promedio region + cuantificacion en pesos del gap
2. 5 dias: Patron de rival con licitaciones recientes
3. 10 dias: Cierre elegante con "cada punto de WR = $XM anuales"
4. 30 dias: Reactivacion solo con dato fresco real (3 opciones: oportunidades nuevas, adjudicaciones rival, LP abiertas)

**10 reglas generales** incluyendo: dato concreto obligatorio, 0 terminos prohibidos, pricing fijo sin negociar, sin emojis, sin "estimado/a".

**Verificacion:**
- 17,451 caracteres (>5,000 requerido)
- 8/8 secciones presentes (PASO 1-6, OBJECIONES, SEGUIMIENTO)
- 0 terminos prohibidos (score_total, cluster, km_score, etc.)
- Pricing consistente: $190K/$250K/$490K
- Tono: ingeniero senior, no vendedor
- Todos los mensajes en bloques de codigo copy-paste ready

Archivos modificados: `GUION-WHATSAPP.md`

### Sesion 8 — 2026-03-28
**Feature 8: alerta_semanal_template** — COMPLETADA

Creado `lead_scoring/generate_weekly_alert.py` — generador de alerta semanal premium para clientes del servicio mensual ($490K/mes):

**Funciones de carga y perfil:**
- `load_client_profile(rut)`: carga datos del cliente desde parquets (enriched > ml > ranked > company_db), loss analysis (rivales top 3), perfil de filtrado (region, monto, tipos LP/LE/L1)
- `_get_preferred_types(company)`: determina tipos de licitacion preferidos segun historial

**Funciones de obtencion de licitaciones:**
- `fetch_recent_tenders(days=7)`: obtiene licitaciones via RSS + API reutilizando `09_tender_matcher.py` (get_rss_tenders + get_api_tenders), dedup por codigo
- `_extract_tender_amount(tender)`: extrae monto estimado de descripcion/nombre con regex
- `_extract_tender_type(tender)`: extrae tipo (LP/LE/L1/LR/LQ) del codigo

**Funciones de filtrado y matching:**
- `filter_tenders_for_client(tenders, profile)`: filtra por region (30pts), tipo (20pts), monto (25pts), construccion (10pts). Umbral minimo 20pts. Retorna top 5
- `check_rival_activity(tenders, profile)`: verifica si rivales conocidos participan via OCDS API (get_tender_participants_ocds). Limita a 10 llamadas API
- `_check_rivals_offline(profile)`: alternativa offline usando awards_construction.parquet

**Generacion de recomendaciones:**
- `generate_recommendations(opportunities, rival_moves, profile)`: genera 1-3 recomendaciones especificas:
  - Oportunidad prioritaria (si match >= 40)
  - Alerta de rival (si detectado)
  - Estrategia selectividad (si WR < 22%) o mantener momentum (si WR >= 22%)
  - Monitoreo continuo (fallback)

**Generacion de PDF premium:**
- `generate_weekly_pdf(profile, opportunities, rival_moves, recommendations)`: PDF de 1-2 paginas usando PremiumPDF de pdf_design.py
  - Header navy con nombre empresa, RUT, semana, fecha
  - 3 metric cards: Oportunidades, Mov. Rivales, Recomendaciones
  - Seccion 1: Oportunidades Esta Semana (tabla con codigo, nombre, tipo, cierre, afinidad + callout de top oportunidad)
  - Seccion 2: Movimiento de Rivales (insight_callout danger por cada rival detectado, o mensaje de sin actividad)
  - Seccion 3: Recomendacion de la Semana (acciones especificas con detalle)
  - Footer con proxima entrega + footer profesional con paginacion

**Generacion WhatsApp:**
- `generate_whatsapp_text(profile, opportunities, rival_moves, recommendations)`: resumen texto plano max 10 lineas con header, oportunidades (codigo/tipo/monto/cierre), rival, recomendacion

**Modos de operacion:**
- `generate_weekly_alert(rut, days, output_dir)`: modo live (RSS + API real)
- `generate_weekly_alert_offline(rut, output_dir)`: modo offline (datos historicos de parquets)
- CLI: `python generate_weekly_alert.py <RUT> [--days 7] [--offline] [--output PATH]`

**Verificacion:**
- `from generate_weekly_alert import *` OK
- 0 terminos prohibidos en output cliente (score_total, cluster, km_score, etc. solo en imports internos)
- Usa pdf_design.py para coherencia visual con diagnostico premium
- Texto sanitizado con _s() para Latin-1
- Soporta modo online (API live) y offline (parquets historicos)
- Output: PDF en data/output/alertas_semanales/ + TXT WhatsApp

Archivos creados: `lead_scoring/generate_weekly_alert.py`
