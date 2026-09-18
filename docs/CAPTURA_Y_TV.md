# Captura de marcas y resultados en vivo

## Operación del evento

1. La inscripción con foto, peso y pago confirma al participante y le asigna número, pero no presupone asistencia. Puede hacerse antes del evento o durante él si administración lo permite; no se requiere una etapa de recepción.
2. Administración inicia la competencia y activa una estación desde el resumen del evento. Actualmente hay **una estación activa por evento**, compartida por todos los coaches; no hay asignaciones individuales de estación ni lotes.
3. Cada coach entra con su cuenta de equipo, abre el evento y busca al participante por nombre o número (también admite `#001`). Comprueba nombre, foto y categoría antes de capturar.
4. Registra la marca en la unidad indicada, la carga si corresponde y los puntos del juez solo en pruebas que usan ese método. La primera marca realizada confirma presencia en el evento. «No se presentó a esta prueba» resuelve únicamente esa estación y permite competir en las siguientes. «Se retiró del evento» conserva marcas anteriores y excluye de las revisiones siguientes; una reactivación requiere administración. «Por revisar» sigue pendiente y nunca se convierte automáticamente en ausencia.
5. Pulsa «Guardar marca» y espera **Guardado confirmado**. Con la confirmación, la ficha se cierra y queda un aviso con el número y nombre; ante un error permanece abierta. «Siguiente por revisar» queda debajo de la ficha. Para corregir una marca, vuelve a buscar al participante. Durante el envío se bloquean los campos de esa tarjeta para evitar cambios que no formen parte de lo enviado. Puede seleccionar otro participante sin perder la ficha que se está guardando.
6. Una corrección requiere motivo. La revisión de cada marca impide que dos dispositivos sobrescriban cambios sin enterarse. Si aparece un conflicto, «Cargar versión guardada» permite revisar la marca del servidor; pide confirmación antes de descartar una edición pendiente.
7. Al terminar los turnos, los coaches revisan la lista «Por revisar», incluyendo quienes nunca pasaron. Administración usa «Cerrar captura de esta estación» en Resumen, habilitado cuando no quedan pendientes, y después activa la siguiente. Puede reabrir la estación para correcciones. Las pantallas bloquean nuevas capturas al cerrarse. Si ingresan nuevos participantes, los coaches reciben un aviso para actualizar después de guardar lo pendiente; si la estación estaba cerrada, administración debe reabrirla y resolverlos antes de avanzar.
8. Al cerrar el evento se fijan los resultados y el servidor rechaza nuevas capturas y correcciones.

Solo las cuentas de coach activas pueden acceder a captura, registrar marcas y corregirlas en la estación activa. Los administradores no pueden capturar ni corregir marcas, aunque tengan también el grupo Coach. No existe una asignación de coach por evento. Administración controla publicación, estación activa y cierre.

## Sincronización y conexión

- **Coaches:** consulta cada 5 segundos y al recuperar conexión/volver a la pestaña. Actualiza las tarjetas sin cambios pendientes; conserva las ediciones locales y señala conflictos. No reordena participantes mientras se captura.
- **Resultados públicos y administración:** actualizan únicamente las tablas cada 5 segundos cuando están visibles. Conservan capacidades desplegadas, foco de teclado y formularios de corrección externos. No interrumpen una selección de texto.
- **TV:** consulta cada 5 segundos y rota página cada 10 segundos. Calcula las filas según la altura disponible, sin límite fijo de doce. Usa dos columnas cuando el tablero tiene al menos 1400 px de ancho y filas compactas; en una TV Full HD puede mostrar alrededor de veinte competidores, según el espacio disponible. Conserva los últimos resultados si pierde conexión y muestra el aviso correspondiente. Distingue espera de inicio, resultados provisionales y resultados finales.
- Un fallo o demora al guardar **no equivale a guardado confirmado**. Los valores permanecen en esa pantalla. Si el servidor sí alcanzó a registrar la marca, la siguiente consulta detecta la nueva revisión y ofrece cargarla.
- No hay cola de guardado sin conexión ni almacenamiento permanente de borradores en el teléfono. No cierres la pestaña con capturas pendientes; se avisa antes de salir cuando el navegador lo permite.

En evaluación relativa, otra marca de la misma categoría puede cambiar los puntos de participantes ya capturados. Esos puntos son provisionales hasta el cierre. Las capacidades se muestran como desglose del desempeño; no tienen clasificación, premio ni desempate propios.

## Celular, tableta y escritorio

