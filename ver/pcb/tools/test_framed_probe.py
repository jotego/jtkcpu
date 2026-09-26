"""Validate rejection using a CRC frame captured from the physical CPU."""
import binascii
import unittest
from framed_probe import check_frame

GOLDEN = bytes.fromhex('a55a017b0100f01000f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff816e')


class FrameTests(unittest.TestCase):
    def test_physical_frame_and_standard_crc_vector(self):
        self.assertEqual(binascii.crc_hqx(b'123456789',0xffff),0x29b1)
        check_frame(GOLDEN,0xf0)

    def test_every_single_bit_corruption_is_rejected(self):
        for bit in range(len(GOLDEN)*8):
            data=bytearray(GOLDEN)
            data[bit//8]^=1<<(bit%8)
            with self.assertRaises(AssertionError):check_frame(data,0xf0)

    def test_wrong_sequence_and_truncated_or_extended_frame(self):
        with self.assertRaises(AssertionError):check_frame(GOLDEN,0xf1)
        for size in range(len(GOLDEN)):
            with self.assertRaises(AssertionError):check_frame(GOLDEN[:size],0xf0)
        with self.assertRaises(AssertionError):check_frame(GOLDEN+b'\0',0xf0)

    def test_generic_payload_still_checks_crc(self):
        data=bytearray(GOLDEN)
        data[9]^=0x55
        with self.assertRaises(AssertionError):check_frame(data,0xf0,False)
        data[-2:]=binascii.crc_hqx(data[:-2],0xffff).to_bytes(2,'big')
        check_frame(data,0xf0,False)
        with self.assertRaises(AssertionError):check_frame(data,0xf0)

    def test_valid_crc_cannot_hide_wrong_image_id(self):
        data=bytearray(GOLDEN)
        data[3:5]=bytes.fromhex('d100')
        data[-2:]=binascii.crc_hqx(data[:-2],0xffff).to_bytes(2,'big')
        with self.assertRaises(AssertionError):check_frame(data,0xf0)
        check_frame(data,0xf0,run_id=0xd100)


if __name__=='__main__':unittest.main()
