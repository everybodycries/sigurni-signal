import tempfile
import unittest
from types import SimpleNamespace as N
from pathlib import Path
from station.radio import profile_check, RadioWorker
from station.core import Store

def interface(psk=bytes(range(32)),region=3,override=False,mqtt=False,uplink=False):
    c=N(index=0,role=1,settings=N(psk=psk,uplink_enabled=uplink,downlink_enabled=False))
    return N(localNode=N(localConfig=N(lora=N(region=region,override_duty_cycle=override)),channels=[c],moduleConfig=N(mqtt=N(enabled=mqtt))))
class RadioTests(unittest.TestCase):
    def test_default_keys_plaintext_and_cloud_are_blocked(self):
        for i in (interface(psk=b''),interface(psk=b'\x01'),interface(psk=bytes.fromhex('d4f1bb3a20290759f0bcffabcf4e6901')),interface(psk=bytes(32)),interface(override=True),interface(region=1),interface(mqtt=True),interface(uplink=True)):
            self.assertFalse(profile_check(i)[0])
        self.assertTrue(profile_check(interface())[0])
    def test_invalid_radio_packet_and_external_interface_dont_confirm(self):
        with tempfile.TemporaryDirectory() as t:
            db=Store(Path(t)/'db');r=RadioWorker(db);r.interface=object()
            r._on_packet({'id':1,'decoded':{'portnum':'TEXT_MESSAGE_APP','text':'[AAAAAAAA] TREBAM POMOĆ'}},object())
            self.assertEqual(db.messages(),[])
            r._on_packet({'id':1,'from':1,'decoded':{'portnum':'TEXT_MESSAGE_APP','text':'[AAAAAAAA] TREBAM POMOĆ'}},r.interface)
            self.assertEqual(db.messages()[0]['incident'],'open');db.close()
if __name__=='__main__':unittest.main()
