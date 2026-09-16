# Cupo, próximo evento y fotos

## Cupo

- Define el cupo en Crear evento. Se exige un valor positivo para publicar.
- Disponibles = cupo − inscripciones confirmadas − reservas pendientes de pago.
- Inicio, ficha del evento y operación muestran confirmaciones, reservas y lugares libres. El desglose se actualiza cada 20 segundos con la página visible.
- Una reserva se libera cuando se verifica su cancelación o expiración; un fallo de red o un reloj vencido no liberan un pago sin conciliar.
- En Operación → Resumen → Cupo del evento, el administrador puede ajustarlo con motivo. No se permite bajar de los lugares ocupados ni editar un evento cerrado. El cambio queda auditado.
- La reserva se verifica dentro de una transacción; 8 solicitudes simultáneas para 1 lugar producen exactamente 1 inscripción.

## Cuenta regresiva

La portada elige el evento publicado con inscripciones abiertas cuya fecha futura es la más cercana. Los borradores no aparecen. Muestra días, horas, minutos y segundos y toma como referencia la hora del servidor. También aparece en la ficha del evento. Llegar a cero no inicia la competencia automáticamente: el administrador mantiene el control de pista.

## Fotos

Participante: Mi rendimiento → Editar perfil → Subir desde el dispositivo o Usar cámara → Tomar foto → Guardar perfil.

Administrador: Usuarios y equipo → Tomar o cambiar foto. También desde Operación → Recepción → desplegar participante → Tomar o cambiar foto. Confirmar con Guardar foto.

El participante debe estar de frente, con buena luz y fondo sencillo. La vista previa permite verificar la imagen antes de guardarla. Cambiar de foto sustituye la mostrada en el perfil; la opción de quitar foto vuelve al identificador de iniciales.

JPG, PNG o WebP; máximo 5 MB y 25 megapíxeles. La carga se valida en servidor, se corrige orientación, se optimiza a un máximo de 1000 × 1000 y se elimina metadata al guardar JPEG. Solo el propio usuario edita su perfil y solo administradores editan las fotos desde recepción.

La cámara exige permiso explícito del navegador y HTTPS o localhost. En un celular conectado mediante una dirección HTTP de la red local, usar carga de archivo o servir el sitio mediante HTTPS. La cámara no se activa sola; se apaga al capturar, cerrar el diálogo, enviar el formulario, cambiar de pestaña o salir de la página.
