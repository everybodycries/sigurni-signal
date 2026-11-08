"""Offline integrity/structure check; no institutional authentication."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 content=ROOT/'content';data=json.loads((content/'guides.json').read_text())
 assert data['version'] and data['updated_at'] and data['guides']
 for g in data['guides']:
  assert g['id'] and g['title'] and g['review_status'] and g['sections']
  assert g['sources'] or g['review_status'].startswith('project_procedure_')
  assert all(s.get('heading') and s.get('text') for s in g['sections'])
  assert all(s['url'].startswith('https://') for s in g['sources'])
 points=json.loads((content/'maps/pilot-points.geojson').read_text());assert points['features']==[]
 manifest=json.loads((content/'manifest.sha256.json').read_text())
 pairs=manifest.get('files',manifest)
 if isinstance(pairs,list):pairs={i['path']:i.get('sha256',i.get('hash')) for i in pairs}
 for name,expected in pairs.items():
  if name in ('version','algorithm','generated_at','warning','signature','updated_at'):continue
  if isinstance(expected,dict):expected=expected['sha256']
  p=ROOT/name
  if not p.exists():p=content/name
  assert hashlib.sha256(p.read_bytes()).hexdigest()==expected, name
 print(f'PASS: {len(data["guides"])} attributed guides; no fabricated map points; integrity manifest checked. Expert/authority review remains pending.')
if __name__=='__main__':main()
