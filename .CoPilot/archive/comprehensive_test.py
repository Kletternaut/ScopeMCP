import usb.core
import usb.util
import time
import json

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def comprehensive_test():
    print("--- DS1102 COMPREHENSIVE SYSTEM TEST (STABILITY FOCUS) ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    # LibUSB-Win32 Initialization
    try:
        dev.set_configuration()
        usb.util.claim_interface(dev, 0)
    except: pass

    def _clear():
        try:
            while True: dev.read(EP_IN, 4096, timeout=10)
        except: pass

    def send_safe(cmd, wait=0.5):
        _clear()
        dev.write(EP_OUT, f"{cmd}\n")
        time.sleep(wait)

    def get_metadata():
        dev.write(EP_OUT, ":DATA:WAVE:SCREEN:HEAD?\n")
        time.sleep(0.8)
        try:
            raw = dev.read(EP_IN, 8192, timeout=2000)
            if b'{' in raw:
                start = raw.find(b'{')
                end = raw.rfind(b'}') + 1
                return json.loads(raw[start:end].decode('ascii', errors='ignore'))
        except: pass
        return None

    # 1. TEST: Horizontal Scales
    h_scales = ["1ms", "500us", "100ns"]
    print("\n--- TEST A: HORIZONTAL SKALIERUNG ---")
    for s in h_scales:
        print(f"Setze Timebase: {s}...", end=" ", flush=True)
        send_safe(f":HORizontal:SCALe {s}", wait=1.0)
        meta = get_metadata()
        res = meta.get("TIMEBASE") if meta else "TIMEOUT"
        print(f"-> Gelesen: {res}")

    # 2. TEST: Vertical Scales (Reliability Check)
    v_scales = ["500mV", "1V", "2V"]
    print("\n--- TEST B: VERTIKAL SKALIERUNG (CH1) ---")
    for s in v_scales:
        print(f"Setze Volt/Div: {s}...", end=" ", flush=True)
        send_safe(f":CH1:SCALe {s}", wait=1.5) # Länger warten für Relais
        meta = get_metadata()
        res = meta["CHANNEL"][0]["SCALE"] if meta else "TIMEOUT"
        print(f"-> Gelesen: {res}")

    # 3. TEST: Run/Stop State
    print("\n--- TEST C: RUN/STOP STATUS ---")
    states = ["STOP", "RUN"]
    for st in states:
        print(f"Setze Status: {st}...", end=" ", flush=True)
        send_safe(f":{st.lower()}", wait=1.0)
        meta = get_metadata()
        res = meta.get("RUNSTATUS") if meta else "TIMEOUT"
        print(f"-> Gelesen: {res}")

    # 4. TEST: Frequency Measurement (Live)
    print("\n--- TEST D: LIVE MESSWERTE ---")
    meta = get_metadata()
    if meta:
        freq = meta.get("FREQUENCE", "N/A")
        vpp = meta.get("VPP", "N/A")
        print(f"Frequenz: {freq} Hz")
        print(f"Vpp:      {vpp} V")
    else:
        print("Konnte keine Live-Werte lesen.")

    # Reset to normal
    send_safe(":CH1:SCALe 2V", wait=1.0)
    send_safe(":horizon:scale 500us", wait=1.0)
    print("\nTest beendet. Gerät ist in stabilem Zustand.")

if __name__ == "__main__":
    comprehensive_test()
