import queue
import socket
import struct
import threading
import time
import unittest

from iec104.protocol import APDUParser, build_i_frame, build_u_frame, decode_asdu
from iec104.tcp_worker import STARTDT_CON, TCPWorker


class TCPWorkerTests(unittest.TestCase):
    def test_startdt_gi_value_and_acknowledgement(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        result = {}

        def remote():
            connection, _ = server.accept()
            parser = APDUParser()
            result["start"] = parser.feed(connection.recv(1024))[0].raw[2]
            connection.sendall(build_u_frame(STARTDT_CON))
            gi = parser.feed(connection.recv(1024))[0]
            result["gi_type"] = gi.asdu[0]
            asdu = bytes((11, 1, 20, 0)) + struct.pack("<H", 2019) + (123).to_bytes(3, "little") + struct.pack("<hB", 77, 0)
            connection.sendall(build_i_frame(asdu, 0, 1))
            result["ack"] = parser.feed(connection.recv(1024))[0].receive_sequence
            connection.close()
            server.close()

        thread = threading.Thread(target=remote, daemon=True)
        thread.start()
        events = queue.Queue()
        worker = TCPWorker(events)
        worker.connect("127.0.0.1", port)
        deadline = time.time() + 3
        received = None
        while time.time() < deadline:
            kind, payload = events.get(timeout=1)
            if kind == "started":
                worker.send_gi(2019)
            elif kind == "asdu":
                received = decode_asdu(payload)[0]
                break
        self.assertIsNotNone(received)
        self.assertEqual((received.ioa, received.value), (123, 77))
        thread.join(timeout=2)
        self.assertEqual(result, {"start": 7, "gi_type": 100, "ack": 1})
        worker.disconnect()


if __name__ == "__main__":
    unittest.main()
