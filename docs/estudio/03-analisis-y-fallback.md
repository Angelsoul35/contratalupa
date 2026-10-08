# 03 — El análisis y el respaldo (fallback)

## La idea: LLM como principal, heurísticas como red de seguridad

Un LLM es excelente leyendo una cláusula y juzgando su tipo y su riesgo en
lenguaje natural. Pero tiene dos fallos que no podemos ignorar:

- **Puede no estar disponible:** sin clave, límite de tasa, caída del proveedor,
  o un despliegue sin internet.
- **Puede responder mal:** devolver prosa en vez de JSON, o un tipo de cláusula
  que no está en nuestro vocabulario.

Una herramienta que no devuelve nada cuando el modelo está caído, o que se fía a
ciegas de una respuesta mal formada, no es fiable para revisar contratos.

Por eso: el LLM es el clasificador **principal**, y las heurísticas deterministas
son el **respaldo** y la **red de seguridad**.

## El contrato estricto con el modelo: JSON

Para usar la salida del modelo en un programa, hay que parsearla. La prosa libre
es difícil de parsear y ambigua. Por eso pedimos al modelo **solo** un objeto
JSON con tres campos:

```json
{"type": "<tipo>", "risk": "low|medium|high", "rationale": "<una frase>"}
```

y le damos en el prompt los valores permitidos de `type` y `risk`.

Al recibir la respuesta:

1. extraemos el primer bloque `{...}` (a veces el modelo lo envuelve en texto) y
   hacemos `json.loads`;
2. **validamos** `type` contra el vocabulario `ClauseType` y `risk` contra
   `Risk`; si algo no es válido, lo corregimos con la heurística;
3. si no hay JSON, lo tratamos como un fallo del proveedor y caemos al respaldo.

Es decir: **validar, no confiar**. El modelo no puede colar un tipo inventado.

## El respaldo por heurísticas

Vive en `clauses.py` como datos:

- **Clasificar el tipo:** un mapa de palabras clave por tipo de cláusula
  (`KEYWORDS`). Se cuenta cuántas pistas de cada tipo aparecen y gana el de más.
- **Evaluar el riesgo:** una lista de frases peligrosas con peso (`RISK_PHRASES`),
  por ejemplo "unlimited liability" (+3), "sole discretion" (+2), "automatically
  renew" (+2). Se suman los pesos: ≥3 → alto, ≥1 → medio, 0 → bajo. La razón es la
  lista de frases encontradas.

## Siempre hay respuesta, y siempre sabes cómo se obtuvo

Cada hallazgo (`ClauseFinding`) guarda su `source`: `"llm"` o `"heuristic"`. Así,
quien lee el informe sabe cómo se llegó a cada veredicto. Esto importa cuando una
persona decide si fiarse.

## Lo que falta: la lista de verificación

Mucho del riesgo de un contrato está en lo que **no** aparece. Por eso, tras
clasificar todas las cláusulas, comparamos los tipos detectados con una lista de
cláusulas estándar (`STANDARD_CLAUSES`) y reportamos las que **faltan**
(`missing_clauses`). Es una simple diferencia de conjuntos: fácil de razonar y de
probar. Lo tratamos como un aviso para que una persona confirme, no como un
veredicto final.

## El informe

`ContractReport` reúne: las cláusulas con su hallazgo, las cláusulas que faltan,
el recuento por nivel de riesgo, el riesgo global (alto si hay alguna alta, etc.)
y el modelo usado (o `heuristic-only`).

## Para fijar la idea

- LLM principal + heurísticas de respaldo = siempre hay respuesta.
- JSON estricto + validación contra el vocabulario = no se confía a ciegas.
- `source` dice cómo se obtuvo cada veredicto.
- Las cláusulas que faltan se detectan con una lista de verificación.
