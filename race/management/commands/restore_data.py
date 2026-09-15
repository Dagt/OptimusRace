import hashlib,json,sqlite3,zipfile
from contextlib import closing
from pathlib import Path,PurePosixPath
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help='Restaura backup a una carpeta NUEVA. Nunca reemplaza la BD activa.'
    def add_arguments(self,p):p.add_argument('archive');p.add_argument('--destination',required=True)
    def handle(self,*args,**options):
        target=Path(options['destination']).resolve()
        if target.exists():raise CommandError('Destino existente. Usa una carpeta nueva para no sobrescribir datos.')
        try:
            with zipfile.ZipFile(options['archive']) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                if manifest.get('format')!=1 or 'db.sqlite3' not in manifest['files']:raise CommandError('Formato de respaldo inválido.')
                verified={}
                for name,digest in manifest['files'].items():
                    path=PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or not (name=='db.sqlite3' or name.startswith('media/')):raise CommandError('Ruta inválida en respaldo.')
                    data=archive.read(name)
                    if hashlib.sha256(data).hexdigest()!=digest:raise CommandError('El respaldo no coincide con su manifiesto.')
                    verified[name]=data
            target.mkdir(parents=True)
            for name,data in verified.items():
                file=target/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
            with closing(sqlite3.connect(target/'db.sqlite3')) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise CommandError('SQLite no pasó verificación. No uses la restauración.')
            self.stdout.write(f'Restaurado en {target}. BD activa sin modificar. Define DATABASE_PATH y MEDIA_ROOT para revisar la copia.')
        except (zipfile.BadZipFile,KeyError,ValueError) as exc:raise CommandError('Respaldo incompleto o inválido.') from exc
