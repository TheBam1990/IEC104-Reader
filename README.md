# IEC104 Reader für Windows

Portable grafische Anwendung zum Lesen, Analysieren und kontrollierten Senden von IEC 60870-5-104 über TCP/IP.
https://github.com/TheBam1990/IEC104-Reader/releases/tag/v1.3.1

## Oberfläche

![IEC104 Reader 1.3.1 mit strukturierter IOA und Qualitätskennzeichen](docs/iec104-reader-1.3.1.png)

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
- Wertetabelle mit getrennten Spalten für CA/ASDU und IOA sowie ASDU-Typ, Übertragungsursache, Empfangswert, Qualität und Zeitstempel
- umschaltbare IOA-Darstellung: unstrukturiert dezimal oder strukturiert als Oktett 1-2-3
- Qualitätskennzeichen einzeln sichtbar und filterbar: OV, BL, SB, NT und IV sowie rohes QDS-Byte
- eigenes Live-Filterfeld über jeder Tabellenspalte; mehrere Filter wirken gemeinsam
- CSV-Export der aktuell sichtbaren Tabellenzeilen
- platzsparende Sendezentrale in einem eigenen Dialogfenster
- Einzel-, Doppel-, Stufen- und Bitmusterbefehle
- normierte, skalierte und Gleitkomma-Sollwerte
- getrennte Aktionen für Select/Auswahl und Execute/Ausführung
- optionale CP56-Zeitstempel bei Befehlen
- General- und Zählerabfrage, Einzelwert lesen, Zeitsynchronisation, Test,
  Prozessreset und Verzögerungsermittlung
- Parameterwerte und Parameteraktivierung
- frei konfigurierbare ASDUs und Vorlagen für die IEC104-Dateitypen 120–126
- ASDU-Vorschau in Hexadezimaldarstellung
- Sicherheitsrückfrage vor jedem einzelnen Befehl
- lokale Speicherung der Verbindungseinstellungen und Faktoren

## Bedienung

1. IP-Adresse oder Hostnamen des IEC104-Servers eintragen.
2. TCP-Port eintragen, normalerweise `2404`.
3. Common Address der Gegenstelle eintragen.
4. **Verbinden** drücken. Das Programm sendet STARTDT automatisch.
5. Bei aktivierter Option **GI nach Verbindung** folgt automatisch eine Generalabfrage.
6. Empfangene Werte erscheinen rechts in der Tabelle.

Die Filterfelder befinden sich direkt über den jeweiligen Spalten. Mehrere ausgefüllte Filter werden als UND-Verknüpfung ausgewertet. Mit **Alle Filter löschen** oder Escape werden alle Zeilen wieder eingeblendet.

## Telegramme senden

Die Schaltfläche **Senden ...** öffnet die Sendezentrale, ohne das
Hauptfenster zu vergrößern. Sie enthält getrennte Reiter für:

- **Standard:** Generalabfrage, Zählerabfrage, IOA lesen, Zeitsynchronisation,
  Testbefehl, Prozessreset und Verzögerungsermittlung
- **Schalten:** Einzel-, Doppel-, Stufen- und Bitmusterbefehle, wahlweise mit
  CP56-Zeitstempel sowie getrennt als Auswahl oder Ausführung
- **Sollwerte:** normierte, skalierte und Gleitkommawerte, ebenfalls mit
  Select-before-operate und optionalem CP56-Zeitstempel
- **Parameter:** Typen 110–113 einschließlich Qualifier
- **ASDU / Datei:** frei bearbeitbarer Typ, VSQ, COT, IOA und Hex-Payload sowie
  Vorlagen für die standardisierten Datei-ASDUs 120–126

Common Address und Originator werden oben im Hauptfenster einmal eingestellt
und von allen Reitern verwendet. Vor dem Senden wird die erzeugte ASDU als
Hexfolge angezeigt. Schreibende und potenziell gefährliche Aktionen verlangen
eine ausdrückliche Bestätigung.

Die Dateivorlagen stellen bewusst keinen automatischen Dateitransfer dar. Ein
vollständiger Transfer ist zustandsbehaftet und muss hinsichtlich Dateiname,
Abschnitten, Segmenten und Bestätigungen exakt zur Gegenstelle passen. Die
Vorlagen erlauben das kontrollierte Erzeugen solcher ASDUs anhand der jeweiligen
Gerätedokumentation.

## Unterstützte Überwachungs-ASDUs

Unter anderem Einzel- und Doppelmeldungen, Stufenstellungen, Bitmuster, normierte, skalierte und Gleitkomma-Messwerte sowie Zählwerte – jeweils ohne Zeitstempel sowie mit CP24- oder CP56-Zeitstempel, soweit durch die standardisierten Typen 1–21 und 30–37 definiert.

Unbekannte ASDUs bleiben vollständig im Telegrammfenster sichtbar, auch wenn dafür keine Tabellenzeile erzeugt wird.

## Sicherheit

- Jeder Befehl muss über eine Sicherheitsrückfrage ausdrücklich bestätigt werden.
- Auswahl und Ausführung sind getrennte Schaltflächen; ein Select wird nicht automatisch ausgeführt.
- Einzelbefehl: `0` oder `1`. Doppelbefehl: `1` für AUS und `2` für EIN.
- Die Bedienperson muss CA, IOA, Befehlstyp und Wert anhand der Anlagendokumentation prüfen.
- Es verwendet keine Cloud-Dienste und keine Telemetrie.
- Einstellungen und Faktoren werden ausschließlich lokal gespeichert.

## EXE selbst bauen

Unter Windows `build-windows.bat` starten. Das Ergebnis liegt anschließend unter:

```text
dist\IEC104-Reader.exe
```

## Lizenz

MIT
