# Dokumentation: Owon/Abestop DS1102 USB-Protokoll

Diese Dokumentation basiert auf dem Reverse Engineering des USB-Traffics zwischen der DSO-Wave Software und dem Oszilloskop (VID: 0x5345, PID: 0x1234).

## 1. Physikalische Schicht
- **Schnittstelle**: USB Bulk Transfer
- **Endpoints**: 
    - OUT: `0x01` (Befehle an das Gerät)
    - IN:  `0x81` (Daten vom Gerät)
- **Max Packet Size**: 64 Bytes (USB 2.0 Full Speed)
- **Terminator**: Alle ASCII-Befehle müssen mit `\r\n` (Hex: `0D 0A`) abgeschlossen werden.

## 2. Kommunikations-Handshake
Bevor Daten abgefragt werden können, muss das Gerät initialisiert werden.
- **Initialisierungs-Befehl**: `:MODel?\r\n`
- **Antwort**: Modellnummer-String (z.B. `110204101->\n`)
- **Wichtig**: Ohne diesen ersten Befehl antwortet das Gerät oft nicht auf `:DATA`-Anfragen.

## 3. Befehlsstruktur (SCPI-ähnlich)
Das Gerät unterstützt eine Mischung aus Standard-SCPI und proprietären Befehlen.

### Steuerbefehle
| Befehl | Aktion |
| :--- | :--- |
| `:AUToset on` | Führt automatisches Setup aus |
| `:RUNning RUN` | Startet die Erfassung (Grüne LED) |
| `:RUNning STOP` | Stoppt die Erfassung (Rote LED) |

### Abfragebefehle (Metadaten)
- **Befehl**: `:DATA:WAVE:SCREEN:HEAD?\r\n`
- **Antwortformat**: `[Header: 4 Bytes][JSON-Payload]`
- **Antwort-Header**: `: \x03 \x00 \x00` (Erstes Byte ist `:`, dann 3 Bytes Längen-Indikator/Typ)
- **JSON-Inhalt**: Enthält `TIMEBASE`, `CHANNEL` Skalierung (z.B. "2.00V"), `OFFSET` und `SAMPLE` Anzahl.

## 4. Wellenform-Daten (Waveform)
- **Befehle**: `:DATA:WAVE:SCREEN:CH1?` oder `:DATA:WAVE:SCREEN:CH2?`
- **Antwortformat**: `[Header: 4 Bytes][Binärdaten]`
- **Header**: Die ersten 4 Bytes enthalten die Länge der folgenden Daten in Little-Endian.
    - Beispiel: `e0 0b 00 00` -> `0x0be0` = 3040 Bytes.
- **Datenpunkte**: 
    - Jedes Sample besteht aus **2 Bytes (16-Bit)**.
    - Format: **Big-Endian** Signed Integer (`>i2`).
    - Anzahl Samples: 1520 pro Kanal (entspricht 3040 Bytes / 2).
- **Berechnung der Spannung**:
    - `Spannung (V) = (Rohwert / Digit_Faktor) * Kanal_Skalierung`
    - Der `Digit_Faktor` liegt beim DS1102 typischerweise bei ca. 100 Digits pro Division.

## 🕹️ Bestätigte SCPI-Befehle (Stand: 15.03.2026)

Diese Befehle wurden erfolgreich am Gerät (Abestop/Owon DS1102) getestet und müssen mit `\n` terminiert werden.

### 🔍 Abfragen (Queries)
| Befehl | Antwort-Beispiel | Beschreibung |
| :--- | :--- | :--- |
| `*IDN?` | `Abestop,DS1102,24250071,V3.1.0` | Geräte-Identifikation |
| `:HORizontal:SCALe?` | `500us` | Aktuelle Zeitbasis |
| `:HORizontal:OFFSet?` | `0.00` | Horizontaler Verschub |
| `:CH1:SCALe?` | `2.00V` | Vertikale Skalierung Kanal 1 |
| `:CH1:OFFSet?` | `0.00000` | Vertikaler Offset Kanal 1 |
| `:TRIGger:STATus?` | `TRIG` | Aktueller Trigger-Zustand (`AUTO`, `TRIG`, `STOP`) |
| `:DATA:WAVE:SCREEN:HEAD?` | `{"model":"DS1102", ...}` | Metadaten/Einstellungen als JSON |

### ⚙️ Steuerungs-Befehle (Write)
| Befehl | Beispiel | Wirkung |
| :--- | :--- | :--- |
| `:AUToset on` | `:AUToset on` | Führt automatisches Setup aus |
| `:RUNning RUN` | `:RUNning RUN` | Startet die Erfassung |
| `:RUNning STOP` | `:RUNning STOP` | Stoppt (Freeze) die Erfassung |
| `:HORizontal:SCALe <val>`| `:HORizontal:SCALe 1ms` | Setzt die Zeitbasis |
| `:CH1:SCALe <val>` | `:CH1:SCALe 1.00V` | Setzt die Skalierung für CH1 |

---

## 🧪 Offene Forschungs-Aufgaben für Claude

Liebe Claude Desktop Instanz, hilf uns, weitere Befehle für dieses Gerät zu finden. Probiere Variationen aus, inspiriert von Owon- und Rigol-Protokollen:

1.  **Messwerte**: Wir suchen Befehle für Vpp, Frequenz, Max/Min. (Probiere: `:MEASure:CH1:PKPK?`, `:MEASure:FREQuency?`, `:MEAS:ITEM? VPP,CHAN1`).
2.  **Trigger-Level**: Wir müssen den Trigger-Level setzen können (Probiere: `:TRIGger:EDGe:LEVel?`, `:TRIGger:LEVel?`).
3.  **Kanal-Steuerung**: Wie schaltet man Kanal 2 ein/aus? (Probiere: `:CH2:DISPlay 1`, `:CHANnel2:STATe ON`).
4.  **Display**: Screenshots oder Helligkeit (Probiere: `:DISPlay:DATA?`, `:PRINt?`).

**Hinweis**: Das Gerät antwortet bei ungültigen Befehlen oft mit einem USB-Timeout. Nutze das `scpi_exploration_test.py` Script für deine Tests.

## 5. Bekannte Unklarheiten
- Der exakte Faktor für die Volt-Umrechnung (25 vs 100 Digits/Div) muss noch final verifiziert werden.
- Befehle für Trigger-Level und Messfunktionen (VPP, Frequenz) müssen einzeln validiert werden.
