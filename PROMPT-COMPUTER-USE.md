# Instrucciones para IA con Computer Use — Licitaciones Chile

## CONTEXTO
Eres un agente con Computer Use ayudando a Sebastián Cortés (ing. civil, Chile) a monitorear licitaciones de obras públicas para su negocio de análisis estratégico con IA. Necesitas ejecutar tareas en el navegador.

---

## TAREA 1: Follow-up ticket API MercadoPublico

1. Abrir Gmail (sebastian.cortes.ing@gmail.com)
2. Componer nuevo correo a: **api@chilecompra.cl**
3. Asunto: `Seguimiento - Solicitud de Ticket de Acceso API Mercado Público`
4. Cuerpo:

```
Estimados,

Les escribo para hacer seguimiento a mi solicitud de ticket de acceso a la API de Mercado Público, enviada hace algunas semanas.

Mi nombre es Sebastián Cortés, estudiante de Ingeniería Civil de la Universidad Católica del Norte. Estoy desarrollando una herramienta de análisis de licitaciones de obras públicas que utiliza inteligencia artificial para facilitar la revisión de bases técnicas y cumplimiento normativo (NCh, OGUC) a empresas constructoras.

El uso previsto es:
- Consulta de licitaciones publicadas filtrando por rubro construcción/obras públicas
- Análisis automatizado de bases técnicas mediante IA

Entiendo que desde diciembre 2025 se requiere validación de cédula de identidad. Quedo disponible para enviar la documentación que necesiten.

Datos de contacto:
- Nombre: Sebastián Cortés
- Email: sebastian.cortes.ing@gmail.com
- Teléfono: +56 9 2213 4294

Saludos cordiales,
Sebastián Cortés
Ingeniería Civil - UCN
```

5. Enviar

---

## TAREA 2: Buscar y descargar 3 bases de licitación de obras

### Paso 1: Ir al buscador
- Navegar a: **https://www.mercadopublico.cl/BuscarLicitacion**

### Paso 2: Aplicar filtros
- **Estado**: Publicada (abierta)
- **Tipo**: LP (Licitación Pública mayor a 1000 UTM) — son las más grandes
- **Rubro/Categoría**: buscar "Construcción" o "Obras civiles"
- Si hay filtro de región, dejarlo en "Todas"

### Paso 3: Seleccionar 3 licitaciones prioritarias
Buscar estas licitaciones específicas (ya identificadas via API):

| Prioridad | Código | Nombre | Cierre |
|-----------|--------|--------|--------|
| 1 | **2405-31-LP26** | Construcción Sede JJVV Los Alelíes II | 02/04/2026 |
| 2 | **2709-4-LP26** | Construcción Sede Social Centro de Madres Sor Teresa, Ovalle | 02/04/2026 |
| 3 | **2693-4-LP26** | Construcción Sendero Peatonal y Reparación Puente La Guitarra, Algarrobo | 06/04/2026 |

**Alternativas** si alguna no aparece:
- 2760-33-LP26 — Reparaciones Reposición Escuela G 666 Escuadrón
- 3015-10-LP26 — Rep. Pavimento Las Palmas Las Acacias
- 2709-7-LP26 — Construcción Plaza Los Geranios

**Criterios para elegir si buscas otras**:
- Tipo LP (las más grandes, >1000 UTM = >$66M CLP)
- Que sean de CONSTRUCCIÓN real (no suministros, no servicios de limpieza)
- Que cierren en al menos 2 semanas (tiempo para contactar constructoras)
- Ideal: escuelas, sedes, plazas, pavimentos, puentes

### Paso 4: Entrar a cada licitación y descargar
Para CADA una de las 3:
1. Click en la licitación
2. Anotar/copiar:
   - Código
   - Nombre completo
   - Organismo comprador
   - Monto estimado
   - Fecha cierre
   - Región/comuna
3. Buscar sección de **"Documentos"** o **"Bases"** o **"Archivos adjuntos"**
4. Descargar TODOS los PDFs (bases administrativas, bases técnicas, especificaciones, planos si hay)
5. Guardar en: **C:\Seba\Nueva carpeta (2)\bases\** creando subcarpeta por código:
   ```
   bases/
   ├── 2405-31-LP26/
   │   ├── bases_administrativas.pdf
   │   ├── bases_tecnicas.pdf
   │   └── ...
   ├── 2709-4-LP26/
   │   └── ...
   └── 2693-4-LP26/
       └── ...
   ```

### Paso 5: Verificar si son escaneados
- Abrir cada PDF
- Intentar seleccionar texto
- Si NO se puede seleccionar texto → es escaneado → ir a https://www.ilovepdf.com/ocr-pdf y convertir

---

## TAREA 3 (OPCIONAL): Buscar contacto de constructoras

Para cada licitación descargada:

1. En MercadoPublico, buscar licitaciones ANTERIORES similares del mismo organismo
2. Ver quién fue adjudicado → esas empresas probablemente postulen de nuevo
3. Buscar en Google: "[nombre empresa] constructora chile contacto"
4. Buscar en Google Maps: "constructora [ciudad de la licitación]"
5. Anotar en un archivo `leads.md`:

```
## Lead 1
- Empresa: [nombre]
- Contacto: [nombre persona]
- Teléfono/WhatsApp: [número]
- Email: [email]
- Licitación relacionada: [código]
- Fuente: [donde encontraste el dato]
```

Buscar al menos 3-5 leads por licitación.

---

## NOTAS IMPORTANTES

- **NO crear cuentas** en MercadoPublico (no es necesario para ver licitaciones)
- **NO postular** a nada
- Las bases de licitación son **públicas** y de descarga libre
- Si alguna página pide login, buscar la licitación por código en el buscador público
- Si hay captcha, resolverlo normalmente
- Guardar todo en **C:\Seba\Nueva carpeta (2)\**

## CUANDO TERMINES

Crear un archivo `resumen_descarga.md` en la carpeta del proyecto con:
- Qué licitaciones descargaste
- Cuántos PDFs por cada una
- Si alguno es escaneado
- Leads encontrados (si hiciste tarea 3)
