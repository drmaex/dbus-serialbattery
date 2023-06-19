# -*- coding: utf-8 -*-

# NOTES
# Please see "Add/Request a new BMS" https://louisvdw.github.io/dbus-serialbattery/general/supported-bms#add-by-opening-a-pull-request
# in the documentation for a checklist what you have to do, when adding a new BMS

# avoid importing wildcards
from battery import Battery
from utils import logger
import utils
from junctek.junctek_kg_device import junctek_Master
from junctek.junctek_kg_registers import junctek_Device, junctek_currentDirection
from enum import IntEnum


class VENUS_OS_PROTECTION_ALARMS(IntEnum):
    OK = 0
    WARNING = 1
    ALARM = 2

    def __str__(self) -> str:
        return self.name


class junctek_kg(Battery):
    def __init__(self, port, baud, address):
        super(junctek_kg, self).__init__(port, baud, address)
        self.type = self.BATTERYTYPE

        self.busmaster = junctek_Master(comport=port, displayPresent=utils.JUNCTEK_DISPLAY_PRESENT)
        self.dev: junctek_Device = None
        self.ot_protection_value = None

    BATTERYTYPE = "Junctek_KG"

    def test_connection(self):
        # call a function that will connect to the battery, send a command and retrieve the result.
        # The result or call should be unique to this BMS. Battery name or version, etc.
        # Return True if success, False for failure
        result = False
        try:
            result = self.busmaster.start()
            if result:
                self.refresh_data()
                self.dev = self.busmaster.daisyChain[0]
        except Exception as err:
            logger.error(f"Unexpected {err=}, {type(err)=}")
            result = False

        return result

    def get_settings(self):
        # After successful  connection get_settings will be call to set up the battery.
        # Set the current limits, populate cell count, etc
        # Return True if success, False for failure
        if self.dev is not None:
            self.capacity = self.dev.getCapacity()
            
            # read protection values. when, like suggested in manual of junctek device, the relais is missing, the values should be left with default 0
            # then fallback values from config.default.ini are used instead
            self.max_battery_charge_current = self.dev.getPOC()
            if self.max_battery_charge_current == 0:
                self.max_battery_charge_current = utils.JUNCTEK_PC_PROTECTION

            self.max_battery_discharge_current = self.dev.getNOC()
            if self.max_battery_discharge_current == 0:
                self.max_battery_discharge_current = utils.JUNCTEK_NC_PROTECTION
            
            self.max_battery_voltage = self.dev.getMaxVoltageSetting()
            if self.max_battery_voltage == 0:
                self.max_battery_voltage = utils.JUNCTEK_OV_PROTECTION

            self.min_battery_voltage = self.dev.getMinVoltageSetting()
            if self.min_battery_voltage == 0:
                self.min_battery_voltage = utils.JUNCTEK_UV_PROTECTION

            self.unique_identifier = self.dev.getDeviceID()
            self.ot_protection_value = self.dev.getMaxTemperatureSetting()
            if self.ot_protection_value == 0:
                self.ot_protection_value = utils.JUNCTEK_OT_PROTECTION
            
            self.hardware_version = "Junctek Lifepo4 Test"
            return True
        return False

    def refresh_data(self):

        result = self.busmaster.updateValues()

        if self.dev is not None:
            self.voltage = self.dev.getCurrentVoltage()
            self.current = self.dev.getCurrentAmpere()
            if (self.dev.getCurrentDirection() == junctek_currentDirection.CURR_DISCHARGING):
                # correct the sign to display discharging
                self.current *= -1
            self.soc = self.dev.getSoC()
            self.total_ah_drawn = self.dev.getTotalAhDrawn()
            self.temp1 = self.dev.getTemperature()
            
            self.protection.temp_high_discharge = VENUS_OS_PROTECTION_ALARMS.OK
            self.protection.temp_high_charge = VENUS_OS_PROTECTION_ALARMS.OK

            if ((self.ot_protection_value - utils.JUNCTEK_OT_WINDOW) <= self.temp1 == self.ot_protection_value):
                logger.warning("Setting alarmstate to {}! temp={}°C; limit={}°C".format(VENUS_OS_PROTECTION_ALARMS.WARNING, self.temp1, self.ot_protection_value))
                if (self.dev.getCurrentDirection() == junctek_currentDirection.CURR_CHARGING):
                    self.protection.temp_high_charge = VENUS_OS_PROTECTION_ALARMS.WARNING
                else:
                    self.protection.temp_high_discharge = VENUS_OS_PROTECTION_ALARMS.WARNING

            if (self.temp1 > self.ot_protection_value):
                logger.warning("Setting alarmstate to {}! temp={}°C; limit={}°C".format(VENUS_OS_PROTECTION_ALARMS.ALARM, self.temp1, self.ot_protection_value))
                if (self.dev.getCurrentDirection() == junctek_currentDirection.CURR_CHARGING):
                    self.protection.temp_high_charge = VENUS_OS_PROTECTION_ALARMS.ALARM
                else:
                    self.protection.temp_high_discharge = VENUS_OS_PROTECTION_ALARMS.ALARM

        return result
