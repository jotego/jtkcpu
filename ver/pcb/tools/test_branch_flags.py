"""Reject corrupted branch identity, data and outcome; retain surprising CC."""
import unittest
from branch_flags import decode_record
class BranchRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = [
            (bytes.fromhex('12346180123480e7'), {'opcode': 97, 'mnemonic': 'BHI', 'input_D': 4660, 'cc': 128, 'taken': True}),
            (bytes.fromhex('12346181123481e6'), {'opcode': 97, 'mnemonic': 'BHI', 'input_D': 4660, 'cc': 129, 'taken': False}),
        ]
    def test_physical_both_outcomes(self):
        self.assertEqual({r['taken'] for b,r in self.samples},{False,True})
        for b,r in self.samples:decode_record(b,r)
    def test_corrupt_echo_data_or_outcome(self):
        for b,r in self.samples:
            for pos in (0,1,2,3,4,5,7):
                mutated=bytearray(b);mutated[pos]^=1
                with self.assertRaises(AssertionError):decode_record(mutated,r)
    def test_unexpected_flags_are_observations(self):
        b,r=self.samples[0];mutated=bytearray(b);mutated[6]^=255
        self.assertEqual(decode_record(mutated,r)['output_CC'],mutated[6])
if __name__=='__main__':unittest.main()
