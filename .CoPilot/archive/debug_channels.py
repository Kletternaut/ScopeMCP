import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time
import struct

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def debug_channel(dev, channel_cmd):
    print(f"\n--- Abfrage: {channel_cmd} ---")
    
    # USB-Buffer leeren (Flush)
    try:
        while True:
            dev.read(EP_IN, 16384, timeout=100)
    except usb.core.USBError:
        pass

    # Befehl senden
    dev.write(EP_OUT, f"{channel_cmd}\r\n".encode('ascii'))
    time.sleep(0.5)

    # Daten lesen
    try:
        data = dev.read(EP_IN, 100000, timeout=5000).tobytes()
        total_len = len(data)
        print(f"Gesamtlänge empfangen: {total_len} Bytes")

        # Hex-Dump der ersten 64 Bytes
        hex_dump = data[:64].hex(' ')
        print(f"Erste 64 Bytes (Hex): {hex_dump}")

        # JSON-Header extrahieren (falls vorhanden)
        if total_len > 4:
            msg_len = int.from_bytes(data[:4], byteorder='little')
            print(f"Längenfeld im Header: {msg_len}")
            
            # Da kein JSON-Header gefunden wurde, interpretieren wir die Daten ab Byte 4 als Samples
            sample_start = 4
            print(f"Versuche Samples ab Byte {sample_start} zu interpretieren (16-bit little-endian)")
            
            # Dekodiere die ersten 20 Samples (16-bit signed little-endian)
            samples_data = data[sample_start:sample_start + 40]
            if len(samples_data) >= 40:
                samples = struct.unpack('<20h', samples_data)
                print(f"Erste 20 Samples: {samples}")
            else:
                print("Nicht genügend Daten für 20 Samples.")

    except usb.core.USBError as e:
        print(f"Fehler beim Lesen: {e}")

def main():
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)

    if dev is None:
        print("Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        
        # Kanal 1
        debug_channel(dev, ":DATA:WAVE:SCREEN:CH1?")
        
        # Kurze Pause
        time.sleep(1)
        
        # Kanal 2
        debug_channel(dev, ":DATA:WAVE:SCREEN:CH2?")

    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
