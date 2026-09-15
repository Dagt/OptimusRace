# Implementación

## Puntuación

`puntos = clamp(50 + 50 × (marca − base) / (élite − base), 0, 100)`.

La dirección de tiempos se resuelve con élite menor que base. Se validan números finitos, repeticiones enteras y tiempos positivos. Una marca válida de cero repeticiones cuenta como realizada; una prueba faltante no se convierte en cero.

Total: suma de puntos realizados / 8. Capacidad: suma de sus dos pruebas / 2, acumulado sobre 100. Una capacidad incompleta puede mostrar 0 de aporte sin inventar una marca; las tarjetas conservan el guion y el estado pendiente. Cada capacidad pesa 25% del total. Completitud /8 y posición actual acompañan siempre al acumulado.

Categorías: mínimo incluido, máximo excluido, máximo vacío sin límite. No se permiten solapamientos; recepción rechaza pesos que caen en huecos. La categoría corresponde al sexo registrado para ese evento, aunque el perfil cambie después.

## Integridad operativa

SQLite usa transacciones IMMEDIATE para serializar escrituras antes de comprobar cupo. Restricciones únicas impiden duplicar inscripción/dorsal y marca por prueba. Versiones de resultado y recepción detectan pantallas desactualizadas.

Una captura normal requiere evento vivo, prueba/lote activos, inscripción confirmada y presencia. Cada corrección guarda motivo y valores antes/después. El administrador puede corregir resultados existentes de otra prueba/lote mientras el evento está vivo, con las mismas comprobaciones de versión. No puede crear por esa vía una marca inexistente.

Peso: referencia 75%, barra/incremento/redondeo opcionales. Corregir pesaje después de capturar exige administrador y motivo, recalcula categoría y referencia, conserva todas las cargas usadas. Cierre bloquea cambios y almacena una instantánea de clasificación.

## Inscripción y pagos

Correo en minúsculas identifica la cuenta. Recepción reutiliza una cuenta existente o crea una con contraseña aleatoria; su titular establece acceso mediante recuperación. El precio se escribe en MXN en pantalla y se almacena como centavos enteros.

Registro presencial durante competencia requiere habilitación explícita. Respeta el mismo cupo/precio. Un Checkout activo impide cobrar también en efectivo. Reservas conservan cupo ante errores de red.

Checkout alojado: tarjeta y MXN. Cada Payment conserva clave de idempotencia y modo test/live. Confirmación exige firma de webhook, sesión, identidad, modo, monto, moneda y `payment_status=paid`. Se procesan completed, expired y async_payment_succeeded; duplicados no se vuelven a aplicar. Una expiración tardía no revierte un pago ni una reserva más reciente.

Cancelar una reserva consulta y expira la sesión en Stripe; solo después libera cupo. Un error externo conserva el estado. `reconcile_payments` consulta sesiones y recupera eventos perdidos, respetando modo; no realiza cargos. No hay tarea programada instalada.

Modo live exige simultáneamente `STRIPE_MODE=live`, `ALLOW_LIVE_PAYMENTS=1`, clave sk_live_, webhook secret, DEBUG=0 y URL HTTPS. Eventos DEMO rechazan cobros reales. No se realizaron pagos externos en esta entrega. Referencias: [fulfillment de Stripe](https://docs.stripe.com/checkout/fulfillment), [inventario limitado](https://docs.stripe.com/payments/checkout/managing-limited-inventory).

## Acceso y fotografías

Django Auth, sesiones, CSRF y permisos en servidor. Login limita intentos por correo; recuperación limita tres envíos por correo cada 15 minutos, responde de forma genérica y registra fallo SMTP sin exponer la cuenta. SMTP real requiere configuración externa.

Fotos propias de hasta 5 MB, reencodificadas a JPEG y hasta 1000×1000, eliminando metadatos y payload original. No se subió una foto al perfil del usuario durante la revisión; se probó en entorno aislado. Los perfiles sin foto muestran iniciales, sin atribuir la imagen de campaña a participantes.

## Catálogo y distribución limpia

El catálogo técnico conserva referencias configurables; press banca permanece sin benchmarks. Dominadas conserva su referencia propia, sin intercambiarla con press banca. Ocho pruebas y categorías se revisan por evento antes de publicar.

Las referencias originales Excel/JPEG se mantienen privadas y fuera de Git. Se corrigieron fórmulas desplazadas y promedios que omitían faltantes; no se copiaron esos defectos.

No existe comando de siembra de datos demo. Las pruebas sintéticas se ejecutan exclusivamente sobre bases temporales. El campo de evento de pruebas se conserva como protección explícita que impide cobros reales; su valor inicial es falso.
