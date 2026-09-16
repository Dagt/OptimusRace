"""Local MODNet portrait matting. No photos leave the application server."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image,ImageOps,ImageEnhance
from .photos import validate_photo

MODEL_SHA256='07c308cf0fc7e6e8b2065a12ed7fc07e1de8febb7dc7839d7b7f15dd66584df9'
MODEL_URL='https://huggingface.co/Xenova/modnet/resolve/fa2fa546052fba4c08921230a26cc69a333fca12/onnx/model.onnx'
processing=BoundedSemaphore(1)

def model_path():
    return Path(getattr(settings,'PORTRAIT_MODEL_PATH',settings.BASE_DIR/'.models'/'modnet.onnx'))

@lru_cache(maxsize=1)
def session():
    import hashlib
    path=model_path()
    if not path.exists():raise ValidationError('El acabado deportivo aún no está instalado. Puedes usar la foto original.')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=MODEL_SHA256:raise ValidationError('El modelo de fotos necesita reinstalarse. Puedes usar la foto original.')
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])

def portrait_cutout(upload):
    import numpy as np
    validate_photo(upload)
    with Image.open(upload) as source:
        image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((1000,1000))
    width,height=image.size
    scale=min(512/min(width,height),1024/max(width,height))
    size=(max(32,round(width*scale/32)*32),max(32,round(height*scale/32)*32))
    pixels=np.asarray(image.resize(size,Image.Resampling.BILINEAR),dtype=np.float32)/127.5-1
    model=session();mask=model.run(None,{model.get_inputs()[0].name:np.transpose(pixels,(2,0,1))[None]})[0].squeeze()
    if not np.isfinite(mask).all():raise ValidationError('No se pudo separar el fondo. Prueba otra foto o usa la original.')
    alpha=Image.fromarray((np.clip(mask,0,1)*255).astype('uint8')).resize(image.size,Image.Resampling.LANCZOS)
    if np.count_nonzero(np.asarray(alpha)>128)<width*height*.01:raise ValidationError('No se distingue una persona. Prueba con más luz o usa la foto original.')
    image=ImageEnhance.Contrast(image).enhance(1.03)
    image=ImageEnhance.Sharpness(image).enhance(1.08)
    image.putalpha(alpha)
    # Center the detected silhouette with breathing room; never generate missing anatomy.
    bounds=alpha.point(lambda value:255 if value>32 else 0).getbbox()
    if bounds:
        left,top,right,bottom=bounds;pad=max(8,round((right-left)*.08))
        image=image.crop((max(0,left-pad),max(0,top-pad),min(width,right+pad),min(height,bottom+pad)))
    output=BytesIO();image.save(output,format='PNG')
    return output.getvalue()
