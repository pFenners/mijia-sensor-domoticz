""""
Read data from Xiaomi Mijia Bluetooth Temp & Humidity sensor.

Reading from the sensor is handled by the command line tool "gatttool" that
is part of bluez on Linux.
No other operating systems are supported at the moment
"""

from datetime import datetime, timedelta
from threading import Lock, current_thread
import re
from subprocess import PIPE, Popen, TimeoutExpired
import logging
import time
import signal
import os

#from gattlib import GATTRequester

MI_TEMPERATURE = "temperature"
MI_HUMIDITY = "humidity"
MI_BATTERY = "battery"

#logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

LOCK = Lock()


def write_readnotif_ble(mac, handle, value, retries=3, timeout=20, adapter='hci0'):
    """
    Write to a BLE address

    @param: mac - MAC address in format XX:XX:XX:XX:XX:XX
    @param: handle - BLE characteristics handle in format 0xXX
    @param: value - value to write to the given handle
    @param: timeout - timeout in seconds
    """

    global LOCK
    attempt = 0
    delay = 10
    LOGGER.debug("Enter write_readnotif_ble (%s)", current_thread())

    while attempt <= retries:
        cmd = "gatttool --device={} --char-write-req -a {} -n {} --adapter={} --listen".format(mac,
                                                                                    handle,
                                                                                    value,
                                                                                    adapter)
        with LOCK:
            LOGGER.debug("Created lock in thread %s",
                         current_thread())
            LOGGER.debug("Running gatttool with a timeout of %s",
                         timeout)

            with Popen(cmd,
                       shell=True,
                       stdout=PIPE,
                       preexec_fn=os.setsid) as process:
                try:
                    result = process.communicate(timeout=timeout)[0]
                    LOGGER.debug("Finished gatttool")
                except TimeoutExpired:
                    # send signal to the process group
                    os.killpg(process.pid, signal.SIGINT)
                    result = process.communicate()[0]
                    LOGGER.debug("Killed hanging gatttool")

        LOGGER.debug("Released lock in thread %s", current_thread())

        result = result.decode("utf-8").strip(' \n\t')
        LOGGER.debug("Got %s from gatttool", result)
        # Parse the output
        res = re.search("( [0-9a-fA-F][0-9a-fA-F])+", result)
        if res:
            LOGGER.debug(
                "Exit write_readnotif_ble with result (%s)", current_thread())
                
            return [int(x, 16) for x in res.group(0).split()]

        attempt += 1
        LOGGER.debug("Waiting for %s seconds before retrying", delay)
        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    LOGGER.debug("Exit write_readnotif_ble, no data (%s)", current_thread())
    return None


def read_ble(mac, handle, retries=3, timeout=20, adapter='hci0'):
    """
    Read from a BLE address

    @param: mac - MAC address in format XX:XX:XX:XX:XX:XX
    @param: handle - BLE characteristics handle in format 0xXX
    @param: timeout - timeout in seconds
    """

    global LOCK
    attempt = 0
    delay = 10
    LOGGER.debug("Enter read_ble (%s)", current_thread())

    while attempt <= retries:
        cmd = "gatttool --device={} --char-read -a {} --adapter={}".format(mac,
                                                                         handle,
                                                                         adapter)
        with LOCK:
            LOGGER.debug("Created lock in thread %s",
                         current_thread())
            LOGGER.debug("Running gatttool with a timeout of %s",
                         timeout)

            with Popen(cmd,
                       shell=True,
                       stdout=PIPE,
                       preexec_fn=os.setsid) as process:
                try:
                    result = process.communicate(timeout=timeout)[0]
                    LOGGER.debug("Finished gatttool")
                except TimeoutExpired:
                    # send signal to the process group
                    os.killpg(process.pid, signal.SIGINT)
                    result = process.communicate()[0]
                    LOGGER.debug("Killed hanging gatttool")

        LOGGER.debug("Released lock in thread %s", current_thread())

        result = result.decode("utf-8").strip(' \n\t')
        LOGGER.debug("Got %s from gatttool", result)
        # Parse the output
        res = re.search("( [0-9a-fA-F][0-9a-fA-F])+", result)
        if res:
            LOGGER.debug(
                "Exit read_ble with result (%s)", current_thread())
            return [int(x, 16) for x in res.group(0).split()]

        attempt += 1
        LOGGER.debug("Waiting for %s seconds before retrying", delay)
        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    LOGGER.debug("Exit read_ble, no data (%s)", current_thread())
    return None


