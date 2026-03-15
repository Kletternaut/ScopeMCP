import usb.core
import usb.util
import sys
import time

# Oszilloskop Konfiguration
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def main():
    print("--- 🛠️ Robustes USB-Verbindungs-Skript (Abestop DS1102) ---")
    print("Versuche Verbindung herzustellen, ohne das Interface exklusiv zu sperren...")

    # 1. Gerät finden
    dev = usb.core.find(idVendor=VID, idProduct=PID)

    if dev is None:
        print("❌ Gerät nicht gefunden. Prüfe das USB-Kabel.")
        return

    print(f"✅ Gerät erkannt: {dev.manufacturer} {dev.product}")

    try:
        # UNTER WINDOWS (libusb0): 
        # Wir verzichten auf set_configuration() und claim_interface(), 
        # da libusb0 dies oft automatisch beim ersten Read/Write macht.
        
        # Test 1: Identifikation abfragen
        cmd = "*IDN?\n"
        print(f"📡 Sende: {cmd.strip()}")
        
        # Direktes Schreiben ohne vorheriges 'Claim'
        # Wir nutzen einen längeren Timeout für Windows (2000ms)
        dev.write(ENDPOINT_OUT, cmd.encode('ascii'), timeout=2000)
        
        print("⏳ Warte auf Antwort...")
        time.sleep(0.5)

        # Versuch zu lesen
        try:
            response = dev.read(ENDPOINT_IN, 128, timeout=2000)
            if response:
                res_str = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in response])
                print(f"📥 Antwort vom Oszi: {res_str}")
        except usb.core.USBError as e:
            print(f"⚠️ Lesefehler (Timeout oder Busy): {e}")

    except Exception as e:
        print(f"❌ Fehler bei der Kommunikation: {e}")
        print("\nTipp: Wenn 'Access Denied' erscheint, könnte ein Neustart des PCs helfen,")
        print("um den libusb0-Treiberfilter zurückzusetzen.")

if __name__ == "__main__":
    main()
