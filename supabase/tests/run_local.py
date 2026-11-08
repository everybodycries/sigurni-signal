#!/usr/bin/env python3
"""Run real RLS tests in a new Unix-socket-only temporary PostgreSQL cluster.
No Supabase network calls, hosted credentials or existing databases are used.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    binaries={}
    configured=os.environ.get('SIGURNI_PG_BIN')
    for name in ('initdb','pg_ctl','psql'):
        p=str(Path(configured)/name) if configured else shutil.which(name)
        if not p or not Path(p).is_file():
            raise SystemExit('PostgreSQL binaries missing; install locally or set SIGURNI_PG_BIN. No hosted fallback.')
        binaries[name]=p
    with tempfile.TemporaryDirectory(prefix='ss-pg-',dir='/tmp') as tmp:
        work=Path(tmp);data=work/'data';log=work/'postgres.log'
        subprocess.run([binaries['initdb'],'-D',str(data),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
        options=f'-k {work} -p 57883 -c listen_addresses= -c fsync=off'
        started=False
        try:
            subprocess.run([binaries['pg_ctl'],'-D',str(data),'-l',str(log),'-o',options,'-w','start'],check=True,stdout=subprocess.DEVNULL)
            started=True
            migration=next((ROOT/'migrations').glob('*_sigurni_signal_encrypted_backups.sql'))
            subprocess.run([binaries['psql'],'-h',str(work),'-p','57883','-d','postgres','-X','-v','ON_ERROR_STOP=1',
                            '-f',str(ROOT/'tests/local_auth_fixture.sql'),'-f',str(migration),'-f',str(ROOT/'tests/rls.sql')],check=True)
        finally:
            if started:
                subprocess.run([binaries['pg_ctl'],'-D',str(data),'-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)

if __name__=='__main__':main()
