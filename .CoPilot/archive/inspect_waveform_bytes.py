import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def inspect_waveform_bytes():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Dev nicht gefunden")
        return

    try:
        dev.set_configuration()
    except: pass

    # Buffer leeren
    try:
        while True: dev.read(EP_IN, 4096, timeout=10)
    except: pass

    print("Fordere :DATA:WAVE:SCREEN:CH1? an...")
    dev.write(EP_OUT, ":DATA:WAVE:SCREEN:CH1?\n")
    time.sleep(0.5)
    
    try:
        data_raw = dev.read(EP_IN, 16384, timeout=3000)
        data = bytes(data_raw)
        print(f"Empfangen: {len(data)} Bytes")
        print("\nROHDATEN ANALYSE (Byte-Ebene):")
        
        # Wir untersuchen jetzt einen größeren Bereich, um die Sprungstellen des Rechtecks zu finden
        print("\nSUCHE NACH SIGNAL-SPRÜNGEN (Rechteck-Flanken):")
        last_val = None
        for i in range(4, 1000, 2):
            val = int.from_bytes(data[i:i+2], byteorder='little', signed=True)
            if last_val is not None and abs(val - last_val) > 500:
                print(f"--- FLANKE GEFUNDEN bei Index {i}: {last_val} -> {val} ---")
            last_val = val

        print("\nERSTE 50 SAMPLES (Little Endian 16-bit):")
        vals = [int.from_bytes(data[i:i+2], 'little', signed=True) for i in range(4, 104, 2)]
        print(vals)

    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    inspect_waveform_bytes()
