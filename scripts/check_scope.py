import usb.core
import usb.util
import sys

# VID und PID laut deinem Gerätemanager
VID = 0x5345
PID = 0x1234

def main():
    # Gerät finden
    dev = usb.core.find(idVendor=VID, idProduct=PID)

    if dev is None:
        print("❌ Oszilloskop wurde nicht gefunden. Prüfe das USB-Kabel.")
        sys.exit(1)

    print(f"✅ Oszilloskop gefunden: {dev.manufacturer} {dev.product}")
    
    try:
        # In Windows ist das Setzen der Konfiguration oft optional oder führt zu Fehlern, 
        # wenn der Treiber (libusb0) das Gerät bereits reserviert hat.
        dev.set_configuration()
        print("✅ Konfiguration gesetzt.")
    except Exception as e:
        print(f"⚠️ Warnung beim Setzen der Konfiguration: {e}")

    # Endpunkte auflisten
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]

    print("\n--- USB Endpunkte ---")
    for ep in intf:
        # Manuelle Zuordnung der Typen
        ep_type_raw = usb.util.endpoint_type(ep.bmAttributes)
        types = {
            0x00: "CONTROL",
            0x01: "ISOCHRONOUS",
            0x02: "BULK",
            0x03: "INTERRUPT"
        }
        ep_type = types.get(ep_type_raw, f"UNKNOWN ({ep_type_raw})")
        direction = "IN  (⬅️)" if usb.util.endpoint_direction(ep.bEndpointAddress) == 0x80 else "OUT (➡️)"
        print(f"Endpoint: 0x{ep.bEndpointAddress:02x} | {ep_type:10} | {direction}")

if __name__ == "__main__":
    main()
