# Fuentes de Data - Licitaciones Chile

## Fuentes de Licitaciones (en orden de prioridad)

### 1. MercadoPublico.cl - Buscador (PRINCIPAL)
- **URL**: https://www.mercadopublico.cl/BuscarLicitacion
- **Acceso**: Abierto, sin registro
- **Contenido**: TODAS las licitaciones del Estado chileno
- **Filtros**: Rubro, tipo, presupuesto, fecha cierre, comprador, proveedor
- **Tipos relevantes**:
  - O1: Licitación Pública de Obras
  - O2: Licitación Privada de Obras
- **Volumen**: 1,868,361 órdenes de compra anuales (2025)
- **Monto**: USD $21,953 millones totales, $3,280M en obras (+70%)

### 2. Visor de Licitaciones MOP-DGOP
- **URL**: https://licitaciones-dgop.mop.gob.cl/
- **Acceso**: Abierto
- **Contenido**: Licitaciones activas de la Dirección General de Obras Públicas
- **Datos**: Código, nombre, región, dirección MOP, fecha cierre, tipo
- **Volumen**: ~60-80 activas en cualquier momento

### 3. Feed MOP en MercadoPublico
- **URL**: https://www.mercadopublico.cl/Portal/FeedOrg.aspx?qs=q2IIpW+1qbUsKrXXGRC+rg%3D%3D
- **Acceso**: Abierto
- **Contenido**: Licitaciones recientes del MOP con fechas cierre

### 4. API MercadoPublico (pendiente ticket)
- **URL**: https://api.mercadopublico.cl/
- **Acceso**: Requiere ticket (solicitado a api@chilecompra.cl)
- **Formato**: JSON, XML, JSONP
- **Endpoints**:
  - Listar por fecha: `/servicios/v1/publico/licitaciones.json?fecha=DDMMAAAA&ticket=TU_TICKET`
  - Listar por código: `/servicios/v1/publico/licitaciones.json?codigo=XXXX-X-XXXX&ticket=TU_TICKET`
  - Buscar proveedor: `/servicios/v1/Publico/Empresas/BuscarProveedor?rutempresaproveedor=RUT&ticket=TU_TICKET`
- **Doc**: https://api.mercadopublico.cl/documentos/Documentaci%C3%B3n%20API%20Mercado%20Publico%20-%20Licitaciones.pdf
- **Impacto sin API**: +30 min/día de trabajo manual. No bloqueante.

### 5. Datos Abiertos ChileCompra
- **URL**: https://datos-abiertos.chilecompra.cl/
- **Contenido**: Descargas masivas de datos históricos
- **Formato**: OCDS (Open Contracting Data Standard)
- **Uso**: Análisis histórico de adjudicaciones para scoring predictivo futuro

---

## Fuentes de Leads (contacto de empresas)

### 1. Dentro de MercadoPublico
- Empresas adjudicadas en licitaciones anteriores similares = empresas que van a postular de nuevo
- RUT de proveedores disponible en adjudicaciones

### 2. Google Maps
- Buscar: "constructora [ciudad]", "oficina cálculo estructural", "ingeniería civil [región]"
- Datos: nombre, teléfono, email, web, dirección

### 3. Registro de Contratistas MOP
- **Obras Mayores**: https://www.mop.gob.cl/serviciosmop/listado-contratistas-de-obras-mayores-mop/
- **Obras Menores**: https://www.mop.gob.cl/serviciosmop/listado-contratistas-de-obras-menores-mop/
- **Registro**: https://dgop.mop.gob.cl/contratistas-y-consultores/
- Contenido: Lista oficial de empresas habilitadas para licitar obras MOP

### 4. CChC (Cámara Chilena de la Construcción)
- ~3,000 empresas socias
- Directorio en cchc.cl

### 5. LinkedIn
- Buscar: gerente constructora, dueño oficina ingeniería
- Útil para contacto directo con decisor

---

## Fuentes de Normativa

### Normas NCh
- **Instituto de la Construcción**: https://www.iconstruccion.cl/listado-nch/
- **AICE**: https://aice.cl/web/listado-normas-nacionales/
- **NCh433 (sísmica)**: https://ingenieria-civil.github.io/chile/normas/00-NCh-433-Of-1996-Mod-2009-DS-61-2011-refundido.pdf

### OGUC
- **MINVU normas obligatorias**: https://proveedorestecnicos.minvu.gob.cl/normas-tecnicas-obligatorias/

### Software gratuito de chequeo
- **CECh-Soft**: https://cechsoft.cl/ (7 módulos de chequeo estructural)

---

## Competencia a Monitorear

| Empresa | Qué hace | URL |
|---------|----------|-----|
| LicitaLAB | Alertas de licitaciones (sin IA) | licitalab.cl |
| iConstruye | Supply chain construcción | iconstruye.com |
| Civils.ai | IA para planos (no Chile) | civils.ai |
| CodeComply | Compliance normativo (no Chile) | codecomply.ai |
| CivCheck | Revisión planos IA (no Chile) | civcheck.ai |
