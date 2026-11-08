#!/usr/bin/env python3
"""Disposable Unix-socket-only Postgres integration tests; NEVER targets hosted DB."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    configured=os.environ.get('SIGURNI_PG_BIN');binary={}
    for name in ('initdb','pg_ctl','psql'):
        value=str(Path(configured)/name)if configured else shutil.which(name)
        if not value or not Path(value).is_file():raise SystemExit('Postgres binaries missing; no hosted fallback')
        binary[name]=value
    with tempfile.TemporaryDirectory(prefix='ss-community-',dir='/tmp') as tmp:
        p=Path(tmp);data=p/'data';started=False
        subprocess.run([binary['initdb'],'-D',str(data),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
        try:
            subprocess.run([binary['pg_ctl'],'-D',str(data),'-l',str(p/'postgres.log'),'-o',f'-k {p} -p 57884 -c listen_addresses= -c fsync=off','-w','start'],check=True,stdout=subprocess.DEVNULL);started=True
            migrations=sorted([*(ROOT/'migrations').glob('*_signal_community_chat_calls.sql'),*(ROOT/'migrations').glob('*_signal_invite_creator_authorization.sql'),*(ROOT/'migrations').glob('*_signal_member_encrypted_backups.sql'),*(ROOT/'migrations').glob('*_signal_kragujevac_operations.sql'),*(ROOT/'migrations').glob('*_signal_operations_delta.sql')])
            args=[binary['psql'],'-h',str(p),'-p','57884','-d','postgres','-X','-v','ON_ERROR_STOP=1','-f',str(ROOT/'tests/local_auth_fixture.sql')]
            for migration in migrations:args+=['-f',str(migration)]
            subprocess.run([*args,'-f',str(ROOT/'tests/community.sql'),'-f',str(ROOT/'tests/operations.sql')],check=True)
        finally:
            if started:subprocess.run([binary['pg_ctl'],'-D',str(data),'-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)
if __name__=='__main__':main()
