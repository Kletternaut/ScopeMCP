import usb.core
import usb.util
import time

def find_ds1102():
    print("Suche Owon/Abestop DS1102 (5345:1234)...")
    dev = usb.core.find(idVendor=0x5345, idProduct=0x1234)
    if dev:
        print("GEFUNDEN!")
        print(f"Vendor:  {hex(dev.idVendor)}")
        print(f"Product: {hex(dev.idProduct)}")
        
        # Versuche Name auszulesen
        try:
            print(f"Hersteller: {usb.util.get_string(dev, dev.iManufacturer)}")
            print(f"Produkt:    {usb.util.get_string(dev, dev.iProduct)}")
        except:
            print("Konnte Strings nicht lesen (normal bei libusb0).")
    else:
        print("OSZI NICHT GEFUNDEN.")
    return dev

if __name__ == "__main__":
    find_ds1102()
