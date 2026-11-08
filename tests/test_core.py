import json
import tempfile
import unittest
from pathlib import Path
from station.core import Store, encode_wire, parse_wire, next_window, required_wh

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'station.sqlite3'
        self.db = Store(self.path)
        self.now = 1800000000
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def create(self, **kw):
        return self.db.create_message('Trebam pomoć', '!1234abcd', kind='help', now=self.now, **kw)
    def test_shared_wire_fixtures(self):
        for f in json.loads((Path(__file__).parents[1]/'shared/protocol.json').read_text())['wire_fixtures']:
            self.assertEqual(encode_wire(f['id'], f['body']), f['wire'])
            self.assertEqual(len(f['wire'].encode()), f['bytes'])
    def test_unicode_boundary_counts_header(self):
        self.assertEqual(len(encode_wire('AAAAAAAA', 'ć'*94+'a').encode()), 200)
        with self.assertRaises(ValueError): encode_wire('AAAAAAAA', 'ć'*95)
    def test_blank_control_and_invalid_destination_rejected(self):
        for text in ('', '  ', 'x\x00y', 'x\ny'):
            with self.assertRaises(ValueError): self.db.create_message(text, 'all', now=self.now)
        with self.assertRaises(ValueError): self.db.create_message('hello', 'internet', now=self.now)
    def test_help_expiry_does_not_resolve_incident(self):
        m=self.create()
        self.assertEqual(m['expires_at']-m['created_at'],3600)
        self.db.reserve_next(now=self.now+3601)
        r=self.db.message(m['id'])
        self.assertEqual(r['status'], 'expired'); self.assertEqual(r['incident'], 'open')
    def test_three_attempts_and_backoff(self):
        m=self.create()
        for i,t in enumerate((self.now,self.now+121,self.now+722)):
            job=self.db.reserve_next(now=t); self.assertEqual(job['attempts'],i+1)
            self.db.mark_submitted(job['id'], 100+i, now=t)
        self.assertIsNone(self.db.reserve_next(now=self.now+1400))
        self.assertEqual(self.db.message(m['id'])['attempts'],3)
    def test_no_retry_before_backoff(self):
        self.create(); j=self.db.reserve_next(now=self.now); self.db.mark_submitted(j['id'],1,now=self.now)
        self.assertIsNone(self.db.reserve_next(now=self.now+60))
    def test_restart_does_not_resend_uncertain_job(self):
        m=self.create(); self.db.reserve_next(now=self.now)
        self.db.close(); self.db=Store(self.path)
        self.assertEqual(self.db.message(m['id'])['status'],'needs_review')
        self.assertIsNone(self.db.reserve_next(now=self.now+300))
    def test_radio_ack_is_not_human_confirmation(self):
        m=self.create(); self.db.reserve_next(now=self.now); self.db.mark_submitted(m['id'],10,now=self.now)
        self.db.radio_ack(10, 'NONE', now=self.now+1)
        r=self.db.message(m['id']); self.assertEqual(r['status'],'radio_acked'); self.assertEqual(r['incident'],'open')
    def test_unverified_receipt_does_not_confirm(self):
        m=self.create(); self.db.receive('POTVRDA '+m['id'],'!abcdef12',77,now=self.now+1)
        self.assertIsNone(self.db.message(m['id'])['human_confirmed_at'])
    def test_incoming_duplicate_uses_sender_and_packet_id(self):
        self.db.receive('[AAAAAAAA] hello','!abcdef12',77,now=self.now)
        self.db.receive('[AAAAAAAA] hello','!abcdef12',77,now=self.now+1)
        self.assertEqual(len(self.db.messages()),1)
        self.db.receive('[AAAAAAAA] other sender','!11111111',77,now=self.now+2)
        self.assertEqual(len(self.db.messages()),2)
    def test_same_wire_id_deduplicates_retries_and_flags_conflicts(self):
        a=self.db.receive('[AAAAAAAA] TREBAM POMOĆ', '!abcdef12',77,now=self.now)
        self.db.receive('[AAAAAAAA] TREBAM POMOĆ', '!abcdef12',78,now=self.now+1)
        self.assertEqual(len(self.db.messages()),1)
        self.assertEqual(a['incident'],'open')
        self.db.receive('[AAAAAAAA] changed', '!abcdef12',79,now=self.now+2)
        self.assertEqual(len(self.db.messages()),1)
        self.assertIn('Sukob',self.db.message(a['id'])['last_error'])
    def test_clock_rollback_pauses_automatic_sending(self):
        self.create(); self.assertIsNone(self.db.reserve_next(now=self.now-60))
    def test_confirmation_stops_retries_but_closure_is_explicit(self):
        m=self.create(); self.db.confirm_human(m['id'],'Ana','Provjereno osobno',now=self.now+5)
        self.assertIsNone(self.db.reserve_next(now=self.now+200))
        self.assertEqual(self.db.message(m['id'])['incident'],'open')
        self.db.close_incident(m['id'],'Ana','Zahtjev riješen',now=self.now+10)
        self.assertEqual(self.db.message(m['id'])['incident'],'closed')
    def test_old_open_help_and_full_audit_export(self):
        m=self.create()
        for i in range(501): self.db.receive('Routine message','!abcdef12',i,now=self.now+i+1)
        self.assertTrue(any(r['id']==m['id'] for r in self.db.messages()))
        self.assertEqual(len(self.db.messages(export=True)),502)
        self.assertEqual(len(self.db.audit(export=True)),502)
    def test_closing_help_stops_sending(self):
        m=self.create();self.db.close_incident(m['id'],'Ana','Riješeno',now=self.now+5)
        self.assertIsNone(self.db.reserve_next(now=self.now+10))
    def test_confirmed_messages_do_not_fill_queue(self):
        for i in range(100):
            m=self.create();self.db.confirm_human(m['id'],'Ana','Provjereno',now=self.now+1)
        self.assertEqual(self.create()['status'],'saved')
    def test_public_radiogram_requires_exact_consent(self):
        with self.assertRaises(ValueError): self.db.create_radiogram('Public text','Sarajevo','other text',True,'Ana',now=self.now)
        with self.assertRaises(ValueError): self.db.create_radiogram('Public text','Sarajevo','Public text',False,'Ana',now=self.now)
    def test_hf_approval_blocked_without_evidence(self):
        r=self.db.create_radiogram('Public text','Sarajevo','Public text',True,'Ana',now=self.now)
        with self.assertRaises(ValueError): self.db.advance_radiogram(r['id'],'approved','Operator','review',now=self.now)
    def test_evidence_is_required_for_each_gate_and_must_be_current(self):
        self.assertFalse(self.db.readiness(now=self.now)['hf_ready'])
        for gate in self.db.readiness(now=self.now)['gates']:
            self.db.record_evidence(gate['key'],'local-report.pdf','Reviewer',self.now-60,self.now+86400,now=self.now)
        self.assertTrue(self.db.readiness(now=self.now)['hf_ready'])
        self.assertFalse(self.db.readiness(now=self.now+86401)['hf_ready'])
    def test_radiogram_transitions_order_and_audit(self):
        for gate in self.db.readiness(now=self.now)['gates']:
            self.db.record_evidence(gate['key'],'report.pdf','Reviewer',self.now-60,self.now+86400,now=self.now)
        r=self.db.create_radiogram('Public text','Beograd','Public text',True,'Ana',now=self.now)
        with self.assertRaises(ValueError): self.db.advance_radiogram(r['id'],'transmitted','Op','note',now=self.now)
        for state in ('approved','transmitted','destination_base','human_confirmed'):
            self.db.advance_radiogram(r['id'],state,'Op','Verified repeatback',now=self.now)
        self.assertEqual(self.db.radiograms()[0]['state'],'human_confirmed')
        self.assertGreaterEqual(len(self.db.audit()),5)
    def test_schedule_local_and_dst(self):
        r=next_window(1794034800,'Zagreb')
        self.assertIn(r['local'][11:16],('08:00','14:00','20:00'))
        self.assertGreaterEqual(r['start_epoch'],1794034800)
        self.assertEqual(r['duration_minutes'],30)
    def test_power_losses_and_reserve(self):
        self.assertAlmostEqual(required_wh(100,3,.8,.9),541.6666667)
        with self.assertRaises(ValueError): required_wh(100,3,0,1)
    def test_plain_parse_never_creates_verified_official_status(self):
        self.assertEqual(parse_wire('POTVRDA AAAAAAAA')['type'],'receipt_claim')
        self.assertEqual(parse_wire('[AAAAAAAA] DOBRO SAM')['type'],'message')
        self.assertEqual(parse_wire('not a command')['type'],'plain')

if __name__=='__main__': unittest.main()
