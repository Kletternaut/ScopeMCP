import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234

def list_endpoints():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    for cfg in dev:
        for intf in cfg:
            for ep in intf:
                print(f"Interface {intf.bInterfaceNumber}, Endpoint 0x{ep.bEndpointAddress:02x}, Attr: {ep.bmAttributes}")

if __name__ == "__main__":
    list_endpoints()
