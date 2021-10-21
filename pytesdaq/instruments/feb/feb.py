import math
import time
from enum import Enum
from pytesdaq.instruments.communication import InstrumentComm
from math import nan


_HEADER = "c4d"
_FOOTER = "00zx"
_READ_COMMAND = "c2x"



class FEBSettings(Enum):
    SENSORBIAS  = 1
    SQUIDBIAS   = 2
    SQUIDLOCK   = 3
    SQUIDGAIN   = 4
    SQUIDDRIVER = 5
    
class FEBChannels(Enum):
    A = 10
    B = 11
    C = 12
    D = 13



class FEB(InstrumentComm):
    """
    FEB control
    """

    def __init__(self, gpib_address, visa_library=None, verbose=False,
                 raise_errors=True):
        
        super().__init__(visa_address=gpib_address,
                         visa_library=visa_library,
                         verbose=verbose,
                         raise_errors=raise_errors)

        self._is_modified = True

        
    def set_phonon_qet_bias(self, subrack, slot, channel, value,
                            millisec_delay = 0.160):
        """
        Set Phonon QET bias
        Value should be [-2000:2000] uA
        """
        if value<-2000:
            print('WARNING: Minimum QET bias value is -2000uA. Setting to -2000uA!')
            value = -2000
        elif value>2000:
            print('WARNING: Maximum QET bias value is 2000uA. Setting to 2000uA!')
            value = 2000

        self._set_param(subrack, slot, FEBSettings.SENSORBIAS.value,
                        channel, value, millisec_delay)
                
        
    def set_phonon_squid_bias(self, subrack, slot, channel,
                              value, millisec_delay = 0.160):
        """
        Set Phonon SQUID bias
        Value should be [-200:200] uA
        """
        if value<-200:
            print('WARNING: Minimum SQUID bias value is -200uA. Setting to -200uA!')
            value = -200
        elif value>200:
            print('WARNING: Maximum SQUID bias value is 200uA. Setting to 200uA!')
            value = 200
        
        self._set_param(subrack, slot, FEBSettings.SQUIDBIAS.value,
                        channel, value, millisec_delay)
                
  
    def set_phonon_lock_point(self,subrack, slot, channel,
                              value, millisec_delay = 0.160):
        """
        Set lock point
        Value should be [-8:8] mV
        """
        if value<-8:
            print('WARNING: Minimum SQUID lock point value is -8mV. Setting to -8mV!')
            value = -8
        elif value>8:
            print('WARNING: Maximum SQUID lock point value is 8mV. Setting to 8mV!')
            value = 8
            
        self._set_param(subrack, slot, FEBSettings.SQUIDLOCK.value,
                        channel, value, millisec_delay)

   
    def set_phonon_preamp_gain(self,subrack, slot, channel,
                               value, millisec_delay = 0.160):
        """
        Set Phonon Preamp Gain
        Value should be [20:100]
        """

        # check min/max
        if value<20:
            print('WARNING: Minimum Preamp gain is 20. Setting to 20!')
            value = 20
        elif value>100:
            print('WARNING: Maxmium Preamp gain is 100. Setting to 100!')
            value = 100
        
        self._set_param(subrack, slot, FEBSettings.SQUIDGAIN.value,
                        channel, value, millisec_delay)

        
    def set_phonon_offset(self,subrack, slot, channel,
                          value, millisec_delay = 0.160):
        """
        Set phonon offset
        Value should be [-5:5] V
        """
        if value<-5:
            print('WARNING: Minimum phonon offset is -5V. Setting to -5V!')
            value = -5
        elif value>5:
            print('WARNING: Maximum phonon offset is 5V. Setting to 5V!')
            value = 5
            
        self._set_param(subrack, slot, FEBSettings.SQUIDDRIVER.value,
                        channel, value, millisec_delay)


    def set_phonon_output_gain(self,subrack, slot, channel,
                               gain, millisec_delay = 0.160):
        """
        Set output gain
        Max gain is +-50
        """

        # list of possible gains
        gain_list = [1, 1.43, 2.0, 5.0, 10.0, 14.3, 20.0, 50.0,
                     -1, -1.43, -2.0, -5.0, -10.0, -14.3, -20.0, -50.0]

        if gain not in gain_list:
            raise Exception("FEB: Invalid gain specified for a phonon channel: " + str(gain))
        

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)
        channel -= 10
            

        # address
        address = (slot << 8) + (14 << 4) + 2

        # get current driver setting
        old_driver_CSR = self._get_param_driver_CSR(subrack, slot)


        # value
        data = 0
        if gain!=1:
            data += gain_list.index(gain) << channel * 4
                    
        for i in range(16):
            if (i != channel * 4
                and i != channel * 4 + 1
                and i != channel * 4 + 2
                and i != channel * 4 + 3):
                data += int(old_driver_CSR[i]) << i

        # write
        time.sleep(millisec_delay)
        self._write_feb(subrack, address, data)

        
    def set_phonon_feedback_loop(self, subrack, slot, channel, closed):
        """
        Set feedback loop to "closed" (=false) or "open (=true)
        """

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)

        if channel < FEBChannels.A.value or channel > FEBChannels.D.value:
            raise Exception("FEB: Invalid channel value specified for feedback loop open/closed: "
                            + str(channel))

        # address
        address = (slot << 8) + (14 << 4) + 1

        # value
        data = 0
        squid_CSR = self._get_param_CSR(subrack, slot)
        if channel == FEBChannels.A.value:
            data += int(not closed)
            for i in range (1, len(squid_CSR)):
                data += int(squid_CSR[i]) << i
                
        elif channel == FEBChannels.B.value:
            data += int(not closed) << 1
            for i in range(0, len(squid_CSR)):
                if i!= 1:
                    data += int(squid_CSR[i]) << i
        elif channel == FEBChannels.C.value:
            data += int(not closed) << 2
            for i in range(0, len(squid_CSR)):
                if i != 2:
                    data += int(squid_CSR[i]) << i
        elif channel == FEBChannels.D.value:
            data += int(not closed) << 3
            for i in range(0, len(squid_CSR)):
                if i != 3:
                    data += int(squid_CSR[i]) << i
                    
        time.sleep(0.16)
        self._write_feb(subrack, address, data)


    def set_phonon_feedback_polarity(self,subrack, slot, channel, inverted):
        """
        Set feedback polarity: inverted = true, non-inverted = false
        """
         # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)

        if channel < FEBChannels.A.value or channel > FEBChannels.D.value:
            raise Exception("FEB: Invalid channel value specified for feedback polarity: "
                            + str(channel))


        # address
        address = (slot << 8) + (14 << 4) + 1

        # value
        data = 0
        squid_CSR = self._get_param_CSR(subrack, slot)
        if channel == FEBChannels.A.value:
            data += int(not inverted) << 4
            for i in range (0, len(squid_CSR)):
                if i != 4:
                    data += int(squid_CSR[i]) << i
        elif channel == FEBChannels.B.value:
            data += int(not inverted) << 5
            for i in range(0, len(squid_CSR)):
                if i!= 5:
                    data += int(squid_CSR[i]) << i
        elif channel == FEBChannels.C.value:
            data += int(not inverted) << 6
            for i in range(0, len(squid_CSR)):
                if i != 6:
                    data += int(squid_CSR[i]) << i
        elif channel == FEBChannels.D.value:
            data += int(not inverted) << 7
            for i in range(0, len(squid_CSR)):
                if i != 7:
                    data += int(squid_CSR[i]) << i
        time.sleep(0.16)
        self._write_feb(subrack, address, data)
       


    def set_phonon_source_preamp(self,subrack, slot, channel, enabled):
        """
        Set signal source to preamp (=true), feedback (=false)
        """
        
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)
            
        if (channel >= FEBChannels.A.value and channel <= FEBChannels.D.value):
            address = (slot << 8) + (14 << 4) + 1
            data = 0
            squid_CSR = self._get_param_CSR(subrack, slot)
            if channel == FEBChannels.A.value:
                data += int(not enabled) << 12
                for i in range (0, len(squid_CSR)):
                    if i != 12:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.B.value:
                data += int(not enabled) << 13
                for i in range(0, len(squid_CSR)):
                    if i!= 13:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.C.value:
                data += int(not enabled) << 14
                for i in range(0, len(squid_CSR)):
                    if i != 14:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.D.value:
                data += int(not enabled) << 15
                for i in range(0, len(squid_CSR)):
                    if i != 15:
                        data += int(squid_CSR[i]) << i
            time.sleep(0.16)
            self._write_feb(subrack, address, data)
        else: 
            raise Exception("FEB: Invalid channel value specified to set signal source: "
                            + str(channel))

        
    def connect_signal_generator_feedback(self,subrack, slot, channel, enabled):
        """
        Connect (true) or disconnect (false) signal generator to feedback
        """

        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)
        
        if (channel >= FEBChannels.A.value and channel <= FEBChannels.D.value):
            address = (slot << 8) + (14 << 4) + 1
            data = 0
            squid_CSR = self._get_param_CSR(subrack, slot)
            if channel == FEBChannels.A.value:
                data += int(enabled) << 8
                for i in range (0, len(squid_CSR)):
                    if i != 8:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.B.value:
                data += int(enabled) << 9
                for i in range(0, len(squid_CSR)):
                    if i!= 9:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.C.value:
                data += int(enabled) << 10
                for i in range(0, len(squid_CSR)):
                    if i != 10:
                        data += int(squid_CSR[i]) << i
            elif channel == FEBChannels.D.value:
                data += int(enabled) << 11
                for i in range(0, len(squid_CSR)):
                    if i != 11:
                        data += int(squid_CSR[i]) << i
            time.sleep(0.16)
            self._write_feb(subrack, address, data)
        else: 
            raise Exception("FEB: Invalid channel value specified for setting SG to FB line:: "
                            + str(channel))



        
    def connect_signal_generator_tes(self,subrack, slot, channel, enable):
        """
        Connect (true) or disconnect (false) signal generator to TES
        """

        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)

        if (channel >= FEBChannels.A.value and channel <= FEBChannels.D.value):
            enable = not enable
            address = (slot << 8) + (14 << 4)
            data = 0
            sense_bias_CSR = self._get_sense_bias(subrack, slot)
            if channel == FEBChannels.A.value:
                data += int(enable)
                for i in range (1, len(sense_bias_CSR)):
                    data += int(sense_bias_CSR[i]) << i
            elif channel == FEBChannels.B.value:
                data += int(enable) << 1
                for i in range(0, len(sense_bias_CSR)):
                    if i!= 1:
                        data += int(sense_bias_CSR[i]) << i
            elif channel == FEBChannels.C.value:
                data += int(enable) << 2
                for i in range(0, len(sense_bias_CSR)):
                    if i != 2:
                        data += int(sense_bias_CSR[i]) << i
            elif channel == FEBChannels.D.value:
                data += int(enable) << 3
                for i in range(0, len(sense_bias_CSR)):
                    if i != 3:
                        data += int(sense_bias_CSR[i]) << i
            time.sleep(0.16)
            self._write_feb(subrack, address, data)
        else: 
            raise Exception("FEB: Invalid channel value specified for setting SG to TES line: "
                            + str(channel))



    def get_phonon_qet_bias(self,subrack, slot, channel, millisec_delay = 0.160):
        """
        Get phonon QET bias

        return:
          float [uA]
        """
        
        return self._get_param(subrack, slot, FEBSettings.SENSORBIAS.value,
                               channel, millisec_delay)


    
    def get_phonon_squid_bias(self,subrack, slot, channel, millisec_delay = 0.160):
        """
        Get phonon SQUID bias

        return:
          float [uA]
        """
        
        return self._get_param(subrack, slot, FEBSettings.SQUIDBIAS.value,
                               channel, millisec_delay)


    
    def get_phonon_lock_point(self, subrack, slot, channel, millisec_delay = 0.160):
        """
        Get phonon SQUID bias

        return:
          float [mV]
        """
        
        return self._get_param(subrack, slot, FEBSettings.SQUIDLOCK.value,
                               channel, millisec_delay)

    
    def get_phonon_preamp_gain(self, subrack, slot, channel, millisec_delay = 0.160):
        """
        Get phonon preamp gain

        return:
          float
        """
        return self._get_param(subrack, slot, FEBSettings.SQUIDGAIN.value,
                               channel, millisec_delay)


    def get_phonon_offset(self, subrack, slot, channel, millisec_delay = 0.160):
        """
        Get phonon output offset

        return:
          float [V]
        """
        return self._get_param(subrack, slot, FEBSettings.SQUIDDRIVER.value,
                               channel, millisec_delay)

    
    
    def get_phonon_output_gain(self, subrack, slot, channel):
        """
        Get phonon output gain (negative gain = inverted)

        return:
          float
        """
        #address = (slot << 8) + (14 << 4) + 2

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)  
        channel -= 10

        # get CSR
        old_driver_CSR = self._get_param_driver_CSR(subrack, slot)
      
        data = 0
        for i in range(channel * 4, channel * 4 + 4):
            if old_driver_CSR[i]:
                data += 1 << (i % 4)
                
        
        # list of possible gains
        gain_list = [1, 1.43, 2.0, 5.0, 10.0, 14.3, 20.0, 50.0,
                     -1, -1.43, -2.0, -5.0, -10.0, -14.3, -20.0, -50.0]

        gain = nan
        if data>=0 and data<16:
            gain = gain_list[int(data)]
        else:
            raise Exception("FEB: Unable to get output gain for channel "
                            + str(channel))
        
        return gain
       

    def is_phonon_feedback_open(self,subrack, slot, channel):
        """
        Is feedback open (true) or closed (false)

        return:
          bool
        """
        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)  

        # get parameters
        squid_CSR = self._get_param_CSR(subrack, slot)

        # return for specified channel
        if channel == FEBChannels.A.value:
            return not squid_CSR[0]
        elif channel == FEBChannels.B.value:
            return not squid_CSR[1]
        elif channel == FEBChannels.C.value:
            return not squid_CSR[2]
        elif channel == FEBChannels.D.value:
            return not squid_CSR[3]
        else:
            raise Exception("FEB: Invalid channel value specified for getSquidFeedbackCO() "
                            + str(channel))

        
        
    def get_phonon_feedback_polarity(self,subrack, slot, channel):
        """
        Feedback polarity: inverted (true), inverted (false)

        return:
          bool
        """

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)

        # read from baord
        squid_CSR = self._get_param_CSR(subrack, slot)

        # return for specified channel
        if channel == FEBChannels.A.value:
            return not squid_CSR[4]
        elif channel == FEBChannels.B.value:
            return not squid_CSR[5]
        elif channel == FEBChannels.C.value:
            return not squid_CSR[6]
        elif channel == FEBChannels.D.value:
            return not squid_CSR[7]
        else:
            raise Exception("FEB: Invalid channel value specified for getSquidFeedbackPolarity(): "
                            + str(channel))

        
    def is_phonon_source_preamp(self,subrack, slot, channel):
        """
        Is signal source preamp (true) or feedback (false)

        return:
          bool
        """

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)  

        # read from board
        squid_CSR = self._get_param_CSR(subrack, slot)

        # return for specified channel
        if channel == FEBChannels.A.value:
            return not squid_CSR[12]
        elif channel == FEBChannels.B.value:
            return not squid_CSR[13]
        elif channel == FEBChannels.C.value:
            return not squid_CSR[14]
        elif channel == FEBChannels.D.value:
            return not squid_CSR[15]
        else:
            raise Exception("FEB: Invalid channel value specified for getSquidFeedbackPreamp() "
                            + str(channel))
                
    def is_signal_generator_feedback_connected(self,subrack, slot, channel):
        """
        Is signal gernetor connected to feedback (true) or feedback (false)

        return:
          bool
        """
        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)  

        # read from board
        squid_CSR = self._get_param_CSR(subrack, slot)

        # return for specified channel
        if channel == FEBChannels.A.value:
            return squid_CSR[8]
        elif channel == FEBChannels.B.value:
            return squid_CSR[9]
        elif channel == FEBChannels.C.value:
            return squid_CSR[10]
        elif channel == FEBChannels.D.value:
            return squid_CSR[11]
        else:
            raise Exception("FEB: Invalid channel value specified for getSquidExternalSignal() "
                            + str(channel))

    def is_signal_generator_tes_connected(self,subrack, slot, channel):
        """
        Is signal gernetor connected to feedback (true) or feedback (false)

        return:
          bool
        """
        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)  

        # read from board
        sense_bias_CSR = self._get_sense_bias(subrack, slot)
        
        # return for specified channel
        if channel == FEBChannels.A.value:
            return not sense_bias_CSR[0]
        elif channel == FEBChannels.B.value:
            return not sense_bias_CSR[1]
        elif channel == FEBChannels.C.value:
            return not sense_bias_CSR[2]
        elif channel == FEBChannels.D.value:
            return not sense_bias_CSR[3]
        else:
            raise Exception("FEB: Invalid channel value specified for getExternalEnable() "
                            + str(channel))




    def _write_feb(self, subrack, address, data):
        """
        Write to FEB
        """
        
        subrack_with_address_bit = subrack | 8
        address_str = _HEADER + self._fourdigit(format(address, "x"))
        address_str += "0" + format(subrack_with_address_bit, "x") + _FOOTER
        data_str = _HEADER + format(data, "x") + "0" + format(subrack, "x") + _FOOTER
        self.write(address_str)
        self.write(data_str)
        time.sleep(0.16)
	

    def _read_feb(self, subrack, address):
        """
        Read from FEB
        """
        subrack_with_address_bit = subrack | 8
        address_str = _HEADER + self._fourdigit(format(address, "x"))
        address_str += "0" + format(subrack_with_address_bit, "x") + _FOOTER
        self.write(address_str)
        data = self.query(_READ_COMMAND)
        return data[:4]



    
    def _fourdigit(self,input_str):
        """
        makes strings that are shorter than 4 digits 4 digits by filling the front with "0"s
        """
        while len(input_str) < 4:
            input_str = "0" + input_str
        return input_str



    def _set_param(self,subrack, slot, setting, channel, value, millisec_delay = 0.160):
        """
        Set FEB parameter
        """

        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)

        # address  number
        address = (slot << 8) + (setting << 4) + channel
        
        # data number
        data = 0
        if setting == FEBSettings.SENSORBIAS.value:
            if self._is_modified:
                data = int(round(4095.0 * (500.0 + value) / 1000.0))
            else:
                data = int(round(4095.0 * (2000.0 + value) / 4000.0)) 
        if setting == FEBSettings.SQUIDBIAS.value:
            data = int(round(4095.0 * (200.0 + value) / 400.0))
        if setting == FEBSettings.SQUIDLOCK.value:
            data = int(round(4095.0 * (8.0 - value) / 16.0))
        if setting == FEBSettings.SQUIDGAIN.value:
            data = int(round(4095.0 * (5.0 - value / 20.0) / 10.0))
        if setting == FEBSettings.SQUIDDRIVER.value:
            data = int(round(4095.0 * (5.0 - value) / 10.0))
        
        time.sleep(millisec_delay)
        self._write_feb(subrack, address, data)
        

    def _get_param(self, subrack, slot, setting, channel, millisec_delay = 0.160):
        """
        Get FEB parameter
        """

        output_val = -999999
        
        # channel
        if isinstance(channel,str):
            channel = int(FEBChannels[channel].value)
                     
        # address  number
        address = (slot << 8) + (setting << 4) + channel
        time.sleep(millisec_delay)

        bias_val_hex = self._read_feb(subrack, address)
        decimal_result = int(bias_val_hex, 16) & 4095

        if setting == FEBSettings.SENSORBIAS.value:
            if self._is_modified:
                output_val = 1000.0 * float(decimal_result) / 4095.0 - 500.0
            else:
                output_val = 4000.0 * float(decimal_result) / 4095.0 - 2000.0
        elif setting == FEBSettings.SQUIDBIAS.value:
            output_val = 400.0 * float(decimal_result) / 4095.0 - 200.0
        elif setting == FEBSettings.SQUIDLOCK.value:
            output_val = -16.0 * float(decimal_result) / 4095.0 + 8.0
        elif setting == FEBSettings.SQUIDGAIN.value:
            output_val = 20.0 * (5.0 - 10.0 * float(decimal_result) / 4095)
        elif setting == FEBSettings.SQUIDDRIVER.value:
            output_val = -(10.0 * float(decimal_result) / 4095.0 - 5.0)
            
        return output_val
    

    def _get_param_driver_CSR(self, subrack, slot):
        """
        Get FEB driver CSR
        """

        # wait
        time.sleep(0.16)
        
        # read
        address = (slot << 8) + (14 << 4) + 2
        driver_csr = self._read_feb(subrack, address)

        # build output
        decimal_result = int(driver_csr, 16)
        output_driver_CSR = [True] * 16
        for inum in range(16):
            output_driver_CSR[inum] = (decimal_result & 2**inum) != 0

        return output_driver_CSR


    
    def _get_param_CSR(self, subrack, slot, millisec_delay = 0.16):
        """
        Get FEB driver CSR
        """
        # wait
        time.sleep(millisec_delay)

        #read 
        address = (slot << 8) + (14 << 4) + 1
        driver_csr = self._read_feb(subrack, address)

        # build output
        output_CSR = [True] * 16
        decimal_result = int(driver_csr, 16)
        for inum in range(16):
            output_CSR[inum] = (decimal_result & 2**inum) != 0
        
        return output_CSR

    def _get_sense_bias(self, subrack, slot, millisec_delay = 0.16):

        # wait
        time.sleep(millisec_delay)


        #read
        address = (slot << 8) + (14 << 4)
        sense_bias_csr = self._read_feb(subrack, address)
        

        # build output
        output_sense_bias_CSR = [True] * 16
        decimal_result = int(sense_bias_csr, 16)
        for inum in range(16):
            output_sense_bias_CSR[inum] = (decimal_result & 2**inum) != 0

        return output_sense_bias_CSR
                
