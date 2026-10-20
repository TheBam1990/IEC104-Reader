import struct
import unittest

from iec104.protocol import APDUParser, build_asdu, build_command, build_general_interrogation, build_parameter_asdu, build_s_frame, build_standard_asdu, build_u_frame, decode_asdu, format_ioa, parse_hex_bytes


class ProtocolTests(unittest.TestCase):
    def test_fragmented_startdt(self):
        parser = APDUParser()
        self.assertEqual(parser.feed(b"\x68\x04\x0b"), [])
        frame = parser.feed(b"\x00\x00\x00")[0]
        self.assertEqual((frame.kind, frame.utype), ("U", 0x08))

    def test_s_frame_sequence(self):
        frame = APDUParser().feed(build_s_frame(123))[0]
        self.assertEqual((frame.kind, frame.receive_sequence), ("S", 123))

    def test_general_interrogation(self):
        frame = APDUParser().feed(build_general_interrogation(2019, 2, 3))[0]
        self.assertEqual((frame.kind, frame.send_sequence, frame.receive_sequence), ("I", 2, 3))
        self.assertEqual(frame.asdu[:6], bytes((100, 1, 6, 0, 0xE3, 0x07)))

    def test_scaled_values_with_sequence_addresses(self):
        header = bytes((11, 0x82, 20, 0)) + struct.pack("<H", 2019)
        objects = (100).to_bytes(3, "little") + struct.pack("<hB", 45, 0) + struct.pack("<hB", -12, 0)
        values = decode_asdu(header + objects)
        self.assertEqual([(v.ioa, v.value, v.quality) for v in values], [(100, 45, "good"), (101, -12, "good")])

    def test_float_and_invalid_quality(self):
        data = bytes((13, 1, 3, 0, 1, 0)) + (7).to_bytes(3, "little") + struct.pack("<fB", 12.5, 0x80)
        value = decode_asdu(data)[0]
        self.assertAlmostEqual(value.value, 12.5)
        self.assertEqual(value.quality, "IV")
        self.assertEqual(value.quality_raw, 0x80)

    def test_all_quality_flags(self):
        data = bytes((11, 1, 3, 0, 1, 0)) + (123).to_bytes(3, "little") + struct.pack("<hB", 7, 0xF1)
        value = decode_asdu(data)[0]
        self.assertEqual(value.quality, "OV,BL,SB,NT,IV")
        self.assertEqual(value.quality_raw, 0xF1)

    def test_structured_and_unstructured_ioa(self):
        self.assertEqual(format_ioa(4235604), "4235604")
        self.assertEqual(format_ioa(4235604, structured=True), "84-161-64")
        with self.assertRaises(ValueError):
            format_ioa(0x1000000, structured=True)

    def test_single_point(self):
        data = bytes((1, 1, 20, 0, 1, 0)) + (9).to_bytes(3, "little") + b"\x01"
        self.assertIs(decode_asdu(data)[0].value, True)

    def test_double_command_select(self):
        frame = APDUParser().feed(build_command(2019, 4251733, 46, 2, True, 4, 7))[0]
        self.assertEqual((frame.send_sequence, frame.receive_sequence), (4, 7))
        self.assertEqual(frame.asdu[:6], bytes((46, 1, 6, 0, 0xE3, 0x07)))
        self.assertEqual(int.from_bytes(frame.asdu[6:9], "little"), 4251733)
        self.assertEqual(frame.asdu[9], 0x82)

    def test_scaled_execute_command(self):
        frame = APDUParser().feed(build_command(1, 99, 49, -123, False, 0, 0))[0]
        self.assertEqual(struct.unpack("<h", frame.asdu[9:11])[0], -123)
        self.assertEqual(frame.asdu[11], 0)

    def test_invalid_single_command_is_rejected(self):
        with self.assertRaises(ValueError):
            build_command(1, 1, 45, 2, False, 0, 0)

    def test_step_and_bitstring_commands(self):
        step = APDUParser().feed(build_command(1, 7, 47, 2, True, 3, 4))[0]
        bits = APDUParser().feed(build_command(1, 8, 51, 0xAABBCCDD, False, 5, 6))[0]
        self.assertEqual(step.asdu[9], 0x82)
        self.assertEqual(int.from_bytes(bits.asdu[9:13], "little"), 0xAABBCCDD)
        self.assertEqual(len(bits.asdu[9:]), 4)
        with self.assertRaises(ValueError):
            build_command(1, 8, 51, 1, True, 0, 0)

    def test_standard_requests(self):
        counter = build_standard_asdu(101, 2019, qualifier=5, originator_address=2)
        read = build_standard_asdu(102, 2019, ioa=123, originator_address=2)
        clock = build_standard_asdu(103, 2019)
        self.assertEqual(counter[:6], bytes((101, 1, 6, 2, 0xE3, 0x07)))
        self.assertEqual(counter[-1], 5)
        self.assertEqual(int.from_bytes(read[6:9], "little"), 123)
        self.assertEqual(len(clock), 16)

    def test_parameter_and_raw_asdu(self):
        parameter = build_parameter_asdu(1, 99, 111, -123, 2, 3)
        self.assertEqual(parameter[:6], bytes((111, 1, 6, 3, 1, 0)))
        self.assertEqual(struct.unpack("<h", parameter[9:11])[0], -123)
        raw = build_asdu(122, 1, 5, parse_hex_bytes("AA:55"), cause=6)
        self.assertEqual(raw[-2:], b"\xAA\x55")


if __name__ == "__main__":
    unittest.main()
