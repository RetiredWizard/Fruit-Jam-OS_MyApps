import json
import board
import displayio
import time
import terminalio
from os import getenv,uname
from sys import implementation
from supervisor import runtime
from adafruit_datetime import datetime,timedelta
from adafruit_display_text import bitmap_label as label
from adafruit_display_text.scrolling_label import ScrollingLabel
from adafruit_bitmap_font import bitmap_font
import adafruit_pathlib as pathlib
from pydos_wifi import Pydos_wifi
try:
    from pydos_ui import Pydos_ui
    from pydos_ui import input
    Pydos_display = ('display' in dir(Pydos_ui))
except:
    Pydos_display = False

def brightness(color,adj):
    mask = 0xf
    newcolor = 0x0
    for i in range(6):
        newcolor |= min(mask,max(0,(color & mask) + adj)) & mask
        adj = adj << 4
        mask = mask << 4
    return newcolor

try:
    type(envVars)
except:
    envVars = {}
    passedIn = ""

if '_display' in envVars.keys():
    display = envVars['_display']
elif Pydos_display:
    display = Pydos_ui.display
elif 'display' in dir(runtime):
    display = runtime.display
elif 'DISPLAY' in dir(board):
    display = board.DISPLAY
else:
    try:
        import matrix
        display = matrix.envVars['_display']
    except:
        try:
            import framebufferio
            import dotclockframebuffer
        except:
            try:
                import adafruit_ili9341
            except:
                import framebufferio
                import picodvi

        displayio.release_displays()

        if 'TFT_PINS' in dir(board):
            sWdth = getenv('CIRCUITPY_DISPLAY_WIDTH')
            if sWdth == None:
                if board.board_id == "makerfabs_tft7":
                    sWdth = input("What is the resolution Width of the touch screen? (1024/800/...): ")
                else:
                    sWdth = board.TFT_TIMINGS['width']
                if 'updateTOML' in dir(Pydos_ui):
                    Pydos_ui.updateTOML("CIRCUITPY_DISPLAY_WIDTH",str(sWdth))

            if sWdth == 1024 and "TFT_TIMINGS1024" in dir(board):
                disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS1024)
            else:
                disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
            display=framebufferio.FramebufferDisplay(disp_bus)

        else:
            try:
                type(adafruit_ili9341)
                if 'SPI' in dir(board):
                    spi = board.SPI()
                else:
                    spi = busio.SPI(clock=board.SCK,MOSI=board.MOSI,MISO=board.MISO)
                disp_bus=displayio.FourWire(spi,command=board.D10,chip_select=board.D9, \
                    reset=board.D6)
                display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240)
            except:
                # DVI Sock
                fb = picodvi.Framebuffer(320,240,clk_dp=board.GP14, clk_dn=board.GP15, \
                    red_dp=board.GP12, red_dn=board.GP13,green_dp=board.GP18, \
                    green_dn=board.GP19,blue_dp=board.GP16, blue_dn=board.GP17,color_depth=8)
                display=framebufferio.FramebufferDisplay(fb)

