'''
File:          junctek_gui.py
Project:       pyJunctek
Created Date:  Friday 16.06.2023 23:13:54
Author:        DrMaex
Description:   Simple GUI to test junctek implementation
-----
Last Modified: Monday 19.06.2023 00:04:34
Modified By:   DrMaex
-----
'''


import logging
import argparse
import os
import tkinter
from tkinter import StringVar, ttk
from junctek_kg_device import junctek_Master, junctek_Device
from junctek_kg_registers import junctek_currentDirection

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
FORMAT = '%(asctime)s - %(levelname)-8s: %(name)-23s %(funcName)28s() (%(lineno)4s): %(message)s'
logging.basicConfig(format=FORMAT, datefmt='%d.%m.%Y %H:%M:%S')

PAD_DEFAULT = 5
RECEIVE_CALLBACK_POLLINGFRQ = 200


class GUI():
    def __init__(self, comport: str) -> None:
        self.deviceconnected = False
        self.comport = comport
        self.root = tkinter.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.onClose)
        self.root.title("Proof of concept Junctek GUI v0.1")
        self.root.geometry("1050x850")
        self.root.resizable(height=False, width=False)
        self.master = junctek_Master(comport=self.comport, displayPresent=True)
        self.master.start()
        # draw UI elements
        self.draw_controls()

        # start polling incoming data from client thread
        self.updateValues()

        # event loop (refresh UI)
        self.root.mainloop()

    def updateValues(self):
        self.master.updateValues()
        if len(self.master.daisyChain) > 0:
            dev: junctek_Device = self.master.daisyChain[0]
            self.voltage_value.set("{}".format(dev.getCurrentVoltage()))
            logger.debug("Reading voltage....{}".format(self.voltage_value.get()))
            ampere = dev.getCurrentAmpere()
            current_direction = dev.getCurrentDirection()
            if current_direction == junctek_currentDirection.CURR_DISCHARGING:
                ampere = ampere * -1
            self.current_value.set("{}".format(ampere))
            logger.debug("Reading Ampere....{}".format(self.current_value.get()))
            self.device_id.set("{}".format(dev.getDeviceID()))
            logger.debug("Reading Device ID....{}".format(self.device_id.get()))
            self.current_soc.set("{}".format(dev.getSoC()))
            logger.debug("Reading Soc....{}".format(self.current_soc.get()))
            self.total_ah.set("{}".format(dev.getTotalAhDrawn()))
            logger.debug("Reading Total Ah....{}".format(self.total_ah.get()))
            self.temperature.set("{}".format(dev.getTemperature()))
            logger.debug("Reading temperature....{}".format(self.temperature.get()))
            self.capacity.set("{}".format(dev.getCapacity()))
            logger.debug("Reading capacity....{}".format(self.capacity.get()))
            self.poc_setting.set("{}".format(dev.getPOC()))
            logger.debug("Reading POC....{}".format(self.poc_setting.get()))
            self.noc_setting.set("{}".format(dev.getNOC()))
            logger.debug("Reading NOC....{}".format(self.noc_setting.get()))
            self.ov_setting.set("{}".format(dev.getMaxVoltageSetting()))
            logger.debug("Reading max voltage setting....{}".format(self.ov_setting.get()))
            self.uv_setting.set("{}".format(dev.getMinVoltageSetting()))
            logger.debug("Reading min voltage setting....{}".format(self.uv_setting.get()))
            self.remaining_ah_value.set("{}".format(dev.getRemainingCapacity()))
            logger.debug("Reading min voltage setting....{}".format(self.remaining_ah_value.get()))
            self.ot_protection_setting.set("{}".format(dev.getMaxTemperatureSetting()))
            logger.debug("Reading max temperature setting....{}".format(self.ot_protection_setting.get()))
        else:
            logger.debug("No Devices found...")
        self.root.after(RECEIVE_CALLBACK_POLLINGFRQ, self.updateValues)  # call this function after defined timespan again

    def onClose(self):
        logger.info("closing gui")
        self.master.kill()
        self.root.destroy()

    def draw_controls(self):
        self.voltage_value = StringVar()
        self.current_value = StringVar()
        self.current_soc = StringVar()
        self.device_id = StringVar()
        self.total_ah = StringVar()
        self.temperature = StringVar()
        self.capacity = StringVar()
        self.poc_setting = StringVar()
        self.noc_setting = StringVar()
        self.uv_setting = StringVar()
        self.ov_setting = StringVar()
        self.ot_protection_setting = StringVar()
        self.remaining_ah_value = StringVar()
        self.mainframe = ttk.Frame(self.root)
        self.mainframe.grid(column=0, row=0)

        self.device_id_label = ttk.Label(self.mainframe, textvariable=self.device_id, width=20)
        self.device_id_label.grid(column=0, row=0, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.voltage_control = ttk.Entry(self.mainframe, width=20, textvariable=self.voltage_value)
        self.voltage_control.grid(column=0, row=1, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.voltage_label = ttk.Label(self.mainframe, text="Volts", width=20)
        self.voltage_label.grid(column=1, row=1, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.ampere_control = ttk.Entry(self.mainframe, width=20, textvariable=self.current_value)
        self.ampere_control.grid(column=0, row=2, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.ampere_label = ttk.Label(self.mainframe, text="Ampere", width=20)
        self.ampere_label.grid(column=1, row=2, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.soc_control = ttk.Entry(self.mainframe, width=20, textvariable=self.current_soc)
        self.soc_control.grid(column=0, row=3, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.soc_label = ttk.Label(self.mainframe, text="%", width=20)
        self.soc_label.grid(column=1, row=3, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.totalAh_control = ttk.Entry(self.mainframe, width=20, textvariable=self.total_ah)
        self.totalAh_control.grid(column=0, row=4, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.totalAh_label = ttk.Label(self.mainframe, text="Total Ah drawn", width=20)
        self.totalAh_label.grid(column=1, row=4, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.temperature_control = ttk.Entry(self.mainframe, width=20, textvariable=self.temperature)
        self.temperature_control.grid(column=0, row=5, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.temperature_label = ttk.Label(self.mainframe, text="Temperature", width=20)
        self.temperature_label.grid(column=1, row=5, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.capacity_control = ttk.Entry(self.mainframe, width=20, textvariable=self.capacity)
        self.capacity_control.grid(column=0, row=6, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.capacity_label = ttk.Label(self.mainframe, text="Ah Total", width=20)
        self.capacity_label.grid(column=1, row=6, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.poc_control = ttk.Entry(self.mainframe, width=20, textvariable=self.poc_setting)
        self.poc_control.grid(column=0, row=7, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.poc_label = ttk.Label(self.mainframe, text="Charge Limit", width=20)
        self.poc_label.grid(column=1, row=7, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.noc_control = ttk.Entry(self.mainframe, width=20, textvariable=self.noc_setting)
        self.noc_control.grid(column=0, row=8, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.noc_label = ttk.Label(self.mainframe, text="Discharge Limit", width=20)
        self.noc_label.grid(column=1, row=8, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.ov_control = ttk.Entry(self.mainframe, width=20, textvariable=self.ov_setting)
        self.ov_control.grid(column=0, row=9, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.ov_label = ttk.Label(self.mainframe, text="OVP", width=20)
        self.ov_label.grid(column=1, row=9, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.uv_control = ttk.Entry(self.mainframe, width=20, textvariable=self.uv_setting)
        self.uv_control.grid(column=0, row=10, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.uv_label = ttk.Label(self.mainframe, text="UVP", width=20)
        self.uv_label.grid(column=1, row=10, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.remaining_ah_control = ttk.Entry(self.mainframe, width=20, textvariable=self.remaining_ah_value)
        self.remaining_ah_control.grid(column=0, row=11, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.remaining_ah_label = ttk.Label(self.mainframe, text="Remaining Ah", width=20)
        self.remaining_ah_label.grid(column=1, row=11, pady=PAD_DEFAULT, padx=PAD_DEFAULT)

        self.remaining_ah_control = ttk.Entry(self.mainframe, width=20, textvariable=self.ot_protection_setting)
        self.remaining_ah_control.grid(column=0, row=12, pady=PAD_DEFAULT, padx=PAD_DEFAULT)
        self.remaining_ah_label = ttk.Label(self.mainframe, text="OTP", width=20)
        self.remaining_ah_label.grid(column=1, row=12, pady=PAD_DEFAULT, padx=PAD_DEFAULT)


def main(comport: str) -> None:
    logger.info('Welcome to main')
    mygui = GUI(comport)
  

if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description='Available parameters:', epilog='Have fun!')
    argParser.add_argument('-c', '--comport', default="/dev/ttyUSB0", metavar='COM port', help='Comminication port of rs485 adapter')
    args = argParser.parse_args()
    logger.info('{} v0.1'.format(os.path.basename(__file__)))
    logger.info('Startup arguments: {}'.format(vars(args))) 
    main(args.comport)