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

## Preparar una demostración con tus datos

1. Admin → Crear evento. Define sede, fecha, precio, cupo, categorías y ocho pruebas, dos por capacidad. Publicar fija sus reglas.
2. Crea participantes desde Unirme, o desde inscripción presencial usando su correo habitual. La cuenta se conserva entre ediciones.
3. Para un coach, abre **Usuarios y equipo → Crear usuario**, selecciona el rol **Coach** y comunica su acceso por tu canal habitual. La plataforma asigna sus permisos automáticamente.
4. Registra efectivo recibido en recepción; confirma peso/asistencia/lote. Para acceso a cuentas creadas allí configura SMTP o establece su contraseña desde Usuarios y equipo durante tus pruebas locales.
5. Inicia competencia, elige prueba/lote y captura. Abre TV desde el evento. Perfil/radar/evolución aparecen cuando existen participaciones; no hay resultados simulados de respaldo.

Un evento que marques expresamente como **evento de pruebas** bloquea cobros reales. Es una protección opcional, no genera datos.

## Qué viaja con GitHub

Código, migraciones, plantillas, imagen editorial de marca, fuentes/gráficas licenciadas, pruebas aisladas y documentación. **No viajan** usuarios ni datos de operación: SQLite, fotos de participantes, secretos, `.env`, `.venv`, respaldos, capturas antiguas y referencias originales privadas están excluidos.

Cada laptop crea su propia base local. `git pull` actualiza código, no sincroniza inscripciones. Para transferir datos después, usa respaldo/restauración deliberados fuera de Git; nunca copies `.venv` entre equipos.

## Servicios externos

Por defecto los pagos están desactivados y el correo usa consola local. Stripe requiere cuenta/claves/webhook y prueba sandbox; SMTP requiere credenciales y entrega verificada. No se cobran tarjetas ni se envían correos externos por instalar. [.env.example](.env.example) contiene opciones y [Operación técnica](docs/OPERACION_TECNICA.md) explica configuración, respaldo y despliegue.

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
| Administrador | Nombre completo, correo, contraseña y confirmación | Ninguno |
| Coach | Nombre completo, correo, contraseña y confirmación | Ninguno |
| Participante | Nombre completo, correo, contraseña y confirmación | Categoría por sexo |

El administrador selecciona primero el rol; el formulario muestra la categoría solo para participantes. Las cuentas nuevas nacen activas. Al editar se puede desactivar el acceso y cambiar la contraseña escribiéndola dos veces; dejar ambos campos vacíos conserva la actual. Mostrar contraseñas permite revisar lo escrito antes de guardar. El registro público siempre crea participantes y también exige confirmación.

La foto es opcional en el perfil. Peso, categoría de peso, lote y asistencia corresponden a la inscripción o recepción de cada evento, no al alta del equipo. Cambiar un participante a coach o administrador conserva su perfil deportivo previo e historial. No se solicitan teléfono ni domicilio. La fecha de nacimiento es opcional para participantes al crear la cuenta y se exige al inscribirse si el evento tiene límites de edad.


## Configuración flexible (eventos nuevos)

El alta de evento inicia sin plantilla. El catálogo describe tipo de resultado, duración, recorridos, carga, protocolo y límites; cada evento guarda su propia copia. Permite estaciones ordenables, máximos que suman 100, categorías, límites de edad, horarios, tarifas por fecha y descuentos con vigencia/usos. Conserva el cálculo y las reglas de las ediciones anteriores.

- [Guía de configuración flexible](docs/CONFIGURACION_FLEXIBLE.md)
- [Guía de puntuación relativa y desempates](docs/PREGUNTAS_PUNTUACION.md)

La paleta usa negro, amarillo y blanco, manteniendo el diseño existente. Tras actualizar ejecutar `python manage.py migrate` y `python manage.py collectstatic --noinput`.


## Cupo, countdown y fotos

Disponible el desglose actualizado de cupo/confirmados/reservas/lugares libres, ajustes auditados sin desplazar inscritos, cuenta regresiva al próximo evento publicado y fotos por archivo o cámara desde perfil, usuarios y recepción. [Guía de uso](docs/CUPO_Y_FOTOS.md).


## Puntuación relativa y cierre

En cada estación puedes elegir evaluación relativa al mejor/peor de la categoría. Se recalcula durante la competencia, excluye faltantes/descalificados y fija los resultados al cerrar. Operación → Resultados permite documentar la destreza sorpresa y ordenar empatados sin alterar puntos. El radar identifica desempeño relativo y la evolución separa protocolos físicos distintos. [Fórmulas y flujo completo](docs/PREGUNTAS_PUNTUACION.md).


Las cuentas de administración y coach muestran Mi cuenta, sin datos deportivos ni inscripción como participante. La confirmación de contraseña informa coincidencias mientras escribes y conserva la validación del servidor. El catálogo organiza la creación en medición, ejecución, carga y opciones avanzadas; la puntuación se configura en el evento.
