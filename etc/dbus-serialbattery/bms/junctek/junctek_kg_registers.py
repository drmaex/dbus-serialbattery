'''
File:          junctek_kg_registers.py
Project:       pyJunctek
Created Date:  Thursday 15.06.2023 00:08:19
Author:        DrMaex
Description:   this file consists of datatypes which are needed to represent the junctek device
-----
Last Modified: Monday 19.06.2023 23:15:17
Modified By:   DrMaex
-----
'''


from enum import IntEnum
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class THREADMESSAGES(IntEnum):
    KILLTHREAD_SIGNAL = 1
    COM_OPENED = 2
    THREAD_DIED = 3

    def __str__(self) -> str:
        return self.name


class junktec_register(IntEnum):
    R_BASIC_INFO = 0
    R_ALL_VALUES = 50
    R_ALL_SETTINGS = 51
    W_ADDR = 1
    W_OUTPUT = 10
    W_OVP = 20
    W_UVP = 21
    W_POC = 22
    W_NOC = 23
    W_OPP = 24
    W_OTP = 25
    W_PROT_REV_TIME = 26
    W_DELAY = 27
    W_BAT_CAP = 28
    W_V_CAL = 29
    W_C_CAL = 30
    W_T_CAL = 31
    W_RES0 = 33
    W_REL_TYPE = 34
    W_FAC_RES = 35
    W_CUR_RAT = 36
    W_V_SCALE = 37
    W_C_SCALE = 38
    W_BAT_PERC = 60
    W_CUR_ZERO = 61
    W_DATA_ZERO = 62

    def __str__(self) -> str:
        return self.name


class junctek_outputStatus(IntEnum):
    OUT_ON = 0
    OUT_OVP = 1
    OUT_OCP = 2
    OUT_LVP = 3
    OUT_NCP = 4
    OUT_OPP = 5
    OUT_OTP = 6
    OUT_OFF = 255

    def __str__(self) -> str:
        return self.name


class junctek_relayType(IntEnum):
    RELAY_NORM_OPEN = 0
    RELAY_NORM_CLOSED = 1

    def __str__(self) -> str:
        return self.name


class junctek_samplerType(IntEnum):
    SAMPLER_HALL = 1
    SAMPLER_SHUNT = 2

    def __str__(self) -> str:
        return self.name


class junctek_currentDirection(IntEnum):
    CURR_DISCHARGING = 0
    CURR_CHARGING = 1

    def __str__(self) -> str:
        return self.name


class rcv_telegram():
    def __init__(self, array: bytearray) -> None:
        self.valid = False
        try:
            self.dataAsString = array.decode("ascii")
        except UnicodeDecodeError:
            logger.error("damaged telegram, skipping")
            return
        if not self.dataAsString.startswith(":"):
            #logger.error("Invalid telegram received, {} does not start with \":\"".format(self.dataAsString))
            return None
        if not self.dataAsString.endswith("\r\n"):
            #logger.error("Invalid telegram received, {} does not end with \"\\r\\n\"".format(self.dataAsString))
            return None
        datafields = self.dataAsString.split("=")
        logger.debug("Telegram splitted in: {}".format(datafields))
        mymatch = re.match(r":(\w{1})(\d{2})", datafields[0])
        self.mode = None
        self.registerAddr = None
        if mymatch:
            self.mode = mymatch.group(1)
            self.registerAddr = mymatch.group(2)
            try:
                logger.debug("Telegram mode \"{}\" at addr: {}".format(self.mode, junktec_register(int(self.registerAddr))))
            except ValueError:
                return
        try:
            self.data = datafields[1].split(",")[:-1]
        except IndexError:
            logger.error("damaged telegram, skipping")
            return
        logger.debug("Data: {}".format(self.data))
        self.commAddr = int(self.data[0])
        self.checksum = int(self.data[1])
        self.calcChecksum = self.calculateChecksum()
        if self.checksum == self.calcChecksum:
            self.valid = True
        else:
            logger.error("Calculated Checksum does not match the received {} <-> {}".format(self.checksum, self.calcChecksum))

    def getMode(self):
        return self.mode

    def getRegister(self):
        return self.registerAddr

    def calculateChecksum(self):
        return rcv_telegram.calculateChecksumStatic(self.data[2:])

    @staticmethod
    def calculateChecksumStatic(data):
        sum = 0
        for i in data:
            if i is not None and not i == '':
                sum += int(i)
        return (sum % 255) + 1

    def getCommunicationAddr(self) -> int:
        return self.commAddr


