"""Background TCP worker for an IEC104 master connection."""

from __future__ import annotations

import queue
import socket
import threading

from .protocol import APDUParser, build_command, build_general_interrogation, build_i_frame, build_s_frame, build_u_frame


STARTDT_ACT = 0x07
STARTDT_CON = 0x0B
STOPDT_ACT = 0x13
STOPDT_CON = 0x23
TESTFR_ACT = 0x43
TESTFR_CON = 0x83


class TCPWorker:
    def __init__(self, events: queue.Queue) -> None:
        self.events = events
        self.socket: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.send_sequence = 0
        self.receive_sequence = 0
        self.started = False
        self.lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self.socket is not None

    def connect(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.disconnect()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(0.5)
        self.socket = sock
        self.stop_event.clear()
        self.send_sequence = 0
        self.receive_sequence = 0
        self.started = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.events.put(("status", f"TCP verbunden mit {host}:{port}"))
        self.send(build_u_frame(STARTDT_ACT))

    def disconnect(self) -> None:
        self.stop_event.set()
        sock, self.socket = self.socket, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        self.started = False

    def send(self, data: bytes) -> None:
        sock = self.socket
        if not sock:
            raise ConnectionError("Keine TCP-Verbindung")
        with self.lock:
            sock.sendall(data)
        self.events.put(("tx", data))

    def send_gi(self, common_address: int) -> None:
        if not self.started:
            raise ConnectionError("IEC104-Datenübertragung ist noch nicht gestartet")
        self.send(build_general_interrogation(common_address, self.send_sequence, self.receive_sequence))
        self.send_sequence = (self.send_sequence + 1) & 0x7FFF

    def send_command(self, common_address: int, ioa: int, type_id: int, value, select: bool, originator_address: int = 0) -> None:
        if not self.started:
            raise ConnectionError("IEC104-Datenübertragung ist noch nicht gestartet")
        frame = build_command(common_address, ioa, type_id, value, select, self.send_sequence, self.receive_sequence, originator_address)
        self.send(frame)
        self.send_sequence = (self.send_sequence + 1) & 0x7FFF

    def send_asdu(self, asdu: bytes) -> None:
        if not self.started:
            raise ConnectionError("IEC104-Datenübertragung ist noch nicht gestartet")
        self.send(build_i_frame(asdu, self.send_sequence, self.receive_sequence))
        self.send_sequence = (self.send_sequence + 1) & 0x7FFF

    def _run(self) -> None:
        parser = APDUParser()
        try:
            while not self.stop_event.is_set():
                try:
                    data = self.socket.recv(65536) if self.socket else b""
                except socket.timeout:
                    continue
                if not data:
                    raise ConnectionError("Gegenstelle hat die Verbindung geschlossen")
                self.events.put(("rx", data))
                for frame in parser.feed(data):
                    if frame.kind == "I":
                        expected = self.receive_sequence
                        self.receive_sequence = ((frame.send_sequence or 0) + 1) & 0x7FFF
                        if frame.send_sequence != expected:
                            self.events.put(("warning", f"Unerwartete Sendefolge: {frame.send_sequence}, erwartet {expected}"))
                        self.events.put(("asdu", frame.asdu))
                        self.send(build_s_frame(self.receive_sequence))
                    elif frame.kind == "U":
                        raw_type = frame.raw[2]
                        if raw_type == STARTDT_CON:
                            self.started = True
                            self.events.put(("started", None))
                        elif raw_type == STARTDT_ACT:
                            self.send(build_u_frame(STARTDT_CON))
                            self.started = True
                            self.events.put(("started", None))
                        elif raw_type == TESTFR_ACT:
                            self.send(build_u_frame(TESTFR_CON))
                        elif raw_type == STOPDT_ACT:
                            self.send(build_u_frame(STOPDT_CON))
                            self.started = False
        except Exception as error:
            if not self.stop_event.is_set():
                self.events.put(("error", str(error)))
        finally:
            self.disconnect()
            self.events.put(("disconnected", None))
