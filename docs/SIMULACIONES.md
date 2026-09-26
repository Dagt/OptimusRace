# Simulaciones privadas de eventos

En **Operación → Resumen → Crear simulación**, un administrador crea una copia del estado actual del evento: reglas, fechas, categorías, precios, inscripciones, participantes, fotos de referencia, estaciones, asignaciones, marcas y desempates. No se altera el original.

**Simulaciones** en el menú permite entrar a la copia desde diferentes dispositivos. Los administradores y coaches activos al crearla usan sus cuentas normales. Visitantes y atletas no tienen acceso. Los cambios posteriores del evento real no se sincronizan con una copia ya creada.

En la franja de simulación:
- **Salir** vuelve al sistema real, conservando la práctica para los demás.
- **Reiniciar capturas** elimina marcas y desempates de la copia, conserva parámetros, participantes y asignaciones, y permite iniciar sus estaciones otra vez. El calendario de la copia se traslada al momento de la práctica; recepción y fin del evento duran hasta su caducidad. Las ventanas de tarifas y descuentos se desplazan junto con el calendario. Las condiciones de inscripción se conservan.
- **Terminar y eliminar** elimina la base y las fotos creadas en esa práctica para todos los usuarios. Cerrar competitivamente el evento permite revisar sus resultados antes de eliminar la práctica.

## Aislamiento y despliegue

No crea registros en PostgreSQL. Cada copia tiene una base SQLite y carpeta de fotos propia en `SIMULATION_ROOT` (por defecto `.simulations/`, excluida de Git y Docker). Las fotos originales son referencias de solo lectura; las nuevas se guardan únicamente en la carpeta temporal. No se copian contraseñas utilizables ni sesiones, y se bloquean pagos externos, recuperación de contraseñas y administración de cuentas dentro de las copias.

Las solicitudes siguen las mismas vistas y servicios de competición. El middleware cambia la conexión **local al hilo** exclusivamente durante la vista y su renderizado; siempre restaura la conexión real antes de guardar la sesión. Las solicitudes de una misma copia se serializan para conservar el bloqueo y las revisiones de captura. Las conexiones de otros hilos permanecen intactas. Las rutas y peticiones JS conservan el prefijo de la copia. Se aplican CSRF, autenticación real, autorización y `no-store/noindex`.

Esta implementación utiliza el despliegue actual: **un proceso Waitress y una réplica Railway**, sin volumen persistente para simulaciones. No escalar a varias réplicas sin implementar afinidad/almacenamiento compartido y bloqueo entre procesos. No montar `SIMULATION_ROOT` en un volumen permanente. Un nuevo despliegue puede descartar las prácticas, nunca el evento real.

Caducidad: 24 horas desde creación; el proceso de arranque limpia cada 60 segundos. También se limpian al abrir el listado o crear otra copia. Límite: 8 simultáneas. No requiere migraciones de la base real ni nuevas credenciales.

Pruebas: copia completa, captura HTTP compartida, restauración de conexión ante errores, aislamiento entre hilos, permisos, CSRF, rutas privadas, fotos de solo lectura, reinicio, eliminación y caducidad.