class junctekBasicRegister(ABC):

    @abstractmethod
    def rcvhandler(self, telegram: rcv_telegram):
        ...

    def getHandler(self):
        return self.rcvhandler


@dataclass
class junctekRegister00(junctekBasicRegister):
    ''' Register 00 with device information '''
    sampler: junctek_samplerType = None
    voltage: int = None
    ampere: int = None
    version: float = None
    serial: int = None
    device_id: str = None

    def rcvhandler(self, telegram: rcv_telegram):
        logger.debug("Handlng register: {}".format(junktec_register(int(telegram.getRegister()))))
        mymatch = re.search("(\d{1})(\d{1})(\d{2})", telegram.data[2])
        if mymatch:
            self.sampler = junctek_samplerType(int(mymatch.group(1)))
            self.voltage = int(mymatch.group(2)) * 100
            self.ampere = int(mymatch.group(3)) * 10
        self.version = telegram.data[3]
        self.serial = telegram.data[4]

        logger.info("Device info: {}".format(self))

        mymatch = re.search("(\d{1})(\d{3})", telegram.data[2])
        if mymatch:
            self.device_id = "KG{}F/v{:1.2f}/#{}".format(mymatch.group(2), float(self.version)/100, self.serial)
    
    def getDeviceID(self):
        return self.device_id

    def __str__(self) -> str:
        return "\nSampler: {};\nVoltage: {};\nAmpere: {};\nVersion: {};\nSerial: {};".format(self.sampler, self.voltage, self.ampere, self.version, self.serial)


@dataclass
class junctekRegister50(junctekBasicRegister):
    ''' Register 50 with all measured values'''
    voltage: float = None
    ampere: float = None
    remainingCapacity_ah: float = None
    cumulatedCapacity_ah: float = None
    kilowattHours: float = None
    runningTimeSeconds: int = None
    temperature: int = None
    pending: int = None
    output: junctek_outputStatus = None
    currentDir: junctek_currentDirection = None
    batteryLifeMinutes: int = None
    internalResistance_mohm: float = None

    def rcvhandler(self, telegram: rcv_telegram):
        logger.debug("Handlng register: {}".format(junktec_register(int(telegram.getRegister()))))
        self.voltage = float(telegram.data[2]) / 100
        self.ampere = float(telegram.data[3]) / 100
        self.remainingCapacity_ah = float(telegram.data[4]) / 1000
        self.cumulatedCapacity_ah = float(telegram.data[5]) / 1000
        self.kilowattHours = float(telegram.data[6]) / 100000
        self.runningTimeSeconds = int(telegram.data[7])
        self.temperature = int(telegram.data[8]) - 100
        self.pending = int(telegram.data[9])
        self.output = junctek_outputStatus(int(telegram.data[10]))
        self.currentDir = junctek_currentDirection(int(telegram.data[11]))
        self.batteryLifeMinutes = int(telegram.data[12])
        self.internalResistance = float(telegram.data[13]) / 100

        logger.debug("Received Values: {}".format(self))
    
    def __str__(self) -> str:
        return "\nVoltage: {} V;\nAmpere: {} A;\nRemaining Ah: {};\nCumulated AH: {};\nkWh:{};\
            \nRuntime: {}s;\nTemperature: {} C;\nPending: {};\nOutput: {};\nCurrent Direction: {};\
            \nEstimated Battery Life: {} m ;\nInt. Resistance: {} mOhm;".format(self.voltage, self.ampere, self.remainingCapacity_ah, self.cumulatedCapacity_ah,
                                                                                self.kilowattHours, self.runningTimeSeconds, self.temperature, self.pending, self.output,
                                                                                self.currentDir, self.batteryLifeMinutes, self.internalResistance)


