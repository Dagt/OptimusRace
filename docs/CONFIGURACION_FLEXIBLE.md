# Configuración de ejercicios y eventos

No hay plantillas predefinidas ni un evento precargado. Crear evento inicia con estaciones, categorías, tarifas, descuentos, nombre, sede, fechas y precio vacíos.

## 1. Catálogo de pruebas

Define nombre, capacidad, tipo de resultado, unidad y dirección (mayor/menor). Parámetros opcionales:

- Duración del esfuerzo en segundos, distancia por recorrido en metros y número de recorridos.
- Carga sin prescripción, fija en kg o porcentaje del peso corporal; barra, incrementos y redondeo.
- Decimales y límites válidos de la marca, equipo y protocolo técnico.
- Referencias base/élite opcionales para quien elija evaluación lineal en su evento.

Ejemplos de modelado (no se cargan automáticamente): burpees → repeticiones durante 60 segundos; shuttle → tiempo para 10 recorridos de 10 m; sentadilla → repeticiones con carga de 75% del peso corporal; salto → distancia/altura en cm. El tipo, nombre y parámetros no están acoplados.

## 2. Crear evento

1. Nombre, sede, fecha y hora, cierre de inscripción, precio general MXN y cupo. El cupo puede quedar vacío en borrador; se exige para publicar.
2. Agregar estaciones desde catálogo o definirlas para esa edición. Se admiten de 1 a 32, ordenables, con parámetros propios. Los máximos deben sumar 100 puntos. Repartir por igual es una acción explícita, no un formato automático de ocho pruebas.
3. Categorías por sexo/peso; máximo incluido; un peso superior al límite pasa al siguiente rango. Máximo vacío = sin límite. Se rechazan solapamientos; un peso fuera de rangos exige resolver las reglas antes de recepción.
4. Edad mínima/máxima al día del evento, apertura de inscripción, recepción, fin del evento, orden de estaciones, reglamento, beneficios y contacto. Horarios en America/Mexico_City; las vigencias se almacenan con zona horaria.
5. Tarifas por periodo, sin solapamientos. Fuera de esos periodos rige el precio general. Cada vigencia incluye inicio y excluye fin.
6. Códigos porcentuales o de importe fijo, fechas y límite de usos. Un código por inscripción, aplicado sobre tarifa vigente. El total no baja de cero. Reservas activas cuentan en el límite y conservan cotización, descuento e importe.

El botón Verificar/Calcular importe consulta el servidor. Confirmar inscripción vuelve a validar precio, código, cupo y edad. El precio no se acepta desde el navegador como autoridad. Los descuentos se controlan dentro de la misma transacción que la reserva. El pago online debe habilitarse expresamente y requiere configuración Stripe.

## 3. Recepción y captura

La fecha de nacimiento es opcional para crear una cuenta y obligatoria para eventos con restricción de edad. Administradores y coaches no tienen este campo deportivo en su alta. Cada inscripción conserva fecha de nacimiento y precio aplicados. Recepción valida horario, peso/categoría y lote.

El coach ve protocolo, duración, recorridos y referencia de carga por estación; captura marca, carga usada si aplica y puntuación si la evaluación es por juez. Valida enteros para repeticiones, decimales y mínimos/máximos. Se conserva una marca final por estación; corregir exige motivo y revisión concurrente. La carga usada se registra y la referencia se muestra; cualquier tolerancia o penalización deportiva requiere el criterio del organizador.

El administrador puede descalificar con motivo. Se conserva el historial y se excluye de posiciones; rectificar una descalificación deja recepción pendiente. Los resultados cerrados no se modifican.

## Compatibilidad y límites expresos

Las ediciones anteriores conservan su cálculo original; las nuevas guardan puntos por estación y suman el total. El radar y la comparación de puntos se normalizan a 0–100 y las marcas originales permanecen disponibles. El catálogo no modifica copias guardadas en eventos.

Capacidades disponibles: Fuerza, Resistencia, Velocidad, Potencia. Una métrica principal por estación, unidades libres, moneda MXN, un descuento por inscripción. No hay agregación de múltiples intentos ni penalizaciones automáticas sin reglas acordadas. La puntuación relativa y los desempates están implementados; consultar PREGUNTAS_PUNTUACION.md para fórmulas y operación.

## Identidad visual

Se conservan composición, tipografía y navegación. Paleta: negro/carbón, blanco y amarillo #F2ED00. Los colores de error mantienen su función de aviso.


## Formularios abiertos y responsabilidades

Todo el formulario permanece visible, sin pasos ni secciones plegables.

