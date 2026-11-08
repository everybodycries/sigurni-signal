"""Evaluate supplied measurements only; not proof of authentic or lawful RF operation."""
import argparse,csv,json
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

def utc(value):
 d=datetime.fromisoformat(value.replace('Z','+00:00'))
 if d.utcoffset()!=timedelta(0):raise ValueError('UTC timestamp with Z or +00:00 required')
 return d

def rows(path):
 with Path(path).open(newline='') as f:return list(csv.DictReader(f))

def local_assessment(records):
 groups=defaultdict(list)
 for r in records:groups[(r['city'],r['route_id'],r['direction'])].append(r)
 results=[]
 for key,group in sorted(groups.items()):
  attempts=[r for r in group if r['attempted'].strip().lower()=='yes'];timely=0;errors=[];seen=set()
  for r in attempts:
   try:
    if not r['message_id'] or r['message_id'] in seen:raise ValueError('Missing or duplicate message_id')
    seen.add(r['message_id']);sent=utc(r['sent_utc'])
    if not r['received_utc']:continue
    latency=(utc(r['received_utc'])-sent).total_seconds()
    if latency<0:raise ValueError('Receipt before send')
    timely+=latency<=120
   except (ValueError,KeyError,TypeError) as e:errors.append(str(e))
  n=len(attempts);fraction=timely/n if n else None
  status='unverified' if not n else 'invalid_records' if errors else 'partial' if n<30 else 'criteria_met' if fraction>=.95 else 'criteria_not_met'
  results.append(dict(city=key[0],route_id=key[1],direction=key[2],attempts=n,timely_receipts=timely,fraction=fraction,assessment=status,errors=errors))
 return results

def intercity_assessment(records):
 groups=defaultdict(list);origins=defaultdict(set)
 for r in records:
  groups[(r['pair'],r['day_index'],r['window_local'])].append(r)
  if r['accepted'].strip().lower()=='yes':
   try:
    day=int(r['day_index']);date=datetime.strptime(r['test_date_local'],'%Y-%m-%d').date()
    if day in (1,2,3):origins[r['pair']].add(date-timedelta(days=day-1))
   except (ValueError,KeyError,TypeError):pass
 result=[]
 for key,group in sorted(groups.items()):
  offered=[r for r in group if r['offered'].strip().lower()=='yes'];accepted=[r for r in group if r['accepted'].strip().lower()=='yes']
  errors=[];seen=set();identity=None;timely=0
  if len(origins[key[0]])>1:errors.append('Inconsistent day-index/calendar mapping')
  for r in accepted:
   try:
    if r['window_local'] not in ('08:00','14:00','20:00') or r['day_index'] not in ('1','2','3'):raise ValueError('Invalid scheduled slot/day')
    if r['timezone'] not in ('Europe/Zagreb','Europe/Sarajevo','Europe/Belgrade'):raise ValueError('Invalid pilot timezone')
    if r['offered'].strip().lower()!='yes':raise ValueError('Accepted without offered')
    if not r['message_id'] or r['message_id'] in seen:raise ValueError('Missing or duplicate message_id')
    seen.add(r['message_id']);start,end,intake=map(utc,(r['window_start_utc'],r['window_end_utc'],r['accepted_utc']))
    ident=(r['test_date_local'],r['timezone'],start,end)
    if identity is None:identity=ident
    elif identity!=ident:raise ValueError('Different calendar windows in one group')
    local=start.astimezone(ZoneInfo(r['timezone']))
    if local.second or local.microsecond or local.strftime('%H:%M')!=r['window_local'] or str(local.date())!=r['test_date_local']:raise ValueError('UTC/local time mismatch')
    if end-start!=timedelta(minutes=30) or not start<=intake<=end:raise ValueError('Invalid30min window/intake')
    if not r['destination_base_received_utc']:continue
    receipt=utc(r['destination_base_received_utc'])
    if receipt<intake:raise ValueError('Receipt before intake')
    timely+=receipt<=end
   except (ValueError,KeyError,TypeError) as e:errors.append(str(e))
  n=len(accepted);fraction=timely/n if n else None
  status='unverified' if not offered and not accepted else 'invalid_records' if errors else 'partial' if n<10 else 'criteria_met' if fraction>=.9 else 'criteria_not_met'
  result.append(dict(pair=key[0],day_index=key[1],window_local=key[2],offered=len(offered),accepted=n,timely_base_receipts=timely,fraction=fraction,assessment=status,errors=errors))
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['local','intercity']);p.add_argument('csv_path');a=p.parse_args()
 print(json.dumps({'warning':__doc__,'groups':(local_assessment if a.kind=='local' else intercity_assessment)(rows(a.csv_path))},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