print("Connecting to %s" % Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID'))

if Pydos_wifi.connect(Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID'), Pydos_wifi.getenv('CIRCUITPY_WIFI_PASSWORD')):
    print("Connected to %s!" % Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID'))
else:
    print("Problem connecting to  %s!" % Pydos_wifi.getenv('CIRCUITPY_WIFI_SSID'))
print("My IP address is", Pydos_wifi.ipaddress)

print("***Internet Clock*** Press 'Q' to exit")

headers = {"user-agent": "CircuitPython@"+implementation.name.lower()+uname()[2]}

displayscale = max(1,min(round(display.height/64),round(display.width/128)))
display.auto_refresh = False

screen = displayio.Group()
#font = terminalio.FONT
font = bitmap_font.load_font("fonts/ter-u12n.bdf")

displaydate = label.Label(font,text="      /  /    ",color=0x008888)
displaydate.x = 20*displayscale
displaydate.y = 5*displayscale
displaydate.scale = displayscale

displaytime = label.Label(font,text = " 0:00 AM",color=0x008888)
displaytime.x = 38*displayscale
displaytime.y = 15*displayscale
displaytime.scale = displayscale

weather = ScrollingLabel(font, text=" ", max_characters=21, animate_time=0.2,color=0x111188)
weather.x = 0
weather.y = 30*displayscale
weather.scale = displayscale

temperature = label.Label(font,text="   "+chr(176)+"F",color=0x888800)
temperature.x = 2*displayscale
temperature.y = 45*displayscale
temperature.scale = displayscale

temperature2 = label.Label(font,text="   "+chr(176)+"F",color=0x888800)
temperature2.x = 2*displayscale
temperature2.y = 55*displayscale
temperature2.scale = displayscale

screen.append(displaydate)
screen.append(displaytime)
screen.append(weather)
screen.append(temperature)
screen.append(temperature2)

# optional configuration file for speaker/headphone setting, check current and root directory
launcher_config = {}
if pathlib.Path("launcher.conf.json").exists():
    with open("launcher.conf.json", "r") as f:
        launcher_config = json.load(f)
elif pathlib.Path("/launcher.conf.json").exists():
    with open("/launcher.conf.json", "r") as f:
        launcher_config = json.load(f)
print(launcher_config)
if 'inetclock' in launcher_config:
    launcher_config = launcher_config['inetclock']

if 'weatherunderground' in launcher_config:
    WU_stationID = launcher_config['weatherunderground'].get('stationID', 'KMABOSTO365')
    WU_stationLbl = launcher_config['weatherunderground'].get('stationLbl', 'Boston')
else:
    WU_stationID = 'KMABOSTO365'
    WU_stationLbl = 'Boston'

if 'weathergov' in launcher_config:
    WG_stationID1 = launcher_config['weathergov'].get('stationID1', 'KBOS')
    WG_stationLbl1 = launcher_config['weathergov'].get('stationLbl1', 'Logan')
    WG_stationID2 = launcher_config['weathergov'].get('stationID2', 'KORH')
    WG_stationLbl2 = launcher_config['weathergov'].get('stationLbl2', 'Worcester')
    WG_stationID3 = launcher_config['weathergov'].get('stationID3', 'KOWD')
    WG_stationLbl3 = launcher_config['weathergov'].get('stationLbl3', 'Norwood')
    WG_lat = launcher_config['weathergov'].get('lat', 42.3555)
    WG_lon = launcher_config['weathergov'].get('lon', -71.0565)
else:
    WG_stationID1 = 'KBOS'
    WG_stationLbl1 = 'Logan'
    WG_stationID2 = 'KORH'
    WG_stationLbl2 = 'Worcester'
    WG_stationID3 = 'KOWD'
    WG_stationLbl3 = 'Norwood'
    WG_lat = 42.3555
    WG_lon = -71.0565

_WG_URL = f"https://api.weather.gov/points/{WG_lat},{WG_lon}"
response = Pydos_wifi.get(_WG_URL,headers,True)
json_response = Pydos_wifi.json()
if 'properties' not in json_response:
    print("Weather.gov API error, using default weather URL")
    _URL = "https://api.weather.gov/gridpoints/BOX/70,76/forecast"
else:
    _URL = json_response['properties']['forecast']

try:
    setbright = int(passedIn)
except:
    if 'brightness' in launcher_config:
        setbright = int(launcher_config['brightness'])
    else:
        setbright = 0
    
if setbright != 0:
    displaydate.color = brightness(displaydate.color,setbright)
    displaytime.color = brightness(displaytime.color,setbright)
    weather.color = brightness(weather.color,setbright)
    temperature.color = brightness(temperature.color,setbright)
    temperature2.color = brightness(temperature2.color,setbright)

display.root_group = screen

cmnd = ""
seconds = -1
minutes = -1
hours = -1
temp = -9999
temp2 = -9999
temp3 = -9999
temp3b = -9999
temptimer = time.time() - 600
temppointer = 0
while cmnd.upper() != "Q":
    if Pydos_ui.serial_bytes_available():
        cmnd = Pydos_ui.read_keyboard(1)
        print(cmnd, end="", sep="")
        if cmnd in "qQ":
            break
        elif cmnd in "+-":
            adj = int(cmnd+'1')
            displaydate.color = brightness(displaydate.color,adj)
            displaytime.color = brightness(displaytime.color,adj)
            weather.color = brightness(weather.color,adj)
            temperature.color = brightness(temperature.color,adj)
            temperature2.color = brightness(temperature2.color,adj)
        elif cmnd == ".":
            displaydate.color=0x008888
            displaytime.color=0x008888
            weather.color=0x111188
            temperature.color=0x888800
            temperature2.color=0x888800

    #if seconds != time.localtime()[5]:
    if minutes != time.localtime()[4]:
        seconds = time.localtime()[5]
        minutes = time.localtime()[4]

        if hours != time.localtime()[3]:
            hours = time.localtime()[3]

            response = Pydos_wifi.get(_URL,headers,True)
            json_response = Pydos_wifi.json()
            if 'properties' not in json_response:
                hours = -1
            else:
                weather.text = json_response['properties']['periods'][0]['detailedForecast']+'...'+' '*5

        i = time.localtime()[6]*3
        displaydate.text = f'{"MonTueWedThuFriSatSun"[i:i+3]} {time.localtime()[1]}/{time.localtime()[2]:02}/{time.localtime()[0]:04}'
        #displaytime.text = f'{time.localtime()[3]%12:2}:{minutes:02}:{seconds:02} {['AM','PM'][time.localtime()[3]//12]}'
        hr = time.localtime()[3]%12 
        displaytime.text = f'{(hr if hr != 0 else 12):2}:{minutes:02} {['AM','PM'][time.localtime()[3]//12]}'

    weather.update()
    display.refresh()

    if time.time()-temptimer >= 600:
        temptimer = time.time()

        newest_obs = datetime.fromisoformat("2000-01-01T00:00:00Z")
        temp3 = -9999
        temp3b = -9999
        search_string = f',{{"stationID":"{WU_stationID}","tz":"'
        search_stringb = '","obsTimeUtc":"'
        search_string1 = '"pressureMax"'
        search_string2 = '"obsTimeLocal":"'
        search_string3 = '"tempAvg":'
        search_string4 = ['"windchillAvg":','"heatindexAvg":']
        response = Pydos_wifi.get(f"https://www.wunderground.com/dashboard/pws/{WU_stationID}",headers)

        response_window = []
        iKount = 0
        maxKount = 80000
        for _ in range(4):
            response_window.append(Pydos_wifi.next(256))
            if len(response_window[-1]) != 256:
                iKount = maxKount - 1
                break

        ltemp = -1
        
        while iKount<maxKount:
            iKount +=1
            if iKount % 10 == 0:
                print(".",end="")

            found_window = str(b''.join(response_window))

            ltemp = found_window.find(search_string)
            if ltemp != -1:
                ltemp += len(search_string)
                ltemp2 = found_window[ltemp:].find(search_stringb)
                if ltemp2 == -1:
                    ltemp = -1
                else:
                    ltemp += (ltemp2 + len(search_stringb))
                
            if ltemp != -1:
                #print(ltemp,len(found_window),': ',end="")
                if found_window[ltemp:].find(search_string1) == -1:
                    #print('incomplete window')
                    ltemp = -1
                else:
                    ltemp_end = found_window[ltemp:].find('"')
                    #print(ltemp,ltemp_end,found_window[ltemp:])
                    #try:
                    test = datetime.fromisoformat(found_window[ltemp:ltemp+ltemp_end])
                    if test > newest_obs:
                        timediff = (datetime.fromtimestamp(time.time()) - datetime.fromtimestamp(test.timestamp())).total_seconds()
                        timediff += 14400
                        if timediff < 0:
                            timediff += 3600
                        if timediff < 900:
                            print("found observation date",test)
                            #print(found_window)
                            #print('---------------------------------------------------------------------')
                            newest_obs = test
                            ltemp = ltemp+found_window[ltemp:].find(search_string3)+len(search_string3)
                            ltemp_end = found_window[ltemp:].find(',')
                            print(f'local temperature: {found_window[ltemp:ltemp+ltemp_end]}',end=" ")
                            temp3 = eval(found_window[ltemp:ltemp+ltemp_end])
                            print(temp3)
                            ltemp = ltemp+found_window[ltemp:].find(search_string4[0 if temp3 < 60 else 1])+len(search_string4[0 if temp3 < 60 else 1])
                            print(ltemp,end=" ")
                            ltemp_end = found_window[ltemp:].find(',')
                            print(ltemp_end,end=" ")
                            print(f'Feels like: {found_window[ltemp:ltemp+ltemp_end]}')
                            temp3b = eval(found_window[ltemp:ltemp+ltemp_end])
                    #except:
                    #    print('Red herring')
                    
            
            if iKount<maxKount:
                for i in range(3):
                    response_window[i] = response_window[i+1]
                try:
                    response_window[3] = Pydos_wifi.next(256)
                    if len(response_window[3]) != 256:
                        print('X',end="")
                        #iKount=maxKount
                except:
                    print('X',end="")
                    #iKount=maxKount
                    break

        print("*\n",iKount)
        
        response = Pydos_wifi.get(f'https://api.weather.gov/stations/{WG_stationID1}/observations/latest',headers,True)
        json_response = Pydos_wifi.json()
        if 'properties' not in json_response or json_response['properties']['temperature']['value'] == None:
            temp = -9999
            temperature.text = f'{WG_stationLbl1}: Not Avail'
        else:
            temp = json_response['properties']['temperature']['value']*9/5 + 32
            temperature.text = f'{WG_stationLbl1}: {temp:.0f}{chr(176)}F'

        response = Pydos_wifi.get(f'https://api.weather.gov/stations/{WG_stationID2}/observations/latest',headers,True)
        json_response = Pydos_wifi.json()
        if 'properties' not in json_response or json_response['properties']['temperature']['value'] == None:
            temp2 = -9999
            temperature2.text = f'{WG_stationLbl2}: Not Avail'
        else:
            temp2 = json_response['properties']['temperature']['value']*9/5 + 32
            temperature2.text = f'{WG_stationLbl2}: {temp2:.0f}{chr(176)}F'

        if temp == -9999 or temp2 == -9999:
            response = Pydos_wifi.get(f'https://api.weather.gov/stations/{WG_stationID3}/observations/latest',headers,True)
            json_response = Pydos_wifi.json()
            if 'properties' not in json_response or json_response['properties']['temperature']['value'] == None:
                temp = -9999
            else:
                if temp == -9999:
                    temp = json_response['properties']['temperature']['value']*9/5 + 32
                    temperature.text = f'{WG_stationLbl3}: {temp:.0f}{chr(176)}F'
                elif temp2 == -9999:
                    temp = json_response['properties']['temperature']['value']*9/5 + 32
                    temperature2.text = f'{WG_stationLbl3}: {temp:.0f}{chr(176)}F'

        if temp3 != -9999:
            temperature2.text = f'{WU_stationLbl}: {temp3:.0f}{chr(176)}F'
            if temp3b != -9999:
                temperature2.text += f'/{temp3b:.0f}{chr(176)}F'

if cmnd.upper() == "Q":
    envVars['errorlevel'] = 999
Pydos_wifi.close()
del json_response
del response_window
screen.pop()
screen.pop()
screen.pop()
screen.pop()
screen.pop()
display.auto_refresh = True
display.root_group = displayio.CIRCUITPYTHON_TERMINAL

