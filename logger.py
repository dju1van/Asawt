import logging
import os
from datetime import datetime


# Osigurava direktorij za logove
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# Dohvaca vrijeme u formatu YYYY-MM-DD_hh:mm:ss
timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
log_file = f"asawt_log_{timestamp}.log"
# Dohvaca putanju do log datoteke
log_path = os.path.join(log_dir, log_file)

# Konfiguracija
logger = logging.getLogger("asawt")
logger.setLevel(logging.INFO)

# Sprijecava stavranje duplikata objekta pri ponovnom uvozu
if not logger.handlers:
    file_handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%d-%m-%Y %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)