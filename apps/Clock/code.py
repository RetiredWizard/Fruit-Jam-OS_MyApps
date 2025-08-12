from time import localtime
from supervisor import reload
from pydos_wifi import Pydos_wifi

if Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID') is None:
    import setenv

if localtime()[0] < 2025:
    import getdate

import clock
reload()

