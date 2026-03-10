# Prompts para Análisis de Bases de Licitación

## Contexto para IA
Estos prompts están diseñados para Claude Opus 4.6 o Gemini 3.1 Pro.
Pegar la base de licitación (PDF/texto) junto con el prompt.

---

## Prompt 1: Análisis Estratégico Completo

```
Eres un ingeniero civil chileno senior especializado en licitaciones públicas MOP.

Analiza la siguiente base de licitación y genera un informe estratégico con:

1. RESUMEN EJECUTIVO (máximo 5 líneas)

2. REQUISITOS DE ADMISIBILIDAD
   - Lista todos los documentos y requisitos obligatorios para no ser descalificado
   - Marca con ⚠️ los que son fáciles de omitir o confundir

3. HALLAZGOS CRÍTICOS
   - Normas NCh o especificaciones técnicas que hayan cambiado recientemente
   - Requisitos inusuales o que difieran del estándar
   - Cláusulas contractuales con riesgo financiero (multas, garantías, plazos)
   - Puntos donde la mayoría de los postulantes pierde puntaje

4. NORMATIVA EXIGIDA
   - Lista completa de normas NCh referenciadas
   - Identifica cuáles tienen versiones actualizadas post-2020
   - Señala interdependencias entre normas

5. RÚBRICA DE EVALUACIÓN TÉCNICA
   - Criterios de evaluación y ponderación
   - Análisis de dónde se concentran los puntos
   - Recomendaciones para maximizar puntaje en cada criterio

6. ALERTAS DE RIESGO
   - Plazos irrealistas
   - Multas desproporcionadas
   - Requisitos técnicos que limitan competencia
   - Condiciones que podrían generar problemas en ejecución

7. RECOMENDACIONES ESTRATÉGICAS
   - Top 5 acciones concretas para maximizar probabilidad de adjudicación
   - Puntos diferenciadores potenciales

Sé específico, cita artículos y páginas de la base. No hagas resumen genérico.
```

---

## Prompt 2: Detección Rápida de Hallazgos (para Loom)

```
Analiza esta base de licitación rápidamente y dame SOLO los 3 hallazgos
más importantes que un postulante promedio podría pasar por alto.

Para cada hallazgo:
- Qué dice exactamente la base (cita artículo/página)
- Por qué es crítico
- Qué pasa si lo ignoras (descalificación, pérdida de puntaje, multa)

Formato: directo, sin introducción, solo los 3 hallazgos.
```

---

## Prompt 3: Verificación Normativa

```
De la siguiente base de licitación, extrae TODAS las normas técnicas
mencionadas (NCh, ASTM, ACI, etc.) y para cada una:

1. Código y nombre de la norma
2. Versión/año que exige la base
3. Si existe versión más reciente
4. Si hay inconsistencias entre lo que pide la base y la norma vigente
5. Normas relacionadas que deberían cumplirse pero no están mencionadas

Formato tabla.
```

---

## Prompt 4: Análisis de Rúbrica de Evaluación

```
Analiza la rúbrica de evaluación técnica de esta base de licitación.

Para cada criterio de evaluación:
1. Qué pide exactamente
2. Cuántos puntos vale
3. Qué diferencia obtener puntaje máximo vs mínimo
4. Error más común que cometen los postulantes en este criterio
5. Recomendación específica para maximizar puntaje

Ordena de mayor a menor impacto en puntaje total.
```

---

## Prompt 5: Generación de Script para Loom

```
Basado en este hallazgo de una base de licitación:

[PEGAR HALLAZGO]

Genera un script de 60 segundos para un video Loom dirigido al
gerente de una constructora mediana. El tono debe ser:
- Profesional pero directo
- Sin tecnicismos innecesarios
- Enfocado en el impacto práctico (puntaje, descalificación, plata)
- Cierre con invitación a conversar

Estructura: saludo (5seg) → contexto (10seg) → hallazgo (30seg) → cierre (15seg)
```

---

## Prompt 6: Ghostwriting Oferta Técnica

```
Eres un ingeniero civil chileno senior redactando una propuesta técnica
para una licitación MOP.

Con base en los siguientes datos del proyecto:
[PEGAR DATOS TÉCNICOS DEL CLIENTE]

Y los requisitos de la base:
[PEGAR REQUISITOS DE EVALUACIÓN TÉCNICA]

Redacta las siguientes secciones:

1. METODOLOGÍA DE TRABAJO
   - Enfoque técnico
   - Etapas del proyecto
   - Actividades críticas
   - Metodologías específicas

2. PROGRAMA DE TRABAJO / CRONOGRAMA DESCRIPTIVO
   - Secuencia lógica de actividades
   - Hitos principales
   - Ruta crítica

3. PLAN DE CALIDAD
   - Procedimientos de control
   - Ensayos y verificaciones
   - Documentación

4. PLAN DE GESTIÓN AMBIENTAL Y SEGURIDAD
   - Medidas de mitigación
   - Protocolos de seguridad

Redacta como ingeniero senior chileno. Lenguaje técnico pero claro.
Responde exactamente a lo que pide la rúbrica de evaluación.
Máximo 50 páginas.
```

---

## Prompt 7: Mensaje WhatsApp Personalizado

```
Genera un mensaje de WhatsApp de máximo 4 líneas para:

Empresa: [nombre]
Licitación: [código y nombre]
Fecha cierre: [fecha]
Hallazgo: [hallazgo en 1 línea]

El mensaje debe:
- Presentarme como "Sebastián Cortés, ing. civil"
- Mencionar SU licitación específica
- Dar un adelanto del hallazgo sin revelarlo completo
- Cerrar con pregunta para abrir conversación

Tono: profesional, directo, sin emojis, sin ser vendedor.
```
