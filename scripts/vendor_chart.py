"""Reproduce the pinned browser dependency without a Node build step."""
import io,tarfile,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent.parent/'static'/'vendor';root.mkdir(parents=True,exist_ok=True)
data=urllib.request.urlopen('https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz',timeout=30).read()
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    for source,dest in [('package/dist/chart.umd.min.js','chart.umd.min.js'),('package/LICENSE.md','CHART-LICENSE.md')]:
        (root/dest).write_bytes(archive.extractfile(source).read())
print('Chart.js 4.5.1 vendored with license.')
