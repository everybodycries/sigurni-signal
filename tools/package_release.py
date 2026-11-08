"""Prepare a public source snapshot and static downloads, never private runtime data."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'__pycache__','.playwright-cli','.git','.gradle','.netlify','.wrangler','.temp','node_modules','build','work'}
PRIVATE_SUFFIXES={'.apk','.zip','.pyc','.jks','.keystore','.sqlite3','.db'}
OMIT_REPORTS={'android-build-log.txt','android-final-assets-log.txt','android-jvm-tests.xml','apk-signature-verification.txt'}
def public_file(p):
 rel=p.relative_to(ROOT)
 return not any(s in EXCLUDE for s in rel.parts) and p.suffix not in PRIVATE_SUFFIXES and not p.name.startswith(('.env','.dev.vars')) and '.sqlite' not in p.name and not p.name.startswith('SHA256SUMS') and p.name not in OMIT_REPORTS

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--staging');a=parser.parse_args()
 files=[p for p in sorted(ROOT.rglob('*'))if p.is_file() and public_file(p)]
 archive=ROOT/'sigurni-signal-source-v0.4.1.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for p in files:z.write(p,Path('sigurni-signal')/p.relative_to(ROOT))
 with zipfile.ZipFile(archive)as z:assert z.testzip() is None
 (ROOT/'web/downloads').mkdir(exist_ok=True)
 shutil.copy2(archive,ROOT/'web/downloads/source.zip')
 native=ROOT/'sigurni-signal-pilot.apk'
 checks={archive.name:hashlib.sha256(archive.read_bytes()).hexdigest()}
 if native.exists():checks[native.name]=hashlib.sha256(native.read_bytes()).hexdigest()
 (ROOT/'SHA256SUMS-v0.4.1').write_text(''.join(h+'  '+n+'\n' for n,h in checks.items()))
 if a.staging:
  staging=Path(a.staging).resolve();staging.mkdir(parents=True,exist_ok=True)
  for p in files:
   target=staging/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 print('Public source files:',len(files),'Source ZIP:',archive.stat().st_size,'bytes. APK separate, runtime data excluded.')
if __name__=='__main__':main()
