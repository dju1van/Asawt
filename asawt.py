import os
import sys
from prompt_toolkit import PromptSession
from messages import messages
import glob
sys.path.append(os.path.join(os.path.dirname(__file__), "tests"))
from tests import auto_deauth, auto_crack, setup
from logger import logger


DUMP_FILE = "dump"
CAPTURE_FILE = "capture"


def del_file(file):
    for f in glob.glob(file + "*"):
        try:
            os.remove(f)

        except OSError:
            print(f"Error deleting file {f}.")
            logger.error(f"Error deleting file {f}.")


def main():
    os.system("clear")
    # Otvori prompt session
    session = PromptSession("asawt > ")
    # Pocetni ispis
    print(messages.START_MESSAGE)

    while True:
        try:
            # Uzimaj naredbe sa standardnog ulaza
            command = session.prompt().strip()

        except(EOFError, KeyboardInterrupt):
            break
        
        # Neke osnovne naredbe
        if command in  ["exit", "q"]:
            break

        elif command in ["clear", "cls"]:
            os.system("clear")

        elif command in ["list", "ls"]:
            for sct in ["auto_deauth", "auto_crack"]:
                print(sct)
            
            print()

        elif command.startswith("help "):
            help_arg = command.split(" ", 1)[1]  # Uzmi argument help naredbe

            if help_arg == "auto_deauth":
                print(messages.HELP_MESSAGES.get("AUTO_DEAUTH_HELP"))

            elif help_arg == "auto_crack":
                print(messages.HELP_MESSAGES.get("AUTO_CRACK_HELP"))
                
            else:
                print(messages.ERROR)
        
        elif command in ["help", "h"]:
            print(messages.HELP_MESSAGES.get("GENERAL_HELP"))
        
        elif command.startswith("run "):
            run_arg = command.split(" ", 1)[1]  # Uzmi argument run naredbe

            if run_arg == "auto_deauth":
                # Pokreni auto_deauth skriptu
                interface, bssid, channel, target, timeout = auto_deauth.main()
                print(f"Starting deauth attack on BSSID: {bssid} and CH {channel}")
                logger.info(f"Starting deauth attack on BSSID: {bssid} and CH {channel}")

                if not timeout:
                    print("Deauth attack started. Stop with Ctrl+C")
                    logger.info("Deauth attack started. Stop with Ctrl+C")

                # Zapocinje napad
                auto_deauth.start_deauth(interface, bssid, channel, target, timeout=timeout)

                if timeout:
                    print(f"Attack stopped after {timeout} seconds.")
                    logger.info(f"Attack stopped after {timeout} seconds.")

                print("Attack finished.")
                logger.info("Attack finished.")

                # Brise privremene dump datoteke
                del_file(DUMP_FILE)

                # Iskljucuje monitor mod
                setup.disable_monitor_mode(interface)

            elif run_arg == "auto_crack":
                # Pokreni auto_crack skriptu
                auto_crack.main()

                # Brise privremenih datoteka
                del_file(DUMP_FILE)
                del_file(CAPTURE_FILE)

            else:
                print(messages.ERROR)
        
        elif len(command) != 0:
            print(messages.ERROR)


if __name__ == "__main__":
    main()