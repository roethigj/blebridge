# ANT+ - Stride Based Speed and Distance Sensor Example
#
# SDM demo working with OpenAnt Library (https://github.com/Tigge/openant)
# using feature of:
# - acting as Transmitting Device (TX-Broadcast)
# - gracefully close ANT-Channels
#
# For further details on Speed & Distance Sensor, check out the thisisant.com webpage

import logging
import time
import asyncio
import threading

from openant.easy.node import Node
from openant.easy.channel import Channel
from openant.base.commons import format_list

from pyftms import FitnessMachine, FtmsEvents, get_client
from pyftms.client import discover_ftms_devices

# Definition of Variables
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]
Device_Type = 124  # 124 = Stride & Distance Sensor
Device_Number = 12345  # Change if you need.
Channel_Period = 8134
Channel_Frequency = 57

# Fictive Config of Treadmill
TreadmillSpeed = 0 # m/s => 10km/h
TreadmillCadence = 160
TreadmillDistance = 0

##########################################################################

def on_event(event: FtmsEvents):
    global TreadmillSpeed, TreadmillDistance
    if event.event_id == 'update':
        if 'speed_instant' in event.event_data:
            print((f"speed! {event.event_data['speed_instant']}"))
            TreadmillSpeed = event.event_data['speed_instant'] / 3.6
        if 'distance_total' in event.event_data:
            print((f"distance! {event.event_data['distance_total']}"))
            TreadmillDistance = event.event_data['distance_total']

def on_disconnect(m: FitnessMachine):
    print("Fitness Machine disconnected.")

async def run_ble(stop_event):
    print("Scanning for available FTMS devices...")

    lst = []

    async for dev, machine_type in discover_ftms_devices(discover_time=3):
        lst.append((dev, machine_type))

        print(
            f"{len(lst)}. {machine_type.name}: name: {dev.name}, address: {dev.address}"
        )

    for dev, machine_type in lst:
        print(
            f"\nConnection to {machine_type.name}: name: {dev.name}, address: {dev.address}"
        )

        async with get_client(dev, machine_type, on_ftms_event=on_event) as c:
            print(f" 1. Device Info: {c.device_info}")
            print(f" 2. Supported settings: {c.supported_settings}")
            print(f" 3. Supported properties: {c.supported_properties}")
            print(f" 4. Available properties: {c.available_properties}")
            while not stop_event.wait(1):
                print('ble alive;)')
                await asyncio.sleep(2)



    print("\nDone.")

