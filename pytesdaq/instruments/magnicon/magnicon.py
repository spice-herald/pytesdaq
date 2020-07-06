import sys
sys.path.insert(0, '/home/vetri/GithubRepos/pytesdaq/pytesdaq/instruments/magnicon/')
sys.path.insert(0, '/home/vetri/GithubRepos/pytesdaq/pytesdaq/utils/')
import remote
# import pytesdaq.utils.remote as remote
import numpy as np
import time

class Magnicon(object):
    """
    Magnicon SQUID driver. Note: currently only works for XXF-1 6MHz in TES mode.
    """

    def __init__(self, channel_list=[], default_active=1, reset_active=True, conn_info=None, remote_inst=None):
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



    def listen_for(self, strings=None, max_loops=100):
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
        Returns -1000 and blank string if failed
        """

        command = '.\\get_amp_gain_bandwidth.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['amp gain', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get amp_gain_bandwidth')
            return -1000, ''
        elif '' in s:
            _, s = s.split('amp gain = ')
            amp_gain = int(s.split(', amp bandwidth'))
            _, s = s.split('amp bandwidth = ')
            amp_bw = s.replace('\n', '')
            return amp_gain, amp_bw
        else:
            print('Could not get amp_gain_bandwidth')
            return -1000, ''




    def get_amp_gain_sign(self, controller_channel):
        """
        Get amplifier gain sign. Return +1 or -1, or 0 if failed.
        """

        command = '.\\get_amp_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['Amp Gain', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

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
        """

        command = '.\\get_feedback_resistor.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get feedback_resistor')
            return
        elif '' in s:
            
        else:
            print('Could not get feedback_resistor')
            return




    def get_flux_bias_disconnect(self, controller_channel):
        """
        """

        command = '.\\get_flux_bias_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get flux_bias_disconnect')
            return
        elif '' in s:
            
        else:
            print('Could not get flux_bias_disconnect')
            return




    def get_generator_onoff(self, controller_channel):
        """
        """

        command = '.\\get_generator_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get generator_onoff')
            return
        elif '' in s:
            
        else:
            print('Could not get generator_onoff')
            return




    def get_generator_params(self, controller_channel):
        """
        """

        command = '.\\get_generator_params.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get generator_params')
            return
        elif '' in s:
            
        else:
            print('Could not get generator_params')
            return




    def get_output_coupling(self, controller_channel):
        """
        """

        command = '.\\get_output_coupling.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get output_coupling')
            return
        elif '' in s:
            
        else:
            print('Could not get output_coupling')
            return




    def get_output_voltage(self, controller_channel):
        """
        """

        command = '.\\get_output_voltage.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get output_voltage')
            return
        elif '' in s:
            
        else:
            print('Could not get output_voltage')
            return




    def get_preamp_input_voltage(self, controller_channel):
        """
        """

        command = '.\\get_preamp_input_voltage.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get preamp_input_voltage')
            return
        elif '' in s:
            
        else:
            print('Could not get preamp_input_voltage')
            return




    def get_squid_bias(self, controller_channel):
        """
        """

        command = '.\\get_squid_bias.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get squid_bias')
            return
        elif '' in s:
            
        else:
            print('Could not get squid_bias')
            return




    def get_squid_gain_sign(self, controller_channel):
        """
        """

        command = '.\\get_squid_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get squid_gain_sign')
            return
        elif '' in s:
            
        else:
            print('Could not get squid_gain_sign')
            return




    def get_temperature(self, controller_channel):
        """
        """

        command = '.\\get_temperature.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get temperature')
            return
        elif '' in s:
            
        else:
            print('Could not get temperature')
            return




    def get_tes_current_bias(self, controller_channel):
        """
        """

        command = '.\\get_tes_current_bias.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_current_bias')
            return
        elif '' in s:
            
        else:
            print('Could not get tes_current_bias')
            return




    def get_tes_pulse_disconnect(self, controller_channel):
        """
        """

        command = '.\\get_tes_pulse_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_disconnect')
            return
        elif '' in s:
            
        else:
            print('Could not get tes_pulse_disconnect')
            return




    def get_tes_pulse_onoff(self, controller_channel):
        """
        """

        command = '.\\get_tes_pulse_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_onoff')
            return
        elif '' in s:
            
        else:
            print('Could not get tes_pulse_onoff')
            return




    def get_tes_pulse_params(self, controller_channel):
        """
        """

        command = '.\\get_tes_pulse_params.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not get tes_pulse_params')
            return
        elif '' in s:
            
        else:
            print('Could not get tes_pulse_params')
            return




    def set_GBP(self, controller_channel):
        """
        """

        command = '.\\set_GBP.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set GBP')
            return
        elif '' in s:
            
        else:
            print('Could not set GBP')
            return




    def set_amp_gain_bandwidth(self, controller_channel):
        """
        """

        command = '.\\set_amp_gain_bandwidth.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_gain_bandwidth')
            return
        elif '' in s:
            
        else:
            print('Could not set amp_gain_bandwidth')
            return




    def set_amp_gain_sign(self, controller_channel):
        """
        """

        command = '.\\set_amp_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_gain_sign')
            return
        elif '' in s:
            
        else:
            print('Could not set amp_gain_sign')
            return




    def set_amp_or_fll(self, controller_channel):
        """
        """

        command = '.\\set_amp_or_fll.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set amp_or_fll')
            return
        elif '' in s:
            
        else:
            print('Could not set amp_or_fll')
            return




    def set_dummy(self, controller_channel):
        """
        """

        command = '.\\set_dummy.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set dummy')
            return
        elif '' in s:
            
        else:
            print('Could not set dummy')
            return




    def set_feedback_resistor(self, controller_channel):
        """
        """

        command = '.\\set_feedback_resistor.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set feedback_resistor')
            return
        elif '' in s:
            
        else:
            print('Could not set feedback_resistor')
            return




    def set_flux_bias_disconnect(self, controller_channel):
        """
        """

        command = '.\\set_flux_bias_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set flux_bias_disconnect')
            return
        elif '' in s:
            
        else:
            print('Could not set flux_bias_disconnect')
            return




    def set_generator_onoff(self, controller_channel):
        """
        """

        command = '.\\set_generator_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set generator_onoff')
            return
        elif '' in s:
            
        else:
            print('Could not set generator_onoff')
            return




    def set_generator_params(self, controller_channel):
        """
        """

        command = '.\\set_generator_params.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set generator_params')
            return
        elif '' in s:
            
        else:
            print('Could not set generator_params')
            return




    def set_output_coupling(self, controller_channel):
        """
        """

        command = '.\\set_output_coupling.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set output_coupling')
            return
        elif '' in s:
            
        else:
            print('Could not set output_coupling')
            return




    def set_squid_bias(self, controller_channel):
        """
        """

        command = '.\\set_squid_bias.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set squid_bias')
            return
        elif '' in s:
            
        else:
            print('Could not set squid_bias')
            return




    def set_squid_gain_sign(self, controller_channel):
        """
        """

        command = '.\\set_squid_gain_sign.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set squid_gain_sign')
            return
        elif '' in s:
            
        else:
            print('Could not set squid_gain_sign')
            return




    def set_tes_current_bias(self, controller_channel):
        """
        """

        command = '.\\set_tes_current_bias.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_current_bias')
            return
        elif '' in s:
            
        else:
            print('Could not set tes_current_bias')
            return




    def set_tes_pulse_disconnect(self, controller_channel):
        """
        """

        command = '.\\set_tes_pulse_disconnect.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_disconnect')
            return
        elif '' in s:
            
        else:
            print('Could not set tes_pulse_disconnect')
            return




    def set_tes_pulse_onoff(self, controller_channel):
        """
        """

        command = '.\\set_tes_pulse_onoff.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_onoff')
            return
        elif '' in s:
            
        else:
            print('Could not set tes_pulse_onoff')
            return




    def set_tes_pulse_params(self, controller_channel):
        """
        """

        command = '.\\set_tes_pulse_params.exe %d %d\n' % (controller_channel, self._reset_active)
        self._remote_inst.send_command(command)
        s = self.listen_for(['', 'ERROR', 'Error'])
        s = self.remove_terminal_output(s, [command], True, True)

        if 'ERROR' in s or 'Error' in s:
            print('Could not set tes_pulse_params')
            return
        elif '' in s:
            
        else:
            print('Could not set tes_pulse_params')
            return























    def get_tes_current_bias(self, controller_channel):
        """
        Get current bias through TES/shunt resistor setup (uA). Return -1000 if failed.
        """

        self._remote_inst.send_command('.\\get_tes_current_bias.exe %d %d\n' % (controller_channel, self._reset_active))
        s = self.listen_for(['Iaux', 'ERROR', 'Error'])

        if 'Iaux' in s:
            _, s = s.split('Iaux = ')
            s, _ = s.split(' (')
            return float(s)
        else:
            print('Could not read Iaux')
            return -1000.



    def set_tes_current_bias(self, controller_channel, Iaux, mode=None):
        """
        Set current bias through TES/shunt Iaux (uA). Return -1000 if failed.
        Argument 'mode' can be 'low', 'high', or None.
        The 'low' range is -125 to +125 uA; the high range is -500 to +500 uA.
        If 'mode' is None, it will set to low if -120 < I < 120, high otherwise.
        """

        if mode is not None:
            self._remote_inst.send_command('.\\set_tes_current_bias.exe %d %d %s %f\n' % (controller_channel, self._reset_active, mode, Iaux))
        elif Iaux > -120 and Iaux < 120:
            self._remote_inst.send_command('.\\set_tes_current_bias.exe %d %d low %f\n' % (controller_channel, self._reset_active, mode, Iaux))
        else:
            self._remote_inst.send_command('.\\set_tes_current_bias.exe %d %d high %f\n' % (controller_channel, self._reset_active, mode, Iaux))

        s = self.listen_for(['Iaux', 'ERROR', 'Error'])

        if 'Iaux' in s:
            _, s = s.split('Iaux = ')
            return float(s)
        else:
            print('Could not set Iaux')
            return -1000.


































    def set_dummy(self, controller_channel, dummy):
        """
        Set dummy status: dummy can be "on" or "off"
        """

        self._remote_inst.send_command('.\\set_dummy.exe %d %d %s\n' % (controller_channel, self._reset_active, dummy))
        s = self.listen_for(None)
        return 0



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



    def get_remote(self):
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
