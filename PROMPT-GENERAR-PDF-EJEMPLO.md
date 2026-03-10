# PROMPT — Generar PDF de Diagnóstico de Licitaciones (con data real completa)

Copia TODO este prompt y pégalo en Claude o GPT. Contiene todos los datos, textos y especificaciones de gráficos necesarios para generar el PDF completo.

---

## INSTRUCCIÓN PRINCIPAL

Genera un **documento profesional de 6 páginas** en formato Markdown listo para convertir a PDF. Este es un diagnóstico real de inteligencia de licitaciones para la empresa GUERCUT, basado en datos públicos de Mercado Público (Chile).

El documento es un entregable gratuito que se envía a constructoras para demostrar el valor del servicio **IngenIA Licitaciones**. Debe verse profesional, con datos concretos, y generar la reacción: *"¿cómo saben todo esto de mi empresa?"*

---

## DATOS COMPLETOS DE LA EMPRESA

### Identificación

| Campo | Valor |
|-------|-------|
| Empresa | Construcciones Guercut SpA |
| Nombre comercial | GUERCUT |
| RUT | 132385-4 |
| Región principal | Valparaíso |
| Dirección | Las Monjitas 89, Padre Hurtado, Región Metropolitana |
| Teléfono | +56 9 4773 7972 |
| Rating Google Maps | 5.0 estrellas |
| Estado del negocio | Operacional |
| Posición en ranking | #80 de 5.232 constructoras activas en Chile |

### Actividad en licitaciones

| Métrica | GUERCUT | Promedio mercado | Mediana mercado |
|---------|---------|------------------|-----------------|
| Licitaciones participadas | 19 | 12,5 | 5 |
| Adjudicadas | 4 | — | — |
| No adjudicadas | 8 | — | — |
| Pendientes/sin resultado | 7 | — | — |
| Win rate | 21,05% | 22,17% | 17,39% |
| Monto total participado | $1.062M CLP | — | — |
| Monto promedio por licitación | $96,5M CLP | $80M CLP | $25M CLP |
| Primera oferta registrada | 15 enero 2024 | — | — |
| Última oferta registrada | 28 febrero 2025 | — | — |
| Días de inactividad | 369 | — | — |
| Competidores promedio por licitación | 3,5 | — | — |

### Tipos de licitación (distribución)

| Tipo | Cantidad | Porcentaje | Descripción |
|------|----------|------------|-------------|
| LP | 12 | 63,2% | Licitación Pública Mayor (>$66M) |
| LQ | 4 | 21,1% | Licitación por convenio marco |
| Otro | 2 | 10,5% | Otros mecanismos |
| LE | 1 | 5,3% | Licitación Entre $5M-$66M |
| L1 | 0 | 0% | Licitación Menor (<$5M) |

---

## DATOS DE COMPETENCIA (RIVALES)

| Rival | Victorias sobre GUERCUT | Proporción de derrotas |
|-------|------------------------|----------------------|
| PREMIUM HOME SpA | 4 | 50% de las derrotas |
| Asesoría y Construcción ACCB SpA | 1 | 12,5% de las derrotas |
| Otros rivales (3 distintos) | 3 | 37,5% de las derrotas |

**Total rivales distintos identificados:** 5

**Insight clave:** Perdió 8 de 19 licitaciones (42%). Su competidor más frecuente, PREMIUM HOME, le ganó en 4 de esas 8 derrotas. Esto indica una superposición directa de mercado en el mismo segmento de obras mayores en la zona central.

---

## DATOS PARA GRÁFICOS

### Gráfico 1: Radar Chart — GUERCUT vs Mercado (8 dimensiones)

Cada eje muestra el percentil de GUERCUT respecto a las 5.232 constructoras activas (0% = peor, 100% = mejor).

| Dimensión | Etiqueta en radar | Percentil | Interpretación |
|-----------|-------------------|-----------|----------------|
| Actividad | Actividad | 80% | Muy activa: más licitaciones que el 80% del mercado |
| Tamaño | Tamaño empresa | 82% | Empresa de tamaño medio-alto (registro MOP) |
| Win rate | Tasa de adjudicación | 90% | Paradójicamente alto — porque el score penaliza win rates extremos |
| Recencia | Actividad reciente | 49% | Promedio — lleva 369 días sin postular |
| Valor | Monto de obras | 82% | Opera en montos significativos ($96,5M promedio) |
| Competencia | Nivel de competencia | 27% | Bajo — compite en nichos con pocos competidores (3,5 promedio) |
| Oportunidad | Potencial de mejora | 86% | Alto — muchas derrotas con rivales recurrentes = espacio para mejorar |
| Especialización | Foco sectorial | 90% | Muy especializada en LP (obras mayores) |