- **Catálogo:** nombre, capacidad y resultado (repeticiones, segundos, centímetros, metros, kg u otra medida). La unidad se propone automáticamente y la dirección puede ajustarse. Duración, recorrido, carga e indicaciones son condiciones opcionales.
- **Evento:** datos generales, selección de pruebas del catálogo, puntos, categorías, inscripción, horarios y tarifas. Seleccionar una prueba copia sus condiciones: no se vuelve a capturar su definición. El reparto automático de 100 puntos puede ajustarse manualmente.
- El alta de pruebas ya no solicita referencias de puntuación, límites técnicos, discos ni redondeo. Los parámetros guardados anteriormente se conservan. Las referencias fijas, si se necesitan, se definen en la estación del evento.
- Administradores y coaches acceden a Mi cuenta sin datos deportivos ni inscripción como participantes.

## Nombres de usuarios

Registro público, alta/edición de equipo y recepción separan Nombre(s), Apellido paterno y Apellido materno. Los apellidos admiten espacios y pueden dejarse vacíos cuando no apliquen. La plataforma reúne los componentes para mostrar el nombre y nuevas inscripciones; conserva cada apellido por separado. Los nombres existentes no se dividen automáticamente, evitando adivinar apellidos compuestos; se pueden distribuir al editar. Las inscripciones históricas conservan el nombre registrado en su momento.

Los nuevos eventos y borradores sin inscripciones asignan 70 kg a 60–70 y 70.001 kg a 70–80. El primer mínimo se incluye. Las ediciones ya publicadas conservan sus reglas. Las decisiones sobre ejecución válida, discos e incidencias corresponden a los jueces y organizadores antes de capturar la marca. No se requieren penalizaciones automáticas. Los nuevos eventos incorporan posiciones por capacidad dentro de cada categoría de sexo/peso, además de la general. Para clasificar por capacidad se deben completar todas sus pruebas; las otras capacidades pueden quedar sin realizar. Los desempates son independientes. El pin sigue identificado en el campeón general.


## Crear, publicar y operar

1. Agrega estaciones desde el botón al pie de su lista.
2. Define las categorías en Varonil y Femenil. Cada rango genera su nombre automáticamente. Para generar varios, escribe límites crecientes separados por coma, por ejemplo `60, 70, 80, 90`. Se crean intervalos consecutivos; un último rango abierto se agrega dejando Hasta vacío. Usa punto para decimales. Los nombres de categorías existentes se conservan mientras no cambien sus límites.
3. **Guardar borrador** conserva un evento privado. **Guardar y publicar** guarda y comprueba estaciones, puntos, categorías, cupo y políticas antes de hacerlo visible. Si falta algo, conserva el borrador y muestra el motivo. Publicar fija las reglas; no inicia la competencia.
4. En **Administrar evento**, la guía indica la etapa. **Mostrador** registra inscripción y efectivo; **Recepción** registra peso, lote y asistencia. Inicia la competencia cuando estén listos; selecciona estación y lote para los coaches.
5. Captura las marcas, revisa resultados y resuelve empates antes del cierre.

## Primer acceso después de mostrador

La inscripción crea una cuenta si no existe. No envía una contraseña. Una cuenta existente conserva la suya. Un participante nuevo abre **Ingresar → Crear o recuperar contraseña**, escribe el mismo correo de inscripción, solicita el enlace, establece su contraseña y después inicia sesión para consultar perfil, eventos y resultados.

El envío real requiere configurar un proveedor de correo SMTP. Con el backend de consola local, el enlace se imprime en la terminal del servidor; no llega a una bandeja de correo. Para probar el acceso local también se puede establecer una contraseña desde **Participantes y mostrador → Editar participante**.


## Autoinscripción, foto y pesaje

Con una cuenta de participante: Explorar eventos → Ver evento → Inscribirme. Se requiere habilitar inscripción y pago en línea en el evento, configurar Stripe y tener inscripciones vigentes y cupo. La confirmación depende de la verificación del pago. Publicar no activa automáticamente la inscripción en línea. Administradores y coaches no pueden autoinscribirse.

Mostrador confirma inscripción y pago, y puede operar antes del evento. El día del evento: Administrar evento → Recepción · foto y pesaje → buscar y abrir la ficha → tomar o revisar foto → volver → capturar peso medido, lote y asistencia → Guardar pesaje y asistencia. La foto es opcional, pertenece al perfil y puede cargarse antes; guardarla no confirma recepción. El peso oficial pertenece a la inscripción de esa edición y determina categoría y carga.

Define Apertura y Cierre de recepción antes de publicar para restringir el pesaje al horario del día del evento. Sin estos límites, el sistema no impone una fecha de pesaje automáticamente. Los límites configurados también afectan correcciones de recepción.
