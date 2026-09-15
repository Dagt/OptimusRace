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

`seed_catalog` solo agrega ejercicios técnicos y el grupo Coach. No sobrescribe ejercicios existentes. Press banca comienza sin benchmarks; debes definirlos antes de publicar. Revisa las demás referencias y categorías con el organizador: no son estándares oficiales.

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
3. Para un coach, crea un usuario en `/admin/auth/user/`, asígnalo al grupo **Coach** y comunica su acceso por tu canal habitual. No necesita ser staff ni superusuario.
4. Registra efectivo recibido en recepción; confirma peso/asistencia/lote. Para acceso a cuentas creadas allí configura SMTP o establece su contraseña desde administración durante tus pruebas locales.
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
