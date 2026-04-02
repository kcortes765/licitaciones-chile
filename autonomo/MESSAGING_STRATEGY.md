# Estrategia de Cold Messaging — IngenIA Licitaciones

> Documento estratégico para mensajes WhatsApp a constructoras chilenas.
> NO es un template — es el análisis psicológico y estratégico detrás de cada mensaje.
> Feature 6 del plan v4. Referencia obligatoria antes de escribir templates en v7.

---

## 1. Perfil del Receptor

### Quién lee estos mensajes

**Cargo**: Gerente general o gerente comercial de constructora mediana (10-50 personas). En empresas más chicas, es el dueño-fundador que hace todo. En las más grandes, puede ser un jefe de propuestas o encargado de licitaciones.

**Contexto físico**: Lee WhatsApp entre reuniones, en la obra, o al final del día. Tiene **30 segundos máximo** para decidir si un mensaje merece atención. Si no lo engancha en la primera línea, lo ignora o lo borra.

**Contexto mental**: Sabe que pierde licitaciones pero no tiene visibilidad de por qué. No tiene un equipo de inteligencia comercial. Su "análisis" es revisar Mercado Público manualmente y postular a lo que "se ve bien". Toma decisiones con el estómago, no con datos.

**Dolor principal**: Ve cómo competidores más chicos o menos técnicos les ganan contratos. No entiende qué está pasando. Sospecha que es precio, pero no está seguro.

**Defensas activas**:
- Desconfía de vendedores — recibe spam de proveedores todos los días
- Ignora mensajes genéricos ("Somos una empresa que ofrece...")
- Rechaza inmediatamente todo lo que suene a marketing ("solución integral", "optimice su gestión")
- Alerta ante anglicismos y jerga tech ("IA", "plataforma", "dashboard")
- En construcción chilena, la credibilidad viene del título profesional y la experiencia en terreno, no de marcas

### Qué lo haría responder

**Una sola cosa**: que el mensaje demuestre que **ya sabes algo específico de SU empresa que él NO sabía**. No algo genérico del rubro — algo de ÉL. Su win rate, su rival, su zona, su monto promedio.

El mecanismo psicológico es: "¿Cómo sabe esto? Yo no lo sabía. Necesito saber más."

Esto activa **curiosidad + ligera incomodidad** (alguien sabe más de mi negocio que yo). Es la combinación que genera respuesta.

---

## 2. Análisis por Tipo de Insight

### Los datos que tenemos por empresa

De los parquets de Mercado Público (48 meses de datos):
- `win_rate` — tasa de adjudicación
- `total_bids` / `total_wins` / `total_lost` — conteos
- `n_LP` — licitaciones públicas (alto valor)
- `monto_total` / `monto_promedio` — en CLP
- `top_rival_1_name` / `top_rival_1_count` — rival dominante
- `loss_rate` — tasa de pérdida concentrada
- `dias_desde_ultima` — inactividad
- `n_tenders_region` — licitaciones en su zona (estimable)

---

### 2.1 RIVAL_FUERTE (rival ganó 3+ veces)

**Dato**: Un competidor específico les ganó 3 o más licitaciones. Tenemos nombre y conteo exacto.

**Por qué es relevante**: El receptor probablemente NO sabe que un solo rival le ha ganado tantas veces. Cada licitación se vive como evento aislado — nadie conecta los puntos.

**Emoción**: **Rabia + curiosidad**. "¿Ese weón me ganó 5 veces? ¿Cómo?" Rabia porque es personal (es un rival con nombre y apellido). Curiosidad porque implica que hay un patrón explotable.

**Gancho psicológico**: Nombrar al rival y cuantificar en PESOS lo que se fue a sus manos. El dinero lo hace tangible. "3 licitaciones" es abstracto. "$1.200M en contratos que se fueron a Constructora X" duele.

**Golpe perfecto**: "Constructora Alfa se adjudicó 5 de las licitaciones que ustedes perdieron — unos $1.800M en contratos que fueron a sus manos. Encontré un patrón en cómo arma las propuestas."

