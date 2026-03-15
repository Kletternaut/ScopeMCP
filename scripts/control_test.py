import usb.core
import usb.util
import time
import sys

# Konfiguration
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def send_command(dev, cmd):
    """Hilfsfunktion zum Senden eines Befehls und Lesen der Antwort (falls vorhanden)."""
    # Sicherstellen, dass der Befehl mit einem Zeilenumbruch endet
    if not cmd.endswith('\n'):
        cmd += '\n'
    
    print(f"📡 Sende: {cmd.strip()}")
    try:
        dev.write(ENDPOINT_OUT, cmd.encode('ascii'), timeout=1000)
        time.sleep(0.3) # Kurze Pause zur Verarbeitung
        
        # Versuche eine Antwort zu lesen (nur bei Query-Befehlen wie '?' nötig, aber wir prüfen es immer)
        try:
            res = dev.read(ENDPOINT_IN, 128, timeout=500)
            if res:
                response_str = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in res])
                print(f"📥 Antwort: {response_str.strip()}")
                return response_str
        except usb.core.USBError:
            # Timeout ist bei Einstellungsbefehlen ohne '?' normal
            pass
            
    except usb.core.USBError as e:
        print(f"❌ Fehler beim Senden von '{cmd.strip()}': {e}")
    return None

def main():
    print("--- 🔬 Abestop DS1102 Remote Control Test ---")
    
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        print("✅ Verbindung hergestellt.")

        # Test 1: Identifikation (als Basis-Check)
        send_command(dev, "*IDN?")

        # Test 2: AUTOSET (Sollte das 1KHz Signal auf CH1 fangen)
        input("\nDrücke ENTER für AUTOSET (Beobachte das Oszi-Display)...")
        send_command(dev, ":AUTOSet")
        
        # Test 3: STOP / RUNU (Display einfrieren)
        input("\nDrücke ENTER für STOP (Display sollte einfrieren)...")
        send_command(dev, ":STOP")
        
        input("\nDrücke ENTER für RUN (Display sollte weiterlaufen)...")
        send_command(dev, ":RUN")

        # Test 4: Messwert abfragen (Frequenz auf CH1)
        # Viele Owon/Abestop nutzen MEASure:FREQuency?
        input("\nDrücke ENTER für Frequenzmessung (Query)...")
        send_command(dev, ":MEASure:FREQuency? CH1")

        print("\n--- Test abgeschlossen ---")

    except Exception as e:
        print(f"💥 Fehler: {e}")

if __name__ == "__main__":
    main()
