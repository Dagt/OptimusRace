# Galería fotográfica

El público entra desde **Galería** en la navegación o desde **Ver galería de fotos** en cada evento. Puede recorrer álbumes, ampliar fotografías en el visor sin iniciar sesión. Las galerías y sus fotos tienen paginación; las miniaturas evitan descargar todas las imágenes grandes al abrir un álbum.

Administración entra desde **Galería fotográfica → Administrar fotos** o desde **Administrar evento → Galería de fotos**. Selecciona hasta 20 fotografías, agrega una descripción opcional y pulsa **Subir fotos con marca de agua**. Cada archivo debe ser JPG, PNG o WebP, pesar menos de 15 MB y tener hasta 25 megapíxeles. El envío completo admite hasta 100 MB. Si algún archivo no es válido, se rechaza el envío completo antes de guardar fotos.

Cada foto se orienta según la cámara, se reduce a un máximo de 1600 píxeles por lado y se guarda como JPEG. El logo oficial de Appex Hub Deportivo queda incorporado grande, centrado y semitransparente, sin fondo; ocupa aproximadamente el 78 % del ancho de la imagen y tiene un 75 % de opacidad. Las miniaturas también llevan la marca. La galería no ofrece enlaces de descarga ni de apertura del archivo. Se deshabilitan el arrastre y el menú contextual de las fotos como disuasión; ningún sitio puede impedir capturas de pantalla o la extracción de una imagen visible en el navegador. No se conserva el original sin marca ni los metadatos EXIF/GPS. Estos cambios corresponden únicamente a las fotos de galería; los retratos de participantes conservan su flujo actual.

Las fotos de eventos publicados, en competencia o cerrados quedan visibles al terminar la carga. Las de borradores solo las ve administración hasta publicar el evento. Coaches y visitantes pueden consultar las galerías públicas; solo administradores pueden subir o eliminar fotos. Para eliminar, despliega **Eliminar foto** y pulsa **Confirmar eliminación**. Las cargas y eliminaciones quedan en la auditoría del evento.

Los archivos usan el almacenamiento configurado para la aplicación: local en desarrollo y R2 en producción. Las simulaciones copian el catálogo de fotos; sus nuevas cargas y eliminaciones quedan aisladas de los archivos reales.

## Actualización

Ejecuta `python manage.py migrate` para aplicar las migraciones de la galería. Después ejecuta `python manage.py update_gallery_watermarks` y reinicia el servicio. El comando actualiza las fotos anteriores al 75 % de opacidad sin acumular marcas al ejecutarse de nuevo. Railway ejecuta las migraciones y la actualización de marcas en el paso previo al despliegue. No se requieren dependencias ni servicios nuevos.

Pruebas: `python manage.py test race.test_gallery race.test_simulations --noinput` y `node --test tests/gallery.test.cjs`.
