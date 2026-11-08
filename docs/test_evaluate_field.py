import unittest,copy
from evaluate_field import local_assessment,intercity_assessment
class FieldTests(unittest.TestCase):
 def local(self,n=30,success=29):return [dict(city='Zagreb',route_id='shelter',direction='forward',attempted='yes',message_id=str(i),sent_utc='2026-11-07T07:00:00Z',received_utc='2026-11-07T07:02:00Z' if i<success else '') for i in range(n)]
 def inter(self):
  return [dict(pair='Zagreb-Sarajevo',day_index='1',window_local='08:00',offered='yes',accepted='yes',message_id=str(i),window_start_utc='2026-11-07T07:00:00Z',window_end_utc='2026-11-07T07:30:00Z',accepted_utc='2026-11-07T07:01:00Z',destination_base_received_utc='2026-11-07T07:20:00Z',timezone='Europe/Zagreb',test_date_local='2026-11-07')for i in range(10)]
 def test_local_pass(self):self.assertEqual(local_assessment(self.local())[0]['assessment'],'criteria_met')
 def test_local_fail(self):self.assertEqual(local_assessment(self.local(success=28))[0]['assessment'],'criteria_not_met')
 def test_local_small(self):self.assertEqual(local_assessment(self.local(n=29))[0]['assessment'],'partial')
 def test_local_duplicate(self):
  r=self.local();r[1]['message_id']='0';self.assertEqual(local_assessment(r)[0]['assessment'],'invalid_records')
 def test_local_clock(self):
  r=self.local();r[0]['received_utc']='2026-11-07T06:59:00Z';self.assertEqual(local_assessment(r)[0]['assessment'],'invalid_records')
 def test_unverified(self):
  r=self.local();[x.update(attempted='no') for x in r];self.assertEqual(local_assessment(r)[0]['assessment'],'unverified')
 def test_inter_pass(self):
  r=self.inter();r[-1]['destination_base_received_utc']='';self.assertEqual(intercity_assessment(r)[0]['assessment'],'criteria_met')
 def test_inter_fail(self):
  r=self.inter();r[-1]['destination_base_received_utc']='';r[-2]['destination_base_received_utc']='';self.assertEqual(intercity_assessment(r)[0]['assessment'],'criteria_not_met')
 def test_unscheduled(self):
  r=self.inter();[x.update(window_local='03:00')for x in r];self.assertEqual(intercity_assessment(r)[0]['assessment'],'invalid_records')
 def test_mixed_dates(self):
  r=self.inter();r[0]['test_date_local']='2026-11-08';self.assertEqual(intercity_assessment(r)[0]['assessment'],'invalid_records')
 def test_nonconsecutive_days(self):
  r=self.inter();other=copy.deepcopy(r)
  for x in other:
   x['day_index']='2';x['message_id']='b'+x['message_id']
   for k in ('test_date_local','window_start_utc','window_end_utc','accepted_utc','destination_base_received_utc'):x[k]=x[k].replace('2026-11-07','2026-11-09')
  self.assertTrue(all(x['assessment']=='invalid_records' for x in intercity_assessment(r+other)))
 def test_invalid_day(self):
  r=self.inter();[x.update(day_index='4')for x in r];self.assertEqual(intercity_assessment(r)[0]['assessment'],'invalid_records')
 def test_inter_empty(self):
  r=self.inter();[x.update(offered='no',accepted='no')for x in r];self.assertEqual(intercity_assessment(r)[0]['assessment'],'unverified')
