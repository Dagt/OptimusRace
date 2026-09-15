import hashlib,json,sqlite3,zipfile
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone

class Command(BaseCommand):
    help='Copia coherente SQLite y fotos a un ZIP nuevo. No incluye secretos.'
    def add_arguments(self,parser):parser.add_argument('--output')
    def handle(self,*args,**options):
        output=Path(options['output']) if options['output'] else settings.BACKUP_DIR/f'optimus-{timezone.now():%Y%m%d-%H%M%S}.zip'
        if output.exists():raise CommandError('El archivo destino ya existe. Usa otro nombre.')
        output.parent.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix='optimus-backup-') as tmp:
            dest=Path(tmp)/'db.sqlite3'
            with closing(sqlite3.connect(settings.DATABASES['default']['NAME'])) as source,closing(sqlite3.connect(dest)) as target:source.backup(target)
            with closing(sqlite3.connect(dest)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise CommandError('La copia no pasó la verificación de integridad.')
            files={'db.sqlite3':dest}
            if settings.MEDIA_ROOT.exists():
                files.update({'media/'+f.relative_to(settings.MEDIA_ROOT).as_posix():f for f in settings.MEDIA_ROOT.rglob('*') if f.is_file() and not f.is_symlink()})
            manifest={'format':1,'created':timezone.now().isoformat(),'files':{name:hashlib.sha256(f.read_bytes()).hexdigest() for name,f in files.items()}}
            with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
                for name,f in files.items():archive.write(f,name)
                archive.writestr('manifest.json',json.dumps(manifest))
        self.stdout.write(f'Backup verificado: {output.resolve()}')
