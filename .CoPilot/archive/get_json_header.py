import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import json
import time

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    dev.write(EP_OUT, cmd.encode('ascii'))

def read_resp(dev, size=16384, timeout=2000):
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return data.tobytes()
    except usb.core.USBError as e:
        print(f"USB Error: {e}")
        return None

def parse_header(header_data):
    if not header_data:
        return None
    try:
        # Die ersten 4 Bytes sind die Länge (Little Endian)
        msg_len = int.from_bytes(header_data[:4], byteorder='little')
        print(f"Header length: {msg_len}")
        json_str = header_data[4:4+msg_len].decode('ascii', errors='replace')
        return json.loads(json_str)
    except Exception as e:
        print(f"Parsing error: {e}")
        print(f"Raw data (first 64 bytes): {header_data[:64].hex()}")
        return None

def main():
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        
        # Manchmal hilft ein kleiner Flush oder ein Reset-Befehl vorab,
        # aber wir versuchen es direkt.
        
        print("Sende :DATA:WAVE:SCREEN:HEAD? ...")
        send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
        
        # Warte kurz auf Antwort
        time.sleep(0.5)
        
        header_raw = read_resp(dev)
        if header_raw:
            header_json = parse_header(header_raw)
            if header_json:
                print("\nKOMPLETTER JSON-INHALT:")
                print(json.dumps(header_json, indent=4))
            else:
                print("Konnte JSON nicht parsen.")
        else:
            print("Keine Antwort vom Gerät erhalten.")

    except Exception as e:
        print(f"Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
