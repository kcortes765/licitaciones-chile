# Guion de Venta WhatsApp — IngenIA Licitaciones

**Version:** 2.0 Premium
**Autor:** Sebastian Cortes, Ing. Civil UCN
**Uso:** Interno. No compartir con prospectos.

Este guion convierte un cold message en un cliente de $190K-$490K/mes. Cada paso esta escrito para que lo ejecute alguien que entiende de construccion y licitaciones publicas, no un vendedor generico. El tono es de colega ingeniero senior que encontro algo interesante en los datos, no de consultor que vende un servicio.

**Regla de oro:** Nunca enviar un mensaje sin al menos un dato concreto ($, %, cantidad). Si no hay dato, no escribir.

---

## ESTRUCTURA DEL FUNNEL

```
Paso 1: Mensaje cold (generado automaticamente — NO TOCAR)
  | responde
Paso 2: Enganche — demostrar dominio del sector
  | pide mas
Paso 3: Mini-analisis por chat — preview del producto
  | interesado
Paso 4: Cierre — pricing + descripcion del entregable
  | acepta
Paso 5: Entrega del PDF + resumen ejecutivo
  | satisfecho
Paso 6: Upsell natural al servicio mensual
```

Tiempo promedio del funnel: 2-7 dias. No acelerar.

---

## PASO 1 — Mensaje inicial

El primer mensaje viene del generador automatico (`mensajes_wsp_v6.txt` o `leads_verificados.xlsx`). No se escribe manualmente. Esta disenado con datos reales del prospecto y sigue la estructura:

```
Hola [NOMBRE], soy Sebastian, ingeniero civil.
[GOLPE: dato concreto impactante]
[CONTEXTO: 1 linea de por que importa]
[CTA: pregunta cerrada si/no]

Sebastian Cortes
IngenIA Licitaciones
```

**No modificar el Paso 1.** Si el mensaje no genera respuesta, ir a la secuencia de follow-up al final de este documento.

---

## PASO 2 — Responden al primer mensaje

El objetivo de este paso es uno solo: que pidan mas informacion. No vender. No explicar que hacemos. Demostrar que sabemos mas de su empresa que ellos mismos.

### Caso A: Interes directo

**Trigger:** "Cuentame mas", "Que encontraste", "Que vieron", "Interesante"

```
Mire, lo que encontre revisando el historial de [EMPRESA] en
Mercado Publico es un patron que se repite.

De las [N] licitaciones donde no fueron adjudicados, [X] las
gano [RIVAL]. Eso es el [X]% de sus no-adjudicaciones contra
un solo competidor.

En licitaciones de construccion publica, cuando un rival
concentra ese porcentaje de victorias contra una misma empresa,
generalmente hay algo estructural: evaluacion tecnica, precio
referencial, o equipo clave que marca la diferencia.

Le puedo mostrar con una licitacion puntual donde se ve claro.
Quiere?
```

**Nota:** Si no hay rival dominante, usar el dato principal del insight (WR bajo, inactividad, concentracion de perdidas). Adaptar manteniendo la estructura: dato → patron → oferta de mostrar.

### Caso B: Curioso o esceptico

**Trigger:** "De donde sacas eso?", "Quien eres?", "Como saben eso?"

```
Soy Sebastian Cortes, ingeniero civil UCN. Llevo anos
trabajando con datos de Mercado Publico — las bases, actas
de adjudicacion, historiales de participacion.

Todo es informacion publica. La diferencia es que la mayoria
de las constructoras no la cruza sistematicamente. Yo la
proceso completa: [X] licitaciones de construccion de los
ultimos [Y] anos, todas las adjudicaciones, todos los
competidores.

En el caso de [EMPRESA], hay [HALLAZGO BREVE en 1 linea].
Si le parece, le muestro con un ejemplo concreto.
```

**Clave:** Presentarse como ingeniero, no como empresa. Mencionar la escala de datos procesados (1.8M registros). Cerrar siempre con oferta de mostrar un ejemplo.

### Caso C: Respuesta corta positiva

