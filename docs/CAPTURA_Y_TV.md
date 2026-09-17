# Captura de marcas y resultados en vivo

## Operación del evento

1. Recepción inscribe al participante con foto, peso y efectivo. Queda confirmado y presente, con su número en el evento.
2. Administración inicia la competencia y activa una estación desde el resumen del evento. Actualmente hay **una estación activa por evento**, compartida por todos los coaches; no hay asignaciones individuales de estación ni lotes.
3. Cada coach entra con su cuenta de equipo, abre el evento y busca al participante por nombre o número (también admite `#001`). Comprueba nombre, foto y categoría antes de capturar.
4. Registra la marca en la unidad indicada, la carga si corresponde y los puntos del juez solo en pruebas que usan ese método. «Ausente», «Retirado» o «Faltante» no conservan marca ni puntos.
5. Pulsa «Guardar marca» y espera **Guardado confirmado**. Durante el envío se bloquean los campos de esa tarjeta para evitar cambios que no formen parte de lo enviado. Las demás tarjetas siguen disponibles.
6. Una corrección requiere motivo. La revisión de cada marca impide que dos dispositivos sobrescriban cambios sin enterarse. Si aparece un conflicto, «Cargar versión guardada» permite revisar la marca del servidor; pide confirmación antes de descartar una edición pendiente.
7. Administración avanza de estación. Las pantallas anteriores bloquean la captura y piden actualizar. Si ingresan nuevos participantes, los coaches reciben un aviso para actualizar la lista después de guardar lo pendiente.
8. Al cerrar el evento se fijan los resultados y el servidor rechaza nuevas capturas y correcciones.

Los coaches activos tienen acceso a captura en los eventos; no existe una asignación de coach por evento. Administración controla publicación, estación activa y cierre.

## Sincronización y conexión

- **Coaches:** consulta cada 5 segundos y al recuperar conexión/volver a la pestaña. Actualiza las tarjetas sin cambios pendientes; conserva las ediciones locales y señala conflictos. No reordena participantes mientras se captura.
- **Resultados públicos y administración:** actualizan únicamente las tablas cada 5 segundos cuando están visibles. Conservan capacidades desplegadas, foco de teclado y formularios de corrección externos. No interrumpen una selección de texto.
- **TV:** consulta cada 5 segundos y rota página cada 10 segundos. Calcula las filas según la altura disponible. Conserva los últimos resultados si pierde conexión y muestra el aviso correspondiente. Distingue espera de inicio, resultados provisionales y resultados finales.
- Un fallo o demora al guardar **no equivale a guardado confirmado**. Los valores permanecen en esa pantalla. Si el servidor sí alcanzó a registrar la marca, la siguiente consulta detecta la nueva revisión y ofrece cargarla.
- No hay cola de guardado sin conexión ni almacenamiento permanente de borradores en el teléfono. No cierres la pestaña con capturas pendientes; se avisa antes de salir cuando el navegador lo permite.

En evaluación relativa, otra marca de la misma categoría puede cambiar los puntos de participantes ya capturados. Esos puntos son provisionales hasta el cierre. Las posiciones por capacidad requieren completar sus pruebas; no equivalen automáticamente a la clasificación general.

## Celular, tableta y escritorio

- Una columna de tarjetas hasta 1100 px; dos en escritorio amplio.
- Campos de al menos 50 px, botones de al menos 46–48 px y teclado decimal en entradas numéricas.
- Búsqueda y filtro se apilan en celulares; marca, unidad y estado permanecen junto al participante.
- TV mantiene fotografía, nombre, número y puntos en vistas estrechas; categoría y completitud tienen columnas propias en pantallas amplias.

## Validación realizada

- 148 pruebas Django: permisos, validación de marcas, revisiones entre coaches, correcciones, cálculo relativo, cierre, privacidad, registros y flujos existentes.
- 13 pruebas JavaScript: captura, respuestas tardías, conflictos, pérdida de confirmación, paginación y conexión de TV, además del modal de fotografía.
- `manage.py check`, revisión de sintaxis JavaScript y renderizado de las plantillas mediante el cliente de pruebas.

**Pendiente de validación física:** no hay navegador conectado a las herramientas de esta sesión. Las pruebas de JavaScript usan dobles de DOM/red; no sustituyen una revisión visual ni una prueba táctil en iPhone/Android/tableta y TV real. No se cambiaron las marcas ni los datos de eventos reales para probar.
