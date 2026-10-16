# IEC104 Reader für Windows

Portable grafische Anwendung zum Lesen und Analysieren von IEC 60870-5-104 über TCP/IP. Das Programm arbeitet als lesender IEC104-Master und sendet keine Schaltbefehle.

## Funktionen

- einzelne portable `IEC104-Reader.exe` ohne Installation
- Ziel-IP/Hostname, TCP-Port und Common Address einstellbar
- STARTDT und Generalabfrage
- optionale Generalabfrage direkt nach dem Verbinden
- optional zyklische Generalabfrage mit einstellbarem Intervall
- Sequenznummern und IEC104-S-Bestätigungen
- automatische Antwort auf TESTFR
- vollständige RX-/TX-Anzeige in Hexadezimaldarstellung
- Sitzungslog `IEC104-Telegrammverkehr.txt` neben der EXE; wird bei jedem Start neu begonnen
- Wertetabelle mit CA, IOA, ASDU-Typ, Übertragungsursache, Empfangswert, Qualität und Zeitstempel
- Faktor pro Zahlenwert; Originalwert und berechneter Wert bleiben gleichzeitig sichtbar
- eigenes Live-Filterfeld über jeder Tabellenspalte; mehrere Filter wirken gemeinsam
- CSV-Export der aktuell sichtbaren Tabellenzeilen
- lokale Speicherung der Verbindungseinstellungen und Faktoren

## Bedienung

1. IP-Adresse oder Hostnamen des IEC104-Servers eintragen.
2. TCP-Port eintragen, normalerweise `2404`.
3. Common Address der Gegenstelle eintragen.
4. **Verbinden** drücken. Das Programm sendet STARTDT automatisch.
5. Bei aktivierter Option **GI nach Verbindung** folgt automatisch eine Generalabfrage.
6. Empfangene Werte erscheinen rechts in der Tabelle.

Die Filterfelder befinden sich direkt über den jeweiligen Spalten. Mehrere ausgefüllte Filter werden als UND-Verknüpfung ausgewertet. Mit **Alle Filter löschen** oder Escape werden alle Zeilen wieder eingeblendet.

## Unterstützte Überwachungs-ASDUs

Unter anderem Einzel- und Doppelmeldungen, Stufenstellungen, Bitmuster, normierte, skalierte und Gleitkomma-Messwerte sowie Zählwerte – jeweils ohne Zeitstempel sowie mit CP24- oder CP56-Zeitstempel, soweit durch die standardisierten Typen 1–21 und 30–37 definiert.

Unbekannte ASDUs bleiben vollständig im Telegrammfenster sichtbar, auch wenn dafür keine Tabellenzeile erzeugt wird.

## Sicherheit

- Das Programm sendet keine IEC104-Schaltbefehle.
- Es sendet ausschließlich Verbindungssteuerung, Bestätigungen und Generalabfragen.
- Es verwendet keine Cloud-Dienste und keine Telemetrie.
- Einstellungen und Faktoren werden ausschließlich lokal gespeichert.

## EXE selbst bauen

Unter Windows `build-windows.bat` starten. Das Ergebnis liegt anschließend unter:

```text
dist\IEC104-Reader.exe
```

## Lizenz

MIT
