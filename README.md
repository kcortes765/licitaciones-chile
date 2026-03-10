# Licitaciones Chile

Proyecto de inteligencia comercial para constructoras que licitan en Mercado Publico Chile. El nucleo tecnico vive en [`lead_scoring/`](./lead_scoring) y combina datos historicos, scoring, enriquecimiento de contactos, analisis competitivo y entregables comerciales.

## Estado actual

- Backup local inicial: `C:\Seba\workspace_backups\workspace_backup_20260305_224227`
- Control de versiones inicializado con Git
- Pipeline historico validado con tests
- Salidas operativas y comerciales separadas de artefactos internos

## Setup rapido

1. Crear entorno virtual con Python 3.8 o 3.10.
2. Instalar dependencias:
   - `pip install -r lead_scoring/requirements-dev.txt`
3. Copiar `lead_scoring/.env.example` a `lead_scoring/.env` y completar claves reales.
4. Normalizar `.env` si vienes de una configuracion antigua:
   - `cd lead_scoring`
   - `python 15_env_hygiene.py --write`
5. Ejecutar preflight:
   - `cd lead_scoring`
   - `python 14_operational_preflight.py`
6. Ejecutar smoke test:
   - `cd lead_scoring`
   - `python run_smoke_pipeline.py`
7. Ejecutar test suite:
   - `python -m pytest test_pipeline.py -q`

## Flujos principales

- Pipeline historico: `python run_pipeline.py`
- Higiene de entorno: `python 15_env_hygiene.py --write`
- Preflight operativo: `python 14_operational_preflight.py`
- Export de leads/CRM: `python 07_export_output.py`
- Validacion cliente-safe: `python validate_outputs.py`
- Monitor diario: `python 12_monitor_api.py`
- Muestra manual de leads: `python 13_prepare_lead_review_sample.py`

## Documentacion viva

- Operacion diaria: [`lead_scoring/OPERATIONS.md`](./lead_scoring/OPERATIONS.md)
- Seguridad operativa: [`lead_scoring/SECURITY_RUNBOOK.md`](./lead_scoring/SECURITY_RUNBOOK.md)
- Playbook comercial: [`lead_scoring/COMMERCIAL_PLAYBOOK.md`](./lead_scoring/COMMERCIAL_PLAYBOOK.md)
