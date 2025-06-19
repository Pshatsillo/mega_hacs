"""Constants for the Mega integration by Petros integration."""
import datetime
import re

DOMAIN = "mega_petros"
IP_FOR_ENTITY = "ip_for_entity"
SCAN_INTERVAL = datetime.timedelta(seconds=10)
PATT_FW = re.compile(r'fw:\s(.+?)\)')