**Golpe mediocre**: "Tienen un competidor que les ha ganado varias veces." (Sin nombre, sin monto, sin patrón — genérico, ignorable.)

---

### 2.2 RIVAL_RECURRENTE (rival ganó 2 veces)

**Dato**: Un competidor les ganó 2 veces. Menos que rival_fuerte pero ya es patrón.

**Por qué es relevante**: Dos veces no es casualidad. El receptor puede racionalizar una pérdida ("mal día", "precio muy bajo"), pero dos contra el mismo rival sugiere algo sistemático.

**Emoción**: **Alerta + curiosidad**. Menos intensa que rival_fuerte pero suficiente para activar atención.

**Gancho psicológico**: Tono de "patrón emergente" — todavía se puede revertir, pero hay que actuar. Urgencia suave.

**Golpe perfecto**: "Constructora Beta les ganó 2 veces en competencia directa — unos $640M en contratos. Vi un patrón claro en cómo diferencia sus propuestas."

**Golpe mediocre**: "Un competidor les ha ganado en más de una ocasión." (Vago, sin acción implícita.)

---

### 2.3 WIN_RATE_GAP_LP (n_LP>=5 y WR<20%)

**Dato**: Postulan a muchas licitaciones de alto valor pero ganan menos del 20%. El rubro está en 22%.

**Por qué es relevante**: Las LP (licitaciones públicas de mayor monto) son donde está el dinero grande. Un gap de pocos puntos porcentuales en LP se traduce en MILLONES perdidos al año.

**Emoción**: **Frustración + oportunidad**. "Estoy postulando bastante pero no gano lo suficiente." La cuantificación en pesos convierte frustración difusa en urgencia concreta.

**Gancho psicológico**: Convertir la brecha porcentual en CONTRATOS PERDIDOS y PESOS. "2 puntos bajo el rubro" no duele. "$380M que se fueron a la competencia" sí.

**Golpe perfecto**: "Con 12 postulaciones LP y tasa de 8%, están 14 puntos bajo el rubro (22%). Eso equivale a unos $380M en contratos que se fueron a la competencia."

**Golpe mediocre**: "Su tasa de adjudicación está por debajo del promedio del rubro." (Sin escala, sin costo de oportunidad.)

---

### 2.4 LP_ALTO (n_LP>=5, WR puede ser alto o bajo)

**Dato**: Postulan activamente a LP. Dos ángulos según su WR:
- Si WR < rubro: "cerrar la brecha" (similar a win_rate_gap pero menos extremo)
- Si WR >= rubro: "proteger la ventaja" (los que ganan bien también tienen no-adjudicadas con patrones)

**Por qué es relevante**: Son empresas activas y sofisticadas. Participan en licitaciones grandes. Valoran la información porque ya invierten esfuerzo serio en propuestas.

**Emoción**:
- WR bajo: **Ambición frustrada** — "Estoy en las grandes pero no gano lo que debería"
- WR alto: **Orgullo + curiosidad** — "Voy bien, pero ¿qué se me escapa?"

**Gancho psicológico**: Para WR bajo, cuantificar costo de oportunidad. Para WR alto, apelar a la optimización — incluso los buenos pueden mejorar, y las licitaciones que perdieron tienen un patrón identificable.

**Golpe perfecto (WR bajo)**: "De 8 licitaciones de alto valor, la tasa es 12% — 10 puntos bajo el rubro (22%). Eso son unos $520M en contratos."

**Golpe perfecto (WR alto)**: "De 9 licitaciones de alto valor, la tasa es 33% — sobre el 22% del rubro. Aun así, en las 6 no adjudicadas hay un patrón medible."

---

### 2.5 INACTIVO (sin postular 6+ meses)

**Dato**: Dejaron de postular hace N meses. Mientras tanto, salieron miles de licitaciones de construcción.

**Por qué es relevante**: La inactividad en Mercado Público es una señal fuerte. Puede ser por frustración ("no ganamos nunca"), cambio de estrategia, o problemas internos. En cualquier caso, sus rivales siguen activos.