**Nota para el gráfico:** Usar colores azul/verde para percentiles altos (>60%), amarillo para medios (40-60%), rojo/naranja para bajos (<40%). GUERCUT tiene un perfil fuerte excepto en Recencia y Competencia.

### Gráfico 2: Histograma — Distribución de Win Rate del Mercado

Distribución de win rate de las 5.232 constructoras activas. GUERCUT (21,05%) se marca con una línea vertical.

| Rango win rate | Cantidad de empresas | Barra |
|----------------|---------------------|-------|
| 0% – 5% | 20 | ▊ |
| 5% – 10% | 155 | ████▊ |
| 10% – 15% | 274 | ████████▊ |
| 15% – 20% | 411 | █████████████▊ |
| **20% – 25%** | **376** | **████████████▊ ← GUERCUT (21,05%)** |
| 25% – 30% | 229 | ███████▊ |
| 30% – 35% | 435 | ██████████████▊ |
| 35% – 40% | 223 | ███████▊ |
| 40% – 50% | 628 | ████████████████████▊ |
| 50% – 60% | 121 | ████▊ |
| 60% – 80% | 209 | ███████▊ |
| 80% – 100% | 137 | ████▊ |

**Nota:** Win rate promedio mercado: 22,17%. Win rate mediana: 17,39%. Percentil 25: 0%. Percentil 75: 35,36%. GUERCUT está ligeramente por debajo del promedio pero por encima de la mediana.

### Gráfico 3: Barras Horizontales — Rivales por Frecuencia de Victoria

| Rival | Victorias | Barra visual |
|-------|-----------|-------------|
| PREMIUM HOME SpA | 4 | ████████████████ |
| Asesoría y Construcción ACCB SpA | 1 | ████ |
| Otros (3 rivales, 1 victoria c/u) | 3 | Agrupados |

### Gráfico 4: Torta/Dona — Tipos de Licitación

| Tipo | % | Color sugerido |
|------|---|----------------|
| LP (Mayor >$66M) | 63,2% | Azul oscuro |
| LQ (Convenio marco) | 21,1% | Azul claro |
| Otro | 10,5% | Gris |
| LE ($5M-$66M) | 5,3% | Verde |

### Gráfico 5: Costo de Oportunidad

| Escenario | Win rate | Adjudicaciones en 19 licitaciones | Ingresos estimados |
|-----------|---------|----------------------------------|-------------------|
| Actual | 21,05% | 4 | $386M CLP |
| Promedio mercado | 22,17% | ~4,2 | $405M CLP |
| Meta +5 puntos | 26,05% | ~5 | $483M CLP |
| Meta +10 puntos | 31,05% | ~5,9 | $569M CLP |

**Cálculo:** Cada punto porcentual de mejora en win rate ≈ 0,19 adjudicaciones adicionales × $96,5M promedio = **~$18,3M CLP adicionales por año** al nivel de actividad actual.

---

## ESTRUCTURA EXACTA DEL PDF (6 PÁGINAS)

### PÁGINA 1 — Portada y Resumen Ejecutivo

**Encabezado:**
- Marca: **IngenIA Licitaciones**
- Línea: "Inteligencia de mercado para licitaciones públicas"

**Título central:**
# Diagnóstico de Inteligencia de Licitaciones
## GUERCUT — Construcciones Guercut SpA
### RUT: 132385-4

**Badge de ranking:**
> Posición #80 de 5.232 constructoras activas en Chile

**Subtítulo:**
> Análisis basado en datos públicos de Mercado Público · Período 2024-2025

**Resumen Ejecutivo (recuadro destacado):**

- **19 licitaciones participadas**, 4 adjudicadas — win rate del 21%, ligeramente bajo el promedio del rubro (22%).
- **Altamente especializada en LP** (obras mayores >$66M): el 63% de sus postulaciones son LP, frente al promedio de mercado donde LP representa solo el 14%.
- **Rival dominante identificado:** PREMIUM HOME SpA les ganó en 4 de 8 licitaciones perdidas — el 50% de todas sus derrotas fueron contra un solo competidor.
- **Oportunidad concreta:** mejorar 5 puntos de win rate representaría ~$97M CLP adicionales en facturación anual.
- **Señal de atención:** 369 días sin postular a nuevas licitaciones.

**Pie de página:**
> Documento generado: marzo 2026 · IngenIA Licitaciones · Datos de Mercado Público (OCDS)

---

### PÁGINA 2 — Desempeño vs Mercado

**Título:** Posicionamiento de GUERCUT en el Mercado de Construcción

**Sección A — Radar de Posicionamiento (Gráfico 1)**

