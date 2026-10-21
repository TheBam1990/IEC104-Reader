from dataclasses import replace
import struct
import unittest
from types import SimpleNamespace

from app import ReaderApp
from iec104.protocol import build_asdu, decode_asdu


class MemoryTable:
    def __init__(self):
        self.rows = {}

    def insert(self, parent, position, values):
        item = str(len(self.rows))
        self.rows[item] = values
        return item

    def item(self, item, option=None, *, values=None):
        if values is not None:
            self.rows[item] = values
        return self.rows[item]

    def move(self, *args):
        pass


class ValueUpdateTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(rows={}, latest_values={}, table=MemoryTable(),
                                   ioa_display_mode=lambda: 'decimal', apply_table_filter=lambda: None)

    def receive(self, cause=20, type_id=11, ca=2019, ioa=4235604, value=50):
        payload = struct.pack('<hB', value, 0)
        if type_id == 35:
            payload += bytes(7)
        decoded = decode_asdu(build_asdu(type_id, ca, ioa, payload, cause=cause))[0]
        ReaderApp.update_value(self.app, decoded, f'time-{cause}')
        return decoded

    def test_new_cause_and_type_replace_same_address(self):
        first = self.receive()
        second = self.receive(cause=3, value=70)
        third = self.receive(cause=3, type_id=35, value=80)
        self.assertEqual(first.key, second.key)
        self.assertEqual(first.key, third.key)
        self.assertEqual(len(self.app.table.rows), 1)
        self.assertEqual(len(self.app.rows), 1)
        self.assertEqual(len(self.app.latest_values), 1)
        row = next(iter(self.app.table.rows.values()))
        self.assertTrue(row[2].startswith('35:'))
        self.assertTrue(row[3].startswith('3:'))
        self.assertEqual(row[4], '80')
        self.assertEqual(row[-2:], ('time-3', 3))
        ReaderApp.update_value(self.app, third, 'time-3', increment=False)
        self.assertEqual(next(iter(self.app.table.rows.values()))[-1], 3)

    def test_log_all_received_values_including_repeated_gi(self):
        logged = []
        self.app.table_log = True
        self.app.log_table_change = logged.append
        first = self.receive()
        self.receive()
        self.assertEqual(len(logged), 2)
        self.receive(value=70)
        self.receive(cause=3, value=70)
        changed = replace(first, quality_raw=128, quality="IV")
        ReaderApp.update_value(self.app, changed, "quality-time")
        self.assertEqual(len(logged), 5)
        ReaderApp.update_value(self.app, changed, "redraw", increment=False)
        self.assertEqual(len(logged), 5)
        self.app.table_log = None
        self.receive(value=90)
        self.app.table_log = True
        self.receive(value=90)
        self.assertEqual(len(logged), 6)

    def test_other_ca_or_ioa_create_separate_rows(self):
        self.receive()
        self.receive(ca=2020)
        self.receive(ioa=4235605)
        self.assertEqual(len(self.app.table.rows), 3)
        self.assertEqual(len(self.app.latest_values), 3)


if __name__ == '__main__':
    unittest.main()
