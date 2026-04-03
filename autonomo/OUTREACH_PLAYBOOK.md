# Outreach Playbook — Operacion WhatsApp Ola 1

> **Fuente de verdad operativa.** Este documento define exactamente como se ejecutan los primeros 45 mensajes de cold outreach. Cada decision tiene un por que. Si hay conflicto con otro documento, este manda para la operacion; POSITIONING.md manda para el copy.

---

## 1. Estructura de cuentas

Tres cuentas de WhatsApp, cada una con un angulo argumental dominante. Esto evita que un mismo numero envie mensajes con tonos contradictorios y permite segmentar respuestas.

### Cuenta A — Rivalry (competencia directa)

| Tipo de insight | Cantidad | Por que en esta cuenta |
|---|---|---|
| rival_fuerte | 2 | Rival dominante: el golpe mas fuerte del arsenal |
| rival_recurrente | 7 | Patron emergente: alerta temprana |
| rival_unico | 5 | Rival identificado con perdidas recurrentes |
| default | 1 | Benchmark honesto para completar la cuenta |
| **Total** | **15** | |

**Tono dominante:** "Se quien les esta ganando y encontre como lo hace."

### Cuenta B — Performance (rendimiento en licitaciones)

| Tipo de insight | Cantidad | Por que en esta cuenta |
|---|---|---|
| lp_alto | 9 | Volumen alto en licitaciones de valor |
| win_rate_gap_LP | 5 | Brecha cuantificable en contratos grandes |
| wr_bajo_lp | 1 | Win rate bajo en LP especificamente |
| **Total** | **15** | |

**Tono dominante:** "Sus numeros en licitaciones grandes dicen algo que no estan viendo."

### Cuenta C — Inactivity (inactividad y brecha general)

| Tipo de insight | Cantidad | Por que en esta cuenta |
|---|---|---|
| inactivo | 10 | Sin postular 6+ meses |
| win_rate_gap_LP | 2 | Excedente de win_rate_gap que no cabe en B |
| wr_bajo | 1 | Win rate bajo general |
| default | 2 | Benchmarks honestos para completar |
| **Total** | **15** | |

**Tono dominante:** "El mercado sigue moviendose y sus rivales estan activos."

### Logica de asignacion

1. Cada lead tiene un `insight_tipo` asignado por el motor de mensajes (v7+).
2. Los tipos se asignan a cuentas segun la tabla anterior.
3. Cuando un tipo se reparte entre dos cuentas (win_rate_gap_LP: 5 en B + 2 en C; default: 1 en A + 2 en C), se asignan en orden de `outreach_rank`: los de mayor prioridad van a la cuenta donde el tipo es protagonista.
4. Dentro de cada cuenta, los leads se ordenan por `outreach_rank` ascendente (1 = mayor prioridad).

---

## 2. Calendario Ola 1

La Ola 1 envía los 45 mensajes en 3 dias habiles. Cada dia, cada cuenta envia 5 mensajes.

| Dia | Fecha | Cuenta A | Cuenta B | Cuenta C | Total dia |
|---|---|---|---|---|---|
| Dia 1 | Lunes | Leads 1-5 | Leads 1-5 | Leads 1-5 | 15 |
| Dia 2 | Martes | Leads 6-10 | Leads 6-10 | Leads 6-10 | 15 |
| Dia 3 | Miercoles | Leads 11-15 | Leads 11-15 | Leads 11-15 | 15 |
| **Total** | | **15** | **15** | **15** | **45** |

### Horarios de envio

- **Ventana:** 09:00 a 12:00 hrs (Chile continental, UTC-4).
- **Espaciado:** minimo 15 minutos entre mensajes por cuenta.
- **Orden:** por `batch_order` dentro de cada CSV (1 a 5).
- **Dias:** solo lunes a viernes. Nunca fines de semana ni feriados.

### Por que 5 por cuenta por dia

- WhatsApp Business penaliza envios masivos. 5 mensajes por numero por dia es el umbral seguro.
- 3 cuentas x 5 mensajes = 15 por dia, ritmo sostenible sin riesgo de bloqueo.
- 3 dias completa los 45 leads verificados de la Ola 1.

---

## 3. Orden de prioridad

Dentro de cada cuenta, los leads se ordenan por `outreach_rank` ascendente.

El `outreach_rank` viene del pipeline (16_verify_contacts.py) y pondera:
- 60% business score (score combinado del motor de 9 dimensiones)
- 40% contact score (calidad del dato de contacto: celular, email, nombre, etc.)

**Rank 1 = lead con mayor probabilidad de conversion + mejor dato de contacto.**

El batch diario respeta este orden: dia 1 recibe los top 5 de cada cuenta, dia 2 los siguientes 5, dia 3 los ultimos 5.

---

## 4. Regla post-45: no seguir hasta reponer

Despues de enviar los 45 mensajes de Ola 1:

1. **STOP.** No enviar mas mensajes frios hasta tener leads nuevos verificados.
2. **Reponer:** Ejecutar el pipeline completo (01→16) con datos actualizados para generar nuevos leads con `wsp_probable = "alta"`.
3. **Verificar:** Los nuevos leads deben pasar por el generador de mensajes (v7+) y por `generar_lote_diario.py` antes de enviarse.
4. **Recien entonces** se arma la Ola 2 con el mismo esquema de 3 cuentas x 5/dia.

**Por que:** Enviar mensajes a leads no verificados (telefono dudoso, sin celular, sin datos de negocio) desperdicia el numero de WhatsApp y baja la tasa de respuesta. Mejor calidad que cantidad.

---

## 5. Regla de follow-up

Si un lead **no responde en 48 horas habiles** despues del primer mensaje:

1. **Enviar 1 follow-up** por la misma cuenta que envio el mensaje original.
2. **Maximo 1 follow-up** por lead. Si no responde al follow-up, no insistir.
3. **Tono del follow-up:** mas corto que el original, sin repetir el dato. Ejemplo:

```
Hola [nombre], le escribi hace un par de dias sobre un patron
que encontre en sus licitaciones.

Si le interesa, se lo mando por aca mismo.

Sebastian Cortes
Ing. Civil — Inteligencia de Licitaciones
```

4. **Horario:** mismo horario que el mensaje original (09:00-12:00 hrs).
5. **Dia:** el follow-up se envia el dia habil siguiente a cumplirse las 48h. Ejemplo: si el mensaje original fue el lunes, el follow-up se envia el jueves (48h habiles = miercoles, envio jueves).

### Follow-ups por dia de envio original

| Mensaje original | 48h se cumplen | Follow-up se envia |
|---|---|---|
| Lunes | Miercoles | Jueves |
| Martes | Jueves | Viernes |
| Miercoles | Viernes | Lunes siguiente |

---

## 6. Regla de respuesta

Cuando un lead **responde** (cualquier respuesta, positiva o negativa):

1. **Responder dentro de 12 horas habiles.** No es necesario responder al instante. El servicio es asincrono.
2. **Sin agenda.** No ofrecer llamada, reunion ni videollamada. Si el cliente pide una llamada, coordinar — pero nunca ofrecer proactivamente.
3. **Canal:** responder por el mismo WhatsApp donde se recibio la respuesta.
4. **Tono:** profesional, directo, primera persona. "Le preparo el detalle y se lo mando por aca."
5. **Siguiente paso:** si muestra interes, preparar el diagnostico competitivo (PDF 10 paginas) y enviarlo por WhatsApp + email.

### Respuestas tipo

**Si muestra interes ("si", "mandelo", "me interesa"):**
```
Perfecto. Le preparo un resumen con los datos especificos de [empresa]
y se lo envio por aca en las proximas 48 horas.

Necesito confirmar: [dato que falte, ej: email para enviar el PDF completo].
```

**Si pide mas informacion ("que es esto", "como funciona"):**
```
Trabajo con datos publicos de Mercado Publico — 1.8 millones de registros
de licitaciones de construccion. Cruzo ese historial por RUT para
identificar donde cada empresa tiene mayor probabilidad de adjudicarse
y contra quien compite.

El resultado es un informe de 10 paginas con su posicion competitiva,
rivales recurrentes y oportunidades especificas. Se lo envio por
WhatsApp y email, sin necesidad de coordinar agenda.

Cuesta $250.000 + IVA. Una sola adjudicacion extra al ano cubre
el costo varias veces.

¿Le preparo uno?
```

**Si responde negativamente ("no gracias", "no me interesa"):**
```
Entendido. Si en algun momento le sirve, me tiene por aca.

Saludos,
Sebastian Cortes
```

---

## 7. Metricas de seguimiento

Registrar en una planilla simple (o en el mismo Excel de leads):

