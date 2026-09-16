# Retratos deportivos locales

## Uso

En **Inscribir en mostrador**, **Editar ficha y foto** o **Mi cuenta → Editar foto**:

1. Recepción pulsa **Tomar foto** o **Elegir archivo**. Centra rostro y hombros con buena luz. No hay temporizador ni modos de selfie.
2. Al capturar, se procesa automáticamente con MODNet local: se elimina el fondo, se ajustan suavemente contraste/nitidez y se compone el retrato sobre negro y amarillo en 600 × 750 píxeles.
3. Revisa una sola vista previa. Si hace falta, toma otra foto; no se elige entre fondos ni se ajustan controles de recorte.
4. Confirma el formulario. El servidor vuelve a generar el acabado desde la fuente validada antes de guardar, incluso si se intenta enviar un archivo saltándose la vista previa. Un fallo deja el formulario con un error, sin guardar una foto nueva sin procesar.

La vista previa no modifica datos. La fuente se conserva internamente como JPEG sin EXIF para futuras correcciones, pero no se ofrece como alternativa de estilo ni se publica en la ficha. Las imágenes anteriores permanecen disponibles; al reemplazarlas se aplica el nuevo acabado.

## Instalación

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py install_portrait_model
.venv/Scripts/python.exe manage.py collectstatic --noinput
```

Reinicia el servidor tras instalar. `run-local.ps1` instala dependencias y prepara el modelo antes de arrancar. Si se usa directamente `manage.py runserver` y falta el modelo, el primer procesamiento lo descarga automáticamente. La descarga requiere conexión a Internet una sola vez, pesa unos 26 MB, está fijada a una revisión y se verifica mediante SHA-256. Queda en `.models/modnet.onnx`, fuera de Git. Si la descarga falla, se muestra un error y permite reintentar; no hay alternativa de fondo original.


El procesamiento usa CPU y no requiere tarjeta gráfica ni API de pago. Las imágenes viajan únicamente al servidor propio de Optimus Race. Se admite una inferencia simultánea por proceso; si está ocupado se pide reintentar. El consumo de cómputo y almacenamiento forma parte del equipo/hosting utilizado. La cámara requiere HTTPS o localhost y permiso explícito del navegador.

## Licencias

MODNet y su conversión ONNX se usan bajo Apache-2.0. Fuente y atribución en `licenses/MODNet-NOTICE.md` y licencia completa en `licenses/MODNet-Apache-2.0.txt`.

## Límites

La segmentación puede fallar con fondos confusos, cabello fino, varias personas o poca luz. Si no se distingue una persona, toma otra foto con más luz. El modelo no reconstruye partes del cuerpo fuera de la foto. No se aplica generación de postura o retoque facial. La guía es orientativa; el usuario revisa el encuadre.
