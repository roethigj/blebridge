import logging
import asyncio
import threading
import time
import ftms
from antsend import AntSend
from bluezero import adapter
import ble_central

from ble_peripheral import FtmsPeripheral

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


async def update_ble_out(ble_out_obj,
                         values,
                         ftms_status_value,
                         training_status_value):
    try:
        ble_out = ble_out_obj
        ble_out.treadmill_data_values = values
        ble_out.ftms_status_value = ftms_status_value
        ble_out.training_status_value = training_status_value

    except asyncio.CancelledError:
        print("ble update was cancelled!")
        raise asyncio.CancelledError


async def update_ble_in(ble_in_obj,
                        ftms_control_value):
    try:
        ble_in = ble_in_obj
        if ftms_control_value[0] is True:
            print("control_point3 - bridge", time.process_time(), ftms_control_value)
            # ftms_control_value[0] = False
            ble_in.ftms_control_value = ftms_control_value

    except asyncio.CancelledError:
        print("ble in update was cancelled!")
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
        ble_in = ble_central
        ble_in_thread = threading.Thread(target=ble_in.ble_central, args=(pill2kill, a[0].address))

        ble_out = FtmsPeripheral(a[0].address)
        ble_out_thread = threading.Thread(target=ble_out.ftms_peripheral_start,
                                          args=(pill2kill3, have_to_work,))

    else:
        have_to_work = True
        ble_in = ble_central
        ble_in_thread = threading.Thread(target=ble_in.ble_central, args=(pill2kill, a[1].address, ),
                                         kwargs={'blacklist_address': a[0].address})

        ble_out = FtmsPeripheral(a[0].address)
        ble_out_thread = threading.Thread(target=ble_out.ftms_peripheral_start,
                                          args=(pill2kill3, have_to_work,))

    ant_send = AntSend()
    ant_thread = threading.Thread(target=ant_send.openchanel, args=(pill2kill2,))

    try:
        ant_thread.start()  # start
        ble_in_thread.start()
        ble_out_thread.start()

        while True:
            # print(ble_central.values)

            try:
                task1 = asyncio.create_task(update_ant(ant_send, ble_central.values))
                task2 = asyncio.create_task(update_ble_out(ble_out,
                                                           ble_central.value,
                                                           ble_central.ftms_status_value,
                                                           ble_central.training_status_value))
                task3 = asyncio.create_task(update_ble_in(ble_in, ftms.ftms_control_value))
                task4 = asyncio.create_task(move_on(0.2))

                await asyncio.gather(*[task1, task2, task3, task4])
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
