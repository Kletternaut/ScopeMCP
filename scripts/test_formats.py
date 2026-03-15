import usb.core
import usb.util
import time
import sys

# Konfiguration
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def test_variant(dev, cmd_base):
    terminators = [("\n", "\\n"), ("\r\n", "\\r\\n"), ("", "kein")]
    
    for term_str, term_label in terminators:
        full_cmd = cmd_base + term_str
        print(f"\n--- Teste Befehl: '{cmd_base}' mit Terminator: {term_label} ---")
        
        try:
            # Sende Befehl
            dev.write(ENDPOINT_OUT, full_cmd.encode('ascii'), timeout=1000)
            print(f"📡 Gesendet: {repr(full_cmd)}")
            
            # Kurze Pause für Hardware-Reaktion
            time.sleep(0.3)
            
            # Versuche zu lesen (falls das Gerät einen Fehler oder Bestätigung schickt)
            try:
                res = dev.read(ENDPOINT_IN, 64, timeout=300)
                if res:
                    response_str = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in res])
                    print(f"📥 Antwort vom Oszi: {response_str.strip()}")
            except usb.core.USBError:
                pass # Timeout ist bei reinen Steuerbefehlen oft normal

            ans = input("❓ Hat das Oszilloskop reagiert? (j/n oder ENTER für weiter): ").lower()
            if ans == 'j':
                print(f"✅ ERFOLG! Das richtige Format ist: '{cmd_base}' + {term_label}")
                return True

        except Exception as e:
            print(f"❌ Fehler bei diesem Test: {e}")
            
    return False

def main():
    print("--- 🔬 Brute-Force Befehlsformat-Test (Abestop DS1102) ---")
    print("Ziel: Das Display von 'RUN' auf 'STOP' (einfrieren) umschalten.\n")
    
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        print("✅ Verbindung bereit.")

        # Verschiedene SCPI-Varianten für "STOP"
        variants = [
            ":STOP",
            "STOP",
            ":ACQuire:STATE STOP",
            "RUN STOP",
            ":RUN:STATE STOP",
            ":HARDCopy:START" # Manchmal triggert das ein Capture
        ]

        for variant in variants:
            if test_variant(dev, variant):
                print(f"\n🏁 Test beendet. Wir haben das Format gefunden!")
                return

        print("\n❌ Keine der Varianten hat funktioniert.")
        print("Mögliche Ursachen:")
        print("1. Das Gerät benötigt einen binären Header (z.B. Owon-Header).")
        print("2. Das Gerät ist in einem Modus, der keine SCPI-Befehle akzeptiert.")

    except Exception as e:
        print(f"💥 Fehler: {e}")

if __name__ == "__main__":
    main()