Insertar radar chart de 8 ejes con los percentiles de la tabla anterior. Incluir leyenda:
> "Cada eje muestra la posición de GUERCUT respecto a 5.232 constructoras activas (100% = mejor posición)."

**Texto interpretativo:**

> GUERCUT muestra un perfil de constructora **especializada y activa**: destaca en actividad (percentil 80), especialización en obras mayores (percentil 90) y tamaño de empresa (percentil 82). Su monto promedio por licitación ($96,5M) supera al mercado ($80M promedio, $25M mediana).
>
> Las áreas de atención son la **actividad reciente** (percentil 49 — lleva más de un año sin postular) y el **nivel de competencia** (percentil 27 — aunque esto puede indicar que opera en nichos con pocos oferentes, lo cual es una ventaja si se sabe aprovechar).

**Sección B — Distribución de Win Rate (Gráfico 2)**

Insertar histograma con la distribución y la línea de GUERCUT al 21,05%.

**Texto:**

> Con un win rate de 21,05%, GUERCUT se ubica ligeramente por debajo del promedio del mercado (22,17%) pero por encima de la mediana (17,39%). Esto significa que gana más que la mitad de las constructoras, pero hay espacio para mejorar.

---

### PÁGINA 3 — Inteligencia Competitiva

**Título:** ¿Quién le gana a GUERCUT y con qué frecuencia?

**Sección A — Gráfico de Rivales (Gráfico 3)**

Insertar barras horizontales de rivales.

**Tabla de detalle:**

| Competidor | Victorias sobre GUERCUT | Tipo de obras | Observación |
|-----------|------------------------|---------------|-------------|
| PREMIUM HOME SpA | 4 de 8 derrotas | LP (obras mayores) | **Rival dominante.** 50% de las derrotas son contra este competidor. |
| Asesoría y Construcción ACCB SpA | 1 de 8 derrotas | LP | Rival ocasional. |
| Otros 3 rivales | 3 de 8 derrotas | Variado | Sin patrón recurrente. |

**Insight destacado (recuadro):**

> 🔍 **Hallazgo clave:** La relación GUERCUT vs PREMIUM HOME es la más relevante de este análisis. En la mitad de las licitaciones donde GUERCUT no fue adjudicada, el ganador fue PREMIUM HOME. Esto sugiere:
>
> 1. **Superposición directa de mercado** — ambas compiten por el mismo tipo de obras.
> 2. **Oportunidad de análisis** — comparar las ofertas ganadoras de PREMIUM HOME podría revelar diferencias en precio, plazo, equipo técnico o experiencia declarada.
> 3. **Estrategia posible** — identificar licitaciones donde PREMIUM HOME tiene desventaja (por región, especialidad o carga de trabajo) para mejorar la tasa de éxito.

---

### PÁGINA 4 — Tendencias y Sectores

**Título:** Perfil de Participación de GUERCUT

**Sección A — Distribución por tipo (Gráfico 4)**

Insertar gráfico de torta/dona con la distribución LP/LQ/LE/Otro.

**Texto:**

> GUERCUT concentra el **63% de sus postulaciones en licitaciones LP** (obras públicas mayores a $66M CLP). Esto la diferencia del mercado general, donde las LP representan solo el 14% del total de licitaciones de construcción.
>
> Esta alta concentración indica:
> - **Especialización fuerte** en obras de mayor envergadura.
> - **Mayor riesgo por licitación** — cada derrota en LP tiene un costo de oportunidad significativo.
> - **Menor volumen de oportunidades** — al concentrarse en LP, el universo de licitaciones disponibles es más reducido.

**Sección B — Datos de operación**

| Indicador | Valor |
|-----------|-------|
| Región principal | Valparaíso |
| Monto total participado | $1.062M CLP |
| Monto promedio por licitación | $96,5M CLP |
| Período de actividad | Enero 2024 — Febrero 2025 (14 meses) |
| Competidores promedio por licitación | 3,5 (bajo respecto al mercado) |

**Señal de atención:**

> ⚠️ GUERCUT lleva **369 días sin postular** a nuevas licitaciones. En un mercado donde las constructoras activas postulan en promedio cada 2-3 meses, esta inactividad puede significar pérdida de posicionamiento o cambio de estrategia. Retomar actividad en licitaciones es urgente para no perder visibilidad ante los organismos compradores.

---

### PÁGINA 5 — Costo de Oportunidad

**Título:** ¿Cuánto vale mejorar la tasa de adjudicación?

**Gráfico 5 / Tabla de escenarios:**