**Emoción**: **Urgencia + FOMO** (fear of missing out). "Mientras yo no postulo, mis competidores están ganando contratos que podrían ser míos."

**Gancho psicológico**: Cuantificar lo que pasó MIENTRAS estaban inactivos. No es "deberían volver" (consejo no pedido) — es "miren lo que pasó sin ustedes" (dato revelador). El número de licitaciones que salieron en su región es el dato killer.

**Golpe perfecto**: "Llevan 9 meses sin postular en Mercado Público. En ese período salieron más de 10.700 licitaciones de construcción, varias en el rango de $180M que manejan."

**Golpe mediocre**: "Noté que llevan tiempo sin participar en licitaciones." (Sin cuantificar el costo de la inactividad.)

---

### 2.6 WR_BAJO_LP (WR<20% con n_LP>=3)

**Dato**: Postulan a licitaciones grandes pero ganan poco. Menos datos que win_rate_gap_LP (3-4 LP vs 5+).

**Por qué es relevante**: Empresas que intentan jugar en ligas mayores pero no tienen los números. El gap porcentual en LP se traduce directamente en millones.

**Emoción**: **Frustración concreta** — postulan a las grandes, invierten tiempo en propuestas complejas, y no ganan.

**Gancho psicológico**: "En contratos de ese tamaño, esos puntos se traducen en millones." Hacer tangible lo que un punto porcentual significa cuando cada contrato es de $200M+.

**Golpe perfecto**: "De 4 postulaciones LP, la tasa es 0% — 22 puntos bajo el 22% del rubro. En contratos de ese tamaño, esos puntos se traducen en millones."

---

### 2.7 LOSS_CONCENTRADO (loss_rate>=40% con 5+ pérdidas)

**Dato**: Pierden más del 40% de sus licitaciones, con al menos 5 pérdidas. Alta concentración de fracasos.

**Por qué es relevante**: El receptor probablemente atribuye cada pérdida a precio. Pero si hay 7 pérdidas de 12, NO todas son por precio — hay un factor sistemático.

**Emoción**: **Intriga + alivio potencial**. "¿No es solo precio? Entonces puedo hacer algo." Es la emoción más constructiva — pasa de impotencia a agencia.

**Gancho psicológico**: "Hay un factor común — y no es precio." Esta frase rompe la narrativa del receptor ("todo es precio") y abre la puerta a una conversación. El "no es precio" es el gancho porque desafía su creencia más arraigada.

**Golpe perfecto**: "7 de 12 licitaciones no se adjudicaron — tasa de pérdida del 58%. Revisé los datos y hay un factor común que no es solo precio."

**Golpe mediocre**: "Tienen una tasa de pérdida alta en sus licitaciones." (Sin el giro "no es precio" que activa curiosidad.)

---

### 2.8 WR_BAJO (WR<19% general)

**Dato**: Win rate general bajo, sin suficientes LP para usar los insights anteriores.

**Por qué es relevante**: Empresas con historial de muchas postulaciones y pocas adjudicaciones. Es un dolor difuso pero real.

**Emoción**: **Resignación que busca explicación**. "Sabemos que no nos va bien, pero no sabemos por qué."

**Gancho psicológico**: Los números crudos + comparación con rubro. El receptor necesita un benchmark externo para calibrar si su situación es normal o alarmante. El rubro al 22% le da ese benchmark.

**Golpe perfecto**: "3 adjudicadas de 18 postulaciones — 17%, con el rubro en 22%. Revisé las no adjudicadas y encontré factores concretos que las definieron."

---

### 2.9 RIVAL_UNICO (rival ganó 1+ con 3+ pérdidas)

**Dato**: Tienen varias pérdidas y un rival identificable aparece en ellas. Menos dramático que rival_fuerte/recurrente.

**Por qué es relevante**: Incluso con solo una victoria del rival, si la empresa tiene muchas pérdidas, el rival nombrado funciona como "cara visible" de un problema más amplio.

