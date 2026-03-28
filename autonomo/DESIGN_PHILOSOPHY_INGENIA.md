# Engineered Clarity

> Filosofía de diseño visual para IngenIA Licitaciones.
> Este documento es la referencia canónica para toda producción visual del proyecto.
> Léase en conjunto con `CANVAS_DESIGN_SYSTEM.md`.

---

## El Movimiento

**Engineered Clarity** — Inteligencia competitiva comunicada con la precisión de un instrumento científico y la composición de una pieza de museo. Cada página es un artefacto meticulosamente elaborado donde los datos no se presentan: se revelan.

---

## Espacio y Forma

El espacio vacío no es ausencia — es confianza. Un margen generoso de 25 mm o más en cada lado declara que la información contenida es tan valiosa que no necesita competir por atención. Cada elemento respira dentro de su territorio: 12 mm entre secciones, 6 mm entre elementos, 3 mm entre líneas de texto. El 30% del espacio vertical de cada página permanece intacto, intencional, inmaculado.

La forma sigue la función con rigor de ingeniería. Los bloques de contenido son rectángulos limpios con bordes definidos. Los charts flotan en campos de aire blanco. Las métricas se anclan como coordenadas en un plano cartesiano. Nada se solapa. Nada se aprieta. Nada se desborda. Si un elemento no cabe con dignidad, se elimina — nunca se comprime.

---

## Color y Material

La paleta es quirúrgica: seis colores, sin excepciones.

| Rol | Color | Hex | Uso |
|---|---|---|---|
| Territorio | Navy profundo | `#0F1B2D` | Headers, barras principales, texto de alto peso |
| Estructura | Gris oscuro | `#2D3748` | Texto body principal, labels |
| Soporte | Gris medio | `#6B7B8D` | Texto secundario, subtítulos, captions |
| Superficie | Gris claro | `#E8ECF0` | Fondos de cards, separadores sutiles |
| Hallazgo | Cobrizo/Dorado | `#B8860B` | Acentos clave — máximo 1-2 por página |
| Aire | Blanco puro | `#FFFFFF` | Fondo, espacio negativo |

El navy es el suelo sobre el que se construye. El dorado es el hallazgo que merece atención — se usa con la parsimonia de un subrayado en un libro de primera edición. Nunca más de 4 colores por página. La restricción cromática es una declaración: la información habla por sí misma.

---

## Escala y Ritmo

El contraste de escala es dramático e intencional. Los números grandes — 28pt, 32pt — actúan como anclas visuales que capturan la mirada antes que cualquier párrafo. Son los titulares de la historia que los datos cuentan. El texto de soporte — 8pt, 9pt — orbita alrededor de estos números como anotaciones en el margen de un tratado científico.

El ritmo vertical es predecible y tranquilizador: header, espacio, contenido, espacio, contenido, espacio, footer. Como la respiración. Como el pulso de un instrumento de medición. Cada transición tiene exactamente el mismo silencio. El ojo del lector nunca se pierde porque el patrón es tan consistente que se vuelve invisible — y esa invisibilidad es el objetivo.

---

## Composición y Balance

El centro es territorio de lo genérico. Engineered Clarity abraza la asimetría controlada: layouts 60/40 o 70/30 donde el contenido principal domina el lado izquierdo y la interpretación habita el derecho. El ojo lee de izquierda a derecha, de lo visual a lo textual, de lo grande a lo pequeño.

Un chart ocupa como máximo la mitad de una página. Dos charts por página es el límite absoluto. Los gráficos no se aprietan en esquinas — se despliegan con la generosidad de una lámina en un atlas de ingeniería. Cada chart tiene su caption debajo, centrada, en gris medio 7pt, como una nota al pie en una publicación científica. Las tablas son limpias: sin bordes verticales, sin zebra stripes, solo un separador de header y una línea de cierre.

---

## Tipografía

Helvetica light para el cuerpo. Helvetica bold exclusivamente para métricas y títulos de sección. Nada más. La tipografía es quirúrgica: fina, precisa, nunca decorativa. Si una palabra puede eliminarse sin perder significado, se elimina. Si un párrafo tiene más de 6 líneas, el párrafo es demasiado largo.

El texto es un acento visual, no el vehículo principal de información. Los números, los charts y la composición cuentan la historia. El texto la contextualiza. Un bloque de texto de 5 líneas bien elegidas comunica más que 20 líneas de prosa genérica. Cada palabra está ahí porque se ganó su lugar.

---

## Craftsmanship

Cada píxel es intencional. Cada milímetro de espacio está medido. Cada color está justificado. El resultado final debe parecer que un equipo de ingenieros senior y diseñadores de información trabajó semanas en cada página — producto de expertise profunda y atención meticulosa a cada detalle.

No es un reporte con gráficos pegados. Es un artefacto de inteligencia competitiva que demuestra, antes de ser leído, que quien lo produjo opera en un nivel diferente. La ejecución nivel maestro es el diferenciador: ingenieros no saben diseñar, diseñadores no entienden licitaciones. IngenIA domina ambos mundos, y cada página lo prueba.

El estándar es simple: si no parece digno de exhibirse en museo, no está terminado.

---

## Aplicación Técnica Rápida

```
MÁRGENES:     left=25mm  right=20mm  top=25mm  bottom=22mm
ANCHO ÚTIL:   165mm
SPACING:      section_gap=12mm  element_gap=6mm  text_gap=3mm
FONTS:        body=9pt  labels=8pt  metrics=28-32pt bold  captions=7pt
CHARTS:       max 1 per half-page, figsize in inches = mm/25.4
COLORES/PÁG:  max 4 (navy + gray + white + gold solo si hay hallazgo)
AIRE:         30% del espacio vertical = vacío intencional
REGLA DE ORO: si parece apretado, está mal
```
