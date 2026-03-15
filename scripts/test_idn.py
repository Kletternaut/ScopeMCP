import usb.core
import usb.util
import sys
import time

# Oszilloskop Identifikation (wie zuvor ermittelt)
VID = 0x5345
PID = 0x1234

def main():
    # 1. Gerät finden
    dev = usb.core.find(idVendor=VID, idProduct=PID)

    if dev is None:
        print("❌ Oszilloskop nicht gefunden. Bitte prüfen, ob es im PC-Mode angeschlossen ist.")
        return

    print(f"✅ Gerät gefunden: {dev.manufacturer} {dev.product}")

    # 2. Treiber-Konfiguration vorbereiten
    try:
        # dev.is_kernel_driver_active ist unter Windows (libusb0) nicht implementiert.
        # Wir versuchen direkt die Konfiguration zu setzen.
        dev.set_configuration()
        print("✅ Kommunikation initialisiert.")
    except Exception as e:
        print(f"ℹ️ Information zur Konfiguration: {e}")
        # Auf Windows ist das oft normal, da libusb0 das Gerät bereits reserviert hat.

    # 3. Endpunkte definieren (Bulk-OUT für Befehle, Bulk-IN für Antworten)
    # Aus unserem vorherigen Scan: 0x01 (OUT), 0x81 (IN)
    endpoint_out = 0x01
    endpoint_in = 0x81

    # 4. Den Standard SCPI Identifikationsbefehl senden
    # Viele Owon/Abestop Geräte nutzen SCPI Befehle, die mit einem Zeilenumbruch enden
    command = "*IDN?\n"
    print(f"📡 Sende Befehl: {command.strip()}")

    try:
        # Sende an Endpoint 0x01
        dev.write(endpoint_out, command.encode('ascii'))
        
        # Kurze Pause für das Gerät zum Verarbeiten
        time.sleep(0.5)

        # Versuche eine Antwort zu lesen von Endpoint 0x81
        # Wir lesen bis zu 100 Bytes
        response = dev.read(endpoint_in, 100, timeout=2000)
        
        # Konvertiere Bytes in String
        response_str = ''.join([chr(b) for b in response])
        print(f"📥 Antwort vom Oszi: {response_str.strip()}")

    except usb.core.USBError as e:
        print(f"❌ Kommunikationsfehler: {e}")
        print("\nHinweis: Wenn ein Timeout auftritt, nutzt das Gerät eventuell ein anderes Protokoll.")

if __name__ == "__main__":
    main()
