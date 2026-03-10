# Plan de Negocio: Analista Estratégico de Licitaciones Públicas Chile

## Identidad
- **Nombre profesional**: Sebastián Cortés
- **Email**: sebastian.cortes.ing@gmail.com
- **Perfil**: Estudiante 5° año Ingeniería Civil, Universidad Católica del Norte
- **Ventaja diferencial**: Ing. civil que domina LLMs de alto contexto (Claude Opus 4.6 + Gemini 3.1 Pro)

---

## El Negocio en 1 párrafo

Servicio de inteligencia competitiva para constructoras medianas chilenas (10-50 personas) que licitan obras públicas. Usando IA de alto contexto, analizo bases de licitación (200-500 páginas) en minutos, detecto requisitos críticos, normas actualizadas que los competidores pasan por alto, y riesgos de descalificación. No vendo "resumen de bases" — vendo **aumento de probabilidad de adjudicación**.

---

## Nota: 8.5/10 (consenso de 6 IAs)

### Por qué:
- Mercado real: USD $22B compras públicas Chile, $3.2B solo obras (+70% en 2025)
- 560 licitaciones MOP planificadas 2025, 1.8M transacciones anuales totales
- 0% mejora productividad construcción en 18 años, digitalización <1%
- No existe competidor con IA + normativa chilena
- Costo de operación: $0 extra (ya tiene Claude Max 5x + Gemini API con crédito)

### Debilidades honestas:
- Moat bajo al inicio (se construye operando)
- Depende de ejecución de ventas personal
- No es unicornio, es servicio B2B nicho

---

## Fases del Negocio

### Fase 1: Cashflow (Mes 1-3)
**Producto**: Análisis estratégico de bases de licitación
- Detectar requisitos críticos, normas actualizadas, riesgos de descalificación
- Identificar dónde van a perder puntaje y cómo corregirlo
- Entrega: informe accionable por licitación

**Precio**: $490.000 + IVA/mes (monitoreo continuo + análisis competitivo)

**Upsell diagnóstico competitivo**: $250.000 + IVA (análisis de derrotas vs rivales clave)

### Fase 2: Retención (Mes 3-6)
**Producto adicional**: RAG sobre normas NCh/OGUC
- Corpus de 1,200+ normas chilenas procesadas
- Verificación automática de cumplimiento normativo
- Diferenciador que ningún competidor tiene

### Fase 3: Moat (Mes 6-12)
**Producto**: Scoring predictivo de adjudicación
- Base de datos propia de resultados históricos
- Patrones de adjudicación por tipo obra/región/monto
- "Tu propuesta tiene 73% de probabilidad. Si corriges estos 3 puntos, sube a 89%"
- ESTE es el moat real — datos propietarios acumulados

---

## Proyección Económica (Conservadora)

| Mes | Clientes nuevos | Churn | Activos | Revenue CLP |
|-----|----------------|-------|---------|-------------|
| 1   | 1              | 0     | 1       | $190-490K   |
| 2   | 1-2            | 0     | 2-3     | $490-980K   |
| 3   | 2              | 0-1   | 3-4     | $980K-1.5M  |
| 4   | 2              | 1     | 4-5     | $1.5-2M     |
| 5   | 2              | 1     | 5-6     | $2-2.5M     |
| 6   | 2 + referidos  | 1     | 6-7     | $2.5M+      |

### Costos mensuales:
- Claude Max 5x: YA PAGADO ($100 USD)
- Gemini 3.1 Pro API: ~$30K CLP crédito gratis, luego pago por uso
- Loom: gratis (25 videos/mes tier free)
- WhatsApp: $0
- API MercadoPublico: $0
- **Inversión extra requerida: $0**

### Unit economics por cliente:
- Revenue: $490.000 + IVA/mes
- Costo API: ~$30-50K CLP
- Tiempo servicio: 2-3 hrs/mes (automatizado)
- **Margen: ~90%**

---

## Funnel de Ventas

### Fuentes de leads (GRATIS):
1. **mercadopublico.cl/BuscarLicitacion** → Todas las licitaciones del Estado con filtros
2. **licitaciones-dgop.mop.gob.cl** → Licitaciones MOP activas
3. **Feed MOP en mercadopublico.cl** → Licitaciones con fechas cierre
4. **API MercadoPublico** (cuando llegue ticket) → Automatización

### Proceso semanal:

