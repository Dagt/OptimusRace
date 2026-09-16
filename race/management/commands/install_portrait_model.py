from hashlib import sha256
from urllib.request import urlopen
from django.core.management.base import BaseCommand,CommandError
from race.portrait import MODEL_URL,MODEL_SHA256,model_path

class Command(BaseCommand):
    help='Download the pinned Apache-2.0 MODNet model once for local photo processing.'
    def handle(self,*args,**options):
        destination=model_path()
        if destination.exists() and sha256(destination.read_bytes()).hexdigest()==MODEL_SHA256:
            self.stdout.write('Modelo de fotos listo.');return
        try:
            with urlopen(MODEL_URL,timeout=90) as response:data=response.read(40*1024*1024)
        except OSError as exc:raise CommandError('No se pudo descargar el modelo.') from exc
        if sha256(data).hexdigest()!=MODEL_SHA256:raise CommandError('La descarga no coincide con el modelo esperado.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=destination.with_suffix('.download');temporary.write_bytes(data);temporary.replace(destination)
        self.stdout.write(self.style.SUCCESS('Modelo de fotos instalado. El procesamiento funciona sin servicios externos.'))