class AntSendDemo:
    def __init__(self):

        self.ANTMessageCount = 0
        self.ANTMessagePayload = [0, 0, 0, 0, 0, 0, 0, 0]

        # Init Variables, needed
        self.LastStrideTime = 0
        self.StridesDone = 0
        self.DistanceAccu = 0
        self.Distance_Last = 0
        self.Speed_Last = 0
        self.TimeRollover = 0
        self.treadmill_distance_old = 0

        self.TimeProgramStart = time.time()
        self.LastTimeEvent = time.time()

        self.node = Node()

        # Building up the Datapages
        # This is just for demo purpose and can/will look diverent for every implementation

    def Create_Next_DataPage(self):
        # Define Variables
        UpdateLatency_7 = 0

        self.ANTMessageCount += 1

        # Time Calculations
        self.ElapsedSseconds = time.time() - self.LastTimeEvent
        self.LastTimeEvent = time.time()
        UpdateLatency_7 += self.ElapsedSseconds  # 1Second / 32 = 0,03125
        UL_7 = int(UpdateLatency_7 / 0.03125)

        # Stride Count, Accumulated strides.
        # This value is incremented once for every two footfalls.
        StrideCountUpValue = 60.0 / (TreadmillCadence / 2.0)  # In our Example 0,75
        while self.LastStrideTime > StrideCountUpValue:
            self.StridesDone += 1
            self.LastStrideTime -= StrideCountUpValue
        self.LastStrideTime += self.ElapsedSseconds
        if self.StridesDone > 255:
            self.StridesDone -= 255

        # DISTANCE
        # Accumulated distance, in m-Meters, Rollover = 256
        #self.DistanceBetween = self.ElapsedSseconds * TreadmillSpeed
        self.treadmill_distance_delta = TreadmillDistance - self.treadmill_distance_old
        self.treadmill_distance_old = TreadmillDistance
        self.DistanceAccu += (
            self.treadmill_distance_delta
        )  # Add Distance between 2 ANT+ Ticks to Accumulated Distance
        if self.DistanceAccu > 255:
            self.DistanceAccu -= 255

        self.distance_H = int(self.DistanceAccu)  # just round it to INT
        self.DistanceLow_HEX = int((self.DistanceAccu - self.distance_H) * 16)

        # SPEED - Calculation
        if TreadmillSpeed > 0:
            pace = 1 / (TreadmillSpeed * 3.6 / 60)
            pace_fast = pace   # - (5 / 60) -> necessary?
            speed_fast = (1 / pace_fast) * 60 / 3.6
        else:
            speed_fast = 0

        self.var_speed_ms_H = int(speed_fast)  # INT-Value
        self.var_speed_ms_L = int(speed_fast * 1000) - (self.var_speed_ms_H * 1000)
        self.var_speed_ms_L_HEX = int((speed_fast - self.var_speed_ms_H) * 256)

        # TIME (changes to Distance or speed will effect if This byte needs to be calculated (<= check Specifikation)
        if self.Speed_Last != TreadmillSpeed or self.Distance_Last != self.DistanceAccu:
            self.TimeRollover += self.ElapsedSseconds
            if self.TimeRollover > 255:
                self.TimeRollover -= 255

        self.TimeRollover_H = int(self.TimeRollover)
        # only integer
        if self.TimeRollover_H > 255:
            self.TimeRollover_H = 255
        self.TimeRollover_L_HEX = int((self.TimeRollover - self.TimeRollover_H) * 200)
        if self.TimeRollover_L_HEX > 255:
            self.TimeRollover_L_HEX -= 255
        self.Speed_Last = TreadmillSpeed
        self.Distance_Last = self.DistanceAccu

        if self.ANTMessageCount < 3:
            self.ANTMessagePayload[0] = 80  # DataPage 80
            self.ANTMessagePayload[1] = 0xFF
            self.ANTMessagePayload[2] = 0xFF  # Reserved
            self.ANTMessagePayload[3] = 1  # HW Revision
            self.ANTMessagePayload[4] = 1
            self.ANTMessagePayload[5] = 1  # Manufacturer ID
            self.ANTMessagePayload[6] = 1
            self.ANTMessagePayload[7] = 1  # Model Number

        elif self.ANTMessageCount > 64 and self.ANTMessageCount < 67:
            self.ANTMessagePayload[0] = 81  # DataPage 81
            self.ANTMessagePayload[1] = 0xFF
            self.ANTMessagePayload[2] = 0xFF  # Reserved
            self.ANTMessagePayload[3] = 1  # SW Revision
            self.ANTMessagePayload[4] = 0xFF
            self.ANTMessagePayload[5] = 0xFF  # Serial Number
            self.ANTMessagePayload[6] = 0xFF
            self.ANTMessagePayload[7] = 0xFF  # Serial Number

        else:
            self.ANTMessagePayload[0] = 0x01  # Data Page 1
            self.ANTMessagePayload[1] = self.TimeRollover_L_HEX
            self.ANTMessagePayload[2] = self.TimeRollover_H  # Reserved
            self.ANTMessagePayload[3] = self.distance_H  # Distance Accumulated INTEGER
            # BYTE 4 - Speed-Integer & Distance-Fractional
            self.ANTMessagePayload[4] = (
                self.DistanceLow_HEX * 16 + self.var_speed_ms_H
            )  # Instaneus Speed, Note: INTEGER
            self.ANTMessagePayload[
                5
            ] = self.var_speed_ms_L_HEX  # Instaneus Speed, Fractional
            self.ANTMessagePayload[6] = self.StridesDone  # Stride Count
            self.ANTMessagePayload[7] = UL_7  # Update Latency

            # ANTMessageCount reset
            if self.ANTMessageCount > 131:
                self.ANTMessageCount = 0

        return self.ANTMessagePayload

    # TX Event
    def on_event_tx(self, data):
        ANTMessagePayload = self.Create_Next_DataPage()
        self.ActualTime = time.time() - self.TimeProgramStart

        # ANTMessagePayload = array.array('B', [1, 255, 133, 128, 8, 0, 128, 0])    # just for Debuggung pourpose

        self.channel.send_broadcast_data(
            self.ANTMessagePayload
        )  # Final call for broadcasting data
        #print(
        #    self.ActualTime,
        #    "TX:",
        #    Device_Number,
        #    ",",
        #    Device_Type,
        #    ":",
        #    format_list(ANTMessagePayload),
        #)

    def node_handler(self):
        self.node.start()

    # Open Channel
    def OpenChannel(self, stop_event):

        # self.node = Node()  # initialize the ANT+ device as node, now in init
        #self.x = asyncio.create_task(self.run_ble())

        # CHANNEL CONFIGURATION
        self.node.set_network_key(0x00, NETWORK_KEY)  # set network key
        self.channel = self.node.new_channel(
            Channel.Type.BIDIRECTIONAL_TRANSMIT, 0x00, 0x00
        )  # Set Channel, Master TX
        self.channel.set_id(
            Device_Number, Device_Type, 5
        )  # set channel id as <Device Number, Device Type, Transmission Type>
        self.channel.set_period(Channel_Period)  # set Channel Period
        self.channel.set_rf_freq(Channel_Frequency)  # set Channel Frequency

        # Callback function for each TX event
        self.channel.on_broadcast_tx_data = self.on_event_tx

        self.channel.open()  # Open the ANT-Channel with given configuration
        node_thread = threading.Thread(target=self.node_handler)
        node_thread.start()
        while not stop_event.wait(1):
            time.sleep(4)
            print("node läuft")

        print("Closing ANT+ Channel...")
        self.channel.close()
        self.node.stop()


        print("Closed ANT+ Channel...")


###########################################################################################################################


def main():
    pill2kill = threading.Event()
    pill2kill2 = threading.Event()


    print("ANT+ Send Broadcast Demo")
    # logging.basicConfig(
    #     filename="example.log", level=logging.DEBUG
    # )  # just for Debugging purpose, outcomment this in live version


    ant_senddemo = AntSendDemo()
    ant_thread = threading.Thread(target=ant_senddemo.OpenChannel, args=(pill2kill2,))
    #ant_thread.daemon = True
    ble_thread = threading.Thread(target=asyncio.run, args=(run_ble(pill2kill),))
    #ble_thread.daemon = True



    try:
        ant_thread.start()  # start
        ble_thread.start()
        while True:
            print('still alive;)')
            time.sleep(3)
    except KeyboardInterrupt:
        pill2kill.set()
        pill2kill2.set()
        ble_thread.join()
        ant_thread.join()
        pass

    #pill2kill.set()

   # ble_thread.join()
    #ant_thread.join()
    logging.shutdown()
    print("Close demo...")


if __name__ == "__main__":
    main()