# Guía de estudio — Contratalupa

Esta carpeta es una guía en español para entender Contratalupa a fondo. El
código, los comentarios y la documentación técnica están en inglés (nivel B2) a
propósito, para que el proyecto sea creíble y sirva para practicar. Esta guía
explica el "por qué" de cada decisión en tu idioma, para estudiar con calma.

## Orden sugerido de lectura

1. **[01-que-hace-y-segmentacion.md](01-que-hace-y-segmentacion.md)** — qué
   resuelve y cómo se parte un contrato en cláusulas.
2. **[02-cascada-de-llm.md](02-cascada-de-llm.md)** — la orquestación multi-LLM:
   una interfaz, varios proveedores, y fallback automático.
3. **[03-analisis-y-fallback.md](03-analisis-y-fallback.md)** — cómo se clasifica
   y se evalúa el riesgo con el LLM y con heurísticas, y por qué siempre hay
   respuesta.
4. **[04-arquitectura-y-diseno.md](04-arquitectura-y-diseno.md)** — cómo encajan
   las piezas y qué decisiones de diseño se tomaron.
5. **[05-preguntas-de-entrevista.md](05-preguntas-de-entrevista.md)** — preguntas
   típicas y cómo responderlas con seguridad.

## Resumen en una frase

Contratalupa parte un contrato en cláusulas, clasifica cada una, marca el
lenguaje arriesgado y avisa de las cláusulas estándar que faltan, usando una
cascada de LLM agnóstica del proveedor (Anthropic, OpenAI, Gemini, DeepSeek,
Ollama) con un respaldo por heurísticas que funciona sin conexión.
