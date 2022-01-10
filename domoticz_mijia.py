print("*****************")
import urllib.request
import base64
import time
import sys
from mijia.mijia_poller import MijiaPoller, \
    MI_HUMIDITY, MI_TEMPERATURE, MI_BATTERY

# Settings for the domoticz server

# Forum see: http://domoticz.com/forum/viewtopic.php?f=56&t=13306&hilit=mi+flora&start=20#p105255

domoticzserver   = "127.0.0.1:8080"
domoticzusername = ""
domoticzpassword = ""

# So id devices use: sudo hcitool lescan

# Sensor IDs

# Create virtual sensors in dummy hardware
# type temperature & humidity


#base64string = base64.encodestring(('%s:%s' % (domoticzusername, domoticzpassword)).encode()).decode().replace('\n', '')

base64string = base64.encodebytes(('%s:%s' % (domoticzusername, domoticzpassword)).encode()).decode().replace('\n', '')

def domoticzrequest (url):
    print(url)
    request = urllib.request.Request(url)
    request.add_header("Authorization", "Basic %s" % base64string)
    try:
        response = urllib.request.urlopen(request, timeout=10)
        print("Calling Domoticz")
    except timeout:
        print("[EROOR] Domoticz API Timeout")
        sys.exit(1)
    return response.read()

def update(address,idx_temp):

    poller = MijiaPoller(address)


    loop = 0
    try:
        temp = poller.parameter_value(MI_TEMPERATURE)
    except:
        temp = "Not set"
    
    while loop < 2 and temp == "Not set":
        print("Error reading value retry after 5 seconds...\n")
        time.sleep(5)
        poller = MijiaPoller(address)
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
	

print("\n1: Updating SEV INT")
update("58:2D:34:3B:7C:93","77")
print("\n2: Updating TEMP 2")
update("58:2D:34:3A:53:01","81")
