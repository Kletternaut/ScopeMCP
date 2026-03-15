import pyshark
import binascii

def check_raw(file_path):
    print(f"\n--- Raw Check {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    for i, packet in enumerate(cap):
        if i > 1000: break # Safety
        try:
            # Try to find ANY raw data field
            raw = None
            if hasattr(packet, 'usb'):
                # Some versions of pyshark/tshark use different field names
                # Try common ones
                for field in ['capdata', 'data', 'raw_id']:
                   val = packet.usb.get_field(field)
                   if val:
                       raw = val
                       break
            
            if not raw and hasattr(packet, 'data'):
                raw = packet.data.data
                
            if raw:
                raw_bytes = binascii.unhexlify(raw.replace(':', ''))
                if b'SPB' in raw_bytes:
                    print(f"Packet {packet.number}: Found SPB!")
                    print(f"Full Data: {raw_bytes.hex(' ')}")
                if i < 20: # Just show first few to see format
                     print(f"Packet {packet.number} raw: {raw_bytes[:20].hex(' ')} (ASCII: {raw_bytes[:20].decode('ascii', 'ignore')})")
        except:
            pass
    cap.close()

check_raw(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
