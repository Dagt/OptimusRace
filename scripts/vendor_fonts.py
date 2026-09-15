"""Vendor Google Fonts Latin faces and their SIL Open Font Licenses."""
import re,hashlib,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent.parent/'static'
fonts=root/'fonts';fonts.mkdir(exist_ok=True)
url='https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=DM+Sans:wght@400;450;500;550;600;650;700&display=swap'
request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
css=urllib.request.urlopen(request,timeout=30).read().decode()
blocks=re.findall(r'/\* latin \*/\s*(@font-face\s*\{[^}]+\})',css)
if not blocks:raise RuntimeError('Latin font faces not found')
result=[]
for block in blocks:
    source=re.search(r'url\(([^)]+)\)',block)[1]
    filename=hashlib.sha256(source.encode()).hexdigest()[:12]+'.woff2'
    target=fonts/filename
    if not target.exists():target.write_bytes(urllib.request.urlopen(source,timeout=30).read())
    result.append(block.replace(source,'fonts/'+filename))
for family in ['barlowcondensed','dmsans']:
    (fonts/(family+'-OFL.txt')).write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/google/fonts/main/ofl/'+family+'/OFL.txt',timeout=30).read())
p=root/'design.css';current=p.read_text(encoding='utf-8');current=re.sub(r'^@import[^\n]+\n','',current);current=re.sub(r'@font-face\s*\{[^}]+\}\s*','',current);p.write_text('\n'.join(result)+'\n'+current,encoding='utf-8')
print('Vendored',len(list(fonts.glob('*.woff2'))),'Latin font files and licenses.')