**Emoción**: **Curiosidad moderada**. "No sabía que ese rival era factor en mis licitaciones."

**Gancho psicológico**: Nombrar al rival + cuantificar en pesos si el monto es significativo. El nombre propio siempre es más poderoso que "la competencia".

**Golpe perfecto**: "En 5 de sus licitaciones no adjudicadas, Constructora Gamma fue quien ganó — unos $890M en contratos. Encontré qué diferencia sus propuestas."

---

### 2.10 DEFAULT (stats honestos)

**Dato**: No hay un insight dramático específico. Tenemos win rate, bids, wins y la comparación con el rubro.

**Por qué es relevante**: Es el caso más débil pero aún tenemos datos que el receptor no tiene: su propia estadística comparada con el rubro.

**Emoción**: **Curiosidad leve**. "No sabía cuáles eran mis números exactos ni cómo me comparo."

**Gancho psicológico**: Honestidad radical — poner los números sobre la mesa sin dramatizar. La transparencia genera credibilidad. Si los números son malos, hablan solos. Si son buenos, el "encontré factores" en las pérdidas mantiene el interés.

**Golpe perfecto**: "Revisé su historial: 4 adjudicadas de 15 postulaciones (27%), con el rubro en 22%. En las no adjudicadas encontré factores concretos que las definieron."

---

## 3. Principios de Copywriting para Chile B2B Construcción

### Tono y registro

**Usted, siempre**. En Chile B2B, el tuteo en un primer contacto es inaceptable. "Usted" es formal pero no distante — es el registro natural entre profesionales que no se conocen. Después de la primera interacción, si el receptor tutea, se puede bajar.

**Primera persona activa**: "Encontré", "Revisé", "Vi", "Detecté". Nunca pasiva ("Se encontró", "Fue detectado"). El mensaje es de una persona, no de un sistema. El receptor debe sentir que un ser humano dedicó tiempo a revisar SU caso.

### Credibilidad

**Título profesional primero**: "Ingeniero civil" es el mayor capital de credibilidad en construcción chilena. Un ingeniero civil que te contacta sobre licitaciones es creíble. Una "empresa de inteligencia" que te contacta es spam.

**Presentación**: "Soy Sebastián Cortés, ingeniero civil." — NO "de IngenIA Licitaciones" (suena a empresa genérica que vende algo). El nombre de la empresa va solo en la firma, reformulado como "Inteligencia de Licitaciones" (descripción de lo que hace, no marca).

**Mercado Público como referencia compartida**: El receptor conoce Mercado Público. Mencionarlo ancla el mensaje en realidad compartida. "Revisé su historial en Mercado Público" es verificable — el receptor puede ir a checkear.

### Cuantificación

**Siempre en pesos chilenos o porcentaje**. Nunca en abstracto. Las reglas:

- Montos: formato chileno con separador de punto. `$447M` (millones), `$1.2B` (miles de millones). Función `formato_monto()`.
- Porcentajes: sin decimales, redondeados. `17%`, `22%`. Función `pct()`.
- Brechas: en "puntos" — "14 puntos bajo el rubro (22%)". No "14% menos" (confuso).
- Contratos: "N contratos" o "N licitaciones". Nunca "N oportunidades" (jerga de marketing).
- Tiempo: "N meses". No "medio año" ni "casi un año" — el número exacto es más creíble.

### Qué NO mencionar jamás

- **IA / Inteligencia Artificial / Machine Learning**: Genera desconfianza en construcción. El receptor piensa "este me quiere vender software".
- **Plataforma / Herramienta / Software / Dashboard**: Mismo efecto. Suena a venta de SaaS.
- **Servicio / Diagnóstico / Análisis**: Suena a consultoría genérica. "Le ofrecemos un diagnóstico" = spam.
- **Score / Ranking / Modelo / Algoritmo / Pipeline**: Jerga interna que filtra al chat de basura.
- **Cluster / Segmento / Vertical**: Jerga de marketing.
- **Anglicismos**: Insight, pipeline, dashboard, KPI, ROI. Usar equivalentes españoles o simplemente describir.

