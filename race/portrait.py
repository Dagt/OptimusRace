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

def ensure_model():
    """Install once, including when the app is started with plain runserver."""
    from django.core.management import call_command
    from django.core.management.base import CommandError
    if not model_path().exists():
        try:call_command('install_portrait_model')
        except CommandError as exc:raise ValidationError('No se pudo preparar el acabado deportivo. Revisa la conexión del servidor y vuelve a intentar.') from exc

def model_path():
    return Path(getattr(settings,'PORTRAIT_MODEL_PATH',settings.BASE_DIR/'.models'/'modnet.onnx'))

@lru_cache(maxsize=1)
def session():
    import hashlib
    path=model_path()
    ensure_model()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=MODEL_SHA256:raise ValidationError('El modelo de fotos necesita reinstalarse con manage.py install_portrait_model.')
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
    if not np.isfinite(mask).all():raise ValidationError('No se pudo separar el fondo. Toma otra foto.')
    alpha=Image.fromarray((np.clip(mask,0,1)*255).astype('uint8')).resize(image.size,Image.Resampling.LANCZOS)
    if np.count_nonzero(np.asarray(alpha)>128)<width*height*.01:raise ValidationError('No se distingue una persona. Toma otra foto con más luz.')
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

def sports_photo(upload):
    """Produce the same final portrait for preview and storage."""
    from PIL import ImageDraw
    if not processing.acquire(blocking=False):raise ValidationError('Se está procesando otra foto. Vuelve a intentar en unos segundos.')
    try:
        cutout=Image.open(BytesIO(portrait_cutout(upload))).convert('RGBA')
        background=Image.new('RGB',(600,750),'#111313')
        draw=ImageDraw.Draw(background)
        for y in range(750):
            value=36-int(y*22/750);draw.line((0,y,600,y),fill=(value,value+1,value+1))
        draw.line((580,0,560,750),fill='#b6b225',width=4)
        draw.line((596,0,576,750),fill='#515024',width=2)
        # Upscale small silhouettes as well: thumbnail only shrank them, leaving faces at the bottom.
        scale=max(552/cutout.width,690/cutout.height)
        if max(cutout.width*scale,cutout.height*scale)>3000:
            raise ValidationError('No se distingue un retrato completo. Centra rostro y hombros y toma otra foto.')
        cutout=cutout.resize((round(cutout.width*scale),round(cutout.height*scale)),Image.Resampling.LANCZOS)
        background.paste(cutout,((600-cutout.width)//2,40),cutout)
        output=BytesIO();background.save(output,'JPEG',quality=92)
        upload.seek(0)
        return output.getvalue()
    finally:processing.release()
