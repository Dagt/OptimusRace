# Puntuación: confirmado y lo que falta precisar

## Ya confirmado; no volver a preguntar

La convocatoria establece cuatro capacidades, ocho estaciones de hasta 12.5 puntos cada una (100 total), un intento por estación, orden de estaciones, carga de fuerza del 75% del peso corporal, participantes desde 16 años y categorías por peso/sexo. Todos reciben medalla y solo el primer lugar por categoría recibe pin. El cliente añadió que se evaluará conforme al mejor y peor resultado y que los empates se resolverán con una destreza sorpresa elegida en cada evento.

## Propuesta concreta para confirmar con el cliente

“Proponemos comparar cada estación entre participantes de la misma categoría. El mejor resultado recibiría 12.5 puntos; el peor, 0; las marcas intermedias se repartirían proporcionalmente. Los puntos se recalcularían mientras faltan resultados y quedarían fijados al cerrar el evento. ¿Es esa la interpretación que desean? Si todos logran la misma marca o solo hay un participante en la categoría, ¿les asignamos el máximo por igual? ¿Una estación no realizada queda sin puntos y sin usarse para calcular el mejor y peor?”

Esta confirmación define lo que ‘mejor y peor’ no resuelve. No necesita volver a pedir el número de intentos, premios ni las estaciones que ya aparecen en la convocatoria.

## Fórmula propuesta, aún no aplicada como regla oficial

Para repeticiones, distancia o altura (mayor es mejor):

`puntos = máximo × (marca − peor) / (mejor − peor)`

Para tiempos (menor es mejor):

`puntos = máximo × (peor − marca) / (peor − mejor)`

Ejemplo: peor = 20 repeticiones, mejor = 40, máximo = 12.5. Las marcas 20 / 30 / 40 reciben 0 / 6.25 / 12.5 puntos. Ser el peor de una categoría fuerte no significa no tener capacidad física: cero representa la posición relativa en ese grupo.

Si mejor = peor, las fórmulas dividen entre cero. El caso debe tener una regla explícita. La propuesta es mismo máximo para los empatados o participante único, con indicador de que no hubo dispersión. No se ha asumido esa decisión por el cliente.

## Gráficos recomendados

- Radar del evento: normalizar cada estación relativa a 0–100 y promediar dentro de cada capacidad. Etiqueta: “Desempeño relativo en tu categoría”. Los valores son provisionales durante la captura.
- Evolución personal: usar marcas originales, conservando unidad, duración, recorridos, carga y protocolo. Un mejor puntaje en otro evento puede deberse al grupo, no a una mejora física.
- Si se requiere un radar comparable de condición física entre años, acordar referencias estables independientes de los competidores. No inventar benchmarks ni llamar a un percentil condición física absoluta.

## Desempate sorpresa

Debe registrarse como decisión separada: evento, categoría, atletas empatados, destreza, resultado, ganador, juez y fecha. Determina campeón/pin y orden de puestos, pero no modifica las ocho marcas ni añade una novena dimensión al radar. Su implementación se definirá con el flujo de puntuación relativa; por ahora el motor conserva empates.

## Estado del sistema

Se conservan las opciones existentes de puntuación lineal por referencias o puntos del juez. La fórmula relativa, su recálculo y el registro del desempate descritos aquí son una propuesta; no se han activado como política oficial.
