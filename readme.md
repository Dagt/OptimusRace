# Optimus Race

Plataforma web en español para organizar eventos, inscribir atletas y capturar resultados. Django, SQLite, interfaz móvil y TV pública. La instalación empieza **sin usuarios, eventos, inscripciones ni marcas**. No hay cuentas predeterminadas ni generador de datos demo.

## Primera instalación en Windows

Instala Python 3.13 y Git. Abre PowerShell:

```powershell
git clone https://github.com/Dagt/OptimusRace.git
cd OptimusRace
py -3.13 -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt
Copy-Item .env.example .env
./.venv/Scripts/python manage.py migrate
./.venv/Scripts/python manage.py seed_catalog
./.venv/Scripts/python manage.py createsuperuser
./.venv/Scripts/python manage.py runserver 127.0.0.1:8000
```

En `createsuperuser`, usa tu **correo en minúsculas como nombre de usuario**, repítelo en correo y elige tu contraseña. No se incluye una contraseña fija. Abre [Optimus Race](http://127.0.0.1:8000/), entra con esa cuenta y crea el primer evento.

`seed_catalog` prepara únicamente el grupo Coach. No crea ejercicios, usuarios ni eventos. Crea tus pruebas desde Catálogo de pruebas.

## Siguientes arranques y actualizaciones

```powershell
cd RUTA/OptimusRace
git pull --ff-only
./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python manage.py migrate
./.venv/Scripts/python manage.py seed_catalog
./.venv/Scripts/python manage.py runserver 127.0.0.1:8000
```

También puedes usar `./run-local.ps1` para arrancar después de instalar dependencias. Mantén la consola abierta; Ctrl+C detiene el servidor. No es necesario Docker ni Node/npm.

## Flujo actual: mostrador y consulta pública

1. Administración crea las pruebas y el evento, revisa las reglas y publica. No hay plantillas precargadas.
2. **Evento → Administrar → Inscribir en mostrador**. Primero busca a la persona por nombre o número P para reutilizar su ficha; si es nueva, completa sus datos. No se crea usuario, contraseña ni acceso para participantes.
3. En el mismo formulario toma/selecciona la **foto**, registra el **peso medido**, lote y **efectivo**. El sistema comprueba edad, horarios, cupo, tarifa/descuento y categoría. Confirma una vez; repetir el envío no duplica la inscripción.
4. Entrega el número permanente **P123** y el dorsal de ese evento. Desde **Buscar participante**, cualquier visitante consulta foto, resultados, radar e historial sin login. El dorsal se busca indicando el evento para evitar confusiones; correo y fecha de nacimiento son privados.
5. Inicia competencia y selecciona estación/lote. Los coaches capturan las marcas. No hace falta una recepción o un segundo pesaje; en **Participantes** se pueden corregir datos con los controles y auditoría existentes.
6. Administradores y coaches conservan sus cuentas y fotos. Crea sus accesos desde **Equipo**.

En ediciones siguientes reutiliza la ficha de la persona y registra nuevamente su peso. Puede conservar su foto o tomar otra. Una edición marcada de pruebas no genera cobros electrónicos ni datos simulados; el efectivo capturado es un registro de prueba.

### Actualización de cuentas anteriores

Haz un respaldo antes de `migrate`. Las migraciones 0011–0013 crean las fichas independientes, vinculan inscripciones existentes y conservan fotos, nombres y resultados. Desactivan el login de las cuentas antiguas de participantes sin borrar los registros de auditoría; administradores y coaches conservan su acceso. Los eventos cerrados mantienen su clasificación fijada. No se modifican ni eliminan pagos históricos.

Consulta la [guía del mostrador y resultados públicos](docs/MOSTRADOR_Y_CONSULTA_PUBLICA.md).

## Qué viaja con GitHub

Código, migraciones, plantillas, imagen editorial de marca, fuentes/gráficas licenciadas, pruebas aisladas y documentación. **No viajan** usuarios ni datos de operación: SQLite, fotos de participantes, secretos, `.env`, `.venv`, respaldos, capturas antiguas y referencias originales privadas están excluidos.

Cada laptop crea su propia base local. `git pull` actualiza código, no sincroniza inscripciones. Para transferir datos después, usa respaldo/restauración deliberados fuera de Git; nunca copies `.venv` entre equipos.

## Servicios externos

Las nuevas inscripciones solo registran **efectivo en mostrador**. No hay alta pública de cuentas de participante ni inicio de pagos en línea. El adaptador y webhook de Stripe se conservan exclusivamente para conciliar pagos históricos; las claves no son necesarias para operar el nuevo flujo. SMTP se usa para recuperar las cuentas del equipo; localmente los mensajes aparecen en consola. El acabado fotográfico se procesa localmente sin API de pago.


## Documentación

- [Visión y alcance](docs/VISION_Y_ALCANCE.md)
- [Implementación](docs/IMPLEMENTACION.md)
- [Arquitectura](docs/ARQUITECTURA.md)
- [Validación](docs/VALIDACION.md)
- [Pendientes externos y límites](docs/PENDIENTES.md)
- [Recursos visuales](docs/RECURSOS_VISUALES.md)

## Gestión dentro de la plataforma

Usuarios y equipo permite crear y editar cuentas, elegir Administrador/Coach/Participante, activar o desactivar acceso y establecer contraseña. Los permisos se asignan automáticamente; no necesitas entrar al panel técnico de Django. No puedes desactivar tu propia cuenta administrativa. Desactivar conserva participaciones e historial.

Catálogo de pruebas permite buscar, crear y editar ejercicios, unidad, capacidad, dirección y referencias. Los cambios no alteran reglas ni resultados de eventos guardados. Las dos pantallas usan el diseño y navegación de Optimus Race.


### Campos de cuentas por rol

| Rol | Datos obligatorios al crear | Datos deportivos |
| --- | --- | --- |
| Administrador | Nombre(s), apellido paterno, apellido materno, correo, contraseña y confirmación | Ninguno |
| Coach | Nombre(s), apellido paterno, apellido materno, correo, contraseña y confirmación | Ninguno |
| Participante (sin cuenta) | Nombre(s), apellidos, género; fecha de nacimiento cuando el evento limita edad; correo opcional | Foto y peso al inscribirse; categoría automática |

El equipo se crea desde **Equipo**: administradores y coaches usan correo, contraseña y confirmación. Los participantes tienen fichas independientes sin login. La foto y peso se registran en mostrador; cada inscripción conserva el peso y categoría de su edición.



## Configuración flexible (eventos nuevos)

El alta de evento inicia sin plantilla. El catálogo describe tipo de resultado, duración, recorridos, carga, protocolo y límites; cada evento guarda su propia copia. Permite estaciones ordenables, máximos que suman 100, categorías, límites de edad, horarios, tarifas por fecha y descuentos con vigencia/usos. Conserva el cálculo y las reglas de las ediciones anteriores.

- [Guía de configuración flexible](docs/CONFIGURACION_FLEXIBLE.md)
- [Guía de puntuación relativa y desempates](docs/PREGUNTAS_PUNTUACION.md)

La paleta usa negro, amarillo y blanco, manteniendo el diseño existente. Tras actualizar ejecutar `python manage.py migrate` y `python manage.py collectstatic --noinput`.


## Cupo, countdown y fotos

Disponible el desglose actualizado de cupo/confirmados/reservas/lugares libres, ajustes auditados sin desplazar inscritos, cuenta regresiva al próximo evento publicado y fotos por archivo o cámara desde perfil, usuarios y recepción. [Guía de uso](docs/CUPO_Y_FOTOS.md).


## Puntuación relativa y cierre

En cada estación puedes elegir evaluación relativa al mejor/peor de la categoría. Se recalcula durante la competencia, excluye faltantes/descalificados y fija los resultados al cerrar. Operación → Resultados permite documentar la destreza sorpresa y ordenar empatados sin alterar puntos. El radar identifica desempeño relativo y la evolución separa protocolos físicos distintos. [Fórmulas y flujo completo](docs/PREGUNTAS_PUNTUACION.md).


Las cuentas de administración y coach muestran Mi cuenta, sin datos deportivos ni inscripción como participante. La confirmación de contraseña informa coincidencias mientras escribes y conserva la validación del servidor. Los formularios están abiertos y sin pasos. El catálogo define la medición y condiciones; el evento selecciona esa definición y configura los puntos. Nombre(s), apellido paterno y apellido materno se capturan por separado.


### Fotos deportivas sin API de pago

Recepción toma la foto o elige un archivo. El acabado deportivo y encuadre se aplican automáticamente, sin temporizador ni selector de fondo. El servidor valida el procesamiento antes de guardar; no acepta una foto nueva sin acabado. `run-local.ps1` prepara dependencias y modelo; al iniciar directamente con Django, el modelo se descarga al primer procesamiento si falta. Consulta [instalación y uso](docs/RETRATOS.md).