### Firma

```
Sebastián Cortés
Ing. Civil — Inteligencia de Licitaciones
```

Dos líneas. "Ing. Civil" primero (credibilidad), luego "Inteligencia de Licitaciones" (descriptivo, no marca). NO "IngenIA Licitaciones" (suena a nombre de startup).

---

## 4. Estructura Óptima del Mensaje

### El modelo de 5 líneas

Cada mensaje de WhatsApp tiene exactamente esta estructura:

```
LÍNEA 1: Saludo + quién soy (credibilidad)
LÍNEA 2-3: El golpe (dato específico de SU empresa)
LÍNEA 4: Por qué importa (contexto / implicancia)
LÍNEA 5: CTA (pregunta cerrada sí/no)
---
Firma (2 líneas)
```

### Desglose

**Línea 1 — Saludo + Credibilidad**
```
Hola [nombre], soy Sebastián, ingeniero civil.
```
- Si hay nombre de contacto: "Hola Juan," (primer nombre, sin apellido)
- Si no hay nombre: "Hola,"
- "Ingeniero civil" — no "Sebastián Cortés, ingeniero civil de IngenIA..." (muy largo)
- Esta línea tiene un solo trabajo: que el receptor NO descarte el mensaje como spam

**Líneas 2-3 — El Golpe**
- El dato más impactante que tenemos de su empresa
- SIEMPRE incluye un número ($, %, o conteo)
- SIEMPRE menciona algo específico (nombre de rival, cantidad de licitaciones, meses de inactividad)
- Máximo 2 oraciones. Si necesita 3, el golpe es débil — reestructurar

**Línea 4 — Contexto / Implicancia**
- Por qué el dato importa o qué se encontró detrás
- Una sola oración corta
- Ejemplo: "Encontré un patrón concreto en cómo arma las propuestas."
- NO es la solución — es el teaser de que hay más

**Línea 5 — CTA**
- Pregunta cerrada (sí/no) de **máximo 4 palabras** terminada en `?`
- Ejemplos válidos: "¿Quiere verlo?", "¿Se lo mando?", "¿Le interesa?"
- Ejemplos inválidos: "¿Le gustaría agendar una reunión para revisar esto juntos?" (demasiado largo, demasiado compromiso)
- El CTA pide POCO. No pide una reunión, no pide tiempo, no pide dinero. Pide un "sí" — y el "sí" abre la puerta

### Largo total

- **Máximo 500 caracteres antes de firma** (WhatsApp muestra preview de ~200 chars, el mensaje completo debe leerse en <15 segundos)
- Si no cabe en 5 líneas, el mensaje es demasiado largo — cortar el golpe, no agregar líneas
- Los saltos de línea dobles (`\n\n`) separan cada bloque visual

---

## 5. Anti-Patrones

### Lo que NUNCA debe aparecer en un mensaje

| Anti-patrón | Por qué falla | Ejemplo malo |
|---|---|---|
| Hablar de uno mismo | El receptor no te conoce ni le importa quién eres | "Somos una empresa especializada en..." |
| Ofrecer servicios | Activa la defensa anti-vendedor inmediatamente | "Ofrecemos un diagnóstico gratuito de..." |
| Múltiples CTA | Parálisis de elección — no responde a ninguno | "¿Quiere una reunión o prefiere que le mande un informe?" |
| Mensaje largo | No se lee completo, se descarta | Cualquier cosa >7 líneas |
| Jerga tech/marketing | Suena a spam automatizado | "Nuestra plataforma de IA analiza..." |
| Datos genéricos | No demuestra conocimiento específico | "El rubro de construcción tiene una tasa promedio de..." |
| Halagar sin dato | Suena falso y manipulador | "Vimos que son una empresa importante en su región..." |
| Usar el nombre de la empresa como marca | Suena a empresa, no a persona | "De IngenIA Licitaciones, la solución para..." |
| Pedir reunión en primer contacto | Demasiado compromiso para un desconocido | "¿Podemos agendar 30 minutos esta semana?" |
| Adjuntar archivos | WhatsApp marca como posible spam | PDF o imagen en primer mensaje |

