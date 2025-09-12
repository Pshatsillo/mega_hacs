"""Constants for the Mega integration by Petros integration."""
import datetime
import re

DOMAIN = "mega_petros"
CUSTOM_CONFIG = "custom_config"
IP_FOR_ENTITY = "ip_for_entity"
SCAN_INTERVAL = datetime.timedelta(seconds=10)
PATT_FW = re.compile(r'fw:\s(.+?)\)')
SENSORS_JSON = f"https://raw.githubusercontent.com/Pshatsillo/openhab2MegadBinding/refs/heads/jsons/sensors.json"