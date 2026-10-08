# 01 — Qué hace y la segmentación

## El problema

El riesgo de un contrato vive en sus cláusulas: una de responsabilidad
ilimitada, una renovación automática, una indemnización demasiado amplia, o una
protección estándar que sencillamente **no está**. Leer a mano cada cláusula de
cada contrato es lento y desigual.

Contratalupa da una **primera lectura** en segundos: parte el contrato en
cláusulas, clasifica cada una, marca el lenguaje arriesgado y avisa de lo que
falta. No sustituye a un abogado; le da una vista estructurada y explicable para
que enfoque su atención.

El nombre es un juego: *contrato* + *lupa*. Lee el contrato como lo haría un
revisor cuidadoso y explica lo que encuentra.

## Dos propiedades importantes

- **Explicable.** Cada cláusula recibe un tipo, un nivel de riesgo y una razón en
  una frase. Nada es una caja negra.
- **Resiliente.** Usa un LLM cuando hay uno disponible, y si no, recurre a
  heurísticas deterministas. Una clave de API que falta o un proveedor caído
  nunca te dejan sin respuesta.

## La segmentación: de texto a cláusulas

Antes de analizar, hay que **partir** el contrato en cláusulas. Eso lo hace
`segment.py`.

Los contratos se escriben en secciones numeradas o con título. El segmentador
reconoce los patrones habituales:

- `1.`, `1.1`, `2)` — numeración.
- `Section 3` — sección.
- `Article IV` — artículo (con números romanos).
- Un título en MAYÚSCULAS corto.

Agrupa cada encabezado con el texto que le sigue. Si **no** encuentra
encabezados, parte por párrafos (líneas en blanco). Así, hasta un documento sin
estructura da cláusulas que analizar.

### Un detalle de diseño

La segmentación es **simple y determinista** a propósito. Es la **entrada** del
análisis, no el lugar para el juicio. El juicio (qué tipo de cláusula es, qué
riesgo tiene) viene después. Separar "partir el texto" de "entender el texto"
mantiene cada parte sencilla y comprobable.

Cada `Clause` tiene un índice, un encabezado y un cuerpo, y una propiedad
`full_text` que los une para pasárselo al analizador.

## Para fijar la idea

- Contratalupa es una herramienta de **apoyo a la decisión**, no asesoría legal.
- Primero **segmenta** (partir en cláusulas), luego **analiza** (clasificar y
  evaluar riesgo).
- La segmentación reconoce secciones numeradas/tituladas y, si no hay, parte por
  párrafos. Es determinista: misma entrada, misma salida.
