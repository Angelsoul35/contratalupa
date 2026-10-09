# 06 — La evaluación con datos reales (LEDGAR)

Las guías anteriores explican cómo Contratalupa segmenta y clasifica cláusulas
con un LLM y con heurísticas. Esta guía trata una pregunta distinta y más
exigente: **¿el clasificador generaliza a cláusulas que no escribió nadie del
proyecto?** Para responderla con pruebas, y no con afirmaciones, el proyecto
incluye un tercer clasificador entrenable (`contratalupa/ml.py`) y un benchmark
sobre un dataset público real (`contratalupa/real_benchmark.py`).

## El tercer clasificador: TF-IDF + regresión logística

Hasta ahora teníamos dos vías: el LLM y las heurísticas de palabras clave. Aquí
añadimos una tercera, **entrenable y sin conexión**:

1. **Vectorizar (TF-IDF).** Cada cláusula se convierte en un vector disperso de
   *unigramas* y *bigramas* (palabras sueltas y pares de palabras) pesados por
   TF-IDF. La intuición: una palabra vale más si aparece mucho en *esta* cláusula
   (TF, *term frequency*) pero poco en el resto del corpus (IDF, *inverse
   document frequency*):

   ```
   tfidf(t, d) = tf(t, d) · idf(t),   idf(t) = ln( N / (1 + df(t)) ) + 1
   ```

   donde `t` es un término, `d` una cláusula, `N` el número de cláusulas y
   `df(t)` en cuántas cláusulas aparece `t`. Así, "indemnify" pesa más que "the".

2. **Clasificar (regresión logística multinomial).** Aprende un vector de pesos
   por tipo de cláusula y elige el de mayor probabilidad. Da `predict_proba`
   (probabilidades por clase), útil para ordenar y para umbrales.

El vectorizador y el clasificador viven en **un solo pipeline** de scikit-learn.
Esto no es un detalle estético: garantiza que el vectorizador **solo** se ajusta
con los datos de entrenamiento de cada partición, nunca con los de prueba. Si lo
ajustáramos con todo, el IDF "vería" el vocabulario de prueba y habría **fuga de
información** (*data leakage*): los números saldrían mejores de lo que son en la
realidad.

## El dataset: LEDGAR

**LEDGAR** forma parte de **LexGLUE**, un conjunto de benchmarks de NLP legal en
inglés. Son cláusulas reales extraídas de contratos públicos presentados ante la
SEC de EE. UU., etiquetadas con **100 tipos** de cláusula (`Governing Laws`,
`Notices`, `Indemnifications`, `Terminations`, ...).

Para un benchmark sólido sin inflar el repositorio, vendorizamos un subconjunto
**balanceado**: los **20 tipos más frecuentes**, con **150 cláusulas cada uno** =
**3000 cláusulas**. Balanceado significa que cada clase tiene el mismo número de
ejemplos; así la línea base aleatoria es exactamente `1/20 = 0,05`.

## Por qué una tarea legal multiclase es difícil

- **Muchas clases.** Con 20 clases, acertar al azar da 5 %. Con 100, un 1 %. El
  espacio de error es enorme comparado con un problema binario.
- **Lenguaje solapado.** Cláusulas de tipos distintos comparten vocabulario
  legal ("shall", "party", "agreement"). La señal útil está en términos sutiles.
- **Fronteras difusas.** Una cláusula de `Indemnifications` puede mencionar
  `Liability`; una de `Terminations`, un `Notice`. Hasta un humano dudaría.
- **Desequilibrio en el mundo real.** En LEDGAR completo unas clases son
  muchísimo más frecuentes que otras. Nosotros balanceamos a propósito para que
  las métricas sean fáciles de interpretar, pero el problema sigue siendo de 20
  vías.

Por todo esto, **un resultado perfecto (1,0) sería sospechoso**, no admirable:
indicaría fuga de información o memorización. Un buen resultado real está muy por
encima de la línea base, pero lejos de 1,0.

## Sobreajuste y subajuste

Dos formas de fallar al aprender:

- **Subajuste (*underfitting*).** El modelo es demasiado simple o está demasiado
  regularizado: no captura la señal. Síntoma: puntuación **baja tanto en
  entrenamiento como en validación**. Es sesgo (*bias*) alto.
