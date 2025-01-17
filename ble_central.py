"""Example of how to create a Central device/GATT Client"""
import struct
import time
import threading
import dbus
import subprocess

from bluezero import adapter
from bluezero import central


def central_handler(ftms_monitor):
    ftms_monitor.run()


class BleCentral:
    def __init__(self, stop_event=None, adapter_address=None, **kwargs):
        self.stop_event = stop_event
        self.adapter_address = adapter_address
        self.blacklist_address = kwargs.get('blacklist_address', None)

        self.ftms_srv = '00001826-0000-1000-8000-00805f9b34fb'
        self.tm_data_uuid = '00002acd-0000-1000-8000-00805f9b34fb'
        self.fm_data_uuid = '00002ada-0000-1000-8000-00805f9b34fb'
        self.ts_data_uuid = '00002ad3-0000-1000-8000-00805f9b34fb'
        self.ftms_ctr_pt_uuid = '00002ad9-0000-1000-8000-00805f9b34fb'

        self.values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.value = struct.pack('<BBHHBHHHHBBH', 140, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.ftms_status_value = struct.pack('<B', 0)
        self.training_status_value = struct.pack('<B', 0)
        self.ftms_control_value = [False, True, struct.pack('<B', 1)]

    def ble_central_start(self):

        dongle = adapter.Adapter(adapter_addr=self.adapter_address)

        if not dongle.powered:
            dongle.powered = True

        print("scanning")
        devices = self.scan_for_ftms()

        for ftms in devices:
            print("FTMS Measurement Device Found!", ftms.alias)
            self.connect_and_run(ftms)
            break
            # Only demo the first device found
        print("No FTMS found.")

    def connect_and_run(self, dev=None):
        """
        Main function intended to show usage of central.Central
        :param dev: Device to connect to if scan was performed
        """

        # Create Interface to Central
        dongle = adapter.Adapter(adapter_addr=dev.adapter)

        if not dongle.powered:
            dongle.powered = True
        monitor = central.Central(
            adapter_addr=dev.adapter,
            device_addr=dev.address)

        # Characteristics that we're interested must be added to the Central
        # before we connect, so they automatically resolve BLE properties

        measurement_char_tm = monitor.add_characteristic(self.ftms_srv, self.tm_data_uuid)
        measurement_char_fm = monitor.add_characteristic(self.ftms_srv, self.fm_data_uuid)
        measurement_char_ts = monitor.add_characteristic(self.ftms_srv, self.ts_data_uuid)

        # FTMS Control Point - write
        control_point_char = monitor.add_characteristic(self.ftms_srv, self.ftms_ctr_pt_uuid)

        # Now Connect to the Device
        print("Connecting to " + dev.alias)

        monitor.connect()

        while not monitor.connected:
            time.sleep(3)
            if not monitor.connected:
                monitor.connect()

        # Check if Connected Successfully
        if not monitor.connected:
            print("Didn't connect to device!")
            return
        else:
            print("BLE_central connected")
            print(time.time())

        # Enable notifications
        measurement_char_tm.start_notify()
        measurement_char_tm.add_characteristic_cb(self.on_new_ftms_measurement)

        measurement_char_fm.start_notify()
        measurement_char_fm.add_characteristic_cb(self.on_new_fm_measurement)

        measurement_char_ts.start_notify()
        measurement_char_ts.add_characteristic_cb(self.on_new_ts_measurement)

        central_thread = threading.Thread(target=central_handler, args=(monitor,))
        central_thread.start()
        try:
            while not self.stop_event.wait(0.25):
                if monitor.connected:
                    if self.ftms_control_value[0] is True:
                        # Write the Control Point Value
                        control_point_char.write_value(self.ftms_control_value[2], flags={})
                        self.ftms_control_value[0] = False
                        self.ftms_control_value[1] = True
                else:
                    print(time.time())
                    print("Central Device disconnected, trying to reconnect")
                    if dev:
                        dongle = adapter.Adapter(adapter_addr=dev.adapter)
                        subprocess.run((['bluetoothctl', 'remove', dev.address]))
                        dongle.powered = False
                        time.sleep(0.5)
                        dongle.powered = True
                        time.sleep(1)
                        subprocess.run((['bluetoothctl', 'remove', dev.address]))
                        print("scanning")
                        devices = self.scan_for_ftms()
                        for ftms in devices:
                            print("FTMS Measurement Device Found!", ftms.alias)
                            self.connect_and_run(ftms)
                            break
                        # Only demo the first device found
                        print("No FTMS found.")

        except dbus.exceptions.DBusException:
            print("Central Device disconnected, trying to reconnect")
            if dev:
                # central_thread.join()
                dongle = adapter.Adapter(adapter_addr=dev.adapter)
                subprocess.run((['bluetoothctl', 'remove', dev.address]))
                dongle.powered = False
                time.sleep(0.5)
                dongle.powered = True
                time.sleep(1)
                subprocess.run((['bluetoothctl', 'remove', dev.address]))
                print("scanning")
                devices = self.scan_for_ftms()
                for ftms in devices:
                    print("FTMS Measurement Device Found!", ftms.alias)
                    self.connect_and_run(ftms)
                    break
                # Only demo the first device found
                print("No FTMS found.")

        print("Disconnecting")

        if dev:
            dongle = adapter.Adapter(adapter_addr=dev.adapter)
            time.sleep(1.5)
            dongle.powered = False
            time.sleep(0.3)
            dongle.powered = True

    # central_thread.join()

    def on_new_fm_measurement(self, iface, changed_props, invalidated_props):

        test_value = changed_props.get('Value', None)
        if not test_value:
            return
        else:
            self.ftms_status_value = test_value

    def on_new_ts_measurement(self, iface, changed_props, invalidated_props):

        test_value = changed_props.get('Value', None)
        if not test_value:
            return
        else:
            self.training_status_value = test_value

    def on_new_ftms_measurement(self, iface, changed_props, invalidated_props):
        """
        Callback used to receive notification events from the device.
        :param iface: dbus advanced data
        :param changed_props: updated properties for this event, contains Value
        :param invalidated_props: dbus advanced data
        """

        test_value = changed_props.get('Value', None)
        if not test_value:
            return
        else:
            self.value = test_value

        payload = self.value[2:]

        fmt = '<HHBHHHHBBH'
        self.values = list(struct.unpack(fmt, bytes(payload[0:struct.calcsize(fmt)])))

    def scan_for_ftms(self):
        """
        Called to scan for BLE devices advertising the FTMS Service UUID
        If there are multiple adapters on your system, this will scan using
        all dongles unless an adapter is specified through its MAC address
        """
        # If there are multiple adapters on your system, this will scan using
        # all dongles unless an adapter is specified through its MAC address
        print(self.adapter_address)
        for dongle in adapter.Adapter.available():
            # Filter dongles by adapter_address if specified
            print(dongle.address)
            if self.adapter_address != dongle.address:
                continue

            # Actually listen to nearby advertisements for timeout seconds
            dongle.nearby_discovery(timeout=5.0)

            # Iterate through discovered devices
            for dev in central.Central.available(dongle.address):
                print(dev.address)
                if self.ftms_srv.lower() in dev.uuids:
                    if self.blacklist_address != dev.address:
                        yield dev
