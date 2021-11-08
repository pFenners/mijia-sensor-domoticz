import urllib.request
import base64
import time
import btlewrap
from btlewrap.base import BluetoothBackendException
from mijia.mitemp2_bt_poller import MiTemp2BtPoller, \
    MI_HUMIDITY, MI_TEMPERATURE, MI_BATTERY
from mijia.mijia_poller import MijiaPoller, \
    MI_HUMIDITY, MI_TEMPERATURE, MI_BATTERY

# Settings for the domoticz server

# Forum see: http://domoticz.com/forum/viewtopic.php?f=56&t=13306&hilit=mi+flora&start=20#p105255

domoticzserver   = "127.0.0.1:8000"
domoticzusername = ""
domoticzpassword = ""

# So id devices use: sudo hcitool lescan

# Sensor IDs

# Create virtual sensors in dummy hardware
# type temperature & humidity

try:
    import bluepy.btle  # noqa: F401 pylint: disable=unused-import

    BACKEND = btlewrap.BluepyBackend
except ImportError:
    BACKEND = btlewrap.GatttoolBackend


base64string = base64.encodestring(('%s:%s' % (domoticzusername, domoticzpassword)).encode()).decode().replace('\n', '')

def domoticzrequest (url):
  print(url)
  request = urllib.request.Request(url)
  request.add_header("Authorization", "Basic %s" % base64string)
  response = urllib.request.urlopen(request)
  return response.read()

def update(address,idx_temp, version):
    if 1 == version:
        poller = MijiaPoller(address)
    elif 2 == version:
        poller = MiTemp2BtPoller(address, BACKEND)
    else:
        print("Unsupported Mijia sensor version\n")
        return

    loop = 0
    try:
        temp = poller.parameter_value(MI_TEMPERATURE)
    except:
        temp = "Not set"
    
    while loop < 2 and temp == "Not set":
        print("Error reading value retry after 5 seconds...\n")
        time.sleep(5)
        if 1 == version:
            poller = MijiaPoller(address)
        elif 2 == version:
            poller = MiTemp2BtPoller(address, BACKEND)
        loop += 1
        try:
            temp = poller.parameter_value(MI_TEMPERATURE)
        except:
            temp = "Not set"
    
    if temp == "Not set":
        print("Error reading value\n")
        return
    
    global domoticzserver

    print("Mi Sensor: " + address)
    print("Firmware: {}".format(poller.firmware_version()))
    print("Name: {}".format(poller.name()))
    print("Temperature: {}°C".format(poller.parameter_value(MI_TEMPERATURE)))
    print("Humidity: {}%".format(poller.parameter_value(MI_HUMIDITY)))
    print("Battery: {}%".format(poller.parameter_value(MI_BATTERY)))

    val_bat  = "{}".format(poller.parameter_value(MI_BATTERY))
    
    # Update temp
    #val_temp = "{}".format(poller.parameter_value(MI_TEMPERATURE))
    #domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=udevice&idx=" + idx_temp + "&nvalue=0&svalue=" + val_temp + "&battery=" + val_bat)

    # Update humidity
    #val_hum = "{}".format(poller.parameter_value(MI_HUMIDITY))
    #domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=udevice&idx=" + idx_hum + "&svalue=" + val_hum + "&battery=" + val_bat)

	#/json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=TEMP;HUM;HUM_STAT
    val_temp = "{}".format(poller.parameter_value(MI_TEMPERATURE))
    val_hum = "{}".format(poller.parameter_value(MI_HUMIDITY))
    
    val_comfort = "0"
    if float(val_hum) < 40:
        val_comfort = "2"
    elif float(val_hum) <= 70:
        val_comfort = "1"
    elif float(val_hum) > 70:
        val_comfort = "3"
    
    domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=udevice&idx=" + idx_temp + "&nvalue=0&svalue=" + val_temp + ";" + val_hum + ";"+ val_comfort + "&battery=" + val_bat)
	

print("\n1: updating")
update("A4:C1:38:A1:D5:92","752", 2)

update("4C:65:A8:D0:26:D2","753", 1)

update("4C:65:A8:D0:57:2A","754", 1)




