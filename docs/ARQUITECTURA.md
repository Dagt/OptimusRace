# Arquitectura

## Stack ejecutable

Python 3.13, Django 5.2.17, SQLite, Stripe SDK 14.4.1, Pillow 12.3.0, Waitress 3.0.2, WhiteNoise 6.11.0, python-dotenv 1.1.1. Versiones fijadas en requirements.txt. Chart.js 4.5.1 y fuentes se sirven desde static; no hay dependencia de CDN ni compilación Node al ejecutar.

| Ruta | Responsabilidad |
| --- | --- |
| optimus/settings.py | .env, base de datos, seguridad, correo, archivos y pagos |
| race/models.py | Perfil, catálogo, evento, inscripción, pago, webhook, resultado, auditoría e intentos |
| race/services.py | Dominio transaccional, puntuación, cupo, captura, pagos y cierre |
| race/views.py / forms.py | Permisos HTTP, formularios, recuperación y respuestas JSON |
| race/context.py | Navegación por rol y evento activo |
| race/admin.py | Usuarios/equipo y catálogo; pagos/auditoría en consulta |
| templates/ | Páginas por rol y recuperación |
| static/design.css | Sistema visual y adaptación móvil/TV |
| static/experience.js | Gráficas, filtros, captura, diálogos, configuración y TV |
| static/vendor/ | Chart.js y licencia |
| race/management/commands/ | Catálogo técnico/grupo Coach, conciliación, respaldo/restauración |
| race/tests.py / scripts/ | Pruebas de dominio, HTTP, arranque y concurrencia |

## Datos

La identidad User/Profile persiste; Registration guarda nombre/sexo/peso/categoría propios de esa participación. Event guarda copia de reglas y versión. Result guarda marca original, carga, puntos, estado y revisión. Payment contiene modo, sesión e idempotencia. Audit registra cambios con actor y motivo. Un evento cerrado sirve su final_board congelado.

Migración0002 añade descripción, registro presencial, revisión de recepción y modo de pago. Se aplicó sin reinicializar la base existente.

## Frontend

Plantillas de servidor mantienen navegación y formularios convencionales. JavaScript agrega interacciones y usa JSON propio para captura/TV; no replica permisos del servidor. Las gráficas se generan con reglas y marcas del historial real. Nulos conservan huecos, las unidades distintas no se mezclan y puntos por edición se muestran con sus benchmarks.

TV usa polling de 5 s y rotación de 10 s. Coach comprueba cambio de prueba/lote cada 10 s y bloquea envío obsoleto. La confirmación de pago se consulta en endpoint privado. No existe WebSocket, cola offline ni aplicación nativa.

## Despliegue previsto

Un servidor con disco persistente y SQLite local, Waitress detrás de proxy HTTPS. WhiteNoise sirve estáticos colectados; el proxy/almacenamiento sirve fotos. BD activa fuera de OneDrive. Para múltiples servidores se requiere migración y pruebas con PostgreSQL y almacenamiento compartido. No se afirma capacidad de tráfico de producción sin medir.

No hay infraestructura contratada ni despliegue público. Consulta OPERACION_TECNICA.md para preparación y verificación.