- **Sobreajuste (*overfitting*).** El modelo memoriza el entrenamiento, incluido
  el ruido, y no generaliza. Síntoma: puntuación **alta en entrenamiento pero
  mucho más baja en validación/prueba**, es decir, una **brecha** grande. Es
  varianza (*variance*) alta.
- **Buen ajuste (*well-fit*).** Puntuación alta y **parecida** en entrenamiento,
  validación cruzada y prueba. Brecha pequeña.

La palanca para moverse entre estos regímenes es la **regularización**. En la
regresión logística se controla con `C`: `C` grande = poca regularización (más
capacidad, riesgo de sobreajuste); `C` pequeño = mucha regularización (menos
capacidad, riesgo de subajuste).

## Exactitud vs macro-F1

Dos formas de medir, y por qué preferimos macro-F1.

**Exactitud (*accuracy*)**: fracción de aciertos.

```
accuracy = aciertos / total
```

Problema: con clases desequilibradas, un modelo que siempre dice la clase
mayoritaria puede tener una exactitud engañosamente alta sin entender nada.

**Precisión, exhaustividad y F1** (por clase):

```
precision = VP / (VP + FP)      (de lo que predije como clase X, cuánto acerté)
recall    = VP / (VP + FN)      (de los X reales, cuántos encontré)
F1        = 2 · (precision · recall) / (precision + recall)   (media armónica)
```

donde VP = verdaderos positivos, FP = falsos positivos, FN = falsos negativos.
F1 castiga quedarse corto en cualquiera de las dos: si la precisión es alta pero
la exhaustividad baja (o al revés), F1 baja.

**Macro-F1**: la media simple del F1 de cada clase.

```
macro-F1 = (1/K) · Σ_k F1_k      (K = número de clases)
```

A diferencia del micro-promedio (que pondera por frecuencia), el macro trata
**todas las clases por igual**. Para una tarea multiclase donde cada tipo de
cláusula importa, macro-F1 es la métrica honrada: no deja que las clases grandes
tapen el mal desempeño en las pequeñas. Por eso el benchmark reporta macro-F1
como métrica principal y la exactitud como apoyo.

### Ejemplo trabajado: la línea base de macro-F1

¿Por qué la línea base de "predecir siempre la clase mayoritaria" da macro-F1 ≈
0,005 en nuestra prueba? La partición de prueba tiene 600 cláusulas (20 % de
3000), 30 por clase. Si predecimos siempre la clase `m`:

- Para `m`: `recall = 30/30 = 1,0`; `precision = 30/600 = 0,05`.
  `F1_m = 2 · (0,05 · 1,0) / (0,05 + 1,0) = 0,0952`.
- Para las otras 19 clases: nunca las predecimos, así que `F1 = 0`.
- `macro-F1 = 0,0952 / 20 = 0,00476 ≈ 0,005`.

La exactitud de esa misma línea base es `30/600 = 0,05`. Esos son exactamente los
números que imprime el benchmark como `Baselines`. Cualquier modelo que valga
algo tiene que dejarlos muy atrás.

## El método de evaluación: tres vistas

El benchmark mide la generalización desde tres ángulos complementarios
(`contratalupa/real_benchmark.py`):

1. **Partición de prueba retenida (*held-out test*).** Se aparta un 20 % de forma
   **estratificada** (manteniendo la proporción de clases) que el modelo **no ve**
   al entrenar. Mide el desempeño en datos verdaderamente nuevos.
2. **Validación cruzada estratificada de 5 particiones (*stratified 5-fold CV*).**
   Sobre el 80 % de entrenamiento: se divide en 5 bloques; 5 veces se entrena con
   4 y se valida con el que queda. Da una media y una **desviación** (cuánto varía
   entre particiones). La estratificación mantiene las 20 clases en cada bloque.
3. **Puntuación en entrenamiento.** Sobre los datos con los que sí se entrenó.
   Sola no dice nada de generalización, pero **restada** de la de prueba revela la
   **brecha** (el síntoma del sobreajuste).

Comparamos las tres contra la línea base y clasificamos el ajuste de forma
**auditable** (los umbrales están escritos en el código, no escondidos):

- `competent`: macro-F1 de CV ≥ 0,50 y ≥ línea base + 0,30.
- `stable`: desviación entre particiones ≤ 0,05 y |CV − prueba| ≤ 0,08.
- `small_gap`: brecha entrenamiento → CV en macro-F1 ≤ 0,25.
- Veredicto: si no es `competent` → **subajuste**; si no es estable con brecha
  pequeña → **sobreajuste**; en otro caso → **buen ajuste**.

