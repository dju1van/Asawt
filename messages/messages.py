START_MESSAGE = """
     ______     ______     ______     __     __     ______  
    /\  __ \   /\  ___\   /\  __ \   /\ \  _ \ \   /\__  _\ 
    \ \  __ \  \ \___  \  \ \  __ \  \ \ \/ ".\ \  \/_/\ \/ 
     \ \_\ \_\  \/\_____\  \ \_\ \_\  \ \__/".~\_\    \ \_\ 
      \/_/\/_/   \/_____/   \/_/\/_/   \/_/   \/_/     \/_/ 
                                                        
    Welcome to asawt. Automated security analysis WiFi tool.
            For help type 'help'. Good luck! :)\n"""

HELP_MESSAGES = {
    "GENERAL_HELP": """Asawt(automated security analysis WiFi tool) is a set of scripts for 
automation of wireless network penetration tools like aircrack-ng, airodump-ng etc.

 - for description of specific script type: help SCRIPT_NAME
 - to run a specific script/attack type: run SCRIPT_NAME

Other commands that might help:
    help    h   - displays this menu
    exit    q   - quit tool
    clear   cls - clear terminal
    list    ls  - list all scripts/attacks\n""",

    "AUTO_DEAUTH_HELP": """
+-------------------------------------------------------------------------------------------+
|AUTO_DEAUTH                                                                                |
+-------------------------------------------------------------------------------------------+
|run with: run auto_deauth                                                                  |
|                                                                                           |
|Scans nearby wireless networks and displays available APs(access points) along with        |
|connected active clients. Allows you to select a specific network and a client to          |
|target with a deauthentication attack, disconnecting them from the network.                |
|                                                                                           |
|Supports both broadcast attacks (all clients) and single client targeting.                 |
+-------------------------------------------------------------------------------------------+\n""",

    "AUTO_CRACK_HELP": """
+-------------------------------------------------------------------------------------------+
|AUTO_CRACK                                                                                 |
+-------------------------------------------------------------------------------------------+
|run with: run auto_crack                                                                   |
|                                                                                           |
|Scans nearby wireless networks and displays available APs(access points) along with        |
|connected active clients. Then attempts to capture a WPA/WPA2 handshake by deauthenticating|
|a client. After successfully capturing the handshake, it uses a wordlist to try and crack  |
|the password.                                                                              |
|                                                                                           |
|Requires a valid wordlist for cracking.                                                    |
+-------------------------------------------------------------------------------------------+\n"""
}

ERROR = "Command not found.\n"