**Trigger:** "Dale", "Ok", "Que mas", "A ver", "Bueno"

No pedir permiso. Ir directo al Paso 3.

```
Le cuento con un ejemplo concreto.
```

E inmediatamente enviar el mini-analisis del Paso 3.

---

## PASO 3 — Mini-analisis por chat (demo del producto)

Este es el momento critico del funnel. El prospecto esta evaluando si lo que tenemos es generico o real. El mini-analisis debe ser tan especifico que la reaccion sea: "esto no se puede inventar".

### Solicitar el caso

```
Para que sea mas util, digame: hay alguna licitacion reciente
donde hayan participado y quiera entender que paso?

Si no tiene una en mente, le miro la mas relevante que tenemos
en el historial de [EMPRESA].
```

Si el prospecto no da codigo, elegir la licitacion perdida mas relevante (monto alto, rival dominante, reciente).

### Estructura fija del mini-analisis

**IMPORTANTE:** Generar los datos con el pipeline ANTES de responder. Cada campo debe ser verificado contra los datos reales. Seguir esta estructura exacta:

```
Revise la licitacion [CODIGO] — "[TITULO CORTO]".

- Tipo: [LP/LE/L1] | Region: [REGION] | Monto: $[X]M
- Adjudico: [EMPRESA GANADORA]
- Participaron: [N] empresas, incluida [EMPRESA]
- Criterio dominante: [evaluacion tecnica / precio / plazo]
  segun el acta de adjudicacion
- Lo que probablemente definio el resultado: [observacion
  concreta — ej: "la diferencia fue de 3 puntos en evaluacion
  tecnica, no en precio"]
- Patron: [RIVAL] ya gano [X] de las ultimas [Y] donde
  [EMPRESA] tambien participo. No es casualidad.
- Oportunidad: [que mejorar — ej: "las constructoras que ganan
  consistentemente en LP sobre $100M en esta region tienden a
  diferenciarse en [equipo clave / metodologia / plazo]"]

Esto es 1 licitacion. El diagnostico completo cubre las [N]
donde han participado, sus [X] rivales principales, y cuanto
les esta costando en pesos el patron actual.

Le interesa ver el cuadro completo?
```

**Reglas del mini-analisis:**
- Minimo 6, maximo 8 bullets
- Siempre incluir monto en pesos
- Siempre nombrar al ganador
- Siempre cerrar con "esto es 1 licitacion" para anclar valor del diagnostico
- El ultimo bullet debe ser una oportunidad, no un problema
- NO incluir el precio aqui. Esperar a que pregunten.

---

## PASO 4 — Cierre y pricing

### Escenario A: "Cuanto cuesta?" / "Cual es el precio?"

```
El diagnostico competitivo completo: $190.000 + IVA.

Que recibe exactamente:
- PDF de 6 paginas con graficos profesionales
- Posicionamiento de [EMPRESA] vs el mercado (percentil exacto)
- Radar de 8 dimensiones de desempeno
- Analisis detallado de sus [X] rivales principales
  (quien le gana, en que, con que frecuencia)
- Costo de oportunidad: cuanto dejan en la mesa
  al win rate actual vs el promedio del rubro
- Recomendaciones especificas para las proximas licitaciones

No es un informe generico. Esta construido con los [N]
registros reales de [EMPRESA] en Mercado Publico.

Plazo de entrega: 24-48 horas habiles.
Le cuadra?
```

### Escenario B: Acepta — "Si, como pago?"

```
Perfecto. Los datos de transferencia:

Banco: [BANCO]
Tipo: Cuenta corriente
Numero: [NUMERO]
RUT: [RUT_EMPRESA]
Nombre: Sebastian Cortes [o razon social]
Email: sebastian.cortes.ing@gmail.com
Monto: $226.100 (IVA incluido)

En cuanto me confirme el deposito, arranco con el diagnostico.
Se lo tengo en [PLAZO — 24-48 hrs habiles].
```

### Escenario C: Confirmacion de pago

