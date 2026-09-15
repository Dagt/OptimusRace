# Preguntas para acordar la puntuación con el cliente

La convocatoria define ocho estaciones de hasta 12.5 puntos cada una, pero no especifica cómo convertir marcas en puntos. Necesitamos estas respuestas antes de implementar una escala oficial.

## Mensaje listo para enviar

Para que el sistema calcule exactamente como ustedes califican, ¿nos pueden confirmar lo siguiente?

1. **Conversión por ejercicio.** Para cada estación, ¿qué tiempo, distancia o número de repeticiones da 0, la mitad y 12.5 puntos? ¿Usan una fórmula continua, una tabla por rangos, comparación con el mejor atleta del evento o una calificación asignada por el juez? Compartan la tabla o fórmula completa; tres ejemplos no definen por sí solos la escala.
2. **Variaciones por categoría.** ¿La escala cambia por sexo, rango de peso o edad? Si cambia, necesitamos una tabla por cada combinación. ¿El resultado de un participante depende de los resultados de otros o es definitivo al capturarlo?
3. **Casos fuera de la escala.** ¿Una marca peor que el mínimo obtiene cero? ¿Una marca superior al máximo queda limitada a 12.5? ¿Qué pasa con una estación no realizada, abandono, ausencia o repetición inválida?
4. **Intentos y ejecución.** ¿Es un único intento por estación? Si habrá más, ¿se usa el mejor, el último, la suma o el promedio? ¿Cómo se registra un intento anulado? Definan la técnica válida de sentadilla, press y burpee, el inicio/fin del cronometraje y la medición de los saltos.
5. **Carga de fuerza.** ¿El 75% incluye barra y discos? ¿Qué incrementos se permiten y se redondea hacia arriba, abajo o al más cercano? ¿Hay tolerancia? ¿Qué sucede si el atleta usa una carga diferente?
6. **Penalizaciones.** ¿Se restan repeticiones, se agregan segundos o se descuentan puntos? ¿Cuánto y por qué infracciones? ¿Una descalificación elimina al atleta de toda la competencia o solo de una estación?
7. **Total y desempates.** ¿El total es la suma de las ocho estaciones sin bonos? ¿Con cuántos decimales se calcula y publica, y en qué momento se redondea? Si empatan, ¿comparten lugar o cuál es el orden exacto de desempate? ¿Cómo se asigna el pin cuando hay empate en primer lugar?
8. **Ejemplo completo.** Envíen una ficha resuelta de un participante con categoría, peso, ocho marcas, cargas, penalizaciones, puntos por estación y total final. Incluyan un empate y una marca fuera de rango si es posible.

## Formato sugerido para sus referencias

| Ejercicio | Sexo / peso / edad aplicable | Unidad | Marca o rango | Puntos | Regla de límites y redondeo |
| --- | --- | --- | --- | --- | --- |
| Por completar por el organizador | | | | | |

## Decisiones relacionadas con categorías

Confirmar a qué categoría pertenece un peso exacto en el límite (por ejemplo 70.00 kg), y si hay participación para varones por debajo de 60 kg o mujeres por debajo de 50 / desde 100 kg. El sistema permite configurar los rangos; actualmente incluye el mínimo y excluye el máximo para evitar solapamientos.

## Alcance actual del motor

Opciones disponibles por estación: conversión lineal con referencias expresamente configuradas (base = 50% del máximo, élite = 100%), o puntos ingresados por el juez con límites. Ninguna se presenta como la escala oficial del cliente. Guarda una marca final por estación, permite correcciones auditadas y conserva empates en la misma posición. Tablas por categoría, múltiples intentos, penalizaciones y desempates deportivos específicos se implementarán según las respuestas, sin asumir reglas.
