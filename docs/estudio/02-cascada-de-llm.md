# 02 — La cascada de LLM (orquestación multi-proveedor)

## El problema de atarse a un solo proveedor

El análisis depende de un modelo de lenguaje grande (LLM). Si atáramos el código
al SDK de un solo proveedor, tendríamos problemas:

- los proveedores cambian precios y disponibilidad;
- modelos distintos encajan con presupuestos distintos;
- un solo proveedor es un **único punto de fallo**.

Además queremos poder preferir un modelo barato o local primero y solo escalar a
uno más potente cuando haga falta.

## La solución: una interfaz y una cascada

Todo el código depende de **una** interfaz pequeña:

```python
class LLMClient(Protocol):
    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult: ...
```

Cada proveedor (Anthropic, OpenAI, Gemini, DeepSeek, Ollama local) es un
**adaptador** detrás de esa interfaz. Así, quien necesita un LLM no depende de
ningún proveedor concreto.

La `CascadeLLM` guarda una lista ordenada de clientes y los prueba **en orden**:
si uno falla (sin clave, límite de tasa, error de red, respuesta ilegible), pasa
al siguiente. Si todos fallan, lanza `LLMError`.

La cascada se construye desde una cadena de configuración:

```
anthropic,openai,gemini,deepseek,ollama
```

## ¿Por qué HTTP plano y no los SDK?

Los adaptadores hablan HTTP directo con `httpx`, no el SDK de cada proveedor.
Ventajas:

- **uniformidad**: todos los adaptadores se parecen;
- **una sola dependencia** en vez de cinco SDK;
- control total del mapeo petición/respuesta.

Las claves de API salen **solo** del entorno (variables como `ANTHROPIC_API_KEY`).
Nada se escribe en el código. Un proveedor sin clave no falla al construirse:
falla al llamarse, y la cascada cae al siguiente.

## Dos cosas a la vez: libertad y resiliencia

- **Libertad:** cambiar o reordenar proveedores es cambiar una cadena de texto,
  no el código. Un Ollama local y un modelo en la nube están tras la misma
  interfaz.
- **Resiliencia:** que un proveedor esté caído o sin clave no detiene el
  análisis; la cascada sigue al siguiente.

## Cómo se prueba sin red

Hay dos dobles de prueba que implementan la misma interfaz:

- `FakeLLM`: devuelve una respuesta preparada (para probar el camino del LLM).
- `FailingLLM`: siempre lanza `LLMError` (para probar el fallback de la cascada).

Así, la cascada y el analizador se prueban **sin tocar la red**.

## Para fijar la idea

- Una interfaz (`LLMClient`), muchos adaptadores: inversión de dependencias.
- La cascada prueba proveedores en orden y cae al siguiente si uno falla.
- HTTP plano con `httpx` → uniforme y una sola dependencia; claves solo del
  entorno.
- `FakeLLM` y `FailingLLM` permiten probar todo sin red.