| Escenario | Win rate | Adjudicaciones estimadas (en 19 licitaciones) | Ingresos potenciales |
|-----------|---------|----------------------------------------------|---------------------|
| **Situación actual** | 21% | 4 | $386M CLP |
| Si iguala el promedio | 22% | 4,2 | $405M CLP |
| **Meta realista (+5pp)** | 26% | 5 | $483M CLP |
| Meta ambiciosa (+10pp) | 31% | 5,9 | $569M CLP |

**Texto principal:**

> Cada punto porcentual de mejora en win rate representa aproximadamente **$18,3M CLP en ingresos adicionales anuales** al nivel de actividad actual de GUERCUT.
>
> Mejorar de 21% a 26% (una meta realista y alcanzable con ajustes en la estrategia de postulación) significaría **~$97M CLP adicionales** — equivalente a ganar una licitación más por año.

**Recuadro de impacto:**

> 💰 **Si GUERCUT hubiera ganado 1 licitación más de las 19 en las que participó, su facturación habría aumentado en ~$97M CLP.**
>
> Las principales palancas para lograrlo son:
> 1. Analizar las ofertas ganadoras de PREMIUM HOME en las 4 licitaciones perdidas contra ellos.
> 2. Detectar requisitos de inadmisibilidad antes de postular.
> 3. Optimizar la presentación de experiencia y equipo técnico en las bases.

---

### PÁGINA 6 — Siguiente Paso

**Título:** ¿Cómo mejorar estos números?

**Texto:**

> Este diagnóstico fue generado con datos públicos de Mercado Público y muestra el panorama general de GUERCUT en licitaciones. Un **análisis profundo** va más allá:

**Servicios disponibles:**

| Servicio | Qué incluye | Valor |
|----------|-------------|-------|
| **Análisis de licitación específica** | Revisión de bases, detección de riesgos de inadmisibilidad, evaluación de criterios de evaluación, estrategia de precio y presentación | $190.000 + IVA |
| **Diagnóstico competitivo completo** | Análisis detallado de las 4 derrotas contra PREMIUM HOME, comparación de ofertas, recomendaciones de diferenciación | $250.000 + IVA |
| **Servicio mensual de inteligencia** | Monitoreo de licitaciones relevantes, alertas de oportunidades, análisis competitivo continuo, soporte en postulaciones | $490.000/mes + IVA |

**CTA (llamado a acción):**

> **¿Le interesa un análisis detallado de sus licitaciones?**
>
> Puedo revisar una licitación real suya de forma gratuita como demo. Solo necesito el código de la licitación.
>
> **Sebastián Cortés**
> Ing. Civil UCN · IngenIA Licitaciones
> +56 9 2213 4294
> sebastian.cortes.ing@gmail.com

**Disclaimer (pie de página, letra pequeña):**

> *Datos obtenidos de fuentes públicas (Mercado Público / OCDS / Registro MOP). Este análisis no constituye asesoría legal, financiera ni de ingeniería. Los montos y tasas son estimaciones basadas en datos históricos disponibles. Se recomienda revisión humana antes de tomar decisiones de negocio. Generado en marzo 2026.*

---

## REGLAS DE ESTILO OBLIGATORIAS

1. **Tono:** Profesional, consultivo, directo. No académico. No condescendiente.
2. **Idioma:** Español chileno formal (sin modismos pero natural).
3. **Números:** Formato chileno — usar punto como separador de miles ($1.062M, no $1,062M), coma para decimales (21,05%, no 21.05%).
4. **Moneda:** Siempre CLP. Montos grandes en millones: "$96,5M CLP".
5. **Gráficos:** Describirlos en detalle suficiente para que se puedan crear con cualquier herramienta (Canva, Google Slides, Python matplotlib, Excel). Incluir datos exactos, colores sugeridos, ejes y leyendas.
6. **NUNCA mencionar:** score, score_combined, score_total, cluster, K-Means, XGBoost, ranking interno, machine learning, modelo predictivo.
7. **SÍ mencionar:** posición relativa, percentil vs mercado, win rate, montos, competidores, patrones de adjudicación.
8. **Marca:** "IngenIA Licitaciones" en encabezado de cada página. "Sebastián Cortés, Ing. Civil UCN" en firma.
9. **Íconos:** Usar emojis moderadamente solo en recuadros destacados (🔍, 💰, ⚠️). No en texto corrido.
10. **Largo:** Cada página debe tener contenido suficiente para llenar una hoja A4 sin verse vacía ni sobrecargada.

## FORMATO DE SALIDA

Genera las 6 páginas completas en Markdown con separadores `---` entre páginas. Incluye todas las tablas, textos, recuadros e instrucciones de gráficos. El documento debe estar 100% listo para diseñar — sin placeholders, sin "[insertar aquí]", sin texto pendiente.
