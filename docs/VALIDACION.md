# Validación de instalación limpia

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
