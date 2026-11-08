"""Build standalone printable handbook from local project-authored guides/docs."""
from pathlib import Path
import html,json,os
ROOT=Path(__file__).resolve().parents[1]
def main():
 chapters=['prirucnik.md','iphone-priprema.md','regulatorna-provjera.md','terenska-provjera.md','napajanje-i-nabava.md']
 parts=[]
 for name in chapters:
  for line in (ROOT/'docs'/name).read_text().splitlines():
   if not line:continue
   level=len(line)-len(line.lstrip('#'))
   if level in (1,2,3) and line[level:level+1]==' ':parts.append(f'<h{level}>{html.escape(line[level+1:])}</h{level}>')
   else:parts.append('<p>'+html.escape(line)+'</p>')
 guides=json.loads((ROOT/'content/guides.json').read_text())
 for g in guides['guides']:
  parts.append('<section><h2>'+html.escape(g['title'])+'</h2><p class="review">Nacrt za pilot; stručni pregled nije potvrđen.</p>')
  for s in g['sections']:parts.append('<h3>'+html.escape(s['heading'])+'</h3><p>'+html.escape(s['text'])+'</p>')
  for s in g['sources']:parts.append('<p class="source">Izvor: <a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s['title'])+'</a></p>')
  parts.append('</section>')
 css='body{font:16px/1.65 system-ui,sans-serif;color:#182b2c;background:#f7f6f0;margin:0}main{max-width:820px;margin:40px auto;padding:40px;background:white}h1{border-top:4px solid #296654;padding-top:22px;font-size:30px}h2{margin-top:30px;color:#235b4d}p{overflow-wrap:anywhere}a{color:#235b4d}.review,.source{font-size:12px;color:#52615c}section{break-inside:avoid}@media print{body,main{background:white;margin:0;padding:0}main{max-width:none}h1{break-before:page}h1:first-child{break-before:auto}@page{size:A4;margin:18mm}}'
 document='<!doctype html><html lang="hr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sigurni Signal — offline priručnik</title><style>'+css+'</style><main><p>PRIPREMA / OFFLINE PILOT / 08.11.2026.</p>'+''.join(parts)+'</main></html>'
 p=ROOT/'docs/prirucnik-offline.html';t=p.with_name(p.name+'.restore');t.write_text(document);os.replace(t,p)
 print('Standalone offline handbook generated; no network resources.')
if __name__=='__main__':main()