```
1. SCRAPING MANUAL (30-45 min/día)
   MercadoPublico → filtrar obras/construcción → licitaciones próximas a cerrar

2. IDENTIFICAR LEADS (30 min)
   Empresas que postulan → buscar contacto en Google/LinkedIn
   Target: constructora mediana 10-50 personas, sin depto. de estudios

3. ANÁLISIS CON IA (5 min por base)
   Claude Opus 4.6 analiza base → detecta hallazgos críticos

4. CONTENIDO OUTREACH (3-15 min por lead)
   Opción A: Loom con cara (mes 1) → 15 min/lead, ~15-20% response
   Opción B: Screenshot + texto WhatsApp → 3 min/lead, ~8-10% response

5. ENVÍO (WhatsApp primario, email backup)
   Chile: 98% usa WhatsApp, 98% open rate, 15-20% response rate B2B
```

### Volumen semanal:
- 25-60 leads contactados (según formato)
- 4-10 conversaciones
- 1-2 reuniones
- ~1 cliente nuevo cada 1-2 semanas

### Secuencia de venta:
```
Loom/WhatsApp: "Encontré ESTO en tu base" (gratis, es el outreach)
    ↓
Responde → "¿Quieres el análisis completo?"
    ↓
Entregas análisis completo de ESA licitación → GRATIS (primera vez)
    ↓
"¿Te sirvió? El servicio mensual es $490K/mes y te monitoreo todo"
```

---

## Stack Tecnológico

| Herramienta | Uso | Costo |
|-------------|-----|-------|
| Claude Max 5x (Opus 4.6) | Análisis de bases, generación de reportes, coding | Ya pagado |
| Gemini 3.1 Pro API | Procesamiento masivo de documentos (1M contexto nativo, barato) | Crédito $30K + pago por uso ($2/M input) |
| MercadoPublico.cl | Fuente de licitaciones y leads | Gratis |
| Loom (free tier) | Videos personalizados de outreach | Gratis (25/mes) |
| WhatsApp | Canal principal de outreach | Gratis |
| Google Maps | Contactos de empresas | Gratis |

### Modelo óptimo por tarea:
- **Ingestar bases de 200+ páginas**: Gemini 3.1 Pro (1M contexto nativo, $2/M tokens input)
- **Análisis estratégico y razonamiento**: Claude Opus 4.6 (80.8% SWE-bench, mejor reasoning)
- **Generar reportes y contenido**: Claude Opus 4.6 (128K output)
- **Verificación normativa masiva**: Gemini 3.1 Pro (más barato para volumen)

---

## Mercado Chile - Datos Clave

### Tamaño:
- Mercado construcción: USD $33.7B (2025), creciendo 3.9%
- Compras públicas totales: USD $21,953M (2025)
- Solo obras públicas: USD $3,280M (+70.4% vs 2024)
- MOP inversiones 2025: CLP $3.8 billones (récord histórico)
- 560 licitaciones MOP planificadas 2025
- 1,868,361 órdenes de compra anuales
- 1,165 entidades públicas comprando
- 118,000+ proveedores registrados

### Target:
- ~3,000 empresas CChC formales
- ~600 constructoras principales (plataforma iConstruye)
- Sweet spot: constructora mediana 10-50 personas sin departamento de estudios

### Dolor documentado:
- 0% mejora productividad construcción en 18 años (vs 20% resto economía)
- Digitalización <1% (McKinsey)
- Solo 29% usa BIM, 35% usa ERP
- 58% cita costos como barrera, 52% falta de conocimiento técnico

### Competencia:
- LicitaLAB: alertas de licitaciones, SIN análisis IA
- Civils.ai, CodeComply, CivCheck: no manejan normativa chilena
- iConstruye: supply chain, no IA
- **No existe competidor con IA + normativa chilena + análisis estratégico**

### Costos de referencia:
- Ingeniero calculista junior: ~$1.4M CLP/mes
- Costo empresa calculista: ~$1.8-2M CLP/mes
- Tu servicio ($490K/mes) < mitad de un calculista

---

## Marco Normativo Chileno

### Estructura:
- **OGUC**: Ordenanza General de Urbanismo y Construcciones (marco legal principal)
- **LGUC**: Ley General de Urbanismo y Construcciones (ley madre)
- **Normas NCh**: 1,200+ estándares técnicos del INN
  - 350 obligatorias
  - 850 voluntarias

### Normas clave para ingeniería estructural:
| Norma | Contenido |
|-------|-----------|
| NCh433 | Diseño sísmico de edificios |
| NCh3171 | Disposiciones generales y combinaciones de cargas |
| NCh427 | Construcción en acero |
| NCh430 | Hormigón armado |
| NCh431 | Construcción en albañilería |
| NCh432 | Cálculo de cargas de nieve |
| NCh1198 | Construcción en madera |
| NCh1537 | Sobrecargas de uso |
| NCh2369 | Diseño sísmico de estructuras industriales |

### Oportunidad IA:
- NCh433 sola referencia al menos 9 normas adicionales
- Interdependencias complejas entre normas
- Actualizaciones frecuentes post-terremoto 2010
- Ninguna herramienta de IA tiene este corpus procesado

