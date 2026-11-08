"""Set Pages TURN secrets from a private local JSON file; never pass secrets as argv."""
from pathlib import Path
import argparse,json,re,subprocess

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('private_json');a=p.parse_args()
 f=Path(a.private_json).expanduser();d=json.loads(f.read_text())
 url=d.get('apiUrl','');key=d.get('apiKey','')
 if not re.fullmatch(r'https://[a-z0-9-]+\.metered\.live/api/v1/turn/credentials',url):raise SystemExit('Invalid Metered HTTPS API URL. No changes made.')
 if not isinstance(key,str) or not 1<=len(key)<=512 or any(ord(c)<33 or ord(c)>126 for c in key):raise SystemExit('Invalid API key. No changes made.')
 root=Path(__file__).resolve().parents[1]
 for name,value in [('TURN_API_URL',url),('TURN_API_KEY',key)]:
  subprocess.run(['wrangler','pages','secret','put',name,'--project-name','sigurni-signal'],input=value+'\n',text=True,cwd=root,check=True)
 print('TURN secrets configured. Redeploy the verified Pages release and run a real relay call check.')
if __name__=='__main__':main()
