"""Space-saving IEC104 send centre."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .protocol import build_asdu, build_parameter_asdu, build_standard_asdu, hex_bytes, parse_hex_bytes


class SendDialog(tk.Toplevel):
    COMMANDS = (
        "45 - Einzelbefehl", "46 - Doppelbefehl", "47 - Stufenbefehl",
        "51 - Bitmuster", "58 - Einzelbefehl CP56", "59 - Doppelbefehl CP56",
        "60 - Stufenbefehl CP56", "64 - Bitmuster CP56",
    )
    SETPOINTS = (
        "48 - Normiert", "49 - Skaliert", "50 - Gleitkomma",
        "61 - Normiert CP56", "62 - Skaliert CP56", "63 - Gleitkomma CP56",
    )
    PARAMETERS = (
        "110 - Normiert", "111 - Skaliert", "112 - Gleitkomma",
        "113 - Aktivierung",
    )
    RAW_PRESETS = {
        "Freie ASDU": (1, 1, 6, 0, ""),
        "Datei bereit (F_FR_NA_1 / 120)": (120, 1, 6, 0, ""),
        "Dateiabschnitt bereit (F_SR_NA_1 / 121)": (121, 1, 6, 0, ""),
        "Dateiaufruf/-auswahl (F_SC_NA_1 / 122)": (122, 1, 6, 0, ""),
        "Letzter Abschnitt (F_LS_NA_1 / 123)": (123, 1, 6, 0, ""),
        "Dateibestätigung (F_AF_NA_1 / 124)": (124, 1, 6, 0, ""),
        "Dateisegment (F_SG_NA_1 / 125)": (125, 1, 6, 0, ""),
        "Verzeichnis (F_DR_TA_1 / 126)": (126, 1, 6, 0, ""),
    }

    def __init__(self, parent: tk.Misc, common_address: Callable[[], int],
                 originator: Callable[[], int], send_command: Callable,
                 send_asdu: Callable[[bytes, str, bool], bool]) -> None:
        super().__init__(parent)
        self.title("IEC104 senden")
        self.geometry("790x530")
        self.minsize(720, 470)
        self.transient(parent)
        self.common_address = common_address
        self.originator = originator
        self.send_command_callback = send_command
        self.send_asdu_callback = send_asdu
        self.preview = tk.StringVar(value="Die ASDU-Vorschau erscheint vor dem Senden.")
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Common Address und Originator werden aus dem Hauptfenster übernommen.").pack(fill=tk.X, padx=10, pady=(10, 4))
        book = ttk.Notebook(self)
        book.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self._standard_tab(book)
        self._command_tab(book)
        self._setpoint_tab(book)
        self._parameter_tab(book)
        self._raw_tab(book)
        frame = ttk.LabelFrame(self, text="ASDU-Vorschau", padding=6)
        frame.pack(fill=tk.X, padx=10, pady=4)
        ttk.Entry(frame, textvariable=self.preview, state="readonly", font=("Consolas", 9)).pack(fill=tk.X)
        ttk.Button(self, text="Schließen", command=self.destroy).pack(anchor=tk.E, padx=10, pady=(2, 10))

    @staticmethod
    def _number(variable: tk.StringVar, name: str, maximum: int = 0xFFFFFF) -> int:
        try:
            value = int(variable.get(), 0)
        except ValueError as error:
            raise ValueError(f"{name} muss eine Ganzzahl sein") from error
        if not 0 <= value <= maximum:
            raise ValueError(f"{name} muss zwischen 0 und {maximum} liegen")
        return value

    @staticmethod
    def _field(parent, label, variable, column, row=0, width=12):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Entry(parent, textvariable=variable, width=width).grid(row=row + 1, column=column, sticky=tk.EW, padx=4)

    def _standard_tab(self, book) -> None:
        tab = ttk.Frame(book, padding=12)
        book.add(tab, text="Standard")
        self.std_ioa = tk.StringVar(value="0")
        self.std_qualifier = tk.StringVar(value="20")
        actions = (
            ("Generalabfrage", 100, False), ("Zählerabfrage", 101, False),
            ("IOA lesen", 102, False), ("PC-Zeit synchronisieren", 103, True),
            ("Testbefehl", 104, False), ("Prozessreset", 105, True),
            ("Verzögerungsermittlung", 106, False),
        )
        ttk.Label(tab, text="IOA (für Lesen; sonst meist 0)").grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Entry(tab, textvariable=self.std_ioa, width=18).grid(row=1, column=0, sticky=tk.W, padx=4)
        ttk.Label(tab, text="Qualifier / QOI / QCC / QRP / Millisekunden").grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Entry(tab, textvariable=self.std_qualifier, width=18).grid(row=1, column=1, sticky=tk.W, padx=4)
        for index, (label, type_id, dangerous) in enumerate(actions):
            ttk.Button(tab, text=label, width=27, command=lambda t=type_id, l=label, d=dangerous: self._send_standard(t, l, d)).grid(row=3 + index // 2, column=index % 2, sticky=tk.W, padx=4, pady=4)
        ttk.Label(tab, text="Bei der Generalabfrage ist QOI 20 der typische Standardwert. Parameter immer mit der Gegenstelle abgleichen.", foreground="#555555").grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=4, pady=12)

    def _command_tab(self, book) -> None:
        tab = ttk.Frame(book, padding=12)
        book.add(tab, text="Schalten")
        self.command_ioa = tk.StringVar()
        self.command_type = tk.StringVar(value=self.COMMANDS[0])
        self.command_value = tk.StringVar(value="0")
        self._field(tab, "IOA", self.command_ioa, 0)
        ttk.Label(tab, text="Befehlstyp").grid(row=0, column=1, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Combobox(tab, textvariable=self.command_type, values=self.COMMANDS, state="readonly", width=29).grid(row=1, column=1, sticky=tk.EW, padx=4)
        self._field(tab, "Wert", self.command_value, 2)
        ttk.Button(tab, text="Auswahl senden", command=lambda: self._send_command(True)).grid(row=3, column=0, padx=4, pady=16, sticky=tk.W)
        ttk.Button(tab, text="Ausführung senden", command=lambda: self._send_command(False)).grid(row=3, column=1, padx=4, pady=16, sticky=tk.W)
        ttk.Label(tab, text="Einzel: 0/1 · Doppel: 1=AUS, 2=EIN · Stufe: 1=TIEFER, 2=HÖHER · Bitmuster: 0…4294967295", foreground="#9b2c2c").grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=4)

    def _setpoint_tab(self, book) -> None:
        tab = ttk.Frame(book, padding=12)
        book.add(tab, text="Sollwerte")
        self.setpoint_ioa = tk.StringVar()
        self.setpoint_type = tk.StringVar(value=self.SETPOINTS[0])
        self.setpoint_value = tk.StringVar(value="0")
        self._field(tab, "IOA", self.setpoint_ioa, 0)
        ttk.Label(tab, text="Sollwerttyp").grid(row=0, column=1, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Combobox(tab, textvariable=self.setpoint_type, values=self.SETPOINTS, state="readonly", width=28).grid(row=1, column=1, sticky=tk.EW, padx=4)
        self._field(tab, "Wert", self.setpoint_value, 2)
        ttk.Button(tab, text="Auswahl senden", command=lambda: self._send_setpoint(True)).grid(row=3, column=0, padx=4, pady=16, sticky=tk.W)
        ttk.Button(tab, text="Ausführung senden", command=lambda: self._send_setpoint(False)).grid(row=3, column=1, padx=4, pady=16, sticky=tk.W)
        ttk.Label(tab, text="Normiert: −1 bis +1 · Skaliert: −32768 bis 32767 · Gleitkomma: Dezimalwert", foreground="#555555").grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=4)

    def _parameter_tab(self, book) -> None:
        tab = ttk.Frame(book, padding=12)
        book.add(tab, text="Parameter")
        self.parameter_ioa = tk.StringVar()
        self.parameter_type = tk.StringVar(value=self.PARAMETERS[0])
        self.parameter_value = tk.StringVar(value="0")
        self.parameter_qpa = tk.StringVar(value="0")
        self._field(tab, "IOA", self.parameter_ioa, 0)
        ttk.Label(tab, text="Parametertyp").grid(row=0, column=1, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Combobox(tab, textvariable=self.parameter_type, values=self.PARAMETERS, state="readonly", width=26).grid(row=1, column=1, sticky=tk.EW, padx=4)
        self._field(tab, "Wert", self.parameter_value, 2)
        self._field(tab, "QPM / QPA", self.parameter_qpa, 3)
        ttk.Button(tab, text="Parameter senden", command=self._send_parameter).grid(row=3, column=0, padx=4, pady=16, sticky=tk.W)
        ttk.Label(tab, text="Parameteränderungen können die Gerätefunktion dauerhaft beeinflussen. Typ, IOA und Qualifier aus der Herstellerdokumentation übernehmen.", foreground="#9b2c2c", wraplength=700).grid(row=4, column=0, columnspan=4, sticky=tk.W, padx=4)

    def _raw_tab(self, book) -> None:
        tab = ttk.Frame(book, padding=12)
        book.add(tab, text="ASDU / Datei")
        self.raw_preset = tk.StringVar(value=next(iter(self.RAW_PRESETS)))
        self.raw_type = tk.StringVar(); self.raw_vsq = tk.StringVar(); self.raw_cot = tk.StringVar()
        self.raw_ioa = tk.StringVar(); self.raw_payload = tk.StringVar()
        ttk.Label(tab, text="Vorlage").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=4)
        box = ttk.Combobox(tab, textvariable=self.raw_preset, values=tuple(self.RAW_PRESETS), state="readonly", width=43)
        box.grid(row=1, column=0, columnspan=5, sticky=tk.EW, padx=4)
        box.bind("<<ComboboxSelected>>", lambda _event: self._apply_raw_preset())
        for column, (label, variable, maximum) in enumerate((("Typ", self.raw_type, 255), ("VSQ", self.raw_vsq, 255), ("COT", self.raw_cot, 63), ("IOA", self.raw_ioa, 0xFFFFFF))):
            self._field(tab, label, variable, column, row=2)
            tab.columnconfigure(column, weight=1)
        ttk.Label(tab, text="Nutzdaten (Hex, ohne ASDU-Kopf und IOA)").grid(row=4, column=0, columnspan=5, sticky=tk.W, padx=4, pady=(15, 2))
        ttk.Entry(tab, textvariable=self.raw_payload, font=("Consolas", 10)).grid(row=5, column=0, columnspan=5, sticky=tk.EW, padx=4)
        ttk.Button(tab, text="ASDU senden", command=self._send_raw).grid(row=6, column=0, sticky=tk.W, padx=4, pady=14)
        ttk.Label(tab, text="Dateiübertragung ist geräte- und sitzungsabhängig. Die Vorlagen erzeugen keinen automatischen Dateitransfer; Payload und Ablauf müssen zur Gegenstelle passen.", foreground="#9b2c2c", wraplength=700).grid(row=7, column=0, columnspan=5, sticky=tk.W, padx=4)
        self._apply_raw_preset()

    def _show_asdu(self, asdu: bytes, description: str, dangerous: bool) -> None:
        self.preview.set(hex_bytes(asdu))
        self.send_asdu_callback(asdu, description, dangerous)

    def _send_standard(self, type_id: int, label: str, dangerous: bool) -> None:
        try:
            ioa = self._number(self.std_ioa, "IOA")
            qualifier = self._number(self.std_qualifier, "Qualifier", 65535 if type_id == 106 else 255)
            self._show_asdu(build_standard_asdu(type_id, self.common_address(), ioa, qualifier, self.originator()), label, dangerous)
        except ValueError as error: messagebox.showerror("IEC104 senden", str(error), parent=self)

    def _command_values(self, type_var, ioa_var, value_var):
        type_id = int(type_var.get().split("-", 1)[0].strip())
        ioa = self._number(ioa_var, "IOA")
        text = value_var.get().strip().replace(",", ".")
        value = float(text) if type_id in (48, 50, 61, 63) else int(text, 0)
        return type_id, ioa, value

    def _send_command(self, select: bool) -> None:
        try:
            type_id, ioa, value = self._command_values(self.command_type, self.command_ioa, self.command_value)
            asdu = self.send_command_callback(type_id, ioa, value, select, "Schaltbefehl")
            if asdu: self.preview.set(hex_bytes(asdu))
        except ValueError as error: messagebox.showerror("IEC104 senden", str(error), parent=self)

    def _send_setpoint(self, select: bool) -> None:
        try:
            type_id, ioa, value = self._command_values(self.setpoint_type, self.setpoint_ioa, self.setpoint_value)
            asdu = self.send_command_callback(type_id, ioa, value, select, "Sollwertbefehl")
            if asdu: self.preview.set(hex_bytes(asdu))
        except ValueError as error: messagebox.showerror("IEC104 senden", str(error), parent=self)

    def _send_parameter(self) -> None:
        try:
            type_id = int(self.parameter_type.get().split("-", 1)[0].strip())
            ioa = self._number(self.parameter_ioa, "IOA")
            qualifier = self._number(self.parameter_qpa, "QPM/QPA", 255)
            value = float(self.parameter_value.get().replace(",", ".")) if type_id in (110, 112) else int(self.parameter_value.get(), 0)
            self._show_asdu(build_parameter_asdu(self.common_address(), ioa, type_id, value, qualifier, self.originator()), "Parameter senden", True)
        except ValueError as error: messagebox.showerror("IEC104 senden", str(error), parent=self)

    def _apply_raw_preset(self) -> None:
        values = self.RAW_PRESETS[self.raw_preset.get()]
        for variable, value in zip((self.raw_type, self.raw_vsq, self.raw_cot, self.raw_ioa, self.raw_payload), values): variable.set(str(value))

    def _send_raw(self) -> None:
        try:
            asdu = build_asdu(self._number(self.raw_type, "Typ", 255), self.common_address(), self._number(self.raw_ioa, "IOA"), parse_hex_bytes(self.raw_payload.get()), self._number(self.raw_cot, "COT", 255), self.originator(), self._number(self.raw_vsq, "VSQ", 255))
            self._show_asdu(asdu, self.raw_preset.get(), True)
        except ValueError as error: messagebox.showerror("IEC104 senden", str(error), parent=self)
