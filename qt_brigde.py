import logging
import threading
import time

from PyQt5 import QtCore

import ftms
from antsend import AntSend
from bluezero import adapter

from ble_peripheral import FtmsPeripheral
from ble_central import BleCentral


logging.basicConfig(level=logging.WARNING)

_LOGGER = logging.getLogger(__name__)


class MoveOnError(Exception):
    pass


def get_adapters():
    a = list(adapter.Adapter.available())
    return a


class BleBridge(QtCore.QThread):

    any_signal = QtCore.pyqtSignal(list)

    def __init__(self, parent=None, adapter_lib=None):
        super(BleBridge, self).__init__(parent)
        self.a = adapter_lib
        self.threads = {}
        self.pill2kill = threading.Event()
        self.pill2kill2 = threading.Event()
        self.pill2kill3 = threading.Event()
        if len(self.a) < 2:
            self.ble_in = BleCentral(stop_event=self.pill2kill, adapter_address=self.a[0])
            self.ble_out = FtmsPeripheral(stop_event=self.pill2kill3, adapter_address=self.a[0], have_to_work=False)
        else:
            self.ble_in = BleCentral(stop_event=self.pill2kill, adapter_address=self.a[0],
                                     blacklist_address=self.a[1])
            self.ble_out = FtmsPeripheral(stop_event=self.pill2kill3, adapter_address=self.a[1])
        self.ant_send = AntSend(self.pill2kill2)
        self.t = []

    def start_pause(self, running):
        if running is False:
            self.ble_in.ftms_control_value = [True, False, bytearray([0x07])]
        else:
            self.ble_in.ftms_control_value = [True, False, bytearray([0x08, 0x02])]

    def stop_running(self):
        self.ble_in.ftms_control_value = [True, False, bytearray([0x08, 0x02])]
        time.sleep(0.25)
        self.ble_in.ftms_control_value = [True, False, bytearray([0x00])]
        time.sleep(0.25)
        self.ble_in.ftms_control_value = [True, False, bytearray([0x01])]
        time.sleep(0.25)
        self.ble_in.ftms_control_value = [True, False, bytearray([0x00])]

    def set_speed(self, speed):
        speed_bytes = bytearray([0x02]) + int(speed*100).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, speed_bytes]

    def set_incline(self, incline):
        incline_bytes = bytearray([0x03]) + int(incline*10).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, incline_bytes]

    def increase_speed(self):
        speed = self.ble_in.values[0] + 20
        speed_bytes = bytearray([0x02]) + int(speed).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, speed_bytes]

    def decrease_speed(self):
        speed = self.ble_in.values[0] - 20
        speed_bytes = bytearray([0x02]) + int(speed).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, speed_bytes]

    def increase_incline(self):
        incline = self.ble_in.values[3] + 5
        incline_bytes = bytearray([0x03]) + int(incline).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, incline_bytes]

    def decrease_incline(self):
        incline = self.ble_in.values[3] - 5
        incline_bytes = bytearray([0x03]) + int(incline).to_bytes(2, byteorder='little')
        self.ble_in.ftms_control_value = [True, False, incline_bytes]

    def update_ble_out(self, ftms_control_value):
        if ftms_control_value[1] is True:
            self.ble_out.treadmill_data_values = self.ble_in.value
            self.ble_out.ftms_status_value = self.ble_in.ftms_status_value
            self.ble_out.training_status_value = self.ble_in.training_status_value
        elif ftms_control_value[0] is True:
            self.ble_in.ftms_control_value = ftms_control_value

    def update_ant(self):

        self.ant_send.TreadmillSpeed = self.ble_in.values[0] / 360  # m/s
        self.ant_send.TreadmillDistance = self.ble_in.values[9]

    def run(self):

        print("start bridge...")
        if len(self.a) < 2:
            print("Only one adapter available. No Peripheral!")

            self.threads[1] = threading.Thread(target=self.ble_in.ble_central_start)
            self.t += [1]

        else:

            self.threads[1] = threading.Thread(target=self.ble_in.ble_central_start)
            self.t += [1]
            self.threads[2] = threading.Thread(target=self.ble_out.ftms_peripheral_start)
            self.t += [2]

        self.threads[3] = threading.Thread(target=self.ant_send.openchanel)
        self.t += [3]
        try:
            for i in self.t:
                print("start thread", i)
                self.threads[i].start()

            while not self.pill2kill.wait(0.1):
                update_ble_out_thread = threading.Thread(target=self.update_ble_out,
                                                         args=(ftms.ftms_control_value, ))
                update_ble_out_thread.start()
                update_ant_thread = threading.Thread(target=self.update_ant)
                update_ant_thread.start()
                self.any_signal.emit(self.ble_in.values)

        except KeyboardInterrupt:
            pass
        finally:
            print("loop ended")
            self.pill2kill.set()
            self.pill2kill2.set()
            self.pill2kill3.set()
            for i in self.t:
                self.threads[i].join()

        logging.shutdown()
        print("Close bridge...")

    def stop(self):
        self.pill2kill.set()
        self.pill2kill2.set()
        self.pill2kill3.set()
        for i in self.t:
            self.threads[i].join()
        self.any_signal = None
        print("Bridge Thread stopped")
        return