class MijiaPoller(object):
    """"
    A class to read data from Xiaomi Mijia Bluetooth sensors.
    """

    def __init__(self, mac, cache_timeout=600, retries=3, adapter='hci0'):
        """
        Initialize a Xiaomi Mijia Poller for the given MAC address.
        """

        self._mac = mac
        self._adapter = adapter
        self._cache = None
        self._cache_timeout = timedelta(seconds=cache_timeout)
        self._last_read = None
        self._fw_last_read = datetime.now()
        self.retries = retries
        self.ble_timeout = 10
        self.lock = Lock()
        self._firmware_version = None
        self._battery_level = None
        self._bat_last_read = datetime.now()

    def name(self):
        """
        Return the name of the sensor.
        """
        name = read_ble(self._mac, "0x03",
                        retries=self.retries,
                        timeout=self.ble_timeout,
                        adapter=self._adapter)
        return ''.join(chr(n) for n in name)

    def fill_cache(self):
        firmware_version = self.firmware_version()
        if not firmware_version:
            # If a sensor doesn't work, wait 5 minutes before retrying
            self._last_read = datetime.now() - self._cache_timeout + \
                timedelta(seconds=300)
            return

        self._cache = write_readnotif_ble(self._mac, "0x10", "0100", retries=self.retries, timeout=self.ble_timeout, adapter=self._adapter)
		
        self._check_data()
        if self._cache is not None:
            self._last_read = datetime.now()
        else:
            # If a sensor doesn't work, wait 5 minutes before retrying
            self._last_read = datetime.now() - self._cache_timeout + \
                timedelta(seconds=300)

    def battery_level(self):
        """
        Return the battery level.
        """
        if (self._battery_level is None) or \
                (datetime.now() - timedelta(hours=1) > self._bat_last_read):
            self._bat_last_read = datetime.now()
            res = read_ble(self._mac, '0x18', retries=self.retries, adapter=self._adapter)
            if res is None:
                self._battery_level = 0
            else:
                self._battery_level = res[0]
        return self._battery_level

    def firmware_version(self):
        """ Return the firmware version. """
        if (self._firmware_version is None) or \
                (datetime.now() - timedelta(hours=24) > self._fw_last_read):
            self._fw_last_read = datetime.now()
            res = read_ble(self._mac, '0x24', retries=self.retries, adapter=self._adapter)
            if res is None:
                self._firmware_version = None
            else:
                self._firmware_version = "".join(map(chr, res))
        return self._firmware_version

    def parameter_value(self, parameter, read_cached=True):
        """
        Return a value of one of the monitored paramaters.

        This method will try to retrieve the data from cache and only
        request it by bluetooth if no cached value is stored or the cache is
        expired.
        This behaviour can be overwritten by the "read_cached" parameter.
        """

        LOGGER.debug("Call to parameter_value (%s)",parameter)
		
        # Special handling for battery attribute
        if parameter == MI_BATTERY:
            return self.battery_level()

        # Use the lock to make sure the cache isn't updated multiple times
        with self.lock:
            if (read_cached is False) or \
                    (self._last_read is None) or \
                    (datetime.now() - self._cache_timeout > self._last_read):
                self.fill_cache() 
            else:
                LOGGER.debug("Using cache (%s < %s)",
                             datetime.now() - self._last_read,
                             self._cache_timeout)

        if self._cache and (len(self._cache) == 14):
            return self._parse_data()[parameter]
        else:
            raise IOError("Could not read data from Mi sensor %s",
                          self._mac)

    def _check_data(self):
        if self._cache is None:
            return
        datasum = 0
        for i in self._cache:
            datasum += i
        if datasum == 0:
            self._cache = None

    def _parse_data(self):
        data = self._cache
        temp,humid = "".join(map(chr, data)).replace("T=", "").replace("H=", "").rstrip(' \t\r\n\0').split(" ")
        res = {}
        res[MI_TEMPERATURE] = temp
        res[MI_HUMIDITY] = humid
        return res