```
Recibido, gracias.

Le tengo el diagnostico completo de [EMPRESA] el [FECHA].
Si necesita algo antes, me avisa.
```

**Nota:** Mensaje corto. No agradecer excesivamente. Tono de profesional que va a trabajar.

### Escenario D: Quiere el tier avanzado

Si el prospecto tiene operacion grande (>$500M en licitaciones, >20 participaciones) o pregunta por algo mas completo:

```
Para una empresa del tamano de [EMPRESA], le recomiendo el
analisis competitivo avanzado: $250.000 + IVA.

Incluye todo lo del diagnostico base mas:
- Analisis licitacion por licitacion de sus [X] derrotas clave
- Benchmark contra el top 10% de constructoras en su segmento
- Estrategia de posicionamiento por tipo (LP vs LE vs L1)
- Recomendaciones de portafolio: donde concentrar esfuerzo

Mismo plazo: 48 horas habiles. Le sirve?
```

---

## PASO 5 — Entrega del PDF

Momento clave para la retencion. El PDF debe llegar con un resumen que demuestre que lo leimos y entendemos.

```
Listo. Aqui esta el diagnostico de [EMPRESA]:
[LINK o archivo adjunto]

Los 3 hallazgos principales:

1. [HALLAZGO 1 — ej: "Su win rate de [X]% esta [Y] puntos
   bajo el promedio del rubro. Eso equivale a ~[Z] contratos
   que se les estan escapando por ano."]
2. [HALLAZGO 2 — ej: "[RIVAL] les ha ganado [N] de las
   ultimas [M] licitaciones. Hay un patron claro en como
   se diferencia."]
3. [HALLAZGO 3 — ej: "Tienen una ventana de oportunidad en
   [TIPO/REGION] donde la competencia es menor y su perfil
   calza bien."]

Le recomiendo mirar la pagina 5 primero — ahi esta el costo
de oportunidad en pesos. Es el numero que mas contexto da.

Si tiene alguna duda sobre los datos o quiere profundizar
en algun punto, me escribe y lo revisamos.
```

**Reglas de entrega:**
- Siempre incluir 3 hallazgos resumidos (no mas, no menos)
- Apuntar a una pagina especifica del PDF para generar engagement
- No ofrecer llamada. Solo si el cliente la pide.
- No pedir feedback inmediato. Dejar que procese.

---

## PASO 6 — Upsell al servicio mensual

**Timing:** 24-48 horas despues de entregar el PDF. No inmediatamente. Dejar que el prospecto lo lea y absorba el valor.

### Mensaje de transicion

```
[NOMBRE], una cosa que queria comentarle.

Lo que le entregue es una foto del historial hasta hoy.
Pero el mercado de licitaciones se mueve semana a semana
— solo en [REGION] se publican [~X] licitaciones de
construccion por mes.

Si le interesa, tenemos un servicio de monitoreo continuo:

- Alerta semanal con las licitaciones nuevas que calzan
  con el perfil de [EMPRESA] (tipo, monto, region)
- Seguimiento de rivales: cuando [RIVAL] y sus otros
  competidores clave participan o ganan
- Recomendacion de cuales perseguir y cuales no
  (basado en su historial de exito por tipo y monto)
- Soporte directo por WhatsApp

$490.000/mes + IVA. Sin contrato de permanencia — si un
mes no le sirve, lo cortamos sin problema.

El objetivo es que cada licitacion donde participen, lo
hagan con toda la informacion sobre la mesa.

Le interesa que le cuente como funciona en la practica?
```

### Si pregunta "Que incluye exactamente?"

```
Cada semana le llega:

1. Reporte de oportunidades: las [3-5] licitaciones nuevas
   en [REGION] que calzan con lo que [EMPRESA] ha ganado
   antes (tipo, rango de monto, criterio de evaluacion)

2. Movimiento de rivales: si [RIVAL] o sus otros
   competidores principales participaron o ganaron algo
   esa semana

3. Recomendacion: cuales vale la pena perseguir segun
   su perfil — no todas las licitaciones son iguales, y
   el costo de preparar una propuesta no es menor

4. Soporte: cualquier duda sobre una licitacion puntual
   me la consulta directo

En la practica, el valor esta en no perder oportunidades
buenas y no gastar recursos en las que no calzan.

Arrancamos la proxima semana?
```

