import logging
import asyncio
import threading


import ftms
from antsend import AntSend
from bluezero import adapter

from ble_peripheral import FtmsPeripheral
from ble_central import BleCentral

# BLE-Adapter for connection to FTMS (0 or 1)
# BLE-Adapter for connection to mobile will be the other one (1 or 0)
x = 1


logging.basicConfig(level=logging.WARNING)

_LOGGER = logging.getLogger(__name__)


async def update_ant(ant_obj, values):

    ant_send = ant_obj
    try:
        ant_send.TreadmillSpeed = values[0] / 360  # m/s
        ant_send.TreadmillDistance = values[9]
    except asyncio.CancelledError:
        print("ant update was cancelled!")
        raise asyncio.CancelledError


async def update_ble_out(ble_in_obj,
                         ble_out_obj,
                         values,
                         ftms_status_value,
                         training_status_value,
                         ftms_control_value):
    try:
        if ftms_control_value[1] is True:
            ble_out = ble_out_obj
            ble_out.treadmill_data_values = values
            ble_out.ftms_status_value = ftms_status_value
            ble_out.training_status_value = training_status_value
        elif ftms_control_value[0] is True:
            ble_in_obj.ftms_control_value = ftms_control_value

    except asyncio.CancelledError:
        print("ble update was cancelled!")
        raise asyncio.CancelledError


class MoveOnError(Exception):
    pass


async def move_on(pause):
    await asyncio.sleep(pause)
    raise MoveOnError()


async def main():
    pill2kill = threading.Event()
    pill2kill2 = threading.Event()
    pill2kill3 = threading.Event()

    a = list(adapter.Adapter.available())
    if len(a) < 2:
        print("Only one adapter available. No Peripheral!")
        have_to_work = False
        ble_in = BleCentral(stop_event=pill2kill, adapter_address=a[x].address)
        ble_in_thread = threading.Thread(target=ble_in.ble_central_start)

        ble_out = FtmsPeripheral(a[x].address)
        ble_out_thread = threading.Thread(target=ble_out.ftms_peripheral_start,
                                          args=(pill2kill3, have_to_work,))

    else:
        if x == 0:
            y = 1
        else:
            y = 0
        have_to_work = True
        ble_in = BleCentral(stop_event=pill2kill, adapter_address=a[y].address, blacklist_address=a[x].address)
        ble_in_thread = threading.Thread(target=ble_in.ble_central_start)

        ble_out = FtmsPeripheral(a[x].address)
        ble_out_thread = threading.Thread(target=ble_out.ftms_peripheral_start,
                                          args=(pill2kill3, have_to_work,))

    ant_send = AntSend()
    ant_thread = threading.Thread(target=ant_send.openchanel, args=(pill2kill2,))

    try:
        ant_thread.start()  # start
        ble_in_thread.start()
        ble_out_thread.start()

        while True:
            try:
                task2 = asyncio.create_task(update_ble_out(ble_in,
                                                           ble_out,
                                                           ble_in.value,
                                                           ble_in.ftms_status_value,
                                                           ble_in.training_status_value,
                                                           ftms.ftms_control_value))
                task1 = asyncio.create_task(update_ant(ant_send, ble_in.values))
                task3 = asyncio.create_task(move_on(0.25))

                await asyncio.gather(*[task2, task3])
            except MoveOnError:
                pass

            for task in [task1, task2, task3]:
                if task.done() is False:
                    task.cancel()

    except asyncio.CancelledError:
        print("Keyboard Interrupt;)")
    finally:
        pill2kill.set()
        pill2kill2.set()
        pill2kill3.set()
        ble_in_thread.join()
        ble_out_thread.join()
        ant_thread.join()

    logging.shutdown()
    print("Close bridge...")


if __name__ == "__main__":
    asyncio.run(main())
