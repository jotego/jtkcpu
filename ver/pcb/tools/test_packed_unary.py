"""Check both record slots using a payload captured from the physical CPU."""
import binascii
import unittest
from packed_unary import decode,expected_d

GOLDEN=bytes.fromhex('a55a01a10000f0100000a5860000a504e700a5860100a504e79bbc')


def capture():
    cases=[];frames=[]
    for i in range(96):
        packet=bytearray(GOLDEN)
        packet[5:7]=(0xf0+i).to_bytes(2,'big')
        packet[-2:]=binascii.crc_hqx(packet[:-2],0xffff).to_bytes(2,'big')
        frames.append(dict(hex=packet.hex()))
        cases.extend(dict(opcode=0x86,mnemonic='NEGA',reg='A',width=8,value=0,input_D=0xa5,cc=cc) for cc in (0,1))
    return dict(validated=True,complete=True,manifest=dict(run_id=0xa100,cases=cases),frames=frames)


class PackedTests(unittest.TestCase):
    def test_rotate_carry_in_and_unused_byte(self):
        cases=[('RORA','A',0,1,0x80a5),('RORB','B',0x80,0,0x5a40),
               ('ROLA','A',0,1,0x01a5),('ROLB','B',0x80,0,0x5a00),
               ('ASRA','A',0x80,0,0xc0a5),('LSRB','B',0x80,1,0x5a40)]
        for name,reg,value,cc,result in cases:
            case=dict(mnemonic=name,reg=reg,value=value,width=8,cc=cc)
            self.assertEqual(expected_d(case),result)

    def test_both_physical_slots(self):
        rows=decode(capture())
        self.assertEqual(len(rows),192)
        self.assertEqual([r['cc'] for r in rows[:2]],[0,1])
        self.assertTrue(all(r['output_D']==0xa5 and r['output_CC']==4 for r in rows))

    def test_semantic_errors_are_rejected_even_with_valid_crc(self):
        for slot in range(2):
            for field in (0,1,2,3,4,5,7):
                data=capture()
                packet=bytearray.fromhex(data['frames'][0]['hex'])
                packet[9+slot*8+field]^=0x80
                packet[-2:]=binascii.crc_hqx(packet[:-2],0xffff).to_bytes(2,'big')
                data['frames'][0]['hex']=packet.hex()
                with self.assertRaises(AssertionError):decode(data)

    def test_flag_observations_are_retained_without_assuming_a_model(self):
        data=capture();packet=bytearray.fromhex(data['frames'][0]['hex'])
        packet[15]=0xfb
        packet[-2:]=binascii.crc_hqx(packet[:-2],0xffff).to_bytes(2,'big')
        data['frames'][0]['hex']=packet.hex()
        self.assertEqual(decode(data)[0]['output_CC'],0xfb)


if __name__=='__main__':unittest.main()
