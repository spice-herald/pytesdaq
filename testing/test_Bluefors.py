#Yue's code following the Bluefors Tmeperature Controller API Manual
# Import needed libraries
import sys
import json
import requests
import time
# Define your device IP here
# Timeout for http operations (in seconds) TIMEOUT = 10
TIMEOUT = 10

def set_power(powersetpoint):
    if powersetpoint>1e-4 :
        print("set power too high!!!")
        return
    else :
        # --- Update settings
        # 'max_power' in Watts
        # 'target_temperature in K
        url = 'http://192.168.10.12:5001/heater/update'
        data = {
            'heater_nr': 4,
            'max_power': powersetpoint,
            'power': powersetpoint,
            'pid_mode': 0,
            'active': True
        }
        #
        req = requests.post(url, json=data, timeout=TIMEOUT)
        data = req.json()
        #
        print('Response: \n{}'.format(json.dumps(data, indent=2)))
        return

def set_temperature(setpoint):
    if setpoint>0.7 :
        print("set point too hot!!!")
        return
    else :
        # --- Update settings
        # 'max_power' in Watts
        # 'target_temperature in K
        url = 'http://192.168.10.12:5001/heater/update'
        data = {
            'heater_nr': 4,
            'max_power': setpoint*setpoint*0.02,#.00005,
            'power': setpoint*setpoint*0.0066,
            'target_temperature': setpoint,
            'target_temperature_shown': True,
            'setpoint': setpoint,
            'pid_mode': 1,
            'control_algorithm_settings': {
                'proportional': 0.0055,
                'integral': 80,
                'derivative': 0
            },
            'active': True
        }
        #
        req = requests.post(url, json=data, timeout=TIMEOUT)
        data = req.json()
        #
        print('Response: \n{}'.format(json.dumps(data, indent=2)))
        return

def waitForStableT(setpoint):
    url = 'http://192.168.10.12:5001/channel/measurement/latest'
    req = requests.get(url, timeout=TIMEOUT)
    data = req.json()
    temperature = data['temperature']
    resistance = data['resistance']
    if resistance>11.75e3 :
        temperature = 0.007
    oldtemperature = temperature
    while (temperature/setpoint-1)**2>1e-6 or (temperature/oldtemperature-1)**2>1e-6:
        oldtemperature = temperature
        time.sleep(10)
        req = requests.get(url, timeout=TIMEOUT)
        data = req.json()
        temperature = data['temperature']
        resistance = data['resistance']
        if resistance>11.75e3 :
            temperature = 0.007
        sys.stdout.write('\033[K'+'Waiting... T = '+str(temperature)+'\r')
    sys.stdout.write('\n')
    print("Set point reached!")
    return

if __name__ == "__main__":
    setpoint = float(sys.argv[1])
    wait = bool(sys.argv[2])
    set_power(5e-5)
    time.sleep(5)
    set_temperature(setpoint)
    if wait:
        waitForStableT(setpoint)
