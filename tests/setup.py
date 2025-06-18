import subprocess
import sys
import re
from logger import logger


# Funkcija za dohvacanje mreznih sucelja
def get_wireless_interfaces():
    try:
        # Poziva 'iw dev' za ispis svih mrežnih sucelja
        output = subprocess.check_output(["iw", "dev"], text=True)

    except subprocess.CalledProcessError:
        print("Failed to run 'iw dev'.")
        logger.error("Failed to run 'iw dev'.")
        sys.exit(1)

    # Uzima sva imena mreznih sucelja iz ispisa
    interfaces = re.findall(r'Interface\s+([\w.-]+)', output)

    return interfaces


# Funkcija za odredivanje spodrzava li sucelje monitor mod
def get_interface_info(interface):
    try:
        # Poziva 'udevadm info --query=all --path=[putanja sucelja]' za ispis metapodataka navedenog sucelja
        output = subprocess.check_output(["udevadm", "info", "--query=all", f"--path=/sys/class/net/{interface}"], text=True)

    except subprocess.CalledProcessError:
        return None

    # Trazi se bilo kakav ispis zapis 'usb' medu metapodacima i zapisuje se rezultat u is_usb kao boolean
    is_usb = "usb" in output.lower()
    # Vraca mapu s informacijama o sucelju
    return {"interface": interface, "is_usb": is_usb}


# Funkcija koja provjerava podrzava li zadano sucelje monitor mod
def supports_monitor_mode(interface):
    phy = get_phy_for_interface(interface)

    if not phy:
        return False

    try:
        # Poziva 'iw phy [phy_name] info'
        output = subprocess.check_output(["iw", "phy", phy, "info"], text=True)
        match = re.search(r"Supported interface modes:(.*?)(\n\s*\n|\Z)", output, re.DOTALL)

        if match:
            return "monitor" in match.group(1).lower()

    except subprocess.CalledProcessError:
        pass

    return False


# Funkcija koja vraca uredaj fizickog sloja vezan uz dano sucelje
def get_phy_for_interface(interface):
    try:
        # Ispis fizickih uredaja i sucelja
        output = subprocess.check_output(["iw", "dev"], text=True)
        # Pomocna varijabla koja prati phy trazenog sucelja
        current_phy = None

        for line in output.splitlines():
            line = line.strip()

            # Ako linija pocinje sa phy# i jos nije nasao trazeno sucelje
            # Azurira phy liniju
            if line.startswith("phy#"):
                phy_number = line.replace("phy#", "")
                current_phy = f"phy{phy_number}"
            # Ako pronade trazeno sucelje vraca pripadni phy
            elif line.startswith("Interface") and interface in line:
                return current_phy

    except subprocess.CalledProcessError:
        pass

    return None


# Funkcija provjerava je li sucelje u monitor modu
def is_in_monitor_mode(interface):
    try:
        # Poziva 'iw dev [mrezno sucelje] info'
        output = subprocess.check_output(["iw", "dev", interface, "info"], text=True)
        match = re.search(r"\btype\s+(\w+)", output)
        # Ako je monitor mod ukljucen vraca Ture
        if match and match.group(1).lower() == "monitor":
            return True
        
    except subprocess.CalledProcessError:
        pass

    return False


# Pokreni monitor mod za dano sucelje
def enable_monitor_mode(interface):
    try:
        # Zavrsava procese koji smetaju
        subprocess.run(["airmon-ng", "check", "kill"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Pokrece monitor mod pomocu airmon-ng
        subprocess.run(["airmon-ng", "start", interface], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Monitor mode enabled on: {interface}")
        logger.info(f"Monitor mode enabled on: {interface}")

    except subprocess.CalledProcessError:
        print(f"Failed to enable monitor mode on: {interface}")
        logger.error(f"Failed to enable monitor mode on: {interface}")
        sys.exit(1)


# Funkcija za vracanje iz monitor u managed mod
def disable_monitor_mode(interface):
    try:
        # Gasi monitor mod pomocu airmon-ng
        subprocess.run(["airmon-ng", "stop", interface], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Monitor mode disabled on: {interface}")
        logger.info(f"Monitor mode disabled on: {interface}")

    except subprocess.CalledProcessError:
        print(f"Failed to disable monitor mode on: {interface}")
        logger.errorprint(f"Failed to disable monitor mode on: {interface}")
        sys.exit(1)


# Funkcija vraca prvo sucelje koje je u monitor modu
def get_monitor_interface():
    for interface in get_wireless_interfaces():
        if is_in_monitor_mode(interface):

            return interface

    return None


def main():
    # Dohvaca sva bezicna sucelja
    interfaces = get_wireless_interfaces()

    # Ako nema bezicnih sucelja, obavijestava korisnika
    if not interfaces:
        print("No wireless interfaces found.")
        logger.error("No wireless interfaces found.")
        sys.exit(1)

    # Ako postoji sucelje u monitor modu, vraca ga
    for i in interfaces:
        if is_in_monitor_mode(i):
            print(f"Interface {i} is already in monitor mode.")
            logger.info(f"Interface {i} is already in monitor mode.")

            return i

    candidates = []

    # Trazi sva bezicna sucelja koja podrzavaju monitor mod
    for i in interfaces:
        info = get_interface_info(i)

        if info and supports_monitor_mode(i):
            candidates.append(info)

    # Ako ne postoje sucelja koja podrzavaju monitor mod, obavijesti korisnika
    if not candidates:
        print("No interfaces that support monitor mode found.")
        logger.errpr("No interfaces that support monitor mode found.")
        sys.exit(1)

    # Preferira eksterne mrezne kartice
    for candidate in candidates:
        if candidate["is_usb"]:
            enable_monitor_mode(candidate["interface"])

            return get_monitor_interface()
    
    enable_monitor_mode(candidates[0]["interface"])

    return get_monitor_interface()


if __name__ == "__main__":
    main()