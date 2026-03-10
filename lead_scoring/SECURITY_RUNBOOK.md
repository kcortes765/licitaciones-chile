# Security Runbook

## Objetivo

Rotar credenciales y operar el servicio sin downtime ni fuga de secretos.

## Secretos en uso

- `GOOGLE_MAPS_API_KEY`
- `MERCADO_PUBLICO_TICKET`
- `APIFY_TOKEN`

## Regla operativa

Nunca editar ni compartir secretos por chat, commit, screenshot o archivo exportable. Solo viven en `lead_scoring/.env` de la maquina operativa o en el gestor de secretos que se adopte despues.

## Rotacion sin downtime

1. Generar nueva credencial en el proveedor.
2. Actualizar `lead_scoring/.env` en la maquina operativa.
3. Ejecutar:
   - `python 14_operational_preflight.py`
   - `python validate_outputs.py --check-env`
4. Validar un smoke real del flujo afectado:
   - Google Places: `python 06_enrich_contacts.py --top 1`
   - Mercado Publico: `python 12_monitor_api.py`
   - Apify: `python 06_enrich_contacts.py --top 1 --use-apify`
5. Confirmar que no hay errores de autenticacion ni cuota.
6. Revocar la credencial antigua.
7. Registrar fecha, proveedor y responsable en el historial interno.

## Respuesta ante incidente

Si una clave se expone:

1. Generar una nueva de inmediato.
2. Actualizar `.env` en la maquina operativa.
3. Revocar la clave comprometida.
4. Ejecutar preflight y smoke del flujo afectado.
5. Revisar si la clave aparecio en logs, backups o archivos compartidos.

## Checklist de go-live

- `.env` existe solo en la maquina operativa
- `.env.example` actualizado
- `python 14_operational_preflight.py` sin blockers
- `python validate_outputs.py --check-env` sin placeholders
- `.gitignore` cubre secretos y datos
- Ningun log imprime fragmentos de claves o tickets
