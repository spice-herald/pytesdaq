import sys
import pytesdaq.utils.remote as remote
import numpy as np
import time

class Magnicon(object):
    """
    Magnicon SQUID driver. Note: currently only works for XXF-1 6MHz in TES mode.
    """

    def __init__(self, channel_list=[], default_active=1, reset_active=1, conn_info=None, remote_inst=None):
        """
        Initialize Magnicon driver.
        Arguments are: list of channels used, default active channel,
        whether to reset the active channel before doing anything (according
        to Magnicon, this is not necessary if Type ID and Version ID are same
        for all channels, but I find that it is necessary ~VV),
        connection info, and a Remote object.
        """

        self._channel_list = channel_list
        self._default_active = default_active
        self._reset_active = reset_active

        if conn_info is None:
            self._conn_info = {'hostname': '',
                               'username': '',
                               'port': 0,
                               'rsa_key': '',
                               'log_file': '',
                               'exe_location': ''}
        else:
            self._conn_info = conn_info

        if isinstance(remote_inst, remote.Remote):
            self._remote_inst = remote_inst
        else:
            self._remote_inst = remote.Remote()



    def __del__(self):
        """
        Destructor
        Close SSH connection if open
        """
        self.disconnect()



    def connect(self):
        """
        Open SSH connection to remote computer
        """
        self._remote_inst.open_connection()



    def disconnect(self):
        """
        Close SSH connection to remote computer
        """
        self._remote_inst.close_connection()



    def chdir(self, new_dir=str()):
        """
        Change directory to executable location, or wherever the user wants
        """

        if self._remote_inst.check_transport_active():
            if new_dir:
                self._remote_inst.send_command('cd %s\n' % new_dir)
            else:
                self._remote_inst.send_command('cd %s\n' % self._conn_info['exe_location'])
        else:
            print('ERROR: SSH connection not open. Command not sent.')



    def listen_for(self, strings=None, max_loops=50):
        """
        Keep receiving output from the SSH connection until a particular
        string is present, or any string in a list of strings. Any of these
        string can be None; this indicates that the SSH connection is not
        actively producing any more text output (including the terminal
        prompt).
        Args: the string or strings (in a Python list, if there are multiple
        strings) to listen for, any of which can be None; the maximum number
        of times to receive output from the Remote object, which can be None.
        Returns: the first instance of the text with any of these string(s).
        """

        if not isinstance(strings, list):
            strings = [strings]

        if max_loops is None:
            max_loops = np.inf

        s = ''
        n = 0
        success = False

        while(n <= max_loops):
            s = self._remote_inst.receive_output()

            for i in range(len(strings)):
                if strings[i] is None and s is None:
                    success = True
                    break
                elif strings[i] is not None and s is not None:
                    if strings[i] in s:
                        success = True
                        break

            if success:
                break
            n += 1

        if success:
            return s
        else:
            return ''



    def remove_terminal_output(self, s, list_of_strings, remove_back_r=True, remove_prompt=True):
        """
        Remove occurrences of some phrase(s) from a string.
        Arguments: s is the string to be modified
                   list_of_strings is a list (can be [], can be one-element) of strings to remove from s
                   remove_back_r removes "backslash r", which is a carriage return on Windows systems
                   remove_prompt removes the system prompt "user@host location>"
                   NOTE: remove_prompt only works if username defined in conn_info
        """

        for string in list_of_strings:
            s = s.replace(string, "")

        if remove_back_r:
            s = s.replace("\r", "")

        if remove_prompt and self._conn_info['username']:
            while(True):
                pos_start = s.find(self._conn_info['username'] + '@')
                if pos_start == -1:
                    break
                pos_search = pos_start + len((self._conn_info['username'] + '@'))
                while pos_search < len(s):
                    if (s[pos_search] == '>'):
                        s = s[:pos_start] + s[(pos_search + 1):]
                        break
                    pos_search += 1
                if pos_search == len(s):
                    break

        return s



    def get_GBP(self, controller_channel):
        """
        Get gain-bandwidth product in GHz. Return -1000 if failed.
        """

        command = '.\\get_GBP.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Gain bandwidth', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get GBP')
            return -1000.
        elif '' in s:
            _, s = s.split('product = ')
            s, _ = s.split(' GHz')
            return float(s)
        else:
            print('Could not get GBP')
            return -1000.




    def get_amp_gain_bandwidth(self, controller_channel):
        """
        Get amplifier gain (unitless) and bandwidth (MHz if numerical, possibly Full or AC_Amp_off).
        Returns -1000 and FAIL if failed
        """

        command = '.\\get_amp_gain_bandwidth.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['amp gain', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get amp_gain_bandwidth')
            return -1000, 'FAIL'
        elif '' in s:
            _, s = s.split('amp gain = ')
            amp_gain, amp_bw = s.split(', amp bandwidth = ')
            amp_gain = int(amp_gain)
            amp_bw = amp_bw.replace('\n', '')
            return amp_gain, amp_bw
        else:
            print('Could not get amp_gain_bandwidth')
            return -1000, 'FAIL'




    def get_amp_gain_sign(self, controller_channel):
        """
        Get amplifier gain sign. Return +1 or -1, or 0 if failed.
        """

        command = '.\\get_amp_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Amp Gain', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get amp_gain_sign')
            return 0
        elif 'Amp Gain' in s:
            if 'negative' in s:
                return -1
            elif 'positive' in s:
                return 1
            else:
                print('Could not get amp_gain_sign')
                return 0
        else:
            print('Could not get amp_gain_sign')
            return 0



    def get_amp_or_fll(self, controller_channel):
        """
        Get mode. Returns "AMP" or "FLL", or "FAIL" if failed.
        """

        command = '.\\get_amp_or_fll.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Electronics mode', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get amp_or_fll')
            return 'FAIL'
        elif 'Electronics mode' in s:
            if 'AMP' in s:
                return 'AMP'
            elif 'FLL' in s:
                return 'FLL'
            else:
                print('Could not get amp_or_fll')
                return 'FAIL'            
        else:
            print('Could not get amp_or_fll')
            return 'FAIL'



    def get_channel_info(self, controller_channel):
        """
        Get channel info: type ID, version ID, board ID, case ID.
        Return -1000 for all if failed.
        """

        command = '.\\get_channel_info.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get channel_info')
            return -1000, -1000, -1000, -1000
        elif 'SUCCESS' in s:
            _, s = s.split('Type ID: ')
            type_id, s = s.split('Version ID: ')
            version_id, s = s.split('Board ID: ')
            board_id, case_id = s.split('Case ID: ')
            return int(type_id), int(version_id), int(board_id), int(case_id)
        else:
            print('Could not get channel_info')
            return -1000, -1000, -1000, -1000



    def get_dummy(self, controller_channel):
        """
        Get status of dummy.
        Returns 'OFF' if dummy off; 'ON' if dummy on; 'FAIL' if failed.
        """

        command = '.\\get_dummy.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get dummy')
            return 'FAIL'
        elif 'SUCCESS' in s:
            if 'off' in s:
                return 'OFF'
            elif 'on' in s:
                return 'ON' 
            else:
                print('Could not get dummy')
                return 'FAIL'
        else:
            print('Could not get dummy')
            return 'FAIL'



    def get_feedback_resistor(self, controller_channel):
        """
        Get feedback coil resistor (kOhms).
        Returns 0 if feedback resistor is off. Returns -1000 if failed.
        """

        command = '.\\get_feedback_resistor.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get feedback_resistor')
            return -1000.
        elif 'SUCCESS' in s:
            _, s = s.split('Rf = ')
            if 'AMP' in s:
                Rf, _ = s.split(' (AMP)')
            elif 'FLL' in s:
                Rf, _ = s.split(' (FLL)')
            else:
                print('Could not get feedback_resistor')
                return -1000.
            if 'off' in Rf:
                return 0.
            else:
                return float(Rf)
        else:
            print('Could not get feedback_resistor')
            return -1000.



    def get_flux_bias_disconnect(self, controller_channel):
        """
        Get status of flux bias connection switch.
        Returns CONNECTED, DISCONNECTED, or FAIL.
        """

        command = '.\\get_flux_bias_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Flux bias', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get flux_bias_disconnect')
            return 'FAIL'
        elif 'Flux bias' in s:
            if 'disconnected' in s:
                return 'DISCONNECTED'
            elif 'connected' in s:
                return 'CONNECTED' 
            else:
                print('Could not get flux_bias_disconnect')
                return 'FAIL'
        else:
            print('Could not get flux_bias_disconnect')
            return 'FAIL'



    def get_generator_onoff(self, controller_channel):
        """
        Get status of both generators and monitoring output.
        Returns ON or OFF for each of the three connections.
        Returns FAIL, FAIL, FAIL if failed.
        """

        command = '.\\get_generator_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Generator', 'Monitoring', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get generator_onoff')
            return 'FAIL', 'FAIL', 'FAIL'
        elif '' in s:
            _, s = s.split('Generator 1 is')
            gen1, s = s.split('Generator 2 is')
            gen2, mon = s.split('Monitoring is')
            if 'off' in gen1:
                gen1_status = 'OFF'
            elif 'on' in gen1:
                gen1_status = 'ON'
            else:
                print('Could not get generator_onoff')
                gen1_status = 'FAIL'
            if 'off' in gen2:
                gen2_status = 'OFF'
            elif 'on' in gen2:
                gen2_status = 'ON'
            else:
                print('Could not get generator_onoff')
                gen2_status = 'FAIL'
            if 'off' in mon:
                mon_status = 'OFF'
            elif 'on' in mon:
                mon_status = 'ON'
            else:
                print('Could not get generator_onoff')
                mon_status = 'FAIL'
            return gen1_status, gen2_status, mon_status
        else:
            print('Could not get generator_onoff')
            return 'FAIL', 'FAIL', 'FAIL'



    def get_generator_params(self, controller_channel, generator_number):
        """
        Get internal Magnicon generator parameters. Requires generator number input (1 or 2).
        Returns: source, waveform, frequency (Hz), frequency divider (0 for off), phase shift,
            peak-to-peak amplitude (uA or uV), status of half-peak-to-peak offset (ON/OFF).
        If failed, returns 'FAIL', 'FAIL', 0, 0, 0, 0, 'FAIL'
        """

        command = '.\\get_generator_params.exe %d %d %d\n' % (controller_channel, self._reset_active, generator_number)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Generator %d' % generator_number, 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get generator_params')
            return 'FAIL', 'FAIL', 0, 0, 0, 0, 'FAIL'
        elif 'Generator %d' % generator_number in s:
            _, s = s.split('source is ')
            source, s = s.split('. The waveform is ')
            waveform, s = s.split(' with a frequency of ')
            gen_freq, s = s.split(' Hz, the divider at ')
            freq_div, s = s.split(' and a phase shift of ')
            if 'off' in freq_div:
                freq_div = '0'
            phase_shift, s = s.split('. The peak-to-peak amplitude is ')
            pp_amplitude, half_pp_offset = s.split(', with the half-peak-to-peak offset')
            if 'off' in half_pp_offset:
                half_pp_offset = 'OFF'
            elif 'on' in half_pp_offset:
                half_pp_offset = 'ON'
            else:
                print('Could not get generator_params')
                return 'FAIL', 'FAIL', 0, 0, 0, 0, 'FAIL'
            return source, waveform, float(gen_freq), int(freq_div), int(phase_shift), float(pp_amplitude), half_pp_offset
        else:
            print('Could not get generator_params')
            return 'FAIL', 'FAIL', 0, 0, 0, 0, 'FAIL'



    def get_output_coupling(self, controller_channel):
        """
        Get electronics coupling (AC or DC). Returns 'FAIL' if failed.
        """

        command = '.\\get_output_coupling.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get output_coupling')
            return 'FAIL'
        elif 'SUCCESS' in s:
            if '(DC)' in s:
                return 'DC'
            elif '(AC)' in s:
                return 'AC'
            else:
                return 'FAIL'
        else:
            print('Could not get output_coupling')
            return 'FAIL'



    def get_output_voltage(self, controller_channel):
        """
        Read output voltage in Volts. Normally you would not use this, rather an ADC card.
        Returns -1000 if failed.
        """

        command = '.\\get_output_voltage.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Output voltage', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get output_voltage')
            return -1000.
        elif 'Output voltage' in s:
            _, s = s.split('Vout = ')
            Vout, _ = s.split(' V')
            return float(Vout)
        else:
            print('Could not get output_voltage')
            return -1000.



    def get_preamp_input_voltage(self, controller_channel):
        """
        Get preamp input voltage, i.e. V-Vb, in uA.
        Returns -1000 if failed.
        """

        command = '.\\get_preamp_input_voltage.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['V - Vb', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get preamp_input_voltage')
            return -1000.
        elif 'V - Vb' in s:
            _, s = s.split('V - Vb = ')
            voltage, _ = s.split(' uV')
            return float(voltage)
        else:
            print('Could not get preamp_input_voltage')
            return -1000.



    def get_squid_bias(self, controller_channel, bias_source):
        """
        Get Ib, Vb, or Phib. Argument bias_source should be I, V, or Phi.
        Returns -1000 if failed.
        """

        if bias_source not in ['I', 'V', 'Phi']:
            print('Invalid squid bias source, not setting.')
            return -1000.

        command = '.\\get_squid_bias.exe %d %d %s\n' % (controller_channel, self._reset_active, bias_source)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get squid_bias')
            return -1000.
        elif 'SUCCESS' in s:
            _, s = s.split(bias_source + 'b = ')
            return float(s)
        else:
            print('Could not get squid_bias')
            return -1000.



    def get_squid_gain_sign(self, controller_channel):
        """
        Get sign of SQUID gain. Returns +1, -1, or 0 if failed.
        """

        command = '.\\get_squid_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Squid Gain', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get squid_gain_sign')
            return 0
        elif 'Squid Gain' in s:
            if 'negative' in s:
                return -1
            elif 'positive' in s:
                return 1
            else:
                print('Could not get squid_gain_sign')
                return 0
        else:
            print('Could not get squid_gain_sign')
            return 0



    def get_temperature(self, controller_channel):
        """
        Get board temperature in degrees Celsius. Returns -1000 if failed.
        """

        command = '.\\get_temperature.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Celsius', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get temperature')
            return -1000.
        elif 'Celsius' in s:
            _, s = s.split('Board temperature = ')
            temp, _ = s.split(' deg Celsius')
            return float(temp)
        else:
            print('Could not get temperature')
            return -1000.



    def get_tes_current_bias(self, controller_channel):
        """
        Get current bias through TES/shunt resistor setup (uA). Return -1000 if failed.
        """

        command = '.\\get_tes_current_bias.exe %d %d\n' % (controller_channel, self._reset_active)
        time.sleep(1)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Iaux', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_current_bias')
            return -1000.
        elif 'Iaux' in s:
            _, s = s.split('Iaux = ')
            if 'low' in s:
                Iaux, _ = s.split(' (low mode)')
                return float(Iaux)
            elif 'high' in s:
                Iaux, _ = s.split(' (high mode)')
                return float(Iaux)
            else:
                print('Could not get tes_current_bias')
                return -1000.
        else:
            print('Could not get tes_current_bias')
            return -1000.



    def get_tes_pulse_disconnect(self, controller_channel):
        """
        Get status of auxiliary current source (through TES/shunt) switch.
        Returns CONNECTED, DISCONNECTED, or FAIL.
        """

        command = '.\\get_tes_pulse_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['TES current pulse', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_disconnect')
            return 'FAIL'
        elif 'TES current pulse' in s:
            if 'disconnected' in s:
                return 'DISCONNECTED'
            elif 'connected' in s:
                return 'CONNECTED' 
            else:
                print('Could not get tes_pulse_disconnect')
                return 'FAIL'
        else:
            print('Could not get tes_pulse_disconnect')
            return 'FAIL'



    def get_tes_pulse_onoff(self, controller_channel):
        """
        Get status of TES pulse generator.
        Returns 'ON', 'OFF', or 'FAIL'
        """

        command = '.\\get_tes_pulse_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['TES current pulse', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_onoff')
            return 'FAIL'
        elif 'TES current pulse' in s:
            if 'pulse is off' in s:
                return 'OFF'
            elif 'pulse is on' in s:
                return 'ON'
            else:
                print('Could not get tes_pulse_onoff')
                return 'FAIL'
        else:
            print('Could not get tes_pulse_onoff')
            return 'FAIL'



    def get_tes_pulse_params(self, controller_channel):
        """
        Get parameters for TES pulse (auxiliary current pulse).
        The parameters are: pulse mode (off, continuous, single),
        pulse amplitude (uA), time between pulses (ms), and pulse
        duration (us).
        If failed, returns 'FAIL', -1000, -1000, -1000.
        """

        command = '.\\get_tes_pulse_params.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Pulse mode', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_params')
            return 'FAIL', -1000., -1000., -1000.
        elif 'Pulse mode' in s:
            _, s = s.split('Pulse mode is ')
            pulse_mode, s = s.split(', with an amplitude of ')
            pulse_amplitude, s = s.split(' uA, ')
            time_between_pulses, s = s.split(' ms between pulses, a pulse duration of ')
            pulse_duration, _ = s.split(' us.')
            if pulse_mode not in ['off', 'continuous', 'single']:
                print('Could not get tes_pulse_params')
                return 'FAIL', -1000., -1000., -1000.
            else:
                return pulse_mode, pulse_amplitude, time_between_pulses, pulse_duration
        else:
            print('Could not get tes_pulse_params')
            return 'FAIL', -1000., -1000., -1000.



    def set_GBP(self, controller_channel, gbp):
        """
        Set gain bandwidth product. Must be one of:
        [0.23,0.27,0.30,0.38,0.47,0.55,0.66,0.82,1.04,1.28,1.50,1.80,
            2.25,2.80,3.30,4.00,5.00,6.20,7.20]
        Returns GBP or -1000 if failed
        """

        if round(gbp, 2) not in [0.23,0.27,0.30,0.38,0.47,0.55,0.66,0.82,1.04,1.28,1.50,1.80,2.25,2.80,3.30,4.00,5.00,6.20,7.20]:
            print('Invalid GBP, not setting')
            return -1000.        

        command = '.\\set_GBP.exe %d %d %.2f\n' % (controller_channel, self._reset_active, gbp)
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set GBP')
            return -1000.
        elif 'DONE' in s:
            return gbp
        else:
            print('Could not set GBP')
            return -1000.



    def set_amp_gain_bandwidth(self, controller_channel, amp_gain, amp_bw):
        """
        Set amplifier gain and bandwidth.
        Gain must be one of [1100, 1400, 1700, 2000].
        Bandwidth must be one of [0.2, 0.7, 1.4, Full, AC_Amp_off]. Numerical values are in MHz.
            If bandwidth is numerical, you can enter the floating-point number or a string.
        Returns the gain and bandwidth or -1000, 'FAIL' if failed.
        """

        if amp_gain not in [1100, 1400, 1700, 2000]:
            print('Invalid amplifier gain, not setting.')
            return -1000, 'FAIL'
        if isinstance(amp_bw, float):
            amp_bw = '%.1f' % amp_bw
        if amp_bw not in ['0.2', '0.7', '1.4', 'Full', 'AC_Amp_off']:
            print('Invalid amplifier bandwidth, not setting.')
            return -1000, 'FAIL'

        command = '.\\set_amp_gain_bandwidth.exe %d %d %d %s\n' % (controller_channel, self._reset_active, amp_gain, amp_bw)
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_gain_bandwidth')
            return -1000, 'FAIL'
        elif 'DONE' in s:
            return amp_gain, amp_bw
        else:
            print('Could not set amp_gain_bandwidth')
            return -1000, 'FAIL'



    def set_amp_gain_sign(self, controller_channel, sign):
        """
        Set sign of amplifier gain. Must be +1 or -1.
        Returns the sign or 0 for failure.
        """

        if sign == 1:
            command = '.\\set_amp_gain_sign.exe %d %d positive\n' % (controller_channel, self._reset_active)
        elif sign == -1:
            command = '.\\set_amp_gain_sign.exe %d %d negative\n' % (controller_channel, self._reset_active)
        else:
            print('Invalid amp_gain_sign, not setting.')
            return 0

        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_gain_sign')
            return 0
        elif 'DONE' in s:
            return sign
        else:
            print('Could not set amp_gain_sign')
            return 0



    def set_amp_or_fll(self, controller_channel, mode):
        """
        Set electronics mode. Must be 'AMP' or 'FLL'.
        Returns the mode or FAIL.
        """

        if mode != "AMP" and mode != "FLL":
            print('Invalid electronics mode, not setting')
            return 'FAIL'

        command = '.\\set_amp_or_fll.exe %d %d %s\n' % (controller_channel, self._reset_active, mode)
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_or_fll')
            return 'FAIL'
        elif 'DONE' in s:
            return mode
        else:
            print('Could not set amp_or_fll')
            return 'FAIL'



    def set_dummy(self, controller_channel, dummy_status):
        """
        Set dummy SQUID status. Must be 'ON' or 'OFF'.
        Returns the status or FAIL.
        """

        if dummy_status == 'ON':
            command = '.\\set_dummy.exe %d %d on\n' % (controller_channel, self._reset_active)
        elif dummy_status == 'OFF':
            command = '.\\set_dummy.exe %d %d off\n' % (controller_channel, self._reset_active)
        else:
            print('Invalid dummy status, not setting')
            return 'FAIL'

        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set dummy')
            return 'FAIL'
        elif 'DONE' in s:
            return dummy_status
        else:
            print('Could not set dummy')
            return 'FAIL'



    def set_feedback_resistor(self, controller_channel, Rf):
        """
        Set resistor in feedback coil. Must be one of:
            [0 (for off),0.70,0.75,0.91,1.00,2.14,2.31,2.73,3.00,7.00,7.50,9.10,10.00,23.10,30.00,100.00] kOhms
        Returns feedback resistance or -1000 if failed.
        """

        if Rf not in [0,0.70,0.75,0.91,1.00,2.14,2.31,2.73,3.00,7.00,7.50,9.10,10.00,23.10,30.00,100.00]:
            print('Invalid feedback resistance, not setting')
            return -1000.

        if Rf == 0:
            command = '.\\set_feedback_resistor.exe %d %d off\n' % (controller_channel, self._reset_active)
        else:
            command = '.\\set_feedback_resistor.exe %d %d %.2f\n' % (controller_channel, self._reset_active, Rf)
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set feedback_resistor')
            return -1000.
        elif 'DONE' in s:
            return Rf
        else:
            print('Could not set feedback_resistor')
            return -1000.



    def set_flux_bias_disconnect(self, controller_channel, flux_bias_status):
        """
        Set status of flux bias disconnect switch. Must be CONNECTED or DISCONNECTED.
        Returns status or FAIL if failed.
        """

        if flux_bias_status != 'CONNECTED' and flux_bias_status != 'DISCONNECTED':
            print('Invalid flux bias status, not setting')
            return 'FAIL'

        command = '.\\set_flux_bias_disconnect.exe %d %d %s\n' % (controller_channel, self._reset_active, flux_bias_status.lower())
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set flux_bias_disconnect')
            return 'FAIL'
        elif 'DONE' in s:
            return flux_bias_status
        else:
            print('Could not set flux_bias_disconnect')
            return 'FAIL'



    def set_generator_onoff(self, controller_channel, gen1_onoff, gen2_onoff, mon_onoff):
        """
        Set status of generators and monitoring output. All must be ON or OFF.
        Returns status of all three, or FAIL, FAIL, FAIL if failed.
        """

        possible_args = ['ON', 'OFF']
        if gen1_onoff not in possible_args or gen2_onoff not in possible_args or mon_onoff not in possible_args:
            print('Invalid generator or monitoring status, not setting.')
            return 'FAIL', 'FAIL', 'FAIL'

        command = '.\\set_generator_onoff.exe %d %d %s %s %s\n' % \
            (controller_channel, self._reset_active, gen1_onoff.lower(), gen2_onoff.lower(), mon_onoff.lower())
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set generator_onoff')
            return 'FAIL', 'FAIL', 'FAIL'
        elif 'DONE' in s:
            return gen1_onoff, gen2_onoff, mon_onoff
        else:
            print('Could not set generator_onoff')
            return 'FAIL', 'FAIL', 'FAIL'



    def set_generator_params(self, controller_channel, gen_num, gen_freq, source, waveform, phase_shift, freq_div, half_pp_offset, pp_amplitude):
        """
        Set parameters for internal source generator:
        Arguments: generator number (1 or 2), generator frequency (Hz),
            source (Ib, Vb, Phib, or I),
            waveform (triangle, sawtoothpos, sawtoothneg, square, sine, noise),
            phase shift (0, 90, 180, or 270),
            frequency divider (0 for off, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024),
            half peak-peak offset (ON or OFF),
            peak-peak amplitude (uA or uV)
        Returns: coerced peak-peak amplitude and coerced frequency,
            or -1000 for both if failed.
        """

        if gen_num not in [1, 2]:
            print('Invalid generator number, not setting')
            return -1000., -1000.
        if source not in ['Ib', 'Vb', 'Phib', 'I']:
            print('Invalid source, not setting')
            return -1000., -1000.
        if waveform not in ['triangle', 'sawtoothpos', 'sawtoothneg', 'square', 'sine', 'noise']:
            print('Invalid waveform, not setting')
            return -1000., -1000.
        if phase_shift not in [0, 90, 180, 270]:
            print('Invalid phase shift, not setting')
            return -1000., -1000.
        if freq_div not in [0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
            print('Invalid frequency divider, not setting')
            return -1000., -1000.
        if half_pp_offset not in ['ON', 'OFF']:
            print('Invalid half peak-peak offset, not setting')
            return -1000., -1000.

        if freq_div == 0:
            command = '.\\set_generator_params.exe %d %d %d %f %s %s %d off %s %f\n' % \
                (controller_channel, self._reset_active, gen_num, gen_freq, source, waveform, phase_shift, half_pp_offset.lower(), pp_amplitude)
        else:
            command = '.\\set_generator_params.exe %d %d %d %f %s %s %d %d %s %f\n' % \
                (controller_channel, self._reset_active, gen_num, gen_freq, source, waveform, phase_shift, freq_div, half_pp_offset.lower(), pp_amplitude)

        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set generator_params')
            return -1000., -1000.
        elif 'Set generator' in s or 'SUCCESS' in s:
            _, s = s.split('peak-peak amplitude of ')
            pp_amplitude_coerced, s = s.split(' and frequency of ')
            gen_freq_coerced, _ = s.split(' Hz.')
            return float(pp_amplitude_coerced), float(gen_freq_coerced)
        else:
            print('Could not set generator_params')
            return -1000., -1000.



    def set_output_coupling(self, controller_channel, coupling):
        """
        Set electronics coupling; must be 'AC' or 'DC'.
        Returns the coupling or 'FAIL' if failed.
        """

        if coupling != 'AC' and coupling != 'DC':
            print('Invalid coupling, not setting')
            return 'FAIL'

        command = '.\\set_output_coupling.exe %d %d %s\n' % (controller_channel, self._reset_active, coupling)
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set output_coupling')
            return 'FAIL'
        elif 'DONE' in s:
            return coupling
        else:
            print('Could not set output_coupling')
            return 'FAIL'



    def set_squid_bias(self, controller_channel, bias_source, new_value):
        """
        Set the current, voltage, or flux bias in the SQUID.
        The argument bias_source must be I, V, or Phi.
        Returns the coerced bias or -1000 if failed.
        """

        if bias_source not in ['I', 'V', 'Phi']:
            print('Invalid SQUID bias source, not setting.')
            return -1000.

        command = '.\\set_squid_bias.exe %d %d %s %f\n' % (controller_channel, self._reset_active, bias_source, new_value)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set squid_bias')
            return -1000.
        elif 'SUCCESS' in s:
            _, s = s.split(bias_source + 'b = ')
            return float(s)
        else:
            print('Could not set squid_bias')
            return



    def set_squid_gain_sign(self, controller_channel, sign):
        """
        Set sign of amplifier gain. Must be +1 or -1.
        Returns the sign or 0 for failure.
        """

        if sign == 1:
            command = '.\\set_squid_gain_sign.exe %d %d positive\n' % (controller_channel, self._reset_active)
        elif sign == -1:
            command = '.\\set_squid_gain_sign.exe %d %d negative\n' % (controller_channel, self._reset_active)
        else:
            print('Invalid squid_gain_sign, not setting.')
            return 0

        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_gain_sign')
            return 0
        elif 'DONE' in s:
            return sign
        else:
            print('Could not set amp_gain_sign')
            return 0



    def set_tes_current_bias(self, controller_channel, Iaux, mode=None):
        """
        Set current bias through TES/shunt Iaux (uA). Return -1000 if failed.
        Argument 'mode' can be 'low', 'high', or None.
        The 'low' range is -125 to +125 uA; the high range is -500 to +500 uA.
        If 'mode' is None, it will set to low if -120 < I < 120, high otherwise.
        """

        if mode is not None and mode not in ['low', 'high']:
            print('Invalid TES bias mode, not setting')
            return -1000.

        if mode is None:
            if Iaux > -120 and Iaux < 120:
                mode = 'low'
            else:
                mode = 'high'
            
        command = '.\\set_tes_current_bias.exe %d %d %s %f\n' % (controller_channel, self._reset_active, mode, Iaux)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Iaux', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_current_bias')
            return -1000.
        elif 'Iaux' in s:
            _, s = s.split('Iaux = ')
            return float(s)
        else:
            print('Could not set tes_current_bias')
            return -1000.


    def set_tes_pulse_disconnect(self, controller_channel, tes_pulse_status):
        """
        Set status of TES pulse disconnect switch. Must be CONNECTED or DISCONNECTED.
        Returns status or FAIL if failed.
        """

        if tes_pulse_status != 'CONNECTED' and tes_pulse_status != 'DISCONNECTED':
            print('Invalid flux bias status, not setting')
            return 'FAIL'

        command = '.\\set_tes_pulse_disconnect.exe %d %d %s\n' % (controller_channel, self._reset_active, tes_pulse_status.lower())
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_disconnect')
            return 'FAIL'
        elif 'DONE' in s:
            return tes_pulse_status
        else:
            print('Could not set tes_pulse_disconnect')
            return 'FAIL'



    def set_tes_pulse_onoff(self, controller_channel, pulse_onoff):
        """
        Set status of TES pulse generator. Can be 'ON' or 'OFF'.
        Returns status or 'FAIL' if failed.
        """

        if pulse_onoff != 'ON' and pulse_onoff != 'OFF':
            print('Invalid TES pulse generator status, not setting')
            return 'FAIL'

        command = '.\\set_tes_pulse_onoff.exe %d %d %s\n' % (controller_channel, self._reset_active, pulse_onoff.lower())
        self._remote_inst.send_command(command)
        s = self.listen_for(['DONE', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_onoff')
            return 'FAIL'
        elif 'DONE' in s:
            return pulse_onoff
        else:
            print('Could not set tes_pulse_onoff')
            return 'FAIL'



    def set_tes_pulse_params(self, controller_channel, pulse_mode, pulse_amplitude, time_between_pulses, pulse_duration):
        """
        Set parameters for current pulse generator through TES/shunt.
        Arguments: pulse mode (must be 'off', 'continuous', or 'single'),
            pulse amplitude (uA), time between pulses (ms), pulse duration (us)
        Returns: coerced pulse amplitude, coerced time between pulses,
            coerced pulse duration, or -1000 for all if failed
        """

        if pulse_mode not in ['off', 'continuous', 'single']:
            print('Invalid TES pulse mode, not setting')
            return -1000., -1000., -1000.

        command = '.\\set_tes_pulse_params.exe %d %d %s %f %f %f\n' % \
            (controller_channel, self._reset_active, pulse_mode, pulse_amplitude, time_between_pulses, pulse_duration)
        self._remote_inst.send_command(command)
        s = self.listen_for(['SUCCESS', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)
        self.listen_for(self._conn_info['username'], max_loops=50)
        self.listen_for([None])

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_params')
            return -1000., -1000., -1000.
        elif '' in s:
            _, s = s.split(pulse_mode + ' mode with ')
            pulse_amplitude_coerced, s = s.split(' uA amplitude, ')
            time_between_pulses_coerced, s = s.split(' ms between pulses, ')
            pulse_duration_coerced, _ = s.split(' us pulse duration.')
            return float(pulse_amplitude_coerced), float(time_between_pulses_coerced), float(pulse_duration_coerced)
        else:
            print('Could not set tes_pulse_params')
            return -1000., -1000., -1000.



    def get_channel_list(self):
        """
        Get list of Magnicon channels
        """
        return self._channel_list



    def get_default_active(self):
        """
        Get default active Magnicon channel
        """
        return self._default_active



    def get_reset_active(self):
        """
        Get behavior regarding whether to reset the active channel every time
        """
        return self._reset_active



    def get_remote_inst(self):
        """
        Get Remote object
        """
        return self._remote_inst



    def get_conn_info(self):
        """
        Get connection info
        Dictionary with minimum keys hostname, username, port, RSA key, log file, executable location
        """
        return self._conn_info



    def set_channel_list(self, channel_list):
        """
        Set list of Magnicon channels
        """
        self._channel_list = channel_list



    def set_default_active(self, default_active):
        """
        Set default active Magnicon channel
        """
        self._default_active = default_active



    def set_reset_active(self, reset_active):
        """
        Set behavior regarding whether to reset the active channel every time
        """
        self._reset_active = reset_active



    def set_remote_inst(self, remote_inst=None):
        """
        Set Remote object
        """

        if isinstance(remote_inst, remote.Remote):
            self._remote_inst = remote_inst
        else:
            try:
               self._remote_inst = remote.Remote(hostname=self._conn_info['hostname'],
                                                 port=self._conn_info['port'],
                                                 username=self._conn_info['username'],
                                                 auth_method='rsa',
                                                 auth_val=self._conn_info['rsa_key'],
                                                 log_file=self._conn_info['log_file'])
            except:
                print('ERROR: Could not set remote instance. Set conn_info first.')



    def set_conn_info(self, conn_info):
        """
        Set connection info
        Dictionary with minimum keys hostname, username, port, RSA key, log file, executable location
        """
        self._conn_info = conn_info
