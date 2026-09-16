# Operación técnica

> **Cambio de flujo (16/09/2026):** las instrucciones anteriores de cuentas de participantes, pagos en línea y recepción posterior quedaron sustituidas por [Mostrador y consulta pública](MOSTRADOR_Y_CONSULTA_PUBLICA.md). Se conservan referencias técnicas a Stripe para operaciones históricas.

## Arranque y configuración

Requisitos y comandos de instalación están en readme.md. `run-local.ps1` prepara migraciones/catálogo y arranca local; no crea usuarios, eventos ni resultados. Tras actualizar código, instala requirements.txt, respalda, ejecuta migrate y reinicia. El servidor de desarrollo se detiene con Ctrl+C.

`.env` se lee automáticamente con python-dotenv. Variables del proceso tienen prioridad. `.env.example` incluye opciones. La clave local se guarda en .local-secret; producción exige SECRET_KEY explícita. Respalda secretos por separado, no en el ZIP de datos.

## Preparación de un evento

1. Crear evento como administrador. Configurar fecha/cierre, precio en MXN, cupo, ocho pruebas, dos por capacidad, benchmarks y categorías sin solapamiento.
2. Revisar barra/redondeo si se usan; referencia de fuerza 75%. Publicar fija reglas, precio, cupo y fechas.
3. Inscribir por Checkout o registrar efectivo exacto en recepción usando correo habitual.
4. Recepción: peso, lote, asistencia. Categoría automática. Para corregir peso después de marcas, explicar motivo; cargas usadas permanecen.
5. Iniciar competencia y elegir prueba/lote. Coach guarda individualmente con confirmación. No rotar pista hasta verificar el lote.
6. Resultados permite al administrador corregir marcas existentes de otras pruebas. Usar motivo y recargar ante conflicto de versión.
7. Resolver reservas antes de cerrar. Cierre conserva resultados y faltantes sin reapertura.

Para recibir atletas con la competencia iniciada, activa **Registro presencial durante la competencia** en Resumen. Con cupo completo, el servidor rechaza nuevas inscripciones.

## Stripe test y live

En `.env`: STRIPE_MODE=test, ALLOW_LIVE_PAYMENTS=0, STRIPE_SECRET_KEY=sk_test_…, STRIPE_WEBHOOK_SECRET=whsec_…, PUBLIC_URL local. Reinicia. Configura reenvío de webhook al endpoint `/stripe/webhook/` mediante herramientas oficiales de Stripe. No se instaló ni conectó una cuenta externa en esta entrega.

Prueba integrada requerida: crear Checkout desde una cuenta propia de prueba, completar pago sandbox, observar webhook, confirmar inscripción/bib y cupo; repetir entrega de evento sin duplicar; expirar/cancelar reserva; simular respuesta perdida y ejecutar conciliación.

```powershell
./.venv/Scripts/python manage.py reconcile_payments
```

La conciliación respeta el modo y conserva reservas inconsistentes para revisión. No cobra. Programarla es una tarea del despliegue; no hay automatización instalada.

Live está implementado, desactivado por defecto. Para habilitarlo se requieren **todos**: STRIPE_MODE=live, ALLOW_LIVE_PAYMENTS=1, clave sk_live_, secreto de webhook live, DEBUG=0 y PUBLIC_URL=https://… . Los eventos DEMO siguen bloqueados para cobro real. Verificar primero cuenta, webhooks e infraestructura del organizador. Cambiar solo la clave no habilita pagos. No se realizaron cargos.

## Correo y activación de acceso

En local el backend de consola muestra enlaces en el servidor; no entrega correos. Para SMTP define EMAIL_BACKEND, HOST, PORT, USER, PASSWORD, USE_TLS/USE_SSL y DEFAULT_FROM_EMAIL. TLS 587 y SSL 465 son alternativas: no actives ambas. La cuenta creada en recepción tiene contraseña aleatoria y recupera acceso con su mismo correo. Recuperación limita envíos y evita exponer si existe la cuenta. Ante fallo SMTP devuelve respuesta genérica y registra un mensaje técnico.

## Respaldo y restauración

```powershell
./.venv/Scripts/python manage.py backup_data
./.venv/Scripts/python manage.py restore_data backups/ARCHIVO.zip --destination C:/OptimusRestore/revision-01
```

Backup usa SQLite online backup, comprueba integridad y agrega media y manifiesto SHA256. No incluye .env, claves ni Excel/JPEG originales. Define BACKUP_DIR en otra ubicación protegida. Los respaldos contienen datos personales; protege su acceso.

Restore exige carpeta nueva; valida rutas y hashes, restaura BD/fotos y ejecuta integrity_check. Nunca reemplaza la BD activa. Revisa con DATABASE_PATH y MEDIA_ROOT apuntando a la copia, en otra instancia/puerto. Para recuperación operativa, detén escrituras, verifica la copia y cambia rutas del proceso antes de reiniciar. Conserva el original hasta confirmar recuperación. No hay respaldo programado automático.

## Despliegue HTTPS

No hay despliegue público. Preparación manual:

- Disco persistente del servidor fuera de OneDrive: DATABASE_PATH y MEDIA_ROOT. No sincronizar una SQLite abierta entre equipos.
- DEBUG=0, SECRET_KEY aleatoria, ALLOWED_HOSTS, PUBLIC_URL y CSRF_TRUSTED_ORIGINS correctos.
- Ejecutar collectstatic. WhiteNoise sirve `/static/` también con DEBUG=0.
- Waitress en loopback detrás de proxy HTTPS. Si activas TRUST_PROXY_SSL=1, el proxy debe reemplazar X-Forwarded-Proto y ser el único acceso a Waitress.
- Servir `/media/` desde el proxy o almacenamiento dedicado; WhiteNoise no sirve uploads de usuarios. Restringir permisos del directorio y usar Content-Type correcto.
- Probar SMTP, Stripe, fotos, recuperación, reinicio, backup, red de teléfonos y TV antes de la operación real.

```powershell
./.venv/Scripts/python manage.py collectstatic --noinput
./.venv/Scripts/waitress-serve --listen=127.0.0.1:8000 optimus.wsgi:application
```

La entrega verifica recursos estáticos y redirección HTTPS mediante cliente local seguro. No sustituye una prueba del proxy/dominio real.

## Diagnóstico

Pago pendiente: no volver a cobrar efectivo; revisar evento de Stripe/conciliación. Captura incierta: recargar para confirmar revisión guardada. Pista cambiada: abrir la prueba/lote vigentes. Peso equivocado: administrador con motivo. Recuperación sin correo: revisar backend/SMTP/log, sin revelar enlaces a terceros. Evento cerrado: conservar historia y preparar nueva edición.