---

## OBJECIONES

### 1. "Es caro" / "$190K es mucho"

```
Entiendo. Pongamoslo en contexto:

El monto promedio de las licitaciones donde [EMPRESA]
participa es de $[X]M. Adjudicarse una sola de esas
cubre el diagnostico [X] veces.

La pregunta real no es si $190K es mucho — es cuanto les
cuesta NO saber por que [RIVAL] les gano [N] veces.
Si la respuesta es "porque tienen mejor precio", perfecto,
no necesitan nada. Pero si no tienen claro que los
diferencia, ahi hay un gap que se paga solo.

Que parte le hace ruido — el monto o lo que incluye?
```

### 2. "Lo veo despues" / "Ahora no es buen momento"

```
Sin problema. Le propongo algo concreto: le escribo
el [DIA + 2 SEMANAS] para retomar. Si para entonces
tienen alguna licitacion en carpeta, el diagnostico
les puede servir para prepararla mejor.

Le parece?
```

**Nota:** Siempre fijar fecha especifica. Si no da fecha, anotar y contactar en 14 dias.

### 3. "Es una IA?" / "Esto lo hace un robot?"

```
Soy Sebastian Cortes, ingeniero civil de la UCN.
Trabajo con herramientas de analisis de datos para
procesar la informacion publica de Mercado Publico
— similar a como un ingeniero estructural usa SAP2000
o un presupuestador usa Presto.

La diferencia es que en vez de analizar una licitacion
a la vez, proceso el registro completo: [1.8M+] registros
historicos de licitaciones de construccion.

Las recomendaciones las reviso y valido yo personalmente
antes de entregarlas. Lo automatizado es el procesamiento,
no el criterio.
```

### 4. "Ya sabemos leer bases" / "Nosotros ya hacemos eso"

```
No me cabe duda — llevan [N] licitaciones, claramente
saben como funciona el sistema.

La diferencia es que esto no es leer sus propias bases.
Es cruzar sistematicamente los resultados de adjudicacion
de todas las constructoras que compiten en su segmento.

Por ejemplo: sabe en cuantas licitaciones [RIVAL] participo
el ultimo ano? O cual es su tasa de adjudicacion en LP
sobre $[X]M? Esa es la informacion que normalmente no se
tiene, porque requiere procesar miles de registros.

Ese cruce es lo que entrega el diagnostico.
```

### 5. "No licitamos mucho" / "Participamos poco"

```
Justamente — si participan poco, cada licitacion donde
deciden entrar tiene que ser la correcta.

El diagnostico le muestra exactamente donde [EMPRESA]
tiene mejor probabilidad de adjudicarse: por tipo
(LP, LE, L1), por rango de monto, por region, y contra
que competidores.

Es mas util para quien licita selectivamente que para
quien postula a todo. Porque ustedes no pueden darse
el lujo de gastar recursos en una que no calza.

Quiere que le muestre un ejemplo con una de las [N]
donde han participado?
```

### 6. "Como se que funciona?" / "Que garantia tengo?"

```
El mini analisis que le hice recien — esa licitacion
[CODIGO] donde [RIVAL] se adjudico — es exactamente
el mismo tipo de analisis que hace el diagnostico completo.

Si esos datos le parecieron correctos y utiles, el
diagnostico es eso mismo multiplicado por todo el
historial de [EMPRESA]: [N] licitaciones, [X] rivales,
con graficos comparativos y recomendaciones.

No tengo garantia de que van a ganar la proxima
licitacion. Lo que si puedo asegurar es que van a
entrar con mas informacion que el [X]% de las
constructoras que compiten contra ustedes.
```

---

## SEGUIMIENTO (si no responden)

