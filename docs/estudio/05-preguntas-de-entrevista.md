# 05 — Preguntas de entrevista

Preguntas típicas sobre este proyecto y cómo responderlas con seguridad.
Practica diciéndolas en voz alta en inglés también.

## Sobre la orquestación de LLM

**¿Qué es una cascada de LLM y por qué la usas?**
Es una lista ordenada de proveedores tras una misma interfaz: se prueban en orden
y, si uno falla, se pasa al siguiente. La uso por dos razones: libertad (cambiar
o reordenar proveedores es config, no código) y resiliencia (un proveedor caído o
sin clave no detiene el análisis).

**¿Por qué HTTP plano y no los SDK de cada proveedor?**
Para tener adaptadores uniformes y una sola dependencia (`httpx`) en vez de cinco
SDK. Controlo el mapeo petición/respuesta y mantengo las claves solo en el
entorno. El coste es mantener un poco de mapeo por proveedor, que es pequeño.

**¿Cómo pruebas esto sin gastar en APIs ni depender de la red?**
Con dobles que implementan la misma interfaz: `FakeLLM` (respuesta preparada) y
`FailingLLM` (siempre falla). Así pruebo el camino del LLM y el fallback de la
cascada sin tocar la red.

## Sobre robustez

**¿Qué pasa si no hay ninguna clave de API?**
El servicio sigue funcionando con heurísticas deterministas. El LLM es el
principal; las heurísticas son el respaldo. Nunca nos quedamos sin respuesta.

**¿Cómo evitas confiar a ciegas en el modelo?**
Le pido solo un JSON con `type`, `risk`, `rationale`, con los valores permitidos
en el prompt, y **valido** la respuesta contra mi vocabulario. Un tipo inventado
se corrige con la heurística. Y si no hay JSON, trato la respuesta como un fallo y
caigo al respaldo.

**¿Por qué JSON estricto y no prosa?**
Porque la prosa es difícil de parsear y ambigua. Un objeto JSON pequeño es
predecible, barato en tokens y fácil de validar. La `rationale` de una línea
conserva una explicación legible sin romper el parseo.

## Sobre el dominio

**¿Cómo detectas el riesgo de una cláusula?**
Dos vías: el LLM da un nivel con su razón; y la heurística suma pesos de frases
peligrosas ("unlimited liability", "sole discretion", "automatically renew"). Con
umbrales: suma ≥3 alto, ≥1 medio, 0 bajo.

**¿Por qué avisas de cláusulas que faltan?**
Porque mucho del riesgo está en lo que **no** aparece: sin límite de
responsabilidad, sin protección de datos, sin resolución de disputas. Comparo los
tipos detectados con una lista estándar y reporto los ausentes. Es una diferencia
de conjuntos, y la trato como un aviso para que una persona confirme.

**¿Esto sustituye a un abogado?**
No. Es apoyo a la decisión: una primera lectura rápida y explicable. La decisión
la toma un profesional. En producción añadiría citas a nivel de cláusula, listas
por tipo de contrato y jurisdicción, y revisión humana de cada cláusula marcada.

## Sobre el diseño

**¿Por qué este proyecto no usa blockchain?**
Porque no lo necesita. Es orquestación de LLM en el dominio legal. Meter un
contrato inteligente sería artificial. La buena ingeniería es elegir la
herramienta adecuada para el problema.

**¿Qué cubren las pruebas?**
La segmentación, el vocabulario, el analizador (camino LLM con un fake y camino
heurístico), la cascada y su fallback, la API y la CLI. Ninguna prueba toca la
red. Cobertura mínima en CI del 80 %.

## Sobre la evaluación con datos reales (LEDGAR)

**¿Cómo demuestras que el clasificador generaliza y no memoriza?**
Lo evalúo en cláusulas reales de LEDGAR con tres vistas: validación cruzada
estratificada de 5 particiones, una partición de prueba retenida que el modelo no
ve, y la puntuación en entrenamiento para medir la brecha. macro-F1 de 0,906 (CV)
y 0,908 (prueba) frente a una línea base de 0,005, con una brecha entrenamiento →
CV de solo +0,083 y CV y prueba coincidiendo a 0,003. Brecha pequeña y vistas que
coinciden = buen ajuste.

**¿Por qué macro-F1 y no exactitud?**
Porque con 20 clases la exactitud puede engañar: un modelo que favorece las clases
frecuentes parece bueno sin serlo. macro-F1 promedia el F1 de cada clase por
igual, así que castiga el mal desempeño en cualquier tipo de cláusula. Reporto
exactitud como apoyo, no como métrica principal.

**¿Qué prueba que la señal es real y no un artefacto?**
El control de etiquetas barajadas. Permuto el vínculo texto → tipo y reentreno:
el macro-F1 de CV se desploma de 0,906 a 0,053, el suelo aleatorio de 20 clases.
Si siguiera alto, habría fuga o memorización. Que se desplome demuestra que el
0,906 venía de aprender la relación real.

**¿Cómo evitas la fuga de información en la evaluación?**
El vectorizador TF-IDF y el clasificador van en un solo pipeline, y en cada
partición el pipeline se ajusta **solo** con los datos de entrenamiento. Así el
IDF nunca ve el vocabulario de la prueba. Si ajustara con todo, los números
saldrían inflados.

**El entrenamiento da 0,989 y la prueba 0,908. ¿No es eso sobreajuste?**
No. Sobreajuste sería entrenamiento alto con prueba mucho más baja (brecha
grande) e inestable. Aquí la brecha es +0,083, CV y prueba coinciden a 0,003 y la
desviación entre particiones es ±0,007. El entrenamiento siempre es algo más alto;
lo que importa es que la prueba lo sigue de cerca. No bajé el modelo para cerrar
la brecha: el macro-F1 de CV es plano para `C` de 1 a 8, y elegí `C = 2,0` por
parsimonia.

## Pregunta trampa

**Si el LLM clasifica mal una cláusula presente, ¿qué pasa con "cláusulas que
faltan"?**
Podría marcar como ausente una cláusula que sí está. Por eso no es un veredicto
final, sino un aviso para que una persona lo confirme. Además, el riesgo de una
cláusula presente pero débil se detecta por separado con la evaluación por
cláusula. Es la postura correcta para una herramienta de apoyo: señalar, no
decidir.
