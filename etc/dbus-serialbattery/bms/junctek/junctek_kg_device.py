'''
File:          junctek_kg_device.py
Project:       pyJunctek
Created Date:  Thursday 15.06.2023 00:08:03
Author:        DrMaex
Description:   script for accessing junctek KG Smartshunt over RS485<->COM converter.
-----
Last Modified: Monday 19.06.2023 22:55:20
Modified By:   DrMaex
-----
'''

import logging
import argparse
import os
import queue
import serial
from serial import SerialException
import threading


from junctek_kg_registers import junctek_Device, rcv_telegram, junctekBasicRegister, junktec_register, THREADMESSAGES
import time


MAX_DEVICES = 1

threadlist = []                 # used as pointer/reference to client thread for indirectly accessing from different functions \

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
FORMAT = '%(asctime)s - %(levelname)-8s: %(name)-23s %(funcName)28s() (%(lineno)4s): %(message)s'
logging.basicConfig(format=FORMAT, datefmt='%d.%m.%Y %H:%M:%S')


class junctek_Master():
    def __init__(self, comport: str, displayPresent: bool = False) -> None:
        self.comport = comport
        self.displayPresent = displayPresent
        self.connectionEstablished = False
        self.daisyChain: list[junctek_Device] = []
        self._receivequeue = queue.Queue()   # used for COM messages backend -> gui
        self._sendqueue = queue.Queue()      # used for COM messages gui -> backend
        self._errorqueue = queue.Queue()     # used for exception messages backend -> gui or killthread signal gui -> backend
        self.waitqueue = []
        self.requestPending = False

    def start(self):
        logger.info("Opening COM: {}".format(self.comport))
        startdaemon(self.comport, self._sendqueue, self._receivequeue, self._errorqueue)
        while self._errorqueue.empty():
            logger.debug("Waiting for message...")
            time.sleep(1)
            continue
        msg = self._errorqueue.get()
        if msg == THREADMESSAGES.COM_OPENED:
            self.connectionEstablished = True
            logger.info("{} opened successfully".format(self.comport))
            self.sendBroadcastMessage()
            self.checkQueues()
            return True
        if msg == THREADMESSAGES.THREAD_DIED:
            self.connectionEstablished = False
            logger.info("{} communication thread died".format(self.comport))
        return False

    def sendBroadcastMessage(self):
        logger.debug("Looking for new devices....")
        for dev in range(1, MAX_DEVICES + 1):
            self.getBasicDeviceInfo(dev)

    def getDeviceByAddr(self, addr: int) -> junctek_Device:
        for dev in self.daisyChain:
            if dev.communicationAddr == addr:
                return dev
        logger.info("No device with address {} found, creating new".format(addr))
        return self.createNewDevice(addr)
    
    def createNewDevice(self, addr: int) -> junctek_Device:
        self.daisyChain.append(junctek_Device(communicationAddr=addr))
        return self.daisyChain[-1]

    def updateValues(self) -> bool:
        logger.debug("Updating values")
        if self.displayPresent is False:
            self.sendBroadcastMessage()
            if len(self.daisyChain) > 0:
                logger.debug("No display present, looping though all known devices ({})".format(len(self.daisyChain)))
                for dev in self.daisyChain:
                    self.getAllMeasuredValuesInfo(dev.communicationAddr)
                    self.getAllSettingValuesInfo(dev.communicationAddr)
                    self.checkQueues()
            else:
                logger.error("No devices found")
                return False
        else:
            self.requestPending = True
            return self.checkQueues()

        return True

    def kill(self):
        self._errorqueue.put(THREADMESSAGES.KILLTHREAD_SIGNAL)

    def checkQueues(self):
        logger.debug("Checking Queue; Request Pending: {}".format(self.requestPending))
        while not self._receivequeue.empty():
            telegram: rcv_telegram = self._receivequeue.get()
            if (telegram.valid is True):
                logger.debug("Received valid telegram, searching for handler with address {}".format(telegram.getCommunicationAddr()))
                handler = None
                device = self.getDeviceByAddr(telegram.getCommunicationAddr())
                if device:
                    register: junctekBasicRegister = device.register[str(junktec_register(int(telegram.getRegister())))]
                    if register:
                        handler = register.getHandler()

                if handler is not None:
                    logger.debug("Handling telegram from device {} for register {}".format(telegram.getCommunicationAddr(), junktec_register(int(telegram.getRegister()))))
                    handler(telegram)
                    self.requestPending = False
                else:
                    logger.error("No Handler for register {}, deviceaddr:{}".format(junktec_register(int(telegram.getRegister())), telegram.getCommunicationAddr()))
                    logger.debug("Available registers {}".format(device.register))
                    self.sendBroadcastMessage()
            else:
                logger.debug("Telegram invalid, skipping and resetting requestFlag")
                self.requestPending = False
        if not self._errorqueue.empty():
            msg = self._errorqueue.get_nowait()
            if msg == THREADMESSAGES.THREAD_DIED:
                self.connectionEstablished = False

        if self.requestPending is False:
            logger.debug("checking for waiting requests...")
            nextRequest = self.dequeueRequest()
            if nextRequest:
                self.putRequestOnBus(nextRequest)
            else:
                logger.debug("No requests in waitqueue")
        
        return self.connectionEstablished

    def getBasicDeviceInfo(self, communicationAddr: int):
        logger.info("Reading basic information of device with address: {}".format(communicationAddr))
        return self.sendReadRequest(junktec_register.R_BASIC_INFO, communicationAddr)

    def getAllMeasuredValuesInfo(self, communicationAddr: int):
        logger.info("Reading measured values of device with address: {}".format(communicationAddr))
        return self.sendReadRequest(junktec_register.R_ALL_VALUES, communicationAddr)

    def getAllSettingValuesInfo(self, communicationAddr: int):
        logger.info("Reading settings of device with address: {}".format(communicationAddr))
        return self.sendReadRequest(junktec_register.R_ALL_SETTINGS, communicationAddr)

    def sendReadRequest(self, register: int, communcationAdress: int):
        tel = ":R{:02}={},{},{}\r\n".format(register, communcationAdress, rcv_telegram.calculateChecksumStatic(["1"]), 1)
        logger.debug("putting message \"{}\" in the waitqueue (Request pending: {})".format(tel, self.requestPending))
        self.enqueueRequest(tel.encode("ascii"))

    def putRequestOnBus(self, request: bytearray):
        self.requestPending = True
        self._sendqueue.put(request)

    def enqueueRequest(self, request: bytearray):
        if request not in self.waitqueue:
            self.waitqueue.append(request)
            logger.debug("Enqueueing new event, total:{}".format(len(self.waitqueue)))
        else:
            logger.debug("Event already exists in queue, skipping")
        if self.requestPending is not True:
            self.putRequestOnBus(self.dequeueRequest())

    def dequeueRequest(self) -> bytearray:
        if len(self.waitqueue) > 0:
            return self.waitqueue.pop(0)
        return None


