# RETOMAR — Proyecto Licitaciones Chile

## Leer primero
1. Este archivo
2. `C:\Seba\claude-system\licitaciones-contexto.md` (contexto completo)
3. MEMORY.md del proyecto

## Estado (sesión 12, 2026-03-07)
- Pipeline: **~20 módulos Python — 11 sesiones**
- **1024 tests** pasando
- **45 leads con WhatsApp verificado** + link wa.me + mensaje personalizado
- Git inicializado, **0 commits** (pendiente)
- Pack comercial completo en `commercial/`
- Auditoría completa: 40 hallazgos, 6 críticos pendientes

## Sesión 12: Guion WhatsApp + humanizador nombres + pricing docs + OpenClaw

### Guion WhatsApp (GUION-WHATSAPP.md)
- Pasos 2-6 con copy exacto listo para copiar-pegar
- Objeciones: "es caro", "lo veo después", "¿eres una IA?", "ya sabemos leer bases", etc.
- Seguimiento: 48h, cierre de lead, reaparición tardía
- Reglas: NO PDF gratis, NO mencionar ML/score, NO llamada para vender

### Humanizador de nombres (humanizar_nombre.py)
- Regla: POST-PIPE + eliminar solo formas legales (SPA, LTDA, EIRL, LIMITADA)
- Conserva: Constructora, Inmobiliaria, Comercial, Rental, etc.
- leads_verificados.xlsx: columna `nombre_humanizado` + wsp_mensaje actualizados
- Ej: "CONSTRUCTORA MONTE VIVO LIMITADA" → "Constructora Monte Vivo"

### Docs de pricing actualizados
- 01-PLAN-NEGOCIO-LICITACIONES.md, 02-OUTREACH-TEMPLATES.md, 05-CONTEXTO-PARA-IA.md
- Todos ahora con $190K / $250K / $490K-mes

### OpenClaw investigado
- Agente IA local que conecta a WhatsApp — útil para escalar respuestas
- Creator se unió a OpenAI para liderar agentes personales
- No usar todavía: validar canal primero con los 5 primeros mensajes manuales

## Sesión 11: Codex refactor + auditoría + verificación contactos + estrategia

### Refactor por Codex (revisado y corregido)
- Módulos compartidos: `pipeline_core.py`, `pipeline_validation.py`
- Scoring centralizado: `recompute_score_total()`, `recompute_score_combined()`
- Precedencia datasets: enriched > ml_ranked > ranked
- Scripts nuevos: smoke pipeline, validate_outputs, monitor API, preflight, env hygiene
- Tests: 1002 → 1024

### Auditoría completa (4 agentes paralelos)
- Pipeline core: 10 hallazgos (2 HIGH, 3 MEDIUM)
- Tests: cobertura débil en funciones críticas (~200 tests redundantes)
- Data/outputs: leaks en mensajes_whatsapp_v2.txt y leads_final.csv
- Docs/comercial: precios inconsistentes, .env.bak sin gitignore

### Verificación de contactos (16_verify_contacts.py)
- 73 teléfonos → 45 celular, 28 fijo, 0 inválidos
- 45 links wa.me generados con mensaje personalizado por lead
- Excel: `data/output/leads_verificados.xlsx` (3 hojas: WhatsApp Listos, Otros, Resumen)

### Estrategia comercial definida
- Pricing: $190K / $250K / $490K-mes
- Funnel: WSP dato → insight gratis chat → demo 1 licitación → PDF pagado → mensual
- NO regalar PDF. El valor gratis es texto en el chat
- 3 números WSP Business × 10 msg/día = ~1 venta/semana estimada

## Pendientes próxima sesión

### CRÍTICOS (antes de git push)
1. Añadir `.env.bak*` a .gitignore
2. Eliminar/regenerar `mensajes_whatsapp_v2.txt` (filtra scores)
3. Filtrar columnas internas en CSV export (`07_export_output.py:228`)
4. Mover ticket hardcodeado de `monitor_licitaciones.py` a .env
5. Hacer primer commit

### ALTOS
6. Corregir pesos en `10_visualizations.py` (14%→15%, falta score_oportunidad)
7. Unificar precios en todos los docs al pricing definitivo
8. Fix FICHA_LEAD.txt precio "00-400K" → "$490K"
9. Fix email Mecvalves `%20marriagada@macep.cl`

### COMERCIALES — PRIORIDAD MÁXIMA
10. **REESCRIBIR los 45 mensajes WSP** — ver análisis abajo, problema estructural
11. **ENVIAR los primeros 5** después de reescribir
12. Medir respuesta en 48h, ajustar copy si 0 respuestas en 30 mensajes
13. Usar GUION-WHATSAPP.md para responder
14. Configurar 2 números WSP Business adicionales

### PROBLEMA DETECTADO — mensajes WSP actuales
Los mensajes actuales dicen cosas que el cliente YA SABE (participó en X licitaciones,
tiene Y adjudicaciones). Eso no genera respuesta.

El mensaje tiene que contener UN insight que el cliente NO puede ver solo en Mercado Público.
Ejemplos de lo que SÍ funciona:
- "La mitad de sus derrotas son contra un solo competidor"
- "Su win rate en LP sobre $80M es X% vs Y% del mercado"
- "Hay un patrón en qué tipo de licitaciones ganan vs pierden"

También: sacar mención a IA del mensaje inicial.

### ESTRATEGIA PDF (decisión pendiente de implementar)
- Sí ampliar PDF pagado ($190K): agregar sección de recomendaciones accionables
  (qué licitaciones buscar, qué hace el rival, en qué criterios pierden puntos)
- No agregar teaser PDF gratuito: el gratis sigue siendo el chat con insight concreto
- El chat obliga a responder; un PDF es consumo pasivo que termina la conversación

## Archivos clave
- Pipeline: `lead_scoring/` (~20 archivos Python)
- Scoring central: `lead_scoring/pipeline_core.py`
- Validación: `lead_scoring/pipeline_validation.py`
- Verificación contactos: `lead_scoring/16_verify_contacts.py`
- Leads verificados: `lead_scoring/data/output/leads_verificados.xlsx`
- PDF generator: `lead_scoring/11_generate_diagnostic_pdf.py`
- Pack comercial: `commercial/` (6 archivos)
- Prompt PDF: `PROMPT-GENERAR-PDF-EJEMPLO.md`
- Config: `lead_scoring/config.py`

## Cómo re-ejecutar
```bash
cd "C:\Seba\Nueva carpeta (2)\lead_scoring"
python -m pytest test_pipeline.py -q              # 1024 pass
python 16_verify_contacts.py                       # Verificar contactos → leads_verificados.xlsx
python 14_operational_preflight.py                 # Preflight check
python run_smoke_pipeline.py                       # Smoke test
python 11_generate_diagnostic_pdf.py 132385-4      # Generar PDF 6 págs
python 12_monitor_api.py                           # Monitor diario
```
