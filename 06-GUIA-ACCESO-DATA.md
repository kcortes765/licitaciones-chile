# Guía Actualizada: Acceso a Data de MercadoPublico (Marzo 2026)

## Estado Actual de las Fuentes

### 1. API MercadoPublico (FUNCIONA - con limitaciones)

**URL**: `https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json`

**Ticket de prueba** (compartido, rate-limited — solicitar a api@chilecompra.cl):
```
<TU_TICKET_AQUI>
```

**Ticket propio**: solicitar a `api@chilecompra.cl` o `+56 44236 0646`
- **Cambio dic 2025**: ahora validan cédula de identidad al solicitar ticket
- **2FA obligatorio** desde dic 2025 para acceso via Clave Única

**Endpoints principales**:
```
# Licitaciones de hoy
?ticket=TU_TICKET

# Por fecha (ddmmaaaa)
?fecha=03032026&ticket=TU_TICKET

# Por estado (activas)
?estado=activas&ticket=TU_TICKET

# Detalle de 1 licitación (retorna info completa)
?codigo=2405-31-LP26&ticket=TU_TICKET

# Por organismo público
?fecha=03032026&CodigoOrganismo=6945&ticket=TU_TICKET

# Por proveedor
?fecha=03032026&CodigoProveedor=17793&ticket=TU_TICKET

# Buscar empresa por RUT
https://api.mercadopublico.cl/servicios/v1/Publico/Empresas/BuscarProveedor?rutempresaproveedor=70.017.820-k&ticket=TU_TICKET
```

**Formatos**: JSON, XML, JSONP

**Códigos de estado**:
| Código | Estado |
|--------|--------|
| 5 | Publicada (abierta) |
| 6 | Cerrada |
| 7 | Desierta |
| 8 | Adjudicada |
| 18 | Revocada |
| 19 | Suspendida |

**Tipos de licitación**:
| Código | Rango |
|--------|-------|
| L1 | Menor a 100 UTM (~$6.6M CLP) |
| LE | 100-1000 UTM (~$6.6M-$66M CLP) |
| LP | Mayor a 1000 UTM (~$66M+ CLP) - **LAS MÁS RELEVANTES** |

### 2. API OCDS (Open Contracting Data Standard)

Endpoints adicionales con más detalle:
```
# Detalle de licitación OCDS
https://apis.mercadopublico.cl/OCDS/data/tender/{codigo}

# Detalle de adjudicación OCDS
https://apis.mercadopublico.cl/OCDS/data/award/{codigo}

# Info de unidad compradora
https://apis.mercadopublico.cl/APISOCDS/Comprador/Unidad/{codigo}
```

### 3. Datos Abiertos ChileCompra (BULK DATA)

**URL**: https://datos-abiertos.chilecompra.cl/descargas

**Contenido**:
- 4.9M procesos de licitación (desde 2009)
- 2.2M oferentes
- 4.9M adjudicaciones
- 4.8M documentos

**Formatos**: CSV (.tar.gz ~2.6GB), JSONL (.gz ~2.3GB), Excel
**Descarga por año o período completo**

**Uso ideal**: scoring predictivo, análisis histórico de adjudicaciones, patrones por organismo

### 4. RSS Feeds (gratis, sin ticket)

```
# Licitaciones destacadas (>1000 UTM)
http://www.mercadopublico.cl/Portal/feedrelevant.aspx

# Feed de organismo específico (ej: MOP)
https://www.mercadopublico.cl/Portal/FeedOrg.aspx?qs=q2IIpW+1qbUsKrXXGRC+rg==
```

### 5. Buscador Web (manual, gratis)

**URL**: https://www.mercadopublico.cl/BuscarLicitacion
- Filtros: tipo, estado, región, montos, rubros, fechas
- Rubro relevante: "Construcción de obras civiles y infraestructuras"

---

## Cambios Importantes 2025-2026

### Seguridad reforzada (dic 2025)
- 2FA obligatorio vía Clave Única
- Validación de cédula para tickets API
- Medidas anti-bots (Art. 160 Decreto 661/2024)

### Nueva API S1 2026 (en desarrollo)
ChileCompra está desarrollando nueva versión de APIs que incluirá:
- **Compra Ágil** (actualmente NO está en la API)
- **Documentos adjuntos** de licitaciones
- Mejor interoperabilidad
- Registro de integraciones validadas

### IA en ChileCompra
- Modelos de IA para monitoreo de probidad
- Modernización a arquitectura cloud

---

## Herramientas Open Source Útiles

| Proyecto | Lenguaje | URL |
|----------|----------|-----|
| gepd/MercadoPublico | TypeScript | github.com/gepd/MercadoPublico |
| imatec/mercadopublico | Python | github.com/imatec/mercadopublico |
| DCCP-Hugo/MercadoPublicoOCDS | R | github.com/DCCP-Hugo/MercadoPublicoOCDS |

---

## Script de Monitoreo

Ver `monitor_licitaciones.py` en esta carpeta.

```bash
# Licitaciones de obras de hoy
python monitor_licitaciones.py

# De una fecha específica
python monitor_licitaciones.py --fecha 03032026

# Detalle de 1 licitación
python monitor_licitaciones.py --detalle 2405-31-LP26

# Últimos 7 días
python monitor_licitaciones.py --dias 7
```

---

## Datos Reales Obtenidos (3 marzo 2026)

De 1,047 licitaciones publicadas hoy:
- **29 licitaciones de obras/construcción abiertas**
- **11 tipo LP** (>1000 UTM = >$66M CLP) - las más relevantes para constructoras

### Licitaciones LP abiertas destacadas:
| Código | Nombre | Cierre |
|--------|--------|--------|
| 2405-31-LP26 | Construcción Sede JJVV Los Alelíes II | 02/04/2026 |
| 2693-4-LP26 | Construcción Sendero Peatonal y Reparación Puente La Guitarra, Algarrobo | 06/04/2026 |
| 2709-4-LP26 | Construcción Sede Social Centro de Madres Sor Teresa, Ovalle | 02/04/2026 |
| 2709-7-LP26 | Construcción Plaza Los Geranios - Barrio 8 de Julio | 02/04/2026 |
| 2760-33-LP26 | Reparaciones Reposición Escuela G 666 Escuadrón | 02/04/2026 |
| 3015-10-LP26 | Rep. Pavimento Las Palmas Las Acacias A. Fernandez | 06/04/2026 |
| 3520-5-LP26 | Asesoría ITO Construcción Centro Cívico Dalcahue | 18/03/2026 |
| 3637-14-LP26 | Conservación y Mant. Distintos Espacios e Inmueble | 23/03/2026 |
| 4037-20-LP26 | Mejoramiento Plaza Villa Esperanza II, Fresia | 25/03/2026 |
| 712307-8-LP26 | Fiscalización Técnica De Obras DS 10 | 24/03/2026 |

---

## Próximos Pasos

1. **URGENTE**: Solicitar ticket propio (el de prueba tiene rate-limit severo)
2. **Con ticket propio**: correr `monitor_licitaciones.py --dias 7` para tener panorama completo
3. **Elegir 3 licitaciones LP** para descargar bases y hacer análisis de demo
4. Las bases se descargan desde la web de MercadoPublico (no desde la API)
