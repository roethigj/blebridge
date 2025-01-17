
"""Example of how to create a Peripheral device/GATT Server"""
import time
import logging
import struct

# Bluezero modules
from bluezero import adapter
from bluezero import peripheral

import ftms
from ftms import services
import threading


class FtmsPeripheral:
    def __init__(self, adapter_address):
        self.treadmill_data_values = struct.pack('<BBHHBHHHHBBH', 140, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.ftms_status_value = struct.pack('<B', 0)
        self.training_status_value = struct.pack('<B', 0)
        self.ftms_control_value = [False, True, struct.pack('<B', 0)]
        self.adapter_address = adapter_address
        self.ftms_monitor = peripheral.Peripheral(adapter_address,
                                                  local_name='BLE_Bridge_Treadmill',
                                                  appearance=0x0440)
        self.stop_event = None
        self.have_to_work = False
        self.dongle = None
        self.peripheral_thread = None

    def peripheral_handler(self):
        self.ftms_monitor.publish()

    def ftms_peripheral_start(self, stop_event, have_to_work):
        """
        Creates advertises and starts the peripheral
        :param stop_event: to cancel publishing loop
        :param have_to have_to_work: only work, when 2nd BT dongle is available
        """

        self.stop_event = stop_event
        self.have_to_work = have_to_work

        logger = logging.getLogger('localGATT')
        logger.setLevel(logging.DEBUG)
        self.dongle = adapter.Adapter(adapter_addr=self.adapter_address)

        if not self.dongle.powered:
            self.dongle.powered = True

        if self.have_to_work:
            print("1st try")

            i = 1
            for key in services:
                self.ftms_monitor.add_service(srv_id=i, uuid=key, primary=True)
                print(i, key)
                i += 1

            i = 1

            for c_uuid in services.values():
                print(i, c_uuid, services.keys())

                j = 1
                for c_key in c_uuid:
                    print(i, j, c_key, c_uuid[c_key])
                    self.ftms_monitor.add_characteristic(srv_id=i,
                                                         chr_id=j,
                                                         uuid=c_key,
                                                         value=c_uuid[c_key][0],
                                                         notifying=c_uuid[c_key][1],
                                                         flags=c_uuid[c_key][2],
                                                         read_callback=c_uuid[c_key][3],
                                                         write_callback=c_uuid[c_key][4],
                                                         notify_callback=c_uuid[c_key][5]
                                                         )
                    j += 1
                i += 1

            # Publish peripheral and start event loop
            self.peripheral_thread = threading.Thread(target=self.peripheral_handler)
            self.peripheral_thread.start()

            while not self.stop_event.wait(0.25):
                ftms.treadmill_values = self.treadmill_data_values
                ftms.ftms_status_value = self.ftms_status_value
                ftms.training_status_value = self.training_status_value

            self.dongle.powered = False
            time.sleep(0.3)
            self.dongle.powered = True
            self.ftms_monitor.mainloop.quit()
            self.peripheral_thread.join(1)
