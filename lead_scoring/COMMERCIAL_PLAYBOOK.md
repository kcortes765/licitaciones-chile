# Playbook comercial

## Marca operativa

IngenIA Licitaciones
Sebastian Cortes
Ing. Civil UCN

## Lo que se vende

No se vende "resumen de bases". Se vende claridad para decidir:

- que licitaciones perseguir
- donde estan perdiendo contra rivales recurrentes
- que riesgos conviene revisar antes de invertir tiempo en la oferta

## ICP prioritario

- constructora que participa con cierta frecuencia en Mercado Publico
- equipo comercial o gerencia que necesita priorizar mejor
- historial visible de adjudicaciones y derrotas
- capacidad real de contratar diagnosticos puntuales o servicio mensual

## Senales de buen lead

- participa en LP o LE con cierta recurrencia
- tiene derrotas repetidas o rivales frecuentes
- hay licitaciones recientes alineadas a su perfil
- existe telefono, email o canal de contacto usable

## Activos comerciales listos

- [Oferta de servicio](C:\Seba\Nueva carpeta (2)\commercial\OFERTA_SERVICIO.md)
- [NDA simple](C:\Seba\Nueva carpeta (2)\commercial\NDA_SIMPLE.md)
- [Propuesta base](C:\Seba\Nueva carpeta (2)\commercial\PROPUESTA_BASE.md)
- [Tarifario](C:\Seba\Nueva carpeta (2)\commercial\TARIFARIO.md)
- [Secuencia de follow-up](C:\Seba\Nueva carpeta (2)\commercial\FOLLOWUP_SEQUENCE.md)
- [Plantilla de analisis gratis](C:\Seba\Nueva carpeta (2)\commercial\ANALISIS_GRATIS_TEMPLATE.md)
- diagnostico PDF
- mensaje WhatsApp personalizado

## Flujo comercial recomendado

1. Identificar lead priorizado en `leads_final.xlsx` o `crm_leads.xlsx`.
2. Confirmar empresa real, dolor visible y canal usable.
3. Preparar un hallazgo concreto, no una venta generica.
4. Generar PDF con `11_generate_diagnostic_pdf.py`.
5. Ejecutar `validate_outputs.py`.
6. Contactar por WhatsApp o email.
7. Registrar resultado y proximo paso en CRM.
8. Hacer follow-up en 48 horas si no hay respuesta.

## Discovery rapido

Preguntas utiles en la primera conversacion:

- Hoy como priorizan que licitaciones mirar en serio?
- Que les toma mas tiempo o mas errores en la decision de ofertar?
- Hay rivales que se les repitan seguido?
- Quien decide avanzar o descartar una oportunidad?

## Objeciones comunes

### "Nosotros ya revisamos bases internamente"

Respuesta:
Perfecto. La idea no es reemplazar esa revision, sino llegar antes con una mirada ejecutiva para priorizar mejor y detectar patrones competitivos que normalmente no quedan visibles en la revision caso a caso.

### "No necesitamos otro informe"

Respuesta:
El formato es ejecutivo y corto. La utilidad real es reducir perdida de tiempo en oportunidades mal alineadas y poner foco donde vale la pena profundizar.

### "No quiero compartir informacion sensible"

Respuesta:
Se puede empezar solo con informacion publica y, si hace sentido avanzar, firmar NDA antes de revisar antecedentes internos.

## Regla interna

Nunca enviar score interno, cluster, ranking interno ni columnas `xgb_*` o `km_*` al cliente.
