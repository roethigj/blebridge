"""Example of how to create a Central device/GATT Client"""
import struct
import time
import threading

from bluezero import adapter
from bluezero import central

FTMS_SRV = '00001826-0000-1000-8000-00805f9b34fb'
TM_DATA_UUID = '00002acd-0000-1000-8000-00805f9b34fb'
FM_DATA_UUID = '00002ada-0000-1000-8000-00805f9b34fb'
TS_DATA_UUID = '00002ad3-0000-1000-8000-00805f9b34fb'
FTMS_CTRL_PT_UUID = '00002ad9-0000-1000-8000-00805f9b34fb'

values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
value = struct.pack('<BBHHBHHHHBBH', 140, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
ftms_status_value = struct.pack('<B', 0)
training_status_value = struct.pack('<B', 0)
ftms_control_value = [False, True, struct.pack('<B', 1)]


def scan_for_ftms(
        adapter_address=None,
        ftms_address=None,
        timeout=5.0,
        **kwargs):
    """
    Called to scan for BLE devices advertising the FTMS Service UUID
    If there are multiple adapters on your system, this will scan using
    all dongles unless an adapter is specified through its MAC address
    :param adapter_address: limit scanning to this adapter MAC address
    :param ftms_address: scan for a specific peripheral MAC address
    :param timeout: how long to search for devices in seconds
    :return: generator of Devices that match the search parameters
    """
    # If there are multiple adapters on your system, this will scan using
    # all dongles unless an adapter is specified through its MAC address
    blacklist_address = kwargs.get('blacklist_address', None)
    print(adapter_address)
    for dongle in adapter.Adapter.available():
        # Filter dongles by adapter_address if specified
        print(dongle.address)
        if adapter_address != dongle.address:
            continue

        # Actually listen to nearby advertisements for timeout seconds
        dongle.nearby_discovery(timeout=timeout)

        # Iterate through discovered devices
        for dev in central.Central.available(dongle.address):
            # Filter devices if we specified a FTMS address
            print(dev.address)
            if ftms_address == dev.address:
                yield dev

            # Otherwise, return devices that advertised the FTMS Service UUID
            if FTMS_SRV.lower() in dev.uuids:
                if blacklist_address != dev.address:
                    yield dev


def on_new_fm_measurement(iface, changed_props, invalidated_props):
    global ftms_status_value

    test_value = changed_props.get('Value', None)
    if not test_value:
        return
    else:
        ftms_status_value = test_value


def on_new_ts_measurement(iface, changed_props, invalidated_props):
    global training_status_value

    test_value = changed_props.get('Value', None)
    if not test_value:
        return
    else:
        training_status_value = test_value


def on_new_ftms_measurement(iface, changed_props, invalidated_props):
    """
    Callback used to receive notification events from the device.
    :param iface: dbus advanced data
    :param changed_props: updated properties for this event, contains Value
    :param invalidated_props: dbus advanced data
    """
    global values
    global value

    test_value = changed_props.get('Value', None)
    if not test_value:
        return
    else:
        value = test_value

    payload = value[2:]

    fmt = '<HHBHHHHBBH'
    values = list(struct.unpack(fmt, bytes(payload[0:struct.calcsize(fmt)])))


def central_handler(ftms_monitor):
    ftms_monitor.run()


def connect_and_run(dev=None, device_address=None, stop_event=None):
    """
    Main function intended to show usage of central.Central
    :param dev: Device to connect to if scan was performed
    :param device_address: instead, connect to a specific MAC address
    :param stop_event: event to stop loop
    """
    global ftms_control_value

    # Create Interface to Central
    if dev:
        dongle = adapter.Adapter(adapter_addr=dev.adapter)

        if not dongle.powered:
            dongle.powered = True
        monitor = central.Central(
            adapter_addr=dev.adapter,
            device_addr=dev.address)
    else:
        monitor = central.Central(device_addr=device_address)

    # Characteristics that we're interested must be added to the Central
    # before we connect so they automatically resolve BLE properties

    measurement_char_tm = monitor.add_characteristic(FTMS_SRV, TM_DATA_UUID)
    measurement_char_fm = monitor.add_characteristic(FTMS_SRV, FM_DATA_UUID)
    measurement_char_ts = monitor.add_characteristic(FTMS_SRV, TS_DATA_UUID)

    # FTMS Control Point - write
    control_point_char = monitor.add_characteristic(FTMS_SRV, FTMS_CTRL_PT_UUID)

    # Now Connect to the Device
    if dev:
        print("Connecting to " + dev.alias)
    else:
        print("Connecting to " + device_address)

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

    # Enable notifications
    measurement_char_tm.start_notify()
    measurement_char_tm.add_characteristic_cb(on_new_ftms_measurement)

    measurement_char_fm.start_notify()
    measurement_char_fm.add_characteristic_cb(on_new_fm_measurement)

    measurement_char_ts.start_notify()
    measurement_char_ts.add_characteristic_cb(on_new_ts_measurement)

    central_thread = threading.Thread(target=central_handler, args=(monitor,))
    central_thread.start()

    while not stop_event.wait(0.2):
        if ftms_control_value[0] is True:
            # Write the Control Point Value to reset calories burned
            control_point_char.write_value(ftms_control_value[2], flags={})
            ftms_control_value[0] = False
            ftms_control_value[1] = True

    print("Disconnecting")
    measurement_char_fm.stop_notify()
    measurement_char_tm.stop_notify()
    measurement_char_ts.stop_notify()
    monitor.quit()
    if dev:
        dongle = adapter.Adapter(adapter_addr=dev.adapter)
        time.sleep(1.5)
        dongle.powered = False
        time.sleep(0.3)
        dongle.powered = True
    central_thread.join()


def ble_central(stop_event, adapter_address, **kwargs):
    # Discovery nearby ftms
    blacklist_address = kwargs.get('blacklist_address', None)

    dongle = adapter.Adapter(adapter_addr=adapter_address)

    if not dongle.powered:
        dongle.powered = True

    device_address = None
    print("scanning")
    devices = scan_for_ftms(adapter_address=adapter_address, blacklist_address=blacklist_address)

    for ftms in devices:
        print("FTMS Measurement Device Found!", ftms.alias)

        connect_and_run(ftms, device_address, stop_event)
        break
        # Only demo the first device found
    print("No FTMS found.")
