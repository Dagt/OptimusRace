# Estado y pendientes reales

## Entregado y comprobado localmente

Frontend por rol en negro/amarillo, campaña editorial, foto de perfil, radar comparativo, evolución por ejercicio, marca/puntos, editor visual, recepción y correcciones, coach móvil y TV Full HD. Persistencia Django/SQLite, permisos, auditoría, cupo, recuperación y pagos test/live con guardas. Backup/restauración con validación. Pruebas automatizadas aprobadas y revisión real en navegador.

## Antes de abrir al público

| Tema | Qué falta |
| --- | --- |
| Reglas deportivas | Configurar categorías, ejercicios, fecha, sede y precio de cada evento. Referencias base/élite solo si se elige evaluación lineal |
| Stripe | Cuenta del organizador, claves y webhooks; prueba integrada sandbox y validación del despliegue antes de activar live |
| SMTP | Credenciales, dominio remitente y entrega real de activación/recuperación |
| Hosting | Servidor, dominio, HTTPS, proxy, fotos, proceso persistente y supervisión |
| Datos | Base activa fuera de OneDrive, creación de cuentas del equipo en cada instalación limpia |
| Respaldos | Programación, destino protegido externo y ensayo de recuperación en infraestructura definitiva |
| Operación | Ensayo con teléfonos/TV y red de la sede; volumen representativo y recuperación ante cortes |
| Privacidad | Aviso, uso público de nombre/resultados y retención; no hay consentimiento/supresión autoservicio |

Live está **implementado y desactivado**. No requiere desarrollo básico adicional para aceptarse, pero sí configuración y pruebas externas. Esta entrega no realizó ni simuló como exitosos pagos reales.

## Limitaciones conocidas

- Sin reembolsos, cancelación de inscripción confirmada, facturación ni pagos parciales. Sí cancela reserva pendiente con expiración verificada.
- Sin reapertura después del cierre. Sí admite correcciones de peso/marcas mientras el evento está vivo con permisos y motivo.
- Sin captura offline ni cola local; advierte sobre cambios sin guardar, pero recargar puede perderlos.
- Coaches con acceso global a eventos; sin asignación específica, MFA ni verificación de correo de alta.
- No hay avance automático de pista, varios intentos, benchmarks por categoría. Sí hay desempate registrado por destreza sorpresa.
- Sin exportación de tarjetas/reportes ni multi-organización.
- Auditoría de aplicación, modificable por alguien con acceso directo a la BD.
- Archivos antiguos de fotos se conservan en disco al reemplazarlos; limpieza/retención requiere procedimiento.
- Reservas ante fallo externo conservan cupo; conciliación disponible, sin monitor programado ni bandeja avanzada de excepciones.
- Solo se probó contención de 8 inscripciones / 1 lugar, no carga sostenida de producción.

No verificado externamente: Checkout sandbox real, SMTP real, proxy HTTPS, variedad completa de navegadores, accesibilidad auditada y carga de la sede. No están bloqueadas las funcionalidades locales por estas dependencias.