def send_receive_thread(comport: str, sendqueue: queue.Queue, receivequeue: queue.Queue, errorqueue: queue.Queue):
    '''serial port send and receive endless loop'''
    exitsignal = None

    try:
        ser = serial.Serial(comport, baudrate=115200)  # open serial port
        logger.debug("COM port opened: {}".format(comport))
        ser.timeout = 5
        errorqueue.put(THREADMESSAGES.COM_OPENED)
        ser.flush()
        time.sleep(1)
        while (1):
            if not errorqueue.empty():  # check if thread should stop
                exitsignal = errorqueue.get_nowait()
                logger.debug("Received {}".format(exitsignal))
                if exitsignal == THREADMESSAGES.KILLTHREAD_SIGNAL:
                    break  # stop communication if KILL signal is present
            if not sendqueue.empty():   # sendque.get() is blocking function - if we wait here (due to queue is empty) we are not able to read out response in buffer of serial port
                msg = sendqueue.get()
                logger.debug("Sending: {}".format(' '.join("{:02X}".format(x) for x in msg)))
                ser.write(msg)
            if ser.in_waiting:
                receivedData = None
                receivedData = ser.readline()
                # logger.debug("Received bytearray: {}".format(' '.join("{:02X}".format(x) for x in receivedData)))
                telegram = rcv_telegram(receivedData)
                receivequeue.put(telegram)
                telegram = None

        logger.info("Closing COM port")
        ser.close()             # close port
        logger.info("Killing Thread")
    except SerialException as ex:
        logger.error(str(ex))
        errorqueue.put(THREADMESSAGES.THREAD_DIED)  # if serial exeption occured, put message in queue and exit
        return
    except OSError as ex:
        logger.error(str(ex))
        errorqueue.put(THREADMESSAGES.THREAD_DIED)  # if serial exeption occured, put message in queue and exit
        return        


def startdaemon(comport: str, sendqueue: queue.Queue, receivequeue: queue.Queue, errorqueue: queue.Queue):
    threadlist.append(threading.Thread(target=send_receive_thread, args=(comport, sendqueue, receivequeue, errorqueue)))    # create thread object and append to threadlist (always unique!)
    threadlist[0].start()


def main(comport: str) -> None:
    logger.info('Starting Testprogram')

    master = junctek_Master(comport=comport, displayPresent=True)    
    master.start()

    while master.connectionEstablished is True:
        master.updateValues()
        time.sleep(0.5)
        # master.kill()


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description='Available parameters:', epilog='Have fun!')
    argParser.add_argument('-c', '--com', default="/dev/ttyUSB0", metavar='COM-Port', help='COM Port for connect to RS485 -> COM Adapter')  # /dev/ttyUSB0  /dev/ttyVS8 sudo socat -d -d pty,raw,echo=0,LINK=/dev/ttyVS8,mode=660 pty,raw,echo=0,LINK=/dev/ttyVS9,mode=660
    args = argParser.parse_args()
    logger.info('{} v0.1'.format(os.path.basename(__file__)))
    logger.info('Startup arguments: {}'.format(vars(args)))
    main(args.com)
