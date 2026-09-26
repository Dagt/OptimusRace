"""Route uploaded practice media to disposable storage; original photos stay read-only."""
from django.core.files.storage import Storage, FileSystemStorage, storages
from .simulation_runtime import current, folder


class SimulationMediaStorage(Storage):
    def temporary(self):
        meta = current.get()
        return FileSystemStorage(location=folder(meta['token'])/'media', base_url=meta['prefix']+'/practice-media/') if meta else None

    def reader(self, name):
        temporary = self.temporary()
        return temporary if temporary and temporary.exists(name) else storages['production_media']

    def _open(self, name, mode='rb'):
        if mode not in ('r', 'rb'):
            raise ValueError('Read-only open')
        return self.reader(name).open(name, mode)

    def _save(self, name, content):
        return (self.temporary() or storages['production_media']).save(name, content)

    def exists(self, name):
        return self.reader(name).exists(name)

    def size(self, name):
        return self.reader(name).size(name)

    def url(self, name):
        return self.reader(name).url(name)

    def path(self, name):
        return self.reader(name).path(name)

    def delete(self, name):
        temporary = self.temporary()
        if temporary:
            if temporary.exists(name):temporary.delete(name)
        else:
            storages['production_media'].delete(name)