Fíjate: el veredicto **se calcula** a partir de los números; no se afirma. El
informe reporta qué conclusión sostienen los datos.

## Ejemplo trabajado: los números reales

Salida real de `python -m contratalupa.real_benchmark`:

| Métrica                         | Valor            |
| ------------------------------- | ---------------- |
| Clases / cláusulas              | 20 / 3000 (balanceado) |
| Modelo                          | TF-IDF (1-2 gramas) + reg. logística, C = 2,0 |
| Línea base (clase mayoritaria)  | exactitud 0,050 · macro-F1 0,005 |
| CV 5-fold — macro-F1            | **0,906 ± 0,007** |
| CV 5-fold — exactitud           | 0,906 |
| CV por partición (macro-F1)     | 0,902 · 0,903 · 0,900 · 0,903 · 0,920 |
| Prueba retenida — exactitud     | 0,910 |
| Prueba retenida — macro-F1      | **0,908** |
| Entrenamiento — macro-F1        | 0,989 |
| Brecha entrenamiento → prueba (exactitud) | +0,079 |
| Brecha entrenamiento → CV (macro-F1)      | +0,083 |
| Acuerdo CV vs prueba (macro-F1) | 0,003 de diferencia |
| **Veredicto**                   | **BUEN AJUSTE** |

Cómo se lee:

- **Señal fuerte.** macro-F1 de 0,906 (CV) y 0,908 (prueba) frente a 0,005 de la
  línea base y un suelo aleatorio de 0,05. El modelo entiende de verdad la
  estructura de las cláusulas.
- **Sin fuga y estable.** CV y prueba coinciden a 0,003 de macro-F1, con una
  desviación entre particiones de solo ±0,007. El resultado no depende de qué
  trozo de datos tocó mirar.
- **Buen ajuste, no memorización.** La brecha entrenamiento → CV es +0,083, dentro
  de la banda sana. El entrenamiento (0,989) es alto, pero la prueba (0,908) lo
  sigue de cerca: generaliza, no memoriza. No lo "arreglamos" bajando el modelo:
  el macro-F1 de CV es prácticamente plano para `C` entre 1 y 8, así que elegimos
  `C = 2,0` por **parsimonia** (la menor capacidad que ya alcanza casi el máximo),
  que además deja la brecha más pequeña sin sacrificar la prueba.

## El control definitivo: barajar las etiquetas

Una puntuación alta podría, en teoría, esconder un error de montaje (por ejemplo,
una fuga sutil). El control más contundente es **barajar las etiquetas**: se
permuta el vínculo entre el texto de cada cláusula y su tipo, y se vuelve a
entrenar y validar con validación cruzada.

Si el modelo aprendía señal real, al romper ese vínculo la señal **desaparece** y
la puntuación debe **desplomarse al suelo aleatorio** (~`1/K`). Si, en cambio,
siguiera alta, sería prueba de que algo hacía trampa (memorización de índices,
fuga, etc.).

Resultado real:

```
Shuffled-label control: CV macro-F1 = 0,053   (vs real 0,906, línea base 0,005)
```

El 0,906 se derrumba a 0,053, justo en el suelo aleatorio de 20 clases. Esto
demuestra que el 0,906 original venía de aprender la relación texto → tipo, no de
un artefacto. Es la diferencia entre *decir* que el resultado es real y
*demostrarlo*.

## Para fijar la idea

- Añadimos un clasificador entrenable y sin conexión (TF-IDF + regresión
  logística) y lo evaluamos en cláusulas reales de LEDGAR.
- En multiclase legal, 1,0 sería sospechoso; buscamos muy por encima de la línea
  base con brecha pequeña.
- **Subajuste** = bajo en todo; **sobreajuste** = alto en entrenamiento y bajo en
  prueba (brecha grande); **buen ajuste** = alto y parecido en todas las vistas.
- **macro-F1** trata todas las clases por igual; es la métrica honrada para
  multiclase. La exactitud es apoyo.
- Tres vistas (prueba retenida, validación cruzada, entrenamiento) + línea base +
  veredicto calculado.
- El pipeline evita la **fuga**: el vectorizador solo ve los datos de
  entrenamiento de cada partición.
- Barajar las etiquetas desploma la puntuación al suelo aleatorio: así se
  **demuestra** que la señal es real.
