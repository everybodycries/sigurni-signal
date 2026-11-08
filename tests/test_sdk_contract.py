import importlib.util,inspect,unittest
from types import SimpleNamespace as N
@unittest.skipUnless(importlib.util.find_spec('meshtastic'),'Optional SDK not installed')
class SdkTests(unittest.TestCase):
 def test_actual_protobuf_profile(self):
  from meshtastic.protobuf import config_pb2,channel_pb2,module_config_pb2
  from station.radio import profile_check
  l=config_pb2.Config.LoRaConfig(region=config_pb2.Config.LoRaConfig.EU_868)
  c=channel_pb2.Channel(index=0,role=channel_pb2.Channel.PRIMARY,settings=channel_pb2.ChannelSettings(psk=bytes(range(32))))
  m=module_config_pb2.ModuleConfig();i=N(localNode=N(localConfig=N(lora=l),channels=[c],moduleConfig=m))
  self.assertTrue(profile_check(i)[0]);m.mqtt.enabled=True;self.assertFalse(profile_check(i)[0])
 def test_actual_sdk_signature(self):
  from meshtastic.serial_interface import SerialInterface
  self.assertIn('devPath',inspect.signature(SerialInterface).parameters)
  self.assertTrue({'text','destinationId','wantAck','channelIndex'}.issubset(inspect.signature(SerialInterface.sendText).parameters))
