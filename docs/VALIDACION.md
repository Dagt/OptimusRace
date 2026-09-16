# Validación de instalación limpia

> **Cambio de flujo (16/09/2026):** las instrucciones anteriores de cuentas de participantes, pagos en línea y recepción posterior quedaron sustituidas por [Mostrador y consulta pública](MOSTRADOR_Y_CONSULTA_PUBLICA.md). Se conservan referencias técnicas a Stripe para operaciones históricas.

La aplicación se distribuye sin base operativa ni datos demo. La limpieza local se hizo después de backup y restauración verificada en una carpeta privada fuera del repositorio. Se eliminaron únicamente cuentas/eventos identificados como sembrados; no había registros reales o inciertos. Los archivos originales de referencia permanecen locales e ignorados.

## Comprobaciones reproducibles

```powershell
./.venv/Scripts/python manage.py test race --noinput
./.venv/Scripts/python scripts/verify_startup.py
./.venv/Scripts/python scripts/concurrency_check.py
./.venv/Scripts/python manage.py collectstatic --noinput
./.venv/Scripts/python scripts/verify_secure.py
git diff --check
```

Las pruebas usan datos sintéticos solo en bases temporales: fórmula, faltantes, categorías, cupo, permisos, revisión, cierre, fotos, pagos con dobles, firmas, recuperación y backups. La prueba de arranque ejecuta migraciones/catálogo repetido y exige cero usuarios/eventos/inscripciones, grupo Coach disponible, press banca sin referencia inventada y portada vacía HTTP200. Los estados vacíos de admin/perfil se comprueban sin añadir datos a la instalación de trabajo.

La suite no demuestra pagos externos Stripe, entrega SMTP, hosting HTTPS ni carga sostenida. Esos pasos requieren cuentas e infraestructura del organizador.

Las capturas e informes históricos que contenían personas/datos ficticios quedaron archivados de forma privada, fuera del proyecto distribuido. No se usan como evidencia del estado limpio.


## Configuración flexible y paleta (15 septiembre 2026)

69 pruebas automatizadas aprobadas. Cobertura agregada: alta vacía sin plantilla, parámetros de ejercicios y carga, eventos de distinto número de estaciones, suma 8 × 12.5, puntos de juez dentro de límites, edad exacta al día del evento, vigencia de tarifas/descuentos, solapamientos, usos máximos, importes incorrectos, cotización congelada de Checkout, horarios de recepción, descalificación e inmutabilidad de reglas publicadas.

Verificación de navegador en servidor y base SQLite aislados (puerto 8001): acceso administrativo, editor vacío, agregar estación/tarifa/descuento, guardado y recepción de configuración, formulario de catálogo y nueva paleta. Sin errores JavaScript en ese recorrido. Los datos de esta verificación no se cargaron en la base de trabajo. No se hicieron cobros externos.


## Cupo y fotos

77 pruebas automatizadas aprobadas. Nuevas comprobaciones: desglose de lugares, exclusión de reservas expiradas, ajuste de cupo con ocupación mínima y permisos, elección del próximo evento, privacidad de borradores, subida/limpieza de foto, conversión JPEG, imagen inválida y retorno seguro. Prueba independiente de concurrencia: 8 solicitudes, 1 lugar, exactamente 1 confirmación.

Recorrido de navegador en base y medios aislados: countdown activo, desglose 24/25, selección de archivo, vista previa, guardar foto y avatar visible en Usuarios y equipo. No se activó la cámara física del usuario en la revisión; requiere su permiso y dispositivo compatible.


## Puntuación relativa y desempates (15 septiembre 2026)

90 pruebas automatizadas aprobadas. Cobertura: extremos por categoría, mayor/menor mejor, empate completo y participante único, marcas cero, faltantes, descalificación, cambio de categoría, correcciones, decisiones obsoletas, permisos, formularios HTTP de desempate/cierre, campeón único y resultados congelados. También se verificó que la evolución separe protocolos físicos distintos.

Navegador con base aislada: login, resultados provisionales, registro de destreza/juez/orden y clasificación actualizada; los empatados conservaron 100 puntos y recibieron posiciones 1 y 2. La confirmación de cierre bloqueó la herramienta del navegador; el cierre completo, rechazo de empates pendientes y etiqueta de campeón se comprobaron mediante la prueba HTTP automatizada, no como recorrido visual completado.

Arranque limpio aprobado sin usuarios/eventos/inscripciones operativos. Migración 0005 aplicada localmente tras backup verificado. JavaScript comprobado con node --check, Django check sin problemas y archivos estáticos recopilados. No se cargaron eventos de ejemplo en la base local de trabajo.


## Formularios claros y separación de roles

90 pruebas existentes y 2 pruebas nuevas aprobadas. Los casos nuevos verifican que administradores/coaches no creen perfil deportivo al consultar su cuenta, no vean inscripción deportiva y no puedan reservar aun si conservan un perfil antiguo. El catálogo de instalación permanece vacío tras ejecutar dos veces el comando de preparación.

Verificación real en navegador: confirmación de contraseña distinta muestra aviso al escribir, coincidencia cambia a confirmación positiva y editar de nuevo la contraseña original restaura el aviso. No se envió el formulario ni se crearon cuentas.

Se retiraron las nueve pruebas precargadas locales, comprobando que coincidían íntegramente con los originales y tras backup verificado. Las cuentas existentes se conservaron. Los ejercicios sintéticos utilizados por pruebas automatizadas están exclusivamente en un módulo de fixtures de test.


## Formularios simplificados

