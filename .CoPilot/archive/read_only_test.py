import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234

def simple_read_only_test():
    print("--- DS1102 READ-ONLY DETECTION TEST ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Gerät NICHT im USB-Bus gefunden.")
        return

    print("Gerät am USB-Bus erkannt.")
    
    try:
        # Versuche nur zu initialisieren ohne zu schreiben
        dev.set_configuration()
        print("Set_configuration() OK.")
    except Exception as e:
        print(f"Set_configuration() FEHLGESCHLAGEN: {e}")
        return

    print("\nLese-Versuch (ohne Kommando) - Prüfe ob das Oszi von selbst sendet...")
    try:
        # 1 Sekunde lang schauen ob IRGENDWAS kommt
        data = dev.read(0x81, 4096, timeout=1000)
        print(f"Überraschung! Daten empfangen: {len(data)} Bytes")
    except Exception as e:
        print(f"Keine spontanen Daten (erwartet): {e}")

    print("\nVersuche minimalen Befehl: *IDN?")
    try:
        dev.write(0x01, b"*IDN?\n")
        time.sleep(0.5)
        resp = dev.read(0x81, 4096, timeout=2000)
        print(f"Antwort auf *IDN?: {bytes(resp).decode('ascii', errors='ignore')}")
    except Exception as e:
        print(f"Kommunikations-Fehler: {e}")

if __name__ == "__main__":
    simple_read_only_test()