- Lista compacta con desplazamiento dentro de una altura limitada, sin páginas de seis participantes. Solo se muestra un formulario de captura. «Siguiente por revisar» recorre participantes sin resolver.
- Vista inicial «Buscar»: escribe nombre o número, selecciona una coincidencia y captura. Enter abre al participante cuando hay una sola coincidencia; nunca guarda automáticamente. «Buscar otro competidor» vuelve al buscador. Las pestañas Todos, Realizados y Pendientes muestran listas desplazables; «Sin guardar» aparece cuando existen borradores. Cambiar de vista o participante conserva las ediciones en esta pestaña. La sincronización nunca cambia la selección.
- Varios coaches pueden capturar distintos participantes del mismo evento. No hay reparto automático ni reserva de participantes; si coinciden en la misma marca, el control de revisión rechaza la segunda escritura y permite revisar la versión guardada.
- Campos de al menos 50 px, botones de al menos 46–48 px y teclado decimal en entradas numéricas.
- Búsqueda y filtro se apilan en celulares; marca, unidad y estado permanecen junto al participante.
- TV mantiene fotografía, nombre, número y puntos en vistas estrechas; categoría y completitud tienen columnas propias en pantallas amplias.

## Validación realizada

- Pruebas Django: permisos, validación de marcas, revisiones entre coaches, correcciones, cálculo relativo, cierre, privacidad, registros y flujos existentes.
- Pruebas JavaScript: captura, respuestas tardías, conflictos, pérdida de confirmación, paginación y conexión de TV, además del modal de fotografía.
- `manage.py check`, revisión de sintaxis JavaScript y renderizado de las plantillas mediante el cliente de pruebas.

**Pendiente de validación física:** no hay navegador conectado a las herramientas de esta sesión. Las pruebas de JavaScript usan dobles de DOM/red; no sustituyen una revisión visual ni una prueba táctil en iPhone/Android/tableta y TV real. No se cambiaron las marcas ni los datos de eventos reales para probar.

## Inscripción con pago confirmado

La inscripción en mostrador y el registro del cobro se guardan en una sola transacción. No se crean reservas ni inscripciones pendientes. El cupo y los usos de descuentos cuentan únicamente inscripciones confirmadas. Ausencia, retiro y demás estados deportivos siguen siendo independientes del pago.

La migración 0014 conserva las antiguas reservas como registros históricos sin inscripción (`expired`), sin ocupar cupo. No inventa pagos ni elimina el historial. Los pagos Stripe históricos pueden conciliarse, verificando importe, identidad, cupo y que el evento no haya cerrado; no se crean nuevos Checkout. La base de datos rechaza los estados de inscripción `reserved` y `pending`.

## Estación y desempates en administración

La estación actual permanece guardada al cambiar de pestaña o volver al evento. El botón indica «Estación activa» y se habilita al elegir otra después de cerrar la captura actual sin pendientes. Repetir la misma activación no modifica marcas ni genera otra transición. Un formulario desactualizado no puede cambiar una estación que otro administrador ya cambió.

«Desempates» tiene una pestaña propia y contador actualizado cada cinco segundos durante la competencia. Resumen muestra un acceso directo cuando hay pendientes. La lista muestra únicamente empates por el primer lugar de cada categoría de sexo y peso y abre un solo formulario a la vez: primero se eligen participantes del primero al último; después se documentan prueba, juez y resultado. No se puede seleccionar dos veces al mismo participante. «Actualizar lista» carga los grupos más recientes; las consultas automáticas no reemplazan una decisión que se está escribiendo. El servidor sigue verificando que las marcas no hayan cambiado antes de aceptar una decisión.

Los empates en segundo lugar o posteriores conservan posiciones compartidas; no generan decisiones pendientes ni impiden cerrar el evento.

## Premiación general por categoría

Hay un ganador por categoría femenil y rango de peso, y uno por categoría varonil y rango de peso. La clasificación usa el acumulado de todas las estaciones (máximos configurados que suman 100); no se suman marcas crudas de unidades distintas ni se premia cada habilidad. Las pruebas sin marca aportan cero según la regla existente; la tabla muestra cuántas se realizaron. Los puntajes son provisionales mientras se captura.

Solo un empate en el mayor acumulado de una categoría requiere desempate. Los eventos con la antigua opción de podios por capacidad también usan esta regla. Los registros históricos de decisiones se conservan para auditoría, pero las decisiones por capacidad no se aplican. Las gráficas por habilidad siguen disponibles como información. Los resultados ya cerrados conservan su acumulado y ganador general; se omite la antigua premiación por capacidad al mostrarlos.
