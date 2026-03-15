import usb.core
import time
import json

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def safe_test():
    print("--- DS1102 CLEAN START TEST (REPAIRED) ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Gerät nicht gefunden.")
        return

    # Die E/A Fehlerbehebung für libusb0 unter Windows:
    # 1. Config setzen
    # 2. Interface claime
    # 3. Kernel-Zustand prüfen (unter Windows meist nicht nötig aber sicherheitshalber)
    
    try:
        dev.set_configuration()
        usb.util.claim_interface(dev, 0)
    except Exception as e:
        print(f"Initialisierung fehlgeschlagen: {e}")
        # Wir versuchen es trotzdem weiter

    print("1. Setze Skalierung auf 2V (Standard)...")
    try:
        dev.write(EP_OUT, ":CH1:SCALe 2V\n")
        time.sleep(1.0)
    except Exception as e:
        print(f"Schreibfehler: {e}")

    print("2. Metadaten-Abfrage...")
    try:
        # Buffer leeren falls noch Reste drin sind
        try:
            while True: dev.read(EP_IN, 4096, timeout=10)
        except: pass

        dev.write(EP_OUT, ":DATA:WAVE:SCREEN:HEAD?\n")
        time.sleep(1.0)
        
        # Antwort in bytes umwandeln
        data_raw = dev.read(EP_IN, 8192, timeout=2000)
        data = bytes(data_raw)
        raw_text = data.decode('ascii', errors='ignore')
        print(f"Antwort (Länge {len(data)}):")
        print("-" * 20)
        print(raw_text[:200]) # Zeige den Anfang der Antwort
        print("-" * 20)
        
        if "{" in raw_text:
            print("ERFOLG: JSON Header empfangen.")
        else:
            print("WARNUNG: Keine JSON-Daten in der Antwort gefunden.")
            
    except Exception as e:
        print(f"Fehler beim Empfangen: {e}")

if __name__ == "__main__":
    safe_test()
