# Revisión de interfaz y mostrador — 16 de septiembre de 2026

## Cambios

- Mostrador separa búsqueda, ficha y pesaje/cobro. La ficha y el cobro aparecen en dos columnas en escritorio y se apilan en pantallas estrechas.
- Buscar un número P exacto selecciona la ficha existente. Las coincidencias ya inscritas enlazan al perfil y no ofrecen otra inscripción.
- Los campos personales se comparten entre inscripción y edición de ficha para mantener etiquetas, orden y errores iguales.
- La foto ocupa una miniatura junto al botón de captura. El modal muestra las acciones correspondientes a elegir, capturar, procesar, revisar o reintentar.
- Cancelar conserva la última foto aceptada. Las respuestas tardías de cámara/procesamiento se ignoran después de cancelar. No se permite guardar una captura pendiente de aceptar.
- El retrato recupera fondo grafito/oliva, diagonales amarillas y detalles deportivos. El procesamiento conserva rostro y postura; no genera anatomía ni inventa información perdida por exposición.
- Un perfil sin participaciones conserva una gráfica de cuatro capacidades, vacía y con valores «sin datos». La ausencia de marcas no se representa como cero.
- Los accesos de inscripción consideran fechas, permiso de registro durante la competencia y cupo disponible. El servidor vuelve a validar esas condiciones al guardar.
- Las reservas históricas solo aparecen en el desglose cuando existen.

## Comprobaciones

```powershell
.venv/Scripts/python.exe manage.py test --noinput
node --test tests/photo-editor.test.cjs
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```

La suite de Django cubre inscripción en efectivo, cálculo y descuentos, capacidad, fechas, publicación y cierre, permisos, privacidad, duplicados, resultados, correcciones, TV y procesamiento de retratos. Las pruebas nuevas cubren selección de ficha, participantes ya inscritos, cupo agotado, perfil sin eventos y estructura HTML de 13 páginas. Las pruebas de JavaScript cubren estados, cancelación, reintento y respuestas tardías mediante dobles de cámara y red.

Las páginas comprobadas son inicio, cuenta, equipo, catálogo, directorio de participantes, búsqueda pública, creación de evento, mostrador, edición de ficha, perfil público, detalle del evento, operaciones y TV. Se comprueba respuesta correcta, ausencia de formularios anidados e identificadores únicos. Esto no sustituye la comprobación de su presentación en un navegador.

## Límites de esta revisión

La herramienta de navegador no ofrece ninguna superficie disponible en esta sesión. No se pudo comprobar visualmente escritorio/móvil ni accionar una cámara física. Sí se inspeccionó una imagen producida por el procesador real a partir de la foto adjunta; ese archivo ya estaba procesado y no reemplaza una prueba con el original de cámara.

Las fotos guardadas no se sobrescriben en lote: «Mejorar foto actual» vuelve a procesar el original conservado. Una foto nueva usa el mismo acabado en la vista previa y al guardar. Los campos privados continúan fuera del perfil público. No se agregaron servicios de pago ni dependencias de procesamiento externo.
