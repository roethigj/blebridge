import time
import threading

from openant.easy.node import Node
from openant.easy.channel import Channel

# Fictive Config of Treadmill


# Definition of Variables
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]
Device_Type = 124  # 124 = Stride & Distance Sensor
Device_Number = 12345  # Change if you need.
Channel_Period = 8134
Channel_Frequency = 57


class AntSend:
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
        self.TreadmillSpeed = 0  # m/s
        self.TreadmillCadence = 160
        self.TreadmillDistance = 0

        self.TimeProgramStart = time.time()
        self.LastTimeEvent = time.time()
        self.ElapsedSeconds = 0

        self.node = Node()

        # Building up the Datapages
        # This is just for demo purpose and can/will look different for every implementation

    def Create_Next_DataPage(self):
        # Define Variables
        UpdateLatency_7 = 0

        self.ANTMessageCount += 1

        # Time Calculations
        self.ElapsedSeconds = time.time() - self.LastTimeEvent
        self.LastTimeEvent = time.time()
        UpdateLatency_7 += self.ElapsedSeconds  # 1Second / 32 = 0,03125
        UL_7 = int(UpdateLatency_7 / 0.03125)

        # Stride Count, Accumulated strides.
        # This value is incremented once for every two footfalls.
        StrideCountUpValue = 60.0 / (self.TreadmillCadence / 2.0)  # In our Example 0,75
        while self.LastStrideTime > StrideCountUpValue:
            self.StridesDone += 1
            self.LastStrideTime -= StrideCountUpValue
        self.LastStrideTime += self.ElapsedSeconds
        if self.StridesDone > 255:
            self.StridesDone -= 255

        # DISTANCE
        # Accumulated distance, in m-Meters, Rollover = 256
        # self.DistanceBetween = self.ElapsedSeconds * TreadmillSpeed
        self.treadmill_distance_delta = self.TreadmillDistance - self.treadmill_distance_old
        self.treadmill_distance_old = self.TreadmillDistance
        self.DistanceAccu += (
            self.treadmill_distance_delta
        )  # Add Distance between 2 ANT+ Ticks to Accumulated Distance
        if self.DistanceAccu > 255:
            self.DistanceAccu -= 255

        self.distance_H = int(self.DistanceAccu)  # just round it to INT
        self.DistanceLow_HEX = int((self.DistanceAccu - self.distance_H) * 16)

        # SPEED - Calculation
        self.var_speed_ms_H = int(self.TreadmillSpeed)  # INT-Value
        self.var_speed_ms_L = int(self.TreadmillSpeed * 1000) - (self.var_speed_ms_H * 1000)
        self.var_speed_ms_L_HEX = int((self.TreadmillSpeed - self.var_speed_ms_H) * 256)

        # TIME (changes to Distance or speed will affect if This byte needs to be calculated (<= check Specification)
        if self.Speed_Last != self.TreadmillSpeed or self.Distance_Last != self.DistanceAccu:
            self.TimeRollover += self.ElapsedSeconds
            if self.TimeRollover > 255:
                self.TimeRollover -= 255

        self.TimeRollover_H = int(self.TimeRollover)
        # only integer
        if self.TimeRollover_H > 255:
            self.TimeRollover_H = 255
        self.TimeRollover_L_HEX = int((self.TimeRollover - self.TimeRollover_H) * 200)
        if self.TimeRollover_L_HEX > 255:
            self.TimeRollover_L_HEX -= 255

        self.Speed_Last = self.TreadmillSpeed
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
        self.ANTMessagePayload = self.Create_Next_DataPage()
        self.ActualTime = time.time() - self.TimeProgramStart

        # ANTMessagePayload = array.array('B', [1, 255, 133, 128, 8, 0, 128, 0])    # just for Debugging purpose
        try:
            self.channel.send_broadcast_data(
                self.ANTMessagePayload)
        except OverflowError:
            print('overflow-error: Watch disconnected?')

    def node_handler(self):
        self.node.start()

    # Open Channel
    def openchanel(self, stop_event):

        # self.node = Node()  # initialize the ANT+ device as node, now in init
        # self.x = asyncio.create_task(self.run_ble())

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
            # print("node läuft")

        print("Closing ANT+ Channel...")
        self.channel.close()
        self.node.stop()

        print("Closed ANT+ Channel...")
########################################################################################################################
