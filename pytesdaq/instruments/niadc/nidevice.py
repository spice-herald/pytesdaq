
import numpy as np
import nidaqmx
import time



class NIDevice(object):

    """
    TBD
    """
    
    @staticmethod
    def get_devices_properties():
        ni_system = nidaqmx.system.system.System()
        device_properties = dict()
        for device in ni_system.devices:
            properties = dict()
            properties['product_type']= device.product_type
            properties['sampling_modes'] = device.ai_samp_modes
            properties['trigger_usage'] = device.ai_trig_usage
            properties['is_continuous_supported'] = device.ai_simultaneous_sampling_supported
            properties['max_sampling_rate'] = device.ai_max_multi_chan_rate
            properties['voltage_ranges'] = device.ai_voltage_rngs
            device_properties[ device.name] = properties
        return device_properties


    @staticmethod
    def get_device_list():
        devices = list()
        ni_system = nidaqmx.system.system.System()
        for device in ni_system.devices:
            devices.append(device.name)
        return devices

    @staticmethod
    def get_product_type(device_name='Dev1'):
        product_type = str()
        ni_system = nidaqmx.system.system.System()
        for device in ni_system.devices:
            if device.name == device_name: 
                product_type = device.product_type
        return product_type

    @staticmethod
    def get_max_sampling_rate(device_name='Dev1'):
        max_sampling_rate = []
        ni_system = nidaqmx.system.system.System()
        for device in ni_system.devices:
            if device.name == device_name: 
                max_sampling_rate = int(round(device.ai_max_multi_chan_rate))
        return max_sampling_rate
