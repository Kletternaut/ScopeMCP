import pyshark
import binascii

def look_for_any_header(file_path):
    print(f"\n--- Checking for headers in {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    
    found_any = False
    
    for packet in cap:
        try:
            # Join all layer data fields if possible
            raw = None
            if 'DATA' in packet:
                raw = packet.data.data
            elif 'USB' in packet:
                raw = packet.usb.get_field('capdata')
            
            if raw:
                data = binascii.unhexlify(raw.replace(':', ''))
                
                # Check for SPB (53 50 42) or other common markers like DS Wave (44 53 20 57 61 76 65)
                if b'SPB' in data:
                    print(f"[Packet {packet.number}] Found SPB!")
                    found_any = True
                if b'DS Wave' in data:
                    print(f"[Packet {packet.number}] Found 'DS Wave' marker!")
                    found_any = True
                
                # Check for SCPI-like commands
                if 2 < len(data) < 64:
                    try:
                        decoded = data.decode('ascii', errors='ignore').strip()
                        if any(c in decoded for c in [':', '?', 'START']):
                            print(f"[Packet {packet.number}] CMD found: {decoded}")
                    except:
                        pass
                        
        except Exception as e:
            pass
            
    if not found_any:
        print("    No markers found in the first layer scan.")
    cap.close()

if __name__ == "__main__":
    look_for_any_header(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
    look_for_any_header(r'c:\Users\Tom\Oszi\analysis\test2.pcapng')