| Metrica | Donde registrar |
|---|---|
| Mensaje enviado (si/no) | Columna `enviado` en leads_verificados_v7.xlsx |
| Fecha de envio | Columna `fecha_envio` |
| Respuesta recibida (si/no) | Columna `respondio` |
| Tipo de respuesta (positiva/negativa/pregunta) | Columna `tipo_respuesta` |
| Follow-up enviado (si/no) | Columna `followup_enviado` |
| Conversion (pidio diagnostico) | Columna `conversion` |

### KPIs objetivo Ola 1

| KPI | Objetivo | Calculo |
|---|---|---|
| Tasa de entrega | >95% | Enviados sin error / Total enviados |
| Tasa de respuesta | >15% | Respondieron / Total enviados |
| Tasa de interes | >8% | Respuestas positivas / Total enviados |
| Conversion a diagnostico | >4% | Pidieron diagnostico / Total enviados |
| Tiempo medio de respuesta | <6h | Promedio entre envio y primera respuesta del lead |

**Benchmark:** en cold outreach B2B por WhatsApp en Chile, una tasa de respuesta del 15% y conversion del 4% son resultados solidos para un primer contacto sin relacion previa.

---

## 8. Generacion de lotes diarios

El script `generar_lote_diario.py` (en la raiz del proyecto) automatiza la creacion de los CSVs de envio:

```
python generar_lote_diario.py
```

**Input:** `lead_scoring/data/output/leads_verificados_v7.xlsx` (hoja "WhatsApp Listos")

**Output:** 9 archivos CSV en `lead_scoring/data/output/lotes/`:
```
lote_cuenta_A_dia1.csv    lote_cuenta_B_dia1.csv    lote_cuenta_C_dia1.csv
lote_cuenta_A_dia2.csv    lote_cuenta_B_dia2.csv    lote_cuenta_C_dia2.csv
lote_cuenta_A_dia3.csv    lote_cuenta_B_dia3.csv    lote_cuenta_C_dia3.csv
```

**Columnas de cada CSV:**
- `empresa` — nombre comercial humanizado
- `rut` — identificador unico
- `telefono` — numero normalizado (+56XXXXXXXXX)
- `wsp_link` — link wa.me listo para abrir
- `mensaje` — texto completo del mensaje
- `insight_tipo` — tipo de insight asignado
- `template_variant` — variante de template usada (A/B/C/D)
- `send_day` — dia de envio (1, 2 o 3)
- `batch_order` — orden dentro del dia (1 a 5)

Cada CSV tiene exactamente 5 filas. Solo abrir, copiar mensaje, y enviar.

---

## 9. Checklist pre-envio

Antes de enviar cada lote diario:

- [ ] Abrir el CSV del dia y verificar que los 5 mensajes tienen telefono valido
- [ ] Verificar que cada mensaje tiene dato duro ($ o %)
- [ ] Verificar que ningun mensaje menciona: servicio, diagnostico, IA, plataforma, llamada, reunion
- [ ] Verificar que la firma es "Sebastian Cortes / Ing. Civil — Inteligencia de Licitaciones"
- [ ] Verificar que cada wsp_link abre correctamente en el navegador
- [ ] Registrar hora de envio de cada mensaje

---

## 10. Reglas absolutas de outreach

1. **CERO referencias proactivas a llamada, reunion, agenda o videollamada.** Solo coordinar si el cliente lo pide explicitamente.
2. **Sin precio en el primer mensaje.** El outreach es insight puro. El precio se comunica solo cuando el prospecto lo pide.
3. **Presentarse como ingeniero:** "Soy Sebastian Cortes, ingeniero civil." Sin "de IngenIA Licitaciones".
4. **Firma:** "Sebastian Cortes / Ing. Civil — Inteligencia de Licitaciones"
5. **Cada mensaje tiene 1 dato duro ($ o %).** Sin excepciones.
6. **CTA: pregunta cerrada de max 4 palabras** terminada en "?".
7. **Max 5 lineas + firma.** Si no cabe, cortar contexto, nunca el dato.
8. **Nunca usar:** score, ranking, pipeline, algoritmo, modelo, cluster, ML, IA, plataforma, herramienta, servicio, diagnostico.
9. **Tratamiento:** "usted" (Chile formal B2B). Sin emojis. Sin "estimado/a". Sin "le saluda".
10. **Responder en 12h habiles.** El servicio es asincrono, no instantaneo.

---

*Documento operativo Ola 1 — 2026-04-03*
*Derivado de autonomo/POSITIONING.md (fuente de verdad de copy)*
