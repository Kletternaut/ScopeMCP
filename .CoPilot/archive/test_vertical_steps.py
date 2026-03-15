import usb.core
import usb.util
import time
import json

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def test_vertical_steps():
    print("--- DS1102 Vertikal-Stufen Test (Volt/Div) ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    dev.set_configuration()

    # Mögliche Stufen zum Testen (von klein bis groß)
    volt_steps = [
        "2mV", "5mV", "10mV", "20mV", "50mV",
        "100mV", "200mV", "500mV",
        "1V", "2V", "5V", "10V"
    ]

    def send_cmd(cmd):
        # Schnelleres Senden
        dev.write(EP_OUT, f"{cmd}\r\n")
        time.sleep(0.3) 

    def get_val():
        # Buffer leeren vor der wichtigen Abfrage
        try:
            while True:
                dev.read(EP_IN, 4096, timeout=10)
        except: pass

        # Erhöhter Timeout für das erste Paket nach Umschaltung
        dev.write(EP_OUT, ":DATA:WAVE:SCREEN:HEAD?\r\n")
        time.sleep(1.0) # Kurze Pause damit die Hardware fertig ist
        
        try:
            # Wir lesen jetzt aggressiver
            full_data = bytearray()
            # Bis zu 5ms warten auf das Paket
            chunk = dev.read(EP_IN, 8192, timeout=2000)
            full_data.extend(chunk)
            
            if b'{' in full_data:
                start = full_data.find(b'{')
                raw_str = full_data[start:].decode('ascii', errors='ignore')
                end_idx = raw_str.rfind('}')
                if end_idx != -1:
                    raw_str = raw_str[:end_idx+1]
                js = json.loads(raw_str)
                return js["CHANNEL"][0]["SCALE"]
        except:
            pass
        return "TIMEOUT"

    print(f"{'Soll-Wert':<12} | {'Ist-Wert (CH1)':<15} | {'Status':<10}")
    print("-" * 45)

    results = []
    for step in volt_steps:
        # Sende Befehl (zuerst ohne Einheit, dann mit)
        send_cmd(f":CH1:SCALe {step}")
        ist = get_val()
        status = "OK" if step.lower() == ist.lower() else "IGNORE"
        print(f"{step:<12} | {ist:<15} | {status}")
        results.append((step, ist))

    # Zurück auf bequeme 2V
    send_cmd(":CH1:SCALe 2V")
    print("\nTest abgeschlossen. Zurück auf 2V/Div.")

if __name__ == "__main__":
    test_vertical_steps()