Cada follow-up lleva un dato concreto nuevo o reformulado. Nunca enviar "le escribia para saber si vio mi mensaje".

### Follow-up 1 — 48 horas despues del primer mensaje

```
[NOMBRE], Cortes nuevamente.

Le agrego un dato que me parecio relevante: de las
constructoras activas en [REGION] en el segmento de
[EMPRESA], el promedio de adjudicacion es [X]%.
[EMPRESA] esta en [Y]%.

Eso son [DIFERENCIA] puntos. En plata, equivale a
aproximadamente $[Z]M anuales en contratos que se
les estan yendo.

Si quiere, le cuento donde esta el gap.

Sebastian Cortes
IngenIA Licitaciones
```

### Follow-up 2 — 5 dias despues del primer mensaje

```
[NOMBRE], ultimo dato y lo dejo tranquilo.

Revise las [N] licitaciones mas recientes en [REGION]
donde participo [EMPRESA]. En [X] de ellas, [RIVAL]
tambien estaba y se adjudico.

Hay un patron en como [RIVAL] estructura sus propuestas
en ese tipo de licitaciones. Es algo que se puede ver
cuando se cruzan todos los resultados.

Si en algun momento quiere entenderlo, me avisa.

Sebastian Cortes
IngenIA Licitaciones
```

### Follow-up 3 — 10 dias despues (cierre elegante)

```
[NOMBRE], cierro el tema por ahora.

Le dejo un numero para que lo tenga en mente: cada punto
de win rate para una constructora del tamano de [EMPRESA]
equivale a ~$[X]M anuales en contratos adjudicados.

Si mas adelante estan evaluando una licitacion puntual
o quieren entender por que ciertos rivales les ganan
repetidamente, escribame directo.

Exito en las proximas.

Sebastian Cortes
IngenIA Licitaciones
```

### Follow-up 4 — 30 dias (reactivacion con dato fresco)

**Solo enviar si hay un dato nuevo real.** Si no hay nada nuevo, no reactivar.

```
[NOMBRE], espero que esten bien.

Tengo un dato fresco que puede interesarle: [DATO NUEVO
— elegir uno de estos segun disponibilidad:
  a) "en [REGION] se publicaron [X] licitaciones de
     construccion en las ultimas 4 semanas que calzan
     con el perfil de [EMPRESA]"
  b) "[RIVAL] se adjudico [X] contratos por $[Y]M
     este mes en su segmento"
  c) "hay [X] licitaciones LP abiertas ahora mismo en
     [REGION] en el rango de monto donde [EMPRESA]
     ha ganado antes"]

Si quieren una revision rapida de como esta el mercado
para ustedes hoy, se la mando por aca mismo.

Sebastian Cortes
IngenIA Licitaciones
```

---

## REGLAS GENERALES

1. **Nunca enviar el PDF gratis.** El valor gratuito es texto en el chat. El PDF es el producto.
2. **Nunca mencionar:** score, cluster, modelo, pipeline, ML, IA, algoritmo, ranking, plataforma.
3. **Nunca afirmar causalidad.** Usar "sugiere", "se observa", "los datos muestran", "hay un patron".
4. **Nunca llamar para vender.** La venta ocurre por chat. Llamada solo si el cliente la pide.
5. **Un mensaje a la vez.** Esperar respuesta antes de enviar el siguiente.
6. **Generar los datos del Paso 3 con el pipeline ANTES de responder.** No inventar numeros.
7. **Cada mensaje debe tener minimo 1 dato concreto** ($, %, cantidad). Si no hay dato, no enviar.
8. **Nunca usar "estimado/a".** Siempre nombre de pila o "Hola," si no hay nombre.
9. **Precio es $190K base, $250K avanzado, $490K/mes mensual.** No negociar, no hacer descuentos.
10. **Si el prospecto dice "no me escriban mas", respetar inmediatamente** y marcar como no-contactar.

---

*IngenIA Licitaciones — Guion de venta WhatsApp v2. Uso interno exclusivo.*
*Sebastian Cortes, Ing. Civil UCN*
