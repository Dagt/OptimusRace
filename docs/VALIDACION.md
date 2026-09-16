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


## Configuración flexible y paleta (15 septiembre 2026)

69 pruebas automatizadas aprobadas. Cobertura agregada: alta vacía sin plantilla, parámetros de ejercicios y carga, eventos de distinto número de estaciones, suma 8 × 12.5, puntos de juez dentro de límites, edad exacta al día del evento, vigencia de tarifas/descuentos, solapamientos, usos máximos, importes incorrectos, cotización congelada de Checkout, horarios de recepción, descalificación e inmutabilidad de reglas publicadas.

Verificación de navegador en servidor y base SQLite aislados (puerto 8001): acceso administrativo, editor vacío, agregar estación/tarifa/descuento, guardado y recepción de configuración, formulario de catálogo y nueva paleta. Sin errores JavaScript en ese recorrido. Los datos de esta verificación no se cargaron en la base de trabajo. No se hicieron cobros externos.


## Cupo y fotos

77 pruebas automatizadas aprobadas. Nuevas comprobaciones: desglose de lugares, exclusión de reservas expiradas, ajuste de cupo con ocupación mínima y permisos, elección del próximo evento, privacidad de borradores, subida/limpieza de foto, conversión JPEG, imagen inválida y retorno seguro. Prueba independiente de concurrencia: 8 solicitudes, 1 lugar, exactamente 1 confirmación.

Recorrido de navegador en base y medios aislados: countdown activo, desglose 24/25, selección de archivo, vista previa, guardar foto y avatar visible en Usuarios y equipo. No se activó la cámara física del usuario en la revisión; requiere su permiso y dispositivo compatible.


## Puntuación relativa y desempates (15 septiembre 2026)

90 pruebas automatizadas aprobadas. Cobertura: extremos por categoría, mayor/menor mejor, empate completo y participante único, marcas cero, faltantes, descalificación, cambio de categoría, correcciones, decisiones obsoletas, permisos, formularios HTTP de desempate/cierre, campeón único y resultados congelados. También se verificó que la evolución separe protocolos físicos distintos.

Navegador con base aislada: login, resultados provisionales, registro de destreza/juez/orden y clasificación actualizada; los empatados conservaron 100 puntos y recibieron posiciones 1 y 2. La confirmación de cierre bloqueó la herramienta del navegador; el cierre completo, rechazo de empates pendientes y etiqueta de campeón se comprobaron mediante la prueba HTTP automatizada, no como recorrido visual completado.

Arranque limpio aprobado sin usuarios/eventos/inscripciones operativos. Migración 0005 aplicada localmente tras backup verificado. JavaScript comprobado con node --check, Django check sin problemas y archivos estáticos recopilados. No se cargaron eventos de ejemplo en la base local de trabajo.


## Formularios claros y separación de roles

90 pruebas existentes y 2 pruebas nuevas aprobadas. Los casos nuevos verifican que administradores/coaches no creen perfil deportivo al consultar su cuenta, no vean inscripción deportiva y no puedan reservar aun si conservan un perfil antiguo. El catálogo de instalación permanece vacío tras ejecutar dos veces el comando de preparación.

Verificación real en navegador: confirmación de contraseña distinta muestra aviso al escribir, coincidencia cambia a confirmación positiva y editar de nuevo la contraseña original restaura el aviso. No se envió el formulario ni se crearon cuentas.

Se retiraron las nueve pruebas precargadas locales, comprobando que coincidían íntegramente con los originales y tras backup verificado. Las cuentas existentes se conservaron. Los ejercicios sintéticos utilizados por pruebas automatizadas están exclusivamente en un módulo de fixtures de test.


## Formularios simplificados

92 pruebas aprobadas. Revisión en navegador con base aislada: navegación de tres pasos, error de campo obligatorio que vuelve al paso inicial, guardado de borrador sin estaciones y creación de prueba con nombre/capacidad/tipo. Elegir tiempo propuso segundos y menor marca es mejor; el catálogo confirmó esos valores. Sin errores JavaScript en ese recorrido. Los datos de revisión no se añadieron a la base local.
