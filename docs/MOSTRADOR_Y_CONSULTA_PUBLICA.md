# Mostrador y consulta pública

Flujo vigente desde el 16 de septiembre de 2026. Sustituye las instrucciones anteriores sobre cuentas de participantes, inscripción en línea, Stripe y recepción/pesaje posterior.

## Inscribir

1. Entra como administrador. Abre un evento publicado y selecciona **Administrar → Inscribir en mostrador**. También puedes elegir el evento en **Participantes y mostrador**.
2. Busca por nombre o número permanente P. Si la persona ya existe, selecciona **Usar esta ficha**. Si no aparece, completa una nueva ficha. Dos personas pueden tener el mismo nombre: no se fusionan automáticamente.
3. Captura nombre(s), apellido paterno, apellido materno y género. La fecha de nacimiento permite verificar restricciones de edad al día del evento. El correo es opcional, privado y no sirve como cuenta de acceso.
4. Pulsa **Tomar o cambiar foto** para abrir la ventana de captura. Toma la foto con cámara o elige una imagen y pulsa **Usar esta foto**. El acabado deportivo y el encuadre se aplican automáticamente. Revisa el resultado o repite la captura. Para otra edición se puede conservar la foto existente.
5. Pesa a la persona y registra el valor medido en kg. Se guarda por inscripción y determina la categoría y las referencias de carga de ese evento. No habrá otro pesaje obligatorio el día de la competencia.
6. Si hay un código de descuento, ingrésalo: el total se actualiza con la tarifa vigente. Cobra ese importe en efectivo; no hay campo para modificarlo. El servidor vuelve a validar vigencia y usos del descuento al confirmar.
7. Confirma. Se valida en el servidor el cupo, horario, edad, categoría, descuento e importe; se guarda todo en una transacción. Ante un error no se crea una ficha nueva incompleta ni se registra el pago. Reenviar el mismo formulario no duplica la inscripción.
8. Anota para el participante su número permanente **P123**, número del evento del evento y la dirección web. No hay contraseña que entregar.

## Consulta del participante

Desde **Buscar participante**, escribe nombre/apellidos, número P o número del evento. Para número del eventoes conviene elegir el evento, porque se reutilizan entre ediciones. Abre **Ver historial**: muestra foto, categoría, peso deportivo del evento, marcas, resultados por capacidad, gráficos e historial de eventos publicados con inscripción confirmada. No publica correo, fecha de nacimiento, archivos originales de fotos ni datos de pago. Cualquiera con acceso a la web puede consultar estas fichas.

## Competencia y correcciones

Una inscripción nueva queda lista para competir. Inicia la competencia desde Resumen y elige estación; los coaches capturan marcas como antes. En **Participantes** se revisan fichas y se corrige peso o estado cuando haga falta. Corregir peso con marcas ya capturadas requiere motivo y conserva las cargas usadas. Los eventos cerrados conservan su clasificación final. No se configura una ventana de recepción.

## Datos anteriores y despliegue

- Respaldar SQLite y fotos antes de aplicar migraciones.
- `python manage.py migrate` crea `Participant`, enlaza las inscripciones históricas y desactiva el login de antiguos participantes; conserva usuarios históricos como referencias de auditoría. No elimina resultados ni fotos.
- `Registration.user` es nullable y queda solo para compatibilidad. Las nuevas inscripciones usan `Registration.participant` sin crear un `User`.
- El número P identifica la ficha entre eventos. `bib` sigue identificando el número del evento dentro de una edición.
- Pagos y reservas antiguos se conservan. No se inicia ningún checkout desde las rutas públicas. El webhook y conciliación históricos siguen disponibles para resolver operaciones pendientes si las hubiera.
- Administradores y coaches conservan sus cuentas y recuperación por correo.
- En esta implementación SQLite usa transacciones `IMMEDIATE`, y la inscripción bloquea evento/ficha para validar cupo y descuento. Hay unicidad por evento/participante, evento/número del evento y token de envío.
- Los registros nuevos siempre se realizan desde el mostrador. En un evento en curso, el control de inscripción presencial determina si se permiten nuevas altas.

Las fechas se escriben día/mes/año: al teclear o pegar `02032000`, el campo muestra `02/03/2000`. Las fechas y horas de evento usan `dd/mm/aaaa HH:MM`.

No se utilizan lotes ni grupos para operar la competencia. Cada estación incluye a todos los participantes confirmados; los campos históricos de lote permanecen en la base para conservar datos anteriores, pero no filtran ni bloquean la captura.

## Estado de inscripciones

El aviso de inscripciones y el registro de mostrador utilizan la misma regla. En un evento publicado, si se permite inscribir durante el evento y ya llegó la hora de inicio, se puede registrar aunque haya vencido el cierre ordinario, sin tener que iniciar la captura de marcas. Un evento cerrado, una apertura futura o una hora de finalización vencida impiden el registro. Iniciar competencia sigue siendo una acción independiente para habilitar a los jueces.

**Ver perfil** está visible en la fila de cada participante de Administración → Participantes, en el directorio y al editar la ficha. Administración también puede revisar fichas sin historial publicado; estas no se muestran al público.
