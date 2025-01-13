import time

from utils import str_to_byte_arr
import dbus
import struct
from bluezero import async_tools

treadmill_values = struct.pack('<BBHHBHHHHBBH', 140, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
ftms_status_value = struct.pack('<B', 0)
ftms_status_value_old = struct.pack('<B', 0)
training_status_value = struct.pack('<B', 0)
training_status_value_old = struct.pack('<B', 0)
ftms_control_value = [False, True, struct.pack('<B', 0)]


def device_information_read():
    return str_to_byte_arr('BLE_Bridge')


def model_number_read():
    return str_to_byte_arr('1')


def serial_number_read():
    return str_to_byte_arr('1234')


def hard_rev_read():
    return str_to_byte_arr('1.0')


def firm_rev_read():
    return str_to_byte_arr('1.0')


def soft_rev_read():
    return str_to_byte_arr('1.0')


def fitness_machine_feature_read():
    fmf = [0x0D,
           0x16,
           0x00,
           0x00,
           0x03,
           0x00,
           0x00,
           0x00]
    #    ]
    fmf_array = dbus.Array(fmf, signature=dbus.Signature("y"))
    return fmf_array


def update_treadmill(characteristic):
    global treadmill_values
    new_value = treadmill_values
    characteristic.set_value(new_value)
    return characteristic.is_notifying


def treadmill_notify(notifying, characteristic):
    if notifying:
        async_tools.add_timer_ms(250, update_treadmill, characteristic)


def speed_range_read():
    speed_range = [0x64, 0x00,  # Minimum speed UInt: 64 00 = 100 = 1.00km/h
                   0x40, 0x06,  # Maximum speed UInt: 04 06 = 1600 = 16.00km/h
                   0x0A, 0x00]
    speed_range_array = dbus.Array(speed_range, signature=dbus.Signature("y"))
    return speed_range_array


def inclination_range_read():
    speed_range = [0x00, 0x00,  # Minimum inclination UInt: 00 00 = 0 = 0
                   0x64, 0x00,  # Maximum inclination UInt: 64 00 = 100 = 10.0
                   0x05, 0x00]
    speed_range_array = dbus.Array(speed_range, signature=dbus.Signature("y"))
    return speed_range_array


def update_ftms_status(characteristic):
    global ftms_status_value
    global ftms_status_value_old
    if ftms_status_value != ftms_status_value_old:
        new_value = ftms_status_value
        characteristic.set_value(new_value)
        ftms_status_value_old = ftms_status_value
    return characteristic.is_notifying


def ftms_status_notify(notifying, characteristic):
    if notifying:
        async_tools.add_timer_ms(75, update_ftms_status, characteristic)


def update_training_status(characteristic):
    global training_status_value
    global training_status_value_old
    if training_status_value != training_status_value_old:
        new_value = training_status_value
        characteristic.set_value(new_value)
        training_status_value_old = training_status_value
    return characteristic.is_notifying


def training_status_read():
    return training_status_value


def training_status_notify(notifying, characteristic):
    if notifying:
        async_tools.add_timer_ms(75, update_training_status, characteristic)


def ftms_control_point_write(value, options):
    global ftms_control_value
    ftms_control_value = [True, False, value]
    print("control_point1 - ftms", time.process_time(), value)
    return


services = {'180A': {'2A29': [str_to_byte_arr('BLE_Bridge'),
                              False,
                              ['read'],
                              device_information_read,
                              None,
                              None],
                     '2A24': [str_to_byte_arr('1'),
                              False,
                              ['read'],
                              model_number_read,
                              None,
                              None],
                     '2A25': [str_to_byte_arr('1234'),
                              False,
                              ['read'],
                              serial_number_read,
                              None,
                              None],
                     '2A27': [str_to_byte_arr('1.0'),
                              False,
                              ['read'],
                              hard_rev_read,
                              None,
                              None],
                     '2A26': [str_to_byte_arr('1.0'),
                              False,
                              ['read'],
                              firm_rev_read,
                              None,
                              None],
                     '2A28': [str_to_byte_arr('1.0'),
                              False,
                              ['read'],
                              soft_rev_read,
                              None,
                              None]},
            '1826': {'2ACC': [[],
                              False,
                              ['read'],
                              fitness_machine_feature_read,
                              None,
                              None],
                     '2ACD': [[],
                              False,
                              ['notify'],
                              None,
                              None,
                              treadmill_notify],
                     '2AD4': [[],
                              False,
                              ['read'],
                              speed_range_read,
                              None,
                              None],
                     '2AD5': [[],
                              False,
                              ['read'],
                              inclination_range_read,
                              None,
                              None],
                     '2ADA': [[],
                              False,
                              ['notify'],
                              None,
                              None,
                              ftms_status_notify],
                     '2AD3': [[],
                              False,
                              ['read', 'notify'],
                              training_status_read,
                              None,
                              training_status_notify],
                     '2AD9': [[],
                              False,
                              ['write'],
                              None,
                              ftms_control_point_write,
                              None]
                     }
            }