### Tests de calidad

Un mensaje está listo si pasa TODOS estos tests:
1. **Test del gerente apurado**: ¿Se entiende en 10 segundos?
2. **Test del número**: ¿Tiene al menos un dato cuantificado ($, %, conteo)?
3. **Test del espejo**: ¿Podría enviarse a ESTA empresa y solo a esta? (Si sirve para cualquiera, es genérico)
4. **Test del vendedor**: ¿Suena como si estuviera vendiendo algo? Si sí, reescribir
5. **Test del WhatsApp**: ¿Cabe en la pantalla sin scroll? Si no, cortar

---

## 6. Métricas de Éxito

### Benchmarks de cold messaging B2B en Chile

| Métrica | Rango esperado | Fuente |
|---|---|---|
| Tasa de lectura WhatsApp | 85-95% | WhatsApp Business global benchmarks |
| Tasa de respuesta cold (genérico) | 2-5% | Industria B2B LATAM |
| Tasa de respuesta cold (personalizado) | 8-15% | Cold outreach con dato específico |
| Tasa de respuesta target IngenIA | **10-18%** | Dato específico + cuantificado + credibilidad ing. civil |
| Conversión respuesta → reunión | 40-60% | El CTA cerrado facilita la transición |
| Conversión reunión → cliente | 20-30% | Depende de la calidad del diagnóstico PDF |

### Qué medir

1. **Tasa de respuesta por tipo de insight**: ¿rival_fuerte convierte más que default? Rankear insights por efectividad real.
2. **Tasa de respuesta por largo de mensaje**: Confirmar que más corto = más respuesta.
3. **Tiempo de respuesta**: ¿Responden en <1h (buena señal) o en >24h (interés tibio)?
4. **Tipo de respuesta**: "Sí" (ideal), pregunta de seguimiento (muy bueno), "no gracias" (normal), sin respuesta (ajustar).
5. **Tasa de bloqueo**: Si >5%, los mensajes son percibidos como spam — cambiar enfoque urgentemente.

### Cuándo ajustar

- **Semana 1-2**: Enviar los 45 mensajes. Medir respuestas brutas.
- **Semana 3**: Si respuesta <5%, el golpe no está pegando — revisar si los datos son realmente sorprendentes para el receptor.
- **Semana 4**: Si respuesta 5-10%, ajustar CTAs y largo. Si >10%, escalar.
- **Mensual**: Comparar insights — mover recursos hacia los tipos que más convierten.

### Señales de éxito cualitativas

- El receptor pregunta "¿Cómo sabe esto?" → El golpe funcionó
- El receptor reenvía el mensaje a un colega → El dato es valioso
- El receptor pide "más detalle" → Listo para el PDF diagnóstico
- El receptor dice "ya lo sabía" → El golpe no fue suficientemente específico

---

## Apéndice: Jerarquía de Impacto Emocional por Insight

```
ALTO IMPACTO (respuesta esperada 12-18%):
  1. rival_fuerte    — Rabia + curiosidad (rival con nombre + pesos)
  2. rival_recurrente — Alerta + curiosidad (patrón emergente)
  3. loss_concentrado — Intriga ("no es precio")

MEDIO IMPACTO (respuesta esperada 8-12%):
  4. win_rate_gap_LP — Frustración + oportunidad (brecha cuantificada)
  5. inactivo        — Urgencia + FOMO (el mercado sigue sin ellos)
  6. lp_alto (WR<rubro) — Ambición frustrada

BAJO IMPACTO (respuesta esperada 5-8%):
  7. wr_bajo_lp      — Frustración concreta
  8. wr_bajo         — Resignación buscando explicación
  9. lp_alto (WR>=rubro) — Orgullo + curiosidad (optimización)
  10. rival_unico    — Curiosidad moderada
  11. default        — Curiosidad leve (benchmark)
```

Esta jerarquía debe validarse con datos reales en las primeras 4 semanas de envío.
