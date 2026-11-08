import unittest
from power_calculator import required_wh
class PowerTests(unittest.TestCase):
 def test_losses_and_reserve(self): self.assertAlmostEqual(required_wh(100,3,.8,.9),541.6666666667)
 def test_invalid_inputs(self):
  for v in (0,-1,float('nan'),float('inf')):
   with self.assertRaises(ValueError): required_wh(v)
  with self.assertRaises(ValueError): required_wh(10,efficiency=0)
