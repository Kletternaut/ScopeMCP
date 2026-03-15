import pyshark
import struct
import binascii

def find_spb_in_test2(file_path):
    print(f"\n--- Searching SPB in {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    
    last_cmd = "None"
    
    for packet in cap:
        try:
            raw = None
            if 'DATA' in packet:
                raw = packet.data.data
            elif 'USB' in packet:
                raw = packet.usb.get_field('capdata')
            
            if not raw: continue
            
            data = binascii.unhexlify(raw.replace(':', ''))
            
            if b'SPB' in data:
                print(f"\n[FRAME {packet.number}] FOUND SPB!")
                print(f"    - Preceding Cmd: {last_cmd}")
                print(f"    - Packet Size:   {len(data)}")
                
                idx = data.find(b'SPB')
                # Check offset 1076
                # Header usually starts with SPB...
                # If SPB is at index 'idx', then frequency is at idx + 1076
                target = idx + 1076
                if len(data) >= target + 4:
                    freq_bytes = data[target:target+4]
                    freq = struct.unpack('<f', freq_bytes)[0]
                    print(f"    - Frequency at offset 1076: {freq} Hz")
                    print(f"    - Bytes at 1076: {freq_bytes.hex(' ')}")
                
                # Show first 64 bytes of the SPB block
                print(f"    - Header Hex: {data[idx:idx+64].hex(' ')}")
                
                # Check if there is another SPB?
                if data.find(b'SPB', idx + 1) != -1:
                     print("    - Note: Multiple SPB found in one packet!")

            # Track commands
            if 2 < len(data) < 100:
                try:
                    s = data.decode('ascii', errors='ignore').strip()
                    if any(c in s for c in [':', '?', 'START']):
                        last_cmd = s
                except: pass
                
        except: pass
    cap.close()

if __name__ == "__main__":
    find_spb_in_test2(r'c:\Users\Tom\Oszi\analysis\test2.pcapng')
