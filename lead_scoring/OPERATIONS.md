# Operacion del servicio

## Entorno soportado

- Baseline: Python 3.8
- Target recomendado: Python 3.10
- Python 3.11 queda diferido hasta validar dependencias

## Preflight antes de operar

0. Normalizar `.env` si hubo cambios manuales o secretos legacy:
   - `python 15_env_hygiene.py --write`
1. `python 14_operational_preflight.py`
2. `python validate_outputs.py --check-env`

No operar si el preflight reporta blockers.

## Secuencia diaria

1. Ejecutar monitor diario:
   - `python 12_monitor_api.py`
2. Revisar:
   - `data/output/monitor_diario.md`
   - `data/output/alertas_contacto.txt`
   - `data/output/crm_leads.xlsx`
3. Elegir leads priorizados para contacto.
4. Generar diagnostico:
   - `python 11_generate_diagnostic_pdf.py <RUT>`
5. Validar entregables:
   - `python validate_outputs.py`
6. Registrar accion en CRM.
7. Enviar outreach manual.

## Secuencia semanal

1. Revisar cobertura en `data/output/coverage_report.json`
2. Revisar muestra manual si hay cambios de scoring o fuentes
3. Depurar leads sin contacto util
4. Actualizar pipeline historico si hace falta recomputar base

## Corridas historicas

1. `python run_pipeline.py`
2. `python 07_export_output.py`
3. `python 08_loss_analysis.py`
4. `python 09_tender_matcher.py`

## Manejo de fallos

- Google Places falla:
  - reintentar
  - revisar quota
  - usar `--use-apify` como fallback
- Mercado Publico falla:
  - revisar ticket
  - reintentar mas tarde
  - usar salida RSS si aplica
- Validacion cliente-safe falla:
  - no enviar nada
  - corregir columnas o texto filtrado
  - volver a ejecutar `validate_outputs.py`
- Score inconsistente:
  - regenerar desde `05_score_leads.py`
  - luego `05b_ml_scoring.py`
  - luego `06_enrich_contacts.py`

## Checklist antes de enviar

- Empresa real verificada
- Contacto util o accion alternativa definida
- Hallazgo concreto preparado
- PDF generado y validado
- Mensaje WhatsApp revisado
- CRM actualizado

## Seguridad operativa

Ver [SECURITY_RUNBOOK.md](C:\Seba\Nueva carpeta (2)\lead_scoring\SECURITY_RUNBOOK.md) para rotacion de claves, respuesta a incidentes y checklist de go-live.
