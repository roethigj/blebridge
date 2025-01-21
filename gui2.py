import sys
import qt_brigde

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSizePolicy
from qt_brigde import BleBridge


class TreadmillGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Treadmill Controller")
        self.layout = QtWidgets.QGridLayout()
        self.layout.setRowStretch(1, 3)
        self.layout.setRowStretch(2, 1)

        self.setLayout(self.layout)

        self.thread = {}

        # Variables for treadmill data
        self.speed = 0.0
        self.pace = "00:00"
        self.distance = 0.000
        self.time_elapsed = "00:00:00"
        self.incline = 0.0
        self.calories = 0
        self.treadmill_dongle = None
        self.peripheral_dongle = None

        # Bluetooth adapter selection
        self.create_connect_disconnect_buttons()

        # Treadmill data display
        self.create_data_display()

        # Control buttons
        self.create_control_buttons()

        # Additional buttons for pace and incline
        self.create_pace_buttons()
        self.create_incline_buttons()

        self.set_button_states(False)

        self.running = False

    def create_connect_disconnect_buttons(self):  # connect and disconnect buttons
        connect_disconnect_group = QtWidgets.QGroupBox("Connect/Disconnect")
        connect_disconnect_layout = QtWidgets.QGridLayout()
        connect_disconnect_group.setLayout(connect_disconnect_layout)
        connect_disconnect_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        connect_disconnect_layout.addWidget(QtWidgets.QLabel("Adapter for Treadmill:"), 0, 0, 1, 1, Qt.AlignRight)
        adapter_combobox = QtWidgets.QComboBox()
        adapters = qt_brigde.get_adapters()
        for adapter in adapters:
            adapter_combobox.addItem(adapter.address + " - " + adapter.name)
        connect_disconnect_layout.addWidget(adapter_combobox, 0, 1, 1, 1)
        self.connect_btn = QtWidgets.QPushButton("Connect")
        connect_disconnect_layout.addWidget(self.connect_btn, 0, 2, 1, 1)
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect and Close")
        connect_disconnect_layout.addWidget(self.disconnect_btn, 0, 3, 1, 1)

        adapter_combobox.currentIndexChanged.connect(self.set_treadmill_dongle)
        if len(adapters) > 1:
            self.treadmill_dongle = adapters[0].address
            self.peripheral_dongle = adapters[1].address
        else:
            self.treadmill_dongle = adapters[0].address

        self.connect_btn.clicked.connect(self.connect)
        self.disconnect_btn.clicked.connect(self.disconnect)

        self.layout.addWidget(connect_disconnect_group, 0, 0, 1, 4)

    def set_treadmill_dongle(self, index):
        if index == 0:
            self.treadmill_dongle = str(self.sender().currentText()).split(" - ")[0]
            self.peripheral_dongle = str(self.sender().itemText(index + 1)).split(" - ")[0]
        else:
            self.treadmill_dongle = str(self.sender().currentText()).split(" - ")[0]
            self.peripheral_dongle = str(self.sender().itemText(index - 1)).split(" - ")[0]

    def connect(self):
        self.sender().setDisabled(True)
        if self.peripheral_dongle is None:
            adapter_lib = [self.treadmill_dongle]
        else:
            adapter_lib = [self.treadmill_dongle,
                           self.peripheral_dongle]
        self.thread[1] = BleBridge(parent=None, adapter_lib=adapter_lib)
        self.thread[1].start()

        self.set_button_states(True)
        self.thread[1].any_signal.connect(self.update_data)

    def update_data(self, data):
        self.speed = data[0]/100
        if data[0] != 0:
            self.pace = str(int(6000/data[0])) + ":" + str(int((6000/data[0] - int(6000/data[0]))*60)).zfill(2)
        else:
            self.pace = "00:00"
        self.distance = data[1]/1000
        if data[9] < 60:
            self.time_elapsed = "00:" + str(data[9]).zfill(2)
        elif data[9] < 3600:
            self.time_elapsed = str(data[9]//60).zfill(2) + ":" + str(data[9] % 60).zfill(2)
        else:
            self.time_elapsed = (str(data[9]//3600) + ":"
                                 + str((data[9] % 3600)//60).zfill(2) + ":"
                                 + str(data[9] % 60).zfill(2))
        self.incline = data[3]/10
        self.calories = data[5]

        for field, value in zip(self.data_fields, [str(self.speed), self.pace, str(self.distance), self.time_elapsed,
                                                   str(self.incline), str(self.calories)]):
            field.setText(str(value))

    def disconnect(self):
        self.thread[1].stop()
        print("Disconnected")
        # self.connect_btn.setEnabled(True)
        # self.close()

    def create_data_display(self):
        data_group = QtWidgets.QGroupBox("Treadmill Data")
        data_layout = QtWidgets.QGridLayout()
        data_group.setLayout(data_layout)
        data_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        data_labels = ["Speed (km/h):", "Pace (min/km):", "Distance (km):", "Time Elapsed:", "Incline (%):",
                       "Calories Burned:"]
        data_values = [str(self.speed), self.pace, str(self.distance), self.time_elapsed, str(self.incline),
                       str(self.calories)]

        self.data_fields = []

        for i, (label, value) in enumerate(zip(data_labels, data_values)):
            lbl = QtWidgets.QLabel(label)
            val = QtWidgets.QLabel(value)
            lbl.setFont(QtGui.QFont("Arial", 16))
            val.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Bold))
            data_layout.addWidget(lbl, i, 0)
            data_layout.addWidget(val, i, 1)
            self.data_fields.append(val)

        self.layout.addWidget(data_group, 1, 1, 1, 2)

    def create_control_buttons(self):
        control_group = QtWidgets.QGroupBox("Controls")
        control_layout = QtWidgets.QGridLayout()
        control_group.setLayout(control_layout)

        self.increase_speed_button = QtWidgets.QPushButton("Increase Speed")
        self.decrease_speed_button = QtWidgets.QPushButton("Decrease Speed")
        self.increase_incline_button = QtWidgets.QPushButton("Increase Incline")
        self.decrease_incline_button = QtWidgets.QPushButton("Decrease Incline")
        self.start_pause_button = QtWidgets.QPushButton("Start/Pause")
        self.stop_button = QtWidgets.QPushButton("Stop")

        for button in [
            self.increase_speed_button, self.decrease_speed_button,
            self.increase_incline_button, self.decrease_incline_button,
            self.start_pause_button, self.stop_button
        ]:
            button.setMinimumSize(40, 40)
            button.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        control_layout.addWidget(self.increase_speed_button, 0, 2)
        control_layout.addWidget(self.decrease_speed_button, 1, 2)
        control_layout.addWidget(self.increase_incline_button, 0, 0)
        control_layout.addWidget(self.decrease_incline_button, 1, 0)
        control_layout.addWidget(self.start_pause_button, 0, 1)
        control_layout.addWidget(self.stop_button, 1, 1)

        self.increase_speed_button.clicked.connect(lambda: self.increase_speed())
        self.decrease_speed_button.clicked.connect(lambda: self.decrease_speed())
        self.increase_incline_button.clicked.connect(lambda: self.increase_incline())
        self.decrease_incline_button.clicked.connect(lambda: self.decrease_incline())
        self.start_pause_button.clicked.connect(self.start_pause)
        self.stop_button.clicked.connect(self.stop)

        self.layout.addWidget(control_group, 2, 0, 1, 4)

    def create_pace_buttons(self):
        pace_group = QtWidgets.QGroupBox("Pace Selection")
        pace_layout = QtWidgets.QVBoxLayout()
        pace_group.setLayout(pace_layout)

        self.pace_buttons = []
        for pace in ["4:00", "4:30", "5:00", "5:30", "6:00"]:
            btn = QtWidgets.QPushButton(f"Set Pace {pace}")
            btn.setMinimumSize(60, 60)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, p=pace: self.set_pace(p))
            self.pace_buttons.append(btn)
            pace_layout.addWidget(btn)

        self.layout.addWidget(pace_group, 1, 0, 1, 1)

    def create_incline_buttons(self):
        incline_group = QtWidgets.QGroupBox("Incline Selection")
        incline_layout = QtWidgets.QVBoxLayout()
        incline_group.setLayout(incline_layout)

        self.incline_buttons = []
        for incline in [0, 2, 4, 6, 8]:
            btn = QtWidgets.QPushButton(f"Set Incline {incline}%")
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, i=incline: self.set_incline(i))
            btn.setMinimumSize(60, 60)
            self.incline_buttons.append(btn)
            incline_layout.addWidget(btn)

        self.layout.addWidget(incline_group, 1, 3, 1, 1)

    def set_button_states(self, enabled):
        buttons = [
            self.disconnect_btn,
            self.increase_speed_button, self.decrease_speed_button,
            self.increase_incline_button, self.decrease_incline_button,
            self.start_pause_button, self.stop_button
        ] + self.pace_buttons + self.incline_buttons

        for button in buttons:
            button.setEnabled(enabled)

    def adjust_speed(self, delta):
        self.speed = max(0, self.speed + delta)
        self.data_fields[0].setText(str(round(self.speed, 1)))

    def adjust_incline(self, delta):
        self.incline = max(0, self.incline + delta)
        self.data_fields[4].setText(str(round(self.incline, 1)))

    def set_pace(self, pace):
        speed = 3600 / ((int((pace.split(":")[0])) * 60) + int(pace.split(":")[1]))
        self.thread[1].set_speed(speed)

    def set_incline(self, incline):
        self.thread[1].set_incline(incline)

    def increase_speed(self):
        self.thread[1].increase_speed()

    def decrease_speed(self):
        self.thread[1].decrease_speed()

    def increase_incline(self):
        self.thread[1].increase_incline()

    def decrease_incline(self):
        self.thread[1].decrease_incline()

    def start_pause(self):
        print("Starting or pausing the treadmill...")
        if self.running is False:
            self.thread[1].start_pause(False)
            self.running = True
        else:
            self.thread[1].start_pause(True)
            self.running = False

    def stop(self):
        print("Stopping the treadmill...")
        self.thread[1].stop_running()
        self.running = False


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = TreadmillGUI()
    window.show()
    app.exec_()
