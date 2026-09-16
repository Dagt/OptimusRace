# Retratos deportivos locales

## Uso

En Mi perfil / Mi cuenta → Editar foto, o en Recepción → Tomar o revisar foto:

1. Elige una foto o abre la cámara. Selfie permite rostro y hombros; Con ayuda muestra una guía de torso. No se exige cruzar brazos. Temporizador: 0, 3, 5 o 10 segundos.
2. Aplica acabado deportivo para eliminar el fondo con MODNet, mejorar suavemente contraste/nitidez y colocar fondo negro/amarillo. La silueta se centra sin generar rostro, cuerpo ni postura.
3. Compara original y resultado. Ajusta acercamiento y posición o elige fondo original.
4. Pulsa Usar este encuadre y después Guarda el formulario. La vista previa no modifica el perfil.

Se conserva una copia de la imagen de origen con su tamaño, normalizada a JPEG y sin EXIF. No se conservan los bytes originales ni sus metadatos. Fotos anteriores a esta función siguen disponibles; su original separado se conserva a partir de una nueva carga. La copia original puede verse desde el editor. Quitar la foto limpia ambas referencias del perfil.

## Instalación

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py install_portrait_model
.venv/Scripts/python.exe manage.py collectstatic --noinput
```

Reinicia el servidor tras instalar. El modelo ocupa aproximadamente 26 MB y se descarga una vez; queda en `.models/modnet.onnx`, excluido de Git. La descarga está fijada a una revisión y se verifica con SHA-256. No se descargan modelos al recibir fotografías. En otra instalación debe ejecutarse el mismo comando antes de habilitar el acabado deportivo. Sin el modelo, el usuario puede guardar la foto con fondo original.

El procesamiento usa CPU y no requiere tarjeta gráfica ni API de pago. Las imágenes viajan únicamente al servidor propio de Optimus Race. Se admite una inferencia simultánea por proceso; si está ocupado se pide reintentar. El consumo de cómputo y almacenamiento forma parte del equipo/hosting utilizado. La cámara requiere HTTPS o localhost y permiso explícito del navegador.

## Licencias

MODNet y su conversión ONNX se usan bajo Apache-2.0. Fuente y atribución en `licenses/MODNet-NOTICE.md` y licencia completa en `licenses/MODNet-Apache-2.0.txt`.

## Límites

La segmentación puede fallar con fondos confusos, cabello fino, varias personas o poca luz. La vista previa permite conservar el original. El modelo no reconstruye partes del cuerpo fuera de la foto. No se aplica generación de postura o retoque facial. La guía es orientativa; el usuario revisa el encuadre.