---

## Advertencias Críticas

### NO hacer:
- No certificar cumplimiento normativo (riesgo legal como estudiante)
- No confiar en LLMs para cálculos matemáticos/estructurales (alucinan)
- No vender "resumen de bases" (commodity, te reemplazan)
- No cobrar por hora (te comparan con practicante)
- No depender de un solo modelo/API (abstraer capa de modelo)

### SÍ hacer:
- Vender "probabilidad de adjudicación" y "reducción de riesgo"
- Dar hallazgos estratégicos, no resúmenes
- Cobrar mensual o por licitación, nunca por hora
- Construir base de datos propia de resultados
- Mostrar valor con datos de SU licitación específica

### Sobre "viene ChatGPT":
- Construcción chilena: <1% digitalización, 0% mejora productividad en 18 años
- Dueños de constructoras (50-60 años) no van a aprender prompt engineering
- Ventana realista: 2-3 años antes de comoditización
- El moat real se construye con datos acumulados, no con la herramienta

---

## Ajustes Operativos Críticos

### 1. PDFs escaneados (OCR)
Muchas bases del Estado son escaneos de documentos impresos (imágenes, no texto).
La IA no los lee o alucina. **Paso previo**: pasar por OCR (ILovePDF, Adobe, o
Gemini 3.1 Pro que tiene visión multimodal y puede leer imágenes directamente).

### 2. Ghostwriting: no pedir 50 páginas de golpe
Ningún LLM genera 50 páginas de calidad en un output. Se degrada y repite.
**Solución**: pedir primero el índice estratégico, luego un prompt por subsección.
Unir en Word al final.

### 3. Pricing alternativo: Bono de Éxito
Si el cliente resiste el fee mensual fijo, ofrecer modelo híbrido:
- Base: $250K CLP/mes (cubre monitoreo)
- Bono de éxito: monto fijo ($1-2M CLP) SOLO si se adjudican
- Alinea incentivos 100% y hace que decir "no" sea irracional

### 4. NDA para Ghostwriting
Las bases son públicas, pero para redactar ofertas técnicas el cliente comparte
info sensible (balances, CVs, equipos, metodologías). Tener formato simple de
Acuerdo de Confidencialidad listo. Enviar ANTES de recibir datos. Te diferencia
del freelance promedio.

### 5. CRM mínimo (Google Sheets)
Con 25 leads/semana, para semana 3 tienes 75 contactos. Sin tracking pierdes seguimiento.
**Google Sheets con columnas**:
| Empresa | Contacto | WhatsApp | Licitación | Loom Link | Fecha Envío | Estado | Notas |

Estados: Enviado → Respondió → Reunión → Análisis Gratis → Propuesta → Cerrado/Rechazado

---

## Próximos Pasos Inmediatos

1. ✅ Correo enviado a api@chilecompra.cl (no esperar respuesta para empezar)
2. ⬜ Crear Google Sheets CRM con columnas de tracking
3. ⬜ Entrar a mercadopublico.cl → filtrar obras construcción → descargar 3 bases
4. ⬜ Si PDF es escaneado → pasar por OCR primero
5. ⬜ Analizar bases con Claude → encontrar hallazgos críticos
6. ⬜ Crear cuenta Loom con perfil "Sebastián Cortés"
7. ⬜ Grabar 3 Looms personalizados con hallazgos reales
8. ⬜ Buscar contacto de las constructoras → Google/LinkedIn
9. ⬜ Enviar por WhatsApp
10. ⬜ Iterar según respuestas

---

## Benchmarks de Modelos IA (Feb 2026)

| Modelo | Contexto | Input/Output por 1M tok | SWE-bench | Uso principal |
|--------|----------|------------------------|-----------|---------------|
| Claude Opus 4.6 | 200K (1M beta) | $5 / $25 | 80.8% | Análisis estratégico, reasoning, coding |
| Gemini 3.1 Pro | 1M nativo | $2 / $12 | 80.6% | Documentos masivos, volumen, costo-efectivo |
| GPT-5.2 | 400K | $1.75 / $14 | ~80% | Alternativa |
| DeepSeek V4 | 1M | $0.30 / $0.50 | ~80%* | Budget option |

---

## Canales de Outreach - Data Chile

| Canal | Open rate | Response rate | Mejor para |
|-------|----------|---------------|------------|
| WhatsApp | 98% | 15-20% cold B2B | Canal primario |
| Email + Loom video | 20% open | 8% reply (consulting) | Backup 48hrs después |
| LinkedIn | Variable | 5-10% | Empresas más grandes |

Chile es top 3 mundial en uso de WhatsApp (98% smartphones).
Loom con cara: reply rate 2-3x vs texto solo.
Consulting firms: 7.88% reply rate promedio (mejor que otros sectores).
