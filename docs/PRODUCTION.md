# Producción: Railway + Cloudflare

## Arquitectura y estado

- Railway ejecuta Django con Waitress y PostgreSQL. `/healthz/` comprueba que la base y sus tablas estén disponibles.
- Cloudflare R2 guarda fotos en un bucket privado. Django genera enlaces temporales; no hace falta dominio público para el bucket.
- Un Worker opcional permite usar una dirección `workers.dev`. Primero se puede operar directamente con la dirección HTTPS `up.railway.app`.
- Los recursos de nube todavía no están creados. No se trasladan usuarios, fotos ni participantes ficticios de la computadora automáticamente.

El código local conserva SQLite y sus fotos. La configuración de producción exige PostgreSQL, R2, HTTPS y una clave secreta explícita. El Dockerfile excluye bases locales, credenciales, respaldos y archivos de participantes.

## 1. Crear servicios

1. Crear un proyecto Railway con PostgreSQL y un servicio desde este repositorio. Seleccionar la rama revisada; no fusionar cambios sin revisarlos.
2. Railway usa `Dockerfile` y `railway.json`. Generar un dominio público temporal para el servicio web. Usar el puerto indicado por `PORT`.
3. Crear un bucket **privado** en R2 y credenciales S3 de lectura/escritura limitadas a ese bucket.
4. Copiar las variables de `deploy/railway.env.example` al servicio web. Sustituir todos los marcadores. Si el servicio de base no se llama `Postgres`, ajustar la referencia de `DATABASE_URL`.
5. Generar `SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Guardarla solo en variables de Railway y conservarla entre despliegues.

No copiar `.env` local a producción. `PUBLIC_URL` se obtiene del dominio Railway; también puede definirse explícitamente como `https://nombre.up.railway.app`, sin ruta ni barra final. Configurar las variables antes del primer despliegue.

HSTS queda limitado al hostname de la aplicación. Las advertencias de precarga HSTS y cobertura de subdominios se silencian deliberadamente mientras se usa un dominio temporal; revisar esa política al adquirir el dominio propio.

La construcción instala el modelo de retratos y recopila estáticos. Antes del arranque se ejecutan las migraciones y `seed_catalog` (grupo Coach, sin datos de demostración). El servicio no utiliza el servidor de desarrollo.

## 2. Arranque y comprobación

- Revisar que ambos trabajos de GitHub Actions pasen: pruebas con PostgreSQL y construcción Docker.
- Desplegar y comprobar `/healthz/`: HTTP 200 y `{"status":"ok"}`.
- Desde una terminal **dentro del servicio Railway**, ejecutar `python manage.py createsuperuser` para crear el administrador real. No existe contraseña de producción predefinida.
- Configurar correo de recuperación con `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL` y un `DEFAULT_FROM_EMAIL` verificado por el proveedor. Probar la entrega real; la consola local no envía correos.
- Probar inicio/cierre de sesión, carga y lectura de una foto después de redesplegar, recuperación de contraseña y dos coaches capturando simultáneamente en un evento de ensayo separado.
- Comprobar publicación, cierre de estaciones, desempates y pantalla live antes del primer evento real.

La edición de retratos consume memoria: comenzar con margen de memoria (por ejemplo 1 GB) y medir con fotos y concurrencia reales. No es una garantía de capacidad. Mantener una réplica inicialmente; verificar rendimiento antes de escalar.

## 3. Worker opcional, sin comprar dominio

El código está en `deploy/cloudflare/worker.mjs`. Reenvía sesiones, formularios y archivos a Railway, sin cachear respuestas. Railway sigue alojando toda la aplicación y la base.

Desde `deploy/cloudflare`:

```sh
npx wrangler login
npx wrangler secret put ORIGIN_URL
npx wrangler secret put WORKER_PROXY_SECRET
npx wrangler deploy
```

`ORIGIN_URL` debe ser la URL HTTPS de Railway, nunca la del propio Worker. Generar otro secreto aleatorio de al menos 32 caracteres para `WORKER_PROXY_SECRET`.

En Railway agregar el mismo `WORKER_PROXY_SECRET`, `WORKER_PUBLIC_HOST=optimus-race.TU_SUBDOMINIO.workers.dev` (sin protocolo) y `PUBLIC_URL=https://optimus-race.TU_SUBDOMINIO.workers.dev`. Usar el hostname real devuelto por Cloudflare. Redesplegar Railway y repetir las pruebas de sesión, fotos y formularios a través del Worker.

El middleware solo reconoce el host del Worker cuando recibe el secreto correcto. No configurar `USE_X_FORWARDED_HOST` ni reglas de caché para las páginas. Cambiar de hostname requiere iniciar sesión otra vez.

## 4. Cuando compres el dominio

Asociarlo al Worker (o directamente a Railway si se omite el Worker), esperar HTTPS y actualizar `PUBLIC_URL`. Si hay Worker, actualizar también `WORKER_PUBLIC_HOST`. La base de datos y las fotos permanecen en los mismos servicios.

## 5. Respaldos y actualizaciones

- Activar respaldos PostgreSQL según el plan disponible y mantener una copia externa cifrada con `pg_dump`. Probar `pg_restore` en una base separada.
- Respaldar también los objetos R2 a un destino independiente: un respaldo SQL no incluye las fotos. Conservar las claves/rutas de los objetos.
- El comando local `backup_data` rechaza PostgreSQL/R2 para no generar una falsa impresión de respaldo completo.
- Antes de actualizar, respaldar y revisar migraciones. Volver a una imagen anterior no revierte la base automáticamente.
- Mantener secretos fuera del repositorio y revisar logs sin publicar enlaces firmados ni datos personales.

No activar pagos reales ni importar datos de prueba como parte de este despliegue. Una importación de datos existentes debe prepararse y verificarse por separado.