92 pruebas aprobadas. Revisión en navegador con base aislada: navegación de tres pasos, error de campo obligatorio que vuelve al paso inicial, guardado de borrador sin estaciones y creación de prueba con nombre/capacidad/tipo. Elegir tiempo propuso segundos y menor marca es mejor; el catálogo confirmó esos valores. Sin errores JavaScript en ese recorrido. Los datos de revisión no se añadieron a la base local.


## Límites superiores y podios por capacidad

Pruebas agregadas: 70 kg pertenece al rango que termina en 70 y 70.001 al siguiente; el primer mínimo se incluye y los eventos anteriores conservan su política. La clasificación por capacidad admite faltantes en otras capacidades, exige completar sus propias pruebas, mantiene desempates independientes y conserva sus resultados al cerrar.


## Formularios abiertos y nombres separados

Se retiraron los pasos y secciones plegables. El catálogo deja de pedir parámetros de discos, redondeo, límites técnicos y referencias; los valores guardados se conservan. El evento reutiliza la definición del catálogo. Nuevas pruebas verifican nombres compuestos, apellidos separados, búsqueda por apellido, conservación de nombres antiguos, interpretación de unidades y edición de borrador sin exigir resultados cerrados.

En navegador con base aislada se creó una prueba con carga del 75%, se seleccionó en un evento y se guardó el borrador. Se verificó la copia visible de la carga sin duplicar campos, y la ausencia de errores JavaScript. Se corrigió la validación de campos internos de cierre que impedía editar un borrador.

Suite completa: 100 pruebas aprobadas tras las migraciones de nombres y validación de borradores.


## Equipo, participantes y mostrador

La administración de equipo solo admite administradores y coaches. Los participantes se crean y editan en una sección independiente; las rutas impiden editar cuentas del otro tipo y el alta de participante no puede otorgar privilegios, aunque se manipule el formulario. Género es un dato personal y la categoría se asigna dentro de cada evento.

Los perfiles de administradores y coaches conservan la tarjeta visual, carga de foto y cámara, sin estadísticas ni datos de competencia. El inicio del participante presenta sus inscripciones y los eventos disponibles. Participantes y mostrador enlaza al registro presencial del evento; se respetan sus restricciones de inscripción.

Verificación: 103 pruebas aprobadas, incluyendo separación de cuentas, permisos, alta de participante, inicio diferenciado y carga/eliminación de foto para ambos roles del equipo. Sin cambios de esquema ni datos operativos de prueba. Cámara física no verificada.


## Estaciones compactas

Las estaciones se presentan como filas con selector de prueba, método y puntos; las marcas objetivo solo se muestran para referencias fijas, explicando la unidad y los puntos que otorgan. Se conservan selección, reglas guardadas y condiciones del catálogo.

Verificado en navegador sobre base aislada: ocho estaciones con 12.5 puntos cada una, activación y retirada de referencias fijas, reordenamiento y eliminación con total de 100 puntos. Revisión visual de filas y 11 pruebas del módulo de experiencia aprobadas; JavaScript válido. Sin cambios en las pruebas creadas por el usuario.


## Categorías, tarifas y descuentos compactos

Campos alineados en filas adaptadas al ancho disponible; fechas completas y controles siempre visibles. Los descuentos identifican su unidad (% o MXN) y el límite vacío indica Sin límite. Verificación visual en navegador con dos filas de cada tipo en la base aislada; cambio de unidad comprobado. 11 pruebas de experiencia aprobadas y sintaxis JavaScript válida. Sin modificar datos del evento real.


## Categorías por rama y publicación directa

Botones para agregar al pie de las listas. Rangos agrupados por rama, con nombres automáticos y generación múltiple mediante límites; conserva nombres existentes sin cambios de peso. Verificación en navegador de generación varonil/femenil y rechazo de solapamientos.

Guardar y publicar usa las validaciones de publicación existentes. Si fallan, conserva el borrador y redirige a editar con el motivo. Guía de operación por etapa y explicación del primer acceso desde mostrador, incluyendo la limitación del correo de consola local. Se comprobó con correo de pruebas que una cuenta creada en mostrador recibe el enlace de primera contraseña. Suite completa: 107 pruebas aprobadas. No se enviaron correos reales ni se modificaron eventos del usuario.


## Claridad de inscripción y recepción

Textos y controles distinguen inscripción/pago de foto/pesaje/asistencia, muestran horarios de recepción y avisan cuando no están configurados. La inscripción en línea se muestra deshabilitada si falta configurar Stripe. Verificación: 15 pruebas de flujos y roles aprobadas. No se habilitaron cobros ni se cambiaron horarios de eventos del usuario.


## Retratos deportivos locales

Modelo MODNet ONNX Apache-2.0 instalado con revisión y hash fijos. Captura guiada selfie/torso, temporizador cancelable, carga de archivo, comparación original/deportivo, ajuste de encuadre y aceptación explícita antes de guardar. Original normalizado sin metadatos conservado por separado, sin sobrescribir imágenes existentes al migrar.

115 pruebas aprobadas (8 nuevas de originales, permisos, validación y vista previa sin escritura). Inferencia real CPU comprobada con imagen de campaña del proyecto. Navegador en base y medios aislados: carga de archivo, segmentación real, centrado, bloqueo de guardado sin aceptación, guardado y visualización en tarjeta. Cámara física y temporizador con cámara real pendientes de prueba en dispositivo; no se accedió a la cámara ni se fotografió al usuario. Copia verificada antes de migrar: before-portraits-20260916.zip.
