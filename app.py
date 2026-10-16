"""Portable graphical IEC 60870-5-104 reader for Windows."""

from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from iec104.protocol import COT_NAMES, TYPE_NAMES, decode_asdu, hex_bytes
from iec104.table_filter import matches_filters
from iec104.tcp_worker import TCPWorker

APP_NAME = "IEC104 Reader"
APP_VERSION = "1.0.0"
CONFIG_FILE = Path.home() / "IEC104-Reader.json"


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class ReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1500x840")
        self.minsize(1080, 640)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.events: queue.Queue = queue.Queue()
        self.worker = TCPWorker(self.events)
        self.rows: dict[str, str] = {}
        self.row_keys: dict[str, str] = {}
        self.latest_values = {}
        self.scaling_factors: dict[str, float] = {}
        self.column_filters: dict[str, tk.StringVar] = {}
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.gi_job: str | None = None
        self.traffic_log_path = application_directory() / "IEC104-Telegrammverkehr.txt"
        self.traffic_log = None
        self.traffic_log_error_reported = False
        self._variables()
        self.open_traffic_log()
        self._style()
        self._layout()
        self.load_settings(silent=True)
        self.after(40, self.process_events)

    def _variables(self) -> None:
        self.host = tk.StringVar(value="192.168.2.101")
        self.port = tk.StringVar(value="2404")
        self.common_address = tk.StringVar(value="2019")
        self.connect_timeout = tk.StringVar(value="5")
        self.auto_gi = tk.BooleanVar(value=True)
        self.cyclic_gi = tk.BooleanVar(value=False)
        self.gi_interval = tk.StringVar(value="60")
        self.autoscroll = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Bereit")
        self.counter = tk.StringVar(value="RX 0 B | TX 0 B | 0 Werte")

    def open_traffic_log(self) -> None:
        try:
            self.traffic_log = self.traffic_log_path.open("w", encoding="utf-8", buffering=1)
            self.traffic_log.write(f"{APP_NAME} {APP_VERSION} - Sitzungsstart {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        except OSError:
            self.traffic_log = None

    def _style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=23)
        style.configure("Status.TLabel", padding=(8, 4))

    def _layout(self) -> None:
        top = ttk.LabelFrame(self, text="IEC104 TCP-Verbindung", padding=8)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))
        fields = [
            ("Host / IP", self.host, 22), ("TCP-Port", self.port, 9),
            ("Common Address", self.common_address, 14), ("Timeout (s)", self.connect_timeout, 10),
            ("GI-Intervall (s)", self.gi_interval, 12),
        ]
        for column, (label, variable, width) in enumerate(fields):
            ttk.Label(top, text=label).grid(row=0, column=column, sticky=tk.W, padx=3)
            ttk.Entry(top, textvariable=variable, width=width).grid(row=1, column=column, sticky=tk.EW, padx=3, pady=2)
        self.connect_button = ttk.Button(top, text="Verbinden", command=self.toggle_connection)
        self.connect_button.grid(row=1, column=5, padx=4)
        ttk.Button(top, text="STARTDT", command=self.send_start).grid(row=1, column=6, padx=4)
        ttk.Button(top, text="Generalabfrage", command=self.send_gi).grid(row=1, column=7, padx=4)
        ttk.Checkbutton(top, text="GI nach Verbindung", variable=self.auto_gi).grid(row=2, column=0, sticky=tk.W, padx=3)
        ttk.Checkbutton(top, text="GI zyklisch", variable=self.cyclic_gi, command=self.configure_cyclic_gi).grid(row=2, column=1, sticky=tk.W, padx=3)
        ttk.Checkbutton(top, text="Traffic automatisch scrollen", variable=self.autoscroll).grid(row=2, column=2, sticky=tk.W, padx=3)
        ttk.Button(top, text="Einstellungen speichern", command=self.save_settings).grid(row=2, column=5, padx=4, pady=3)

        toolbar = ttk.Frame(self, padding=(8, 3))
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Traffic leeren", command=self.clear_traffic).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="Wertetabelle leeren", command=self.clear_values).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="CSV exportieren", command=self.export_csv).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="Faktor für Wert setzen", command=self.set_selected_factor).pack(side=tk.RIGHT, padx=3)
        ttk.Button(toolbar, text="Alle Filter löschen", command=self.clear_table_filters).pack(side=tk.RIGHT, padx=3)

        split = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        split.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        traffic_frame = ttk.LabelFrame(split, text="IEC104-Telegrammverkehr", padding=4)
        values_frame = ttk.LabelFrame(split, text="Aktuelle Werte (jede CA/IOA/Typ-Kombination einmal)", padding=4)
        split.add(traffic_frame, weight=2)
        split.add(values_frame, weight=3)

        self.traffic = tk.Text(traffic_frame, wrap=tk.NONE, font=("Consolas", 9), bg="#101418", fg="#d7e1e8", insertbackground="white")
        traffic_y = ttk.Scrollbar(traffic_frame, orient=tk.VERTICAL, command=self.traffic.yview)
        traffic_x = ttk.Scrollbar(traffic_frame, orient=tk.HORIZONTAL, command=self.traffic.xview)
        self.traffic.configure(yscrollcommand=traffic_y.set, xscrollcommand=traffic_x.set)
        self.traffic.grid(row=0, column=0, sticky="nsew")
        traffic_y.grid(row=0, column=1, sticky="ns")
        traffic_x.grid(row=1, column=0, sticky="ew")
        traffic_frame.rowconfigure(0, weight=1)
        traffic_frame.columnconfigure(0, weight=1)
        for tag, color in {"rx": "#7CFC9A", "tx": "#79B8FF", "error": "#FF7B72", "meta": "#C9D1D9"}.items():
            self.traffic.tag_configure(tag, foreground=color)

        columns = ("address", "type", "cot", "received", "factor", "calculated", "quality", "unit", "timestamp", "count")
        headings = {
            "address": "CA / IOA", "type": "ASDU-Typ", "cot": "Übertragungsursache",
            "received": "Empfangen", "factor": "Faktor", "calculated": "Berechnet",
            "quality": "Qualität", "unit": "Einheit", "timestamp": "Zeitstempel", "count": "Anzahl",
        }
        widths = {"address": 180, "type": 205, "cot": 150, "received": 120, "factor": 80,
                  "calculated": 125, "quality": 100, "unit": 75, "timestamp": 170, "count": 65}
        self.table = ttk.Treeview(values_frame, columns=columns, show="headings")
        for name in columns:
            self.table.heading(name, text=headings[name], command=lambda n=name: self.sort_table(n, False))
            self.table.column(name, width=widths[name], minwidth=55, stretch=False)
        self.filter_canvas = tk.Canvas(values_frame, height=27, highlightthickness=0)
        x = 0
        for name in columns:
            variable = tk.StringVar()
            self.column_filters[name] = variable
            entry = ttk.Entry(self.filter_canvas, textvariable=variable)
            entry.bind("<Escape>", lambda _event: self.clear_table_filters())
            self.filter_canvas.create_window(x, 1, anchor="nw", width=widths[name], height=25, window=entry)
            x += widths[name]
            variable.trace_add("write", lambda *_args: self.apply_table_filter())
        self.filter_canvas.configure(scrollregion=(0, 0, x, 27))
        self.table.bind("<Double-1>", self.set_selected_factor)
        table_y = ttk.Scrollbar(values_frame, orient=tk.VERTICAL, command=self.table.yview)
        table_x = ttk.Scrollbar(values_frame, orient=tk.HORIZONTAL, command=self.scroll_value_table)
        self.table.configure(yscrollcommand=table_y.set, xscrollcommand=lambda first, last: self.sync_table_scroll(table_x, first, last))
        self.filter_canvas.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.table.grid(row=1, column=0, sticky="nsew")
        table_y.grid(row=1, column=1, sticky="ns")
        table_x.grid(row=2, column=0, sticky="ew")
        values_frame.rowconfigure(1, weight=1)
        values_frame.columnconfigure(0, weight=1)

        statusbar = ttk.Frame(self)
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(statusbar, textvariable=self.status, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Label(statusbar, textvariable=self.counter, style="Status.TLabel").pack(side=tk.RIGHT)

    def connection_values(self) -> tuple[str, int, int, float]:
        host = self.host.get().strip()
        if not host:
            raise ValueError("Bitte Host oder IP-Adresse eingeben")
        port, ca, timeout = int(self.port.get()), int(self.common_address.get()), float(self.connect_timeout.get())
        if not 1 <= port <= 65535: raise ValueError("TCP-Port muss zwischen 1 und 65535 liegen")
        if not 0 <= ca <= 65535: raise ValueError("Common Address muss zwischen 0 und 65535 liegen")
        if not 0.2 <= timeout <= 120: raise ValueError("Timeout muss zwischen 0,2 und 120 Sekunden liegen")
        return host, port, ca, timeout

    def toggle_connection(self) -> None:
        if self.worker.connected:
            self.stop_cyclic_gi()
            self.worker.disconnect()
            self.connect_button.configure(text="Verbinden")
            self.status.set("Getrennt")
            return
        try:
            host, port, _ca, timeout = self.connection_values()
            self.worker.connect(host, port, timeout)
            self.connect_button.configure(text="Trennen")
            self.save_settings(silent=True)
        except Exception as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)

    def send_start(self) -> None:
        try:
            from iec104.protocol import build_u_frame
            from iec104.tcp_worker import STARTDT_ACT
            self.worker.send(build_u_frame(STARTDT_ACT))
        except Exception as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)

    def send_gi(self) -> None:
        try:
            self.worker.send_gi(self.connection_values()[2])
            self.status.set("Generalabfrage gesendet")
        except Exception as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)

    def configure_cyclic_gi(self) -> None:
        self.stop_cyclic_gi()
        if self.cyclic_gi.get() and self.worker.started:
            self.schedule_cyclic_gi()

    def schedule_cyclic_gi(self) -> None:
        try:
            seconds = max(5, int(self.gi_interval.get()))
        except ValueError:
            seconds = 60
        self.gi_job = self.after(seconds * 1000, self.cyclic_gi_tick)

    def cyclic_gi_tick(self) -> None:
        self.gi_job = None
        if self.cyclic_gi.get() and self.worker.started:
            try:
                self.worker.send_gi(self.connection_values()[2])
            except Exception as error:
                self.log("ERR", str(error), "error")
            self.schedule_cyclic_gi()

    def stop_cyclic_gi(self) -> None:
        if self.gi_job:
            self.after_cancel(self.gi_job)
            self.gi_job = None

    def process_events(self) -> None:
        try:
            for _ in range(500):
                kind, payload = self.events.get_nowait()
                if kind == "rx":
                    self.rx_bytes += len(payload)
                    self.log("RX", hex_bytes(payload), "rx")
                elif kind == "tx":
                    self.tx_bytes += len(payload)
                    self.log("TX", hex_bytes(payload), "tx")
                elif kind == "asdu":
                    self.handle_asdu(payload)
                elif kind == "started":
                    self.status.set("IEC104-Datenübertragung aktiv")
                    if self.auto_gi.get(): self.after(100, self.send_gi)
                    self.configure_cyclic_gi()
                elif kind == "warning":
                    self.log("WARN", str(payload), "error")
                elif kind == "error":
                    self.log("ERR", str(payload), "error")
                    self.status.set(str(payload))
                elif kind == "disconnected":
                    self.connect_button.configure(text="Verbinden")
                    self.stop_cyclic_gi()
                else:
                    self.status.set(str(payload))
        except queue.Empty:
            pass
        self.counter.set(f"RX {self.rx_bytes} B | TX {self.tx_bytes} B | {len(self.rows)} Werte")
        self.after(40, self.process_events)

    def handle_asdu(self, data: bytes) -> None:
        if len(data) >= 6:
            type_id, cause = data[0], data[2] & 0x3F
            ca = int.from_bytes(data[4:6], "little")
            self.log("   ", f"ASDU {type_id}: {TYPE_NAMES.get(type_id, 'unbekannt')}; COT {cause}: {COT_NAMES.get(cause, 'unbekannt')}; CA {ca}", "meta")
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for value in decode_asdu(data):
                self.update_value(value, value.source_timestamp or now)
        except Exception as error:
            self.log("ERR", f"ASDU konnte nicht dekodiert werden: {error}", "error")

    def update_value(self, value, timestamp: str, increment: bool = True) -> None:
        rendered = str(value.value)
        numeric = isinstance(value.value, (int, float)) and not isinstance(value.value, bool)
        factor = self.scaling_factors.get(value.key, 1.0) if numeric else None
        calculated = self.format_number(float(value.value) * factor) if numeric else rendered
        factor_text = self.format_number(factor) if numeric else ""
        row = (f"CA {value.common_address} / IOA {value.ioa}", f"{value.type_id}: {value.type_name}",
               f"{value.cause}: {value.cause_name}", rendered, factor_text, calculated,
               value.quality, value.unit, timestamp, 1)
        current = self.rows.get(value.key)
        if current:
            old = self.table.item(current, "values")
            row = row[:-1] + (int(old[9]) + (1 if increment else 0),)
            self.table.item(current, values=row)
            self.table.move(current, "", 0)
        else:
            current = self.table.insert("", 0, values=row)
            self.rows[value.key] = current
            self.row_keys[current] = value.key
        self.latest_values[value.key] = (value, timestamp)
        self.apply_table_filter()

    @staticmethod
    def format_number(value: float) -> str:
        return f"{value:.12g}"

    def set_selected_factor(self, _event=None) -> None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Bitte zuerst einen Zahlenwert auswählen.", parent=self)
            return
        key = self.row_keys.get(selected[0], "")
        latest = self.latest_values.get(key)
        if not latest or not isinstance(latest[0].value, (int, float)) or isinstance(latest[0].value, bool):
            messagebox.showinfo(APP_NAME, "Für diesen Wert kann kein Zahlenfaktor gesetzt werden.", parent=self)
            return
        factor = simpledialog.askfloat(APP_NAME, f"Faktor für {key}:\n\nBerechnet = Empfangen × Faktor",
                                       initialvalue=self.scaling_factors.get(key, 1.0), parent=self)
        if factor is None: return
        self.scaling_factors[key] = factor
        self.update_value(latest[0], latest[1], increment=False)
        self.save_settings(silent=True)

    def apply_table_filter(self) -> None:
        columns = tuple(self.table["columns"])
        active = {i: self.column_filters[name].get() for i, name in enumerate(columns) if self.column_filters[name].get().strip()}
        visible = 0
        for item in self.rows.values():
            if matches_filters(self.table.item(item, "values"), active):
                self.table.reattach(item, "", "end")
                visible += 1
            else:
                self.table.detach(item)
        if active: self.status.set(f"{len(active)} Filter aktiv: {visible} von {len(self.rows)} Werten sichtbar")

    def clear_table_filters(self) -> None:
        for variable in self.column_filters.values(): variable.set("")
        self.status.set(f"Alle Filter gelöscht: {len(self.rows)} Werte sichtbar")

    def scroll_value_table(self, *args) -> None:
        self.table.xview(*args)
        self.filter_canvas.xview(*args)

    def sync_table_scroll(self, scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self.filter_canvas.xview_moveto(first)

    def log(self, direction: str, message: str, tag: str) -> None:
        line = f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction:<4} {message}\n"
        self.traffic.insert(tk.END, line, tag)
        if self.traffic_log:
            try: self.traffic_log.write(line)
            except OSError as error:
                if not self.traffic_log_error_reported:
                    self.status.set(f"Logdatei konnte nicht geschrieben werden: {error}")
                    self.traffic_log_error_reported = True
        if int(self.traffic.index("end-1c").split(".")[0]) > 20000: self.traffic.delete("1.0", "2001.0")
        if self.autoscroll.get(): self.traffic.see(tk.END)

    def clear_traffic(self) -> None:
        self.traffic.delete("1.0", tk.END)

    def clear_values(self) -> None:
        for item in tuple(self.rows.values()): self.table.delete(item)
        self.rows.clear(); self.row_keys.clear(); self.latest_values.clear()

    def sort_table(self, column: str, reverse: bool) -> None:
        rows = [(self.table.set(item, column).casefold(), item) for item in self.table.get_children("")]
        rows.sort(reverse=reverse)
        for index, (_, item) in enumerate(rows): self.table.move(item, "", index)
        self.table.heading(column, command=lambda: self.sort_table(column, not reverse))

    def export_csv(self) -> None:
        filename = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not filename: return
        with open(filename, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow([self.table.heading(column, "text") for column in self.table["columns"]])
            for item in self.table.get_children(""): writer.writerow(self.table.item(item, "values"))
        self.status.set(f"CSV gespeichert: {filename}")

    def settings_dict(self) -> dict:
        result = {name: variable.get() for name, variable in {
            "host": self.host, "port": self.port, "common_address": self.common_address,
            "connect_timeout": self.connect_timeout, "auto_gi": self.auto_gi,
            "cyclic_gi": self.cyclic_gi, "gi_interval": self.gi_interval,
        }.items()}
        result["scaling_factors"] = self.scaling_factors
        return result

    def save_settings(self, silent: bool = False) -> None:
        try:
            CONFIG_FILE.write_text(json.dumps(self.settings_dict(), indent=2), encoding="utf-8")
            if not silent: self.status.set(f"Einstellungen gespeichert: {CONFIG_FILE}")
        except OSError as error:
            if not silent: messagebox.showerror(APP_NAME, str(error), parent=self)

    def load_settings(self, silent: bool = False) -> None:
        if not CONFIG_FILE.exists(): return
        try:
            values = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            variables = {"host": self.host, "port": self.port, "common_address": self.common_address,
                         "connect_timeout": self.connect_timeout, "auto_gi": self.auto_gi,
                         "cyclic_gi": self.cyclic_gi, "gi_interval": self.gi_interval}
            for key, variable in variables.items():
                if key in values: variable.set(values[key])
            factors = values.get("scaling_factors", {})
            if isinstance(factors, dict):
                self.scaling_factors = {str(k): float(v) for k, v in factors.items() if isinstance(v, (int, float))}
        except (OSError, ValueError) as error:
            if not silent: messagebox.showerror(APP_NAME, str(error), parent=self)

    def close(self) -> None:
        self.stop_cyclic_gi()
        self.worker.disconnect()
        if self.traffic_log: self.traffic_log.close()
        self.destroy()


if __name__ == "__main__":
    ReaderApp().mainloop()
