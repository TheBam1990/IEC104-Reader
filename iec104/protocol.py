"""Small, read-oriented IEC 60870-5-104 codec."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import struct


TYPE_NAMES = {
    1: "M_SP_NA_1 Einzelmeldung", 2: "M_SP_TA_1 Einzelmeldung CP24",
    3: "M_DP_NA_1 Doppelmeldung", 4: "M_DP_TA_1 Doppelmeldung CP24",
    5: "M_ST_NA_1 Stufenstellung", 6: "M_ST_TA_1 Stufenstellung CP24",
    7: "M_BO_NA_1 Bitmuster", 8: "M_BO_TA_1 Bitmuster CP24",
    9: "M_ME_NA_1 Messwert normiert", 10: "M_ME_TA_1 Messwert normiert CP24",
    11: "M_ME_NB_1 Messwert skaliert", 12: "M_ME_TB_1 Messwert skaliert CP24",
    13: "M_ME_NC_1 Messwert Gleitkomma", 14: "M_ME_TC_1 Messwert Gleitkomma CP24",
    15: "M_IT_NA_1 Zählwert", 16: "M_IT_TA_1 Zählwert CP24",
    20: "M_PS_NA_1 Statusänderung",
    21: "M_ME_ND_1 Messwert normiert ohne Qualität",
    30: "M_SP_TB_1 Einzelmeldung CP56", 31: "M_DP_TB_1 Doppelmeldung CP56",
    32: "M_ST_TB_1 Stufenstellung CP56", 33: "M_BO_TB_1 Bitmuster CP56",
    34: "M_ME_TD_1 Messwert normiert CP56", 35: "M_ME_TE_1 Messwert skaliert CP56",
    36: "M_ME_TF_1 Messwert Gleitkomma CP56", 37: "M_IT_TB_1 Zählwert CP56",
    45: "C_SC_NA_1 Einzelbefehl", 46: "C_DC_NA_1 Doppelbefehl",
    48: "C_SE_NA_1 Sollwert normiert", 49: "C_SE_NB_1 Sollwert skaliert",
    50: "C_SE_NC_1 Sollwert Gleitkomma",
    58: "C_SC_TA_1 Einzelbefehl CP56", 59: "C_DC_TA_1 Doppelbefehl CP56",
    61: "C_SE_TA_1 Sollwert normiert CP56", 62: "C_SE_TB_1 Sollwert skaliert CP56",
    63: "C_SE_TC_1 Sollwert Gleitkomma CP56",
    100: "C_IC_NA_1 Generalabfrage", 103: "C_CS_NA_1 Zeitsynchronisation",
}

COT_NAMES = {
    1: "zyklisch", 2: "Hintergrundabfrage", 3: "spontan", 4: "initialisiert",
    5: "Abfrage", 6: "Aktivierung", 7: "Aktivierungsbestätigung",
    10: "Aktivierungsende", 20: "Generalabfrage",
}

OBJECT_LAYOUT = {
    1: (1, "sp"), 2: (4, "sp_cp24"), 3: (1, "dp"), 4: (4, "dp_cp24"),
    5: (2, "step"), 6: (5, "step_cp24"), 7: (5, "bits"), 8: (8, "bits_cp24"),
    9: (3, "norm"), 10: (6, "norm_cp24"), 11: (3, "scaled"), 12: (6, "scaled_cp24"),
    13: (5, "float"), 14: (8, "float_cp24"), 15: (5, "counter"), 16: (8, "counter_cp24"),
    20: (5, "status"), 21: (2, "norm_noq"),
    30: (8, "sp_cp56"), 31: (8, "dp_cp56"), 32: (9, "step_cp56"),
    33: (12, "bits_cp56"), 34: (10, "norm_cp56"), 35: (10, "scaled_cp56"),
    36: (12, "float_cp56"), 37: (12, "counter_cp56"),
}


@dataclass(frozen=True)
class APCI:
    kind: str
    raw: bytes
    send_sequence: int | None = None
    receive_sequence: int | None = None
    utype: int | None = None
    asdu: bytes = b""


@dataclass(frozen=True)
class Value:
    key: str
    common_address: int
    ioa: int
    type_id: int
    type_name: str
    cause: int
    cause_name: str
    value: object
    quality: str
    unit: str = ""
    source_timestamp: str = ""


class APDUParser:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[APCI]:
        self.buffer.extend(data)
        frames = []
        while True:
            try:
                start = self.buffer.index(0x68)
            except ValueError:
                self.buffer.clear()
                break
            if start:
                del self.buffer[:start]
            if len(self.buffer) < 2:
                break
            total = self.buffer[1] + 2
            if total < 6:
                del self.buffer[0]
                continue
            if len(self.buffer) < total:
                break
            raw = bytes(self.buffer[:total])
            del self.buffer[:total]
            frames.append(decode_apci(raw))
        return frames


def decode_apci(raw: bytes) -> APCI:
    if len(raw) < 6 or raw[0] != 0x68 or raw[1] != len(raw) - 2:
        raise ValueError("Ungültiger IEC104-APDU-Rahmen")
    c0, c1, c2, c3 = raw[2:6]
    if c0 & 1 == 0:
        return APCI("I", raw, (c0 | c1 << 8) >> 1, (c2 | c3 << 8) >> 1, asdu=raw[6:])
    if c0 & 3 == 1:
        return APCI("S", raw, receive_sequence=(c2 | c3 << 8) >> 1)
    return APCI("U", raw, utype=c0 & 0xFC)


def build_i_frame(asdu: bytes, send_sequence: int, receive_sequence: int) -> bytes:
    tx = (send_sequence & 0x7FFF) << 1
    rx = (receive_sequence & 0x7FFF) << 1
    body = struct.pack("<HH", tx, rx) + asdu
    return bytes((0x68, len(body))) + body


def build_s_frame(receive_sequence: int) -> bytes:
    rx = (receive_sequence & 0x7FFF) << 1
    return bytes((0x68, 4, 1, 0, rx & 0xFF, rx >> 8))


def build_u_frame(utype: int) -> bytes:
    return bytes((0x68, 4, utype, 0, 0, 0))


def build_general_interrogation(common_address: int, send_sequence: int, receive_sequence: int) -> bytes:
    if not 0 <= common_address <= 0xFFFF:
        raise ValueError("Common Address muss zwischen 0 und 65535 liegen")
    asdu = bytes((100, 1, 6, 0)) + struct.pack("<H", common_address) + b"\x00\x00\x00\x14"
    return build_i_frame(asdu, send_sequence, receive_sequence)


def cp56_now() -> bytes:
    now = datetime.now()
    milliseconds = now.second * 1000 + now.microsecond // 1000
    return struct.pack("<HBBBBB", milliseconds, now.minute, now.hour, now.day, now.month, now.year % 100)


def build_command(
    common_address: int,
    ioa: int,
    type_id: int,
    value: float | int | bool,
    select: bool,
    send_sequence: int,
    receive_sequence: int,
    originator_address: int = 0,
) -> bytes:
    """Build a standard activation command I-frame."""
    if not 0 <= common_address <= 0xFFFF:
        raise ValueError("Common Address muss zwischen 0 und 65535 liegen")
    if not 0 <= ioa <= 0xFFFFFF:
        raise ValueError("IOA muss zwischen 0 und 16777215 liegen")
    if not 0 <= originator_address <= 255:
        raise ValueError("Originator Address muss zwischen 0 und 255 liegen")
    qualifier = 0x80 if select else 0
    if type_id in (45, 58):
        numeric = int(value)
        if numeric not in (0, 1): raise ValueError("Einzelbefehl erlaubt nur 0 oder 1")
        payload = bytes((numeric | qualifier,))
    elif type_id in (46, 59):
        numeric = int(value)
        if numeric not in (1, 2): raise ValueError("Doppelbefehl erlaubt nur 1 (AUS) oder 2 (EIN)")
        payload = bytes((numeric | qualifier,))
    elif type_id in (48, 61):
        numeric = float(value)
        if not -1.0 <= numeric <= 1.0: raise ValueError("Normierter Sollwert muss zwischen -1 und +1 liegen")
        raw = max(-32768, min(32767, round(numeric * 32767)))
        payload = struct.pack("<hB", raw, qualifier)
    elif type_id in (49, 62):
        numeric = int(value)
        if not -32768 <= numeric <= 32767: raise ValueError("Skalierter Sollwert muss zwischen -32768 und 32767 liegen")
        payload = struct.pack("<hB", numeric, qualifier)
    elif type_id in (50, 63):
        payload = struct.pack("<fB", float(value), qualifier)
    else:
        raise ValueError(f"Nicht unterstützter Befehlstyp {type_id}")
    if type_id in (58, 59, 61, 62, 63):
        payload += cp56_now()
    asdu = bytes((type_id, 1, 6, originator_address)) + struct.pack("<H", common_address) + ioa.to_bytes(3, "little") + payload
    return build_i_frame(asdu, send_sequence, receive_sequence)


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def quality_text(qds: int) -> str:
    flags = []
    if qds & 0x01: flags.append("OV")
    if qds & 0x10: flags.append("BL")
    if qds & 0x20: flags.append("SB")
    if qds & 0x40: flags.append("NT")
    if qds & 0x80: flags.append("IV")
    return ",".join(flags) if flags else "good"


def cp56_text(data: bytes) -> str:
    if len(data) < 7:
        return ""
    milliseconds = int.from_bytes(data[0:2], "little")
    second, ms = divmod(milliseconds, 1000)
    minute, hour = data[2] & 0x3F, data[3] & 0x1F
    day, month, year = data[4] & 0x1F, data[5] & 0x0F, 2000 + (data[6] & 0x7F)
    try:
        return datetime(year, month, day, hour, minute, second, ms * 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except ValueError:
        return "ungültiger Zeitstempel"


def decode_value(kind: str, payload: bytes) -> tuple[object, str, str]:
    timestamp = ""
    if kind.endswith("_cp56"):
        timestamp = cp56_text(payload[-7:])
        payload = payload[:-7]
    elif kind.endswith("_cp24"):
        payload = payload[:-3]
    if kind.startswith("sp"):
        return bool(payload[0] & 1), quality_text(payload[0] & 0xF0), timestamp
    if kind.startswith("dp"):
        return payload[0] & 3, quality_text(payload[0] & 0xF0), timestamp
    if kind.startswith("step"):
        raw = payload[0] & 0x7F
        value = raw - 128 if raw & 0x40 else raw
        return value, quality_text(payload[1]), timestamp
    if kind.startswith("bits") or kind == "status":
        return f"0x{int.from_bytes(payload[:4], 'little'):08X}", quality_text(payload[4]), timestamp
    if kind.startswith("norm"):
        raw = int.from_bytes(payload[:2], "little", signed=True)
        quality = "good" if kind == "norm_noq" else quality_text(payload[2])
        return raw / 32768.0, quality, timestamp
    if kind.startswith("scaled"):
        return int.from_bytes(payload[:2], "little", signed=True), quality_text(payload[2]), timestamp
    if kind.startswith("float"):
        return struct.unpack("<f", payload[:4])[0], quality_text(payload[4]), timestamp
    if kind.startswith("counter"):
        return int.from_bytes(payload[:4], "little", signed=True), quality_text(payload[4]), timestamp
    return hex_bytes(payload), "unbekannt", timestamp


def decode_asdu(data: bytes) -> list[Value]:
    if len(data) < 6:
        raise ValueError("ASDU zu kurz")
    type_id, vsq = data[0], data[1]
    count, sequential = vsq & 0x7F, bool(vsq & 0x80)
    cause = data[2] & 0x3F
    common_address = int.from_bytes(data[4:6], "little")
    layout = OBJECT_LAYOUT.get(type_id)
    if not layout or count == 0:
        return []
    size, kind = layout
    offset, first_ioa = 6, None
    values = []
    for index in range(count):
        if not sequential or index == 0:
            if offset + 3 > len(data): raise ValueError("IOA fehlt")
            ioa = int.from_bytes(data[offset:offset + 3], "little")
            offset += 3
            if first_ioa is None: first_ioa = ioa
        else:
            ioa = first_ioa + index
        if offset + size > len(data): raise ValueError("Informationsobjekt unvollständig")
        value, quality, source_timestamp = decode_value(kind, data[offset:offset + size])
        offset += size
        values.append(Value(
            key=f"CA{common_address}:IOA{ioa}:T{type_id}", common_address=common_address,
            ioa=ioa, type_id=type_id, type_name=TYPE_NAMES.get(type_id, f"Typ {type_id}"),
            cause=cause, cause_name=COT_NAMES.get(cause, f"COT {cause}"), value=value,
            quality=quality, source_timestamp=source_timestamp,
        ))
    return values
