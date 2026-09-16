"""Local MODNet portrait matting. No photos leave the application server."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image,ImageOps,ImageEnhance
from .photos import validate_photo

def clean_matte_edges(image,alpha):
    """Remove light-background spill at semi-transparent silhouette edges."""
    import numpy as np
    from PIL import ImageFilter
    rgb=np.asarray(image,dtype=np.float32)
    matte=np.asarray(alpha,dtype=np.float32)/255
    core=(matte>.95).astype(np.float32)
    def blur(values):
        return np.asarray(Image.fromarray(np.uint8(np.clip(values,0,255))).filter(ImageFilter.GaussianBlur(3)),dtype=np.float32)
    weight=blur(core*255)/255
    interior=np.stack([blur(rgb[...,c]*core)/np.maximum(weight,.001) for c in range(3)],axis=-1)
    edge=((matte>.03)&(matte<.95)&(weight>.08))
    blend=np.where(edge,np.clip((1-matte)*1.5,0,.85),0)[...,None]
    cleaned=rgb*(1-blend)+interior*blend
    new_alpha=np.clip((matte-.025)/.975,0,1)**1.1
    return Image.fromarray(np.uint8(np.clip(cleaned,0,255))),Image.fromarray(np.uint8(new_alpha*255))

def balance_portrait_light(image,alpha):
    """Bounded exposure and broad lighting correction using only the subject.

    Preserve channel ratios and facial detail; clipped camera data cannot be recovered.
    Background pixels must not determine the portrait exposure.
    """
    import numpy as np
    from PIL import ImageFilter
    rgb=np.asarray(image,dtype=np.float32)/255
    mask=np.asarray(alpha,dtype=np.float32)/255
    luminance=rgb @ np.array([.2126,.7152,.0722],dtype=np.float32)
    ys,xs=np.where(mask>.8)
    if len(ys)<100:return image
    upper=(np.indices(mask.shape)[0] <= ys.min()+(ys.max()-ys.min())*.6)
    samples=luminance[(mask>.8)&upper&(luminance>.05)]
    if len(samples)<100:return image
    exposure=float(np.clip(.48/max(float(np.percentile(samples,65)),.08),.65,1.45))
    radius=max(12,min(image.size)*.09)
    def blur(values):
        return np.asarray(Image.fromarray(np.uint8(np.clip(values,0,1)*255)).filter(ImageFilter.GaussianBlur(radius)),dtype=np.float32)/255
    local=blur(luminance*mask)/np.maximum(blur(mask),.01)
    center=float(np.median(samples))
    correction=np.clip((max(center,.08)/np.maximum(local,.08))**.4,.75,1.25)
    adjusted=luminance*exposure*correction
    # Gentle highlight roll-off instead of further clipping bright skin.
    adjusted=np.where(adjusted>.75,.75+(adjusted-.75)*.65,adjusted)
    ratio=adjusted/np.maximum(luminance,.001)
    corrected=np.clip(rgb*ratio[...,None],0,1)
    return Image.fromarray(np.uint8(corrected*255))

def refresh_saved_portrait(person):
    """Reprocess the preserved source, never repeatedly filter an already edited image."""
    import uuid
    from django.core.files.base import ContentFile
    if not person.original_photo:
        raise ValidationError('Esta ficha no tiene foto original. Toma una foto nueva.')
    with person.original_photo.open('rb') as source:
        result=sports_photo(source)
    person.photo.save(f'{uuid.uuid4()}.jpg',ContentFile(result),save=True)

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
    image,alpha=clean_matte_edges(image,alpha)
    image=balance_portrait_light(image,alpha)
    image=ImageEnhance.Sharpness(image).enhance(1.04)
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
        background=Image.new('RGB',(600,750),'#202822')
        draw=ImageDraw.Draw(background)
        for y in range(750):
            value=38-int(y*14/750);draw.line((0,y,600,y),fill=(value,value+6,value+1))
        # Restrained gym colors and diagonal geometry stay behind the silhouette.
        draw.polygon([(470,0),(600,0),(600,750),(570,750),(390,300)],fill='#3e452d')
        draw.line((510,0,588,220,550,410,600,570),fill='#b2b337',width=5)
        draw.line((550,0,600,150),fill='#e8e637',width=10)
        for y in range(65,740,60):draw.line((25,y,70,y),fill='#59623c',width=1)
        # Upscale small silhouettes as well: thumbnail only shrank them, leaving faces at the bottom.
        scale=max(552/cutout.width,710/cutout.height)
        if max(cutout.width*scale,cutout.height*scale)>3000:
            raise ValidationError('No se distingue un retrato completo. Centra rostro y hombros y toma otra foto.')
        cutout=cutout.resize((round(cutout.width*scale),round(cutout.height*scale)),Image.Resampling.LANCZOS)
        background.paste(cutout,((600-cutout.width)//2,40),cutout)
        output=BytesIO();background.save(output,'JPEG',quality=92)
        upload.seek(0)
        return output.getvalue()
    finally:processing.release()
