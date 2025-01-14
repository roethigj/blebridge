# BLE Bridge - Python Script to connect BLE FTM to several Devices

The intention was to connect my treadmill, which is a FTMS device with my Garmin Forerunner, which only can connect via ANT+. 
The reason, I wanted to have the "Running Dynamics" from my HRM pro, whis was connected to my Forerunner too.

In addition I didn't wanted to loose the ability to control my treadmill with the app on my mobile, which gives me structured trainings.


## Requirments

1. `bluezero`
2. `openant`
3. Bluetooth adapter to connec to FTMS (treadmill)
4. ANT+ Adapter to connect to Forerunner (as stride sensor: pace and distance)
5. Bluetooth adapter to connect to mobile for control


## Usage
clone/ download git
run python blebridge.py

## Hints
some Bluetooth Adapters don't connect well to FTMS's. You may switch the adapter in blebridge.py header.
