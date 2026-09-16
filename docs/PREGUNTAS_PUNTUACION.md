# Puntuación relativa y desempates

## Regla implementada

Cada estación compara marcas realizadas dentro de la misma categoría y evento. El mejor resultado recibe el máximo configurado; el peor, cero; las marcas intermedias reciben puntos proporcionales.

- Mayor es mejor: `máximo × (marca − peor) / (mejor − peor)`.
- Menor es mejor: `máximo × (peor − marca) / (peor − mejor)`.
- Si todos tienen la misma marca o hay un único participante con marca válida, reciben el máximo.
- Pruebas no realizadas y descalificados no determinan extremos; no aportan puntos.
- Una marca válida de cero sí participa en la comparación.

Ejemplo: 20, 30 y 40 repeticiones con máximo 12.5 producen 0, 6.25 y 12.5 puntos. Cero describe la posición relativa en ese grupo, no ausencia de capacidad física.

Los puntos se recalculan al capturar o corregir marcas, cambiar categoría o descalificar. Son provisionales hasta cerrar el evento. Se calculan con seis decimales por estación y cuatro en el total; los empates se determinan por ese total. La presentación habitual muestra dos decimales.

## Flujo administrativo

1. Crear ejercicios en **Catálogo de pruebas**, con unidad, dirección, duración, recorrido, carga y protocolo.
2. Crear evento vacío y agregar sus estaciones. Elegir **Relativa: mejor y peor de la categoría**. Los máximos deben sumar 100. También siguen disponibles referencias lineales y puntos del juez.
3. Configurar categorías, fechas, cupo, edad, tarifas y descuentos; publicar.
4. Inscribir, confirmar recepción/peso y comenzar competencia. El coach registra marcas originales y carga cuando corresponda.
5. En **Operación → Resultados → Desempates por categoría**, registrar destreza, juez, resultado observado y una posición distinta para cada empatado. La posición 1 corresponde al ganador de ese grupo empatado.
6. Revisar completitud y resolver empates del podio. En **Resumen → Cerrar edición y fijar resultados**, cerrar: se conserva la clasificación final y se identifica al campeón de cada categoría para el pin. No hay reapertura.

La destreza sorpresa solo cambia posiciones entre empatados: no cambia las marcas, los puntos ni el radar. Si cambian las marcas o participantes de la categoría, la decisión anterior deja de ser vigente y debe revisarse. Se conserva auditoría de las decisiones. El cierre de eventos con puntuación relativa exige resolver los empates que afecten los primeros tres lugares; permite conservar faltantes explícitos.

## Gráficos

- Radar: desempeño relativo de 0 a 100, ponderado por los máximos de las estaciones de cada capacidad. Con máximos iguales equivale al promedio. Identifica puntos provisionales.
- Evolución: marcas originales; separa ejercicios con distinta duración, recorrido, carga prescrita, equipo o protocolo. Muestra la carga real registrada.
- Un aumento de puntos entre eventos puede deberse al grupo de competidores. No representa por sí solo mejora física ni un percentil.

No se inventaron referencias físicas absolutas ni se cargaron eventos predefinidos. Los datos de la convocatoria son una referencia de lo que el organizador puede configurar. La medalla para todos y el pin para el campeón no requieren modificar el puntaje.