@dataclass
class junctekRegister51(junctekBasicRegister):
    ''' Register 51 with all configuration values '''
    ov_protection: float = None
    uv_protection: float = None
    poc_protection: float = None
    noc_protection: float = None
    op_protection: float = None
    ot_protection: float = None
    protection_recovery_time_s: int = None
    battery_preset_ah: float = None
    voltage_calibration: int = None
    current_calibration: int = None
    temp_calibration: int = None
    reserved0: int = None
    relay_type: junctek_relayType = None
    current_ratio: int = None
    volt_per_division: int = None
    ampere_per_devision: int = None

    def rcvhandler(self, telegram: rcv_telegram):
        logger.debug("Handlng register: {}".format(junktec_register(int(telegram.getRegister()))))
        self.ov_protection = float(telegram.data[2]) / 100
        self.uv_protection = float(telegram.data[3]) / 100
        self.poc_protection = float(telegram.data[4]) / 100
        self.noc_protection = float(telegram.data[5]) / 100
        self.op_protection = float(telegram.data[6]) / 100
        self.ot_protection = int(telegram.data[7]) - 100
        self.protection_recovery_time_s = int(telegram.data[8])
        self.delay_time = int(telegram.data[9])
        self.battery_preset_ah = float(telegram.data[10]) / 10
        self.voltage_calibration = int(telegram.data[11]) - 100
        self.current_calibration = int(telegram.data[12]) - 100
        self.temp_calibration = int(telegram.data[13]) - 100
        self.reserved0 = int(telegram.data[14])
        self.relay_type = junctek_relayType(int(telegram.data[16]))
        self.current_ratio = int(telegram.data[16])
        # self.volt_per_division = int(telegram.data[16])
        # self.ampere_per_devision = int(telegram.data[17])
        logger.debug("Received values: {}".format(self))

    def __str__(self) -> str:
        return "\nOVP: {} V;\nUVP: {} V;\nPos OCP: {} A;\nNeg OCP: {} A;\nOPP:{} W;\
            \nOTP: {} C;\nProtection Recovery Time: {} s;\nBattery preset: {} Ah;\nVoltage calib: {} ;\nCurrent calib: {};\
            \nTemp calib: {};\nReserved0: {};\nRelay Type: {};\nCurrent ratio: {};".format( self.ov_protection, self.uv_protection, self.poc_protection,
                                                                                            self.noc_protection, self.op_protection, self.ot_protection,
                                                                                            self.protection_recovery_time_s, self.battery_preset_ah, self.voltage_calibration,
                                                                                            self.current_calibration, self.temp_calibration, self.reserved0, self.relay_type,
                                                                                            self.current_ratio)


@dataclass
class junctek_Device():
    communicationAddr: int = None
    device_id: str = None

    def getDeviceID(self) -> str:
        reg: junctekRegister00 = self.register[str(junktec_register.R_BASIC_INFO)]
        return reg.getDeviceID()

    def return_None():
        return None

    register = defaultdict(return_None)

    register[str(junktec_register.R_BASIC_INFO)] = junctekRegister00()
    register[str(junktec_register.R_ALL_VALUES)] = junctekRegister50()
    register[str(junktec_register.R_ALL_SETTINGS)] = junctekRegister51()

    def getCurrentVoltage(self) -> float:
        logger.debug("Reading voltage from register")
        reg: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg.voltage

    def getCurrentAmpere(self) -> float:
        logger.debug("Reading ampere from register")
        reg: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg.ampere

    def getCurrentDirection(self) -> junctek_currentDirection:
        logger.debug("Reading current direction from register")
        reg: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg.currentDir

    def getSoC(self) -> int:
        ''' read current state of charge '''
        logger.debug("Calculating SoC (State of Charge)")
        preset_capacity = self.getCapacity()
        remaining_capacity = self.getRemainingCapacity()
        return int((remaining_capacity / preset_capacity) * 100)

    def getTotalAhDrawn(self) -> float:
        logger.debug("Reading total Ah drawn")
        reg_values: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg_values.cumulatedCapacity_ah

    def getTemperature(self) -> int:
        logger.debug("Reading Temperature")
        reg_values: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg_values.temperature

    def getCapacity(self) -> float:
        logger.debug("Reading capacity")
        reg_settings: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_settings.battery_preset_ah

    def getPOC(self) -> float:
        ''' read positive over current protection value '''
        logger.debug("Reading positive overcurrent limit")
        reg_settings: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_settings.poc_protection

    def getNOC(self) -> float:
        ''' read negative over current protection value '''
        logger.debug("Reading negative overcirrent limit")
        reg_settings: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_settings.noc_protection

    def getMinVoltageSetting(self) -> float:
        ''' read undervoltage protection value '''
        logger.debug("Reading min. voltage setting")
        reg_settings: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_settings.uv_protection

    def getMaxVoltageSetting(self) -> float:
        ''' read overvoltage protection value '''
        logger.debug("Reading max voltage setting")
        reg_settings: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_settings.ov_protection

    def getRemainingCapacity(self) -> float:
        logger.debug("Reading remaining capacity")
        reg_values: junctekRegister50 = self.register[str(junktec_register.R_ALL_VALUES)]
        return reg_values.remainingCapacity_ah

    def getMaxTemperatureSetting(self) -> float:
        logger.debug("Reading remaining capacity")
        reg_values: junctekRegister51 = self.register[str(junktec_register.R_ALL_SETTINGS)]
        return reg_values.ot_protection