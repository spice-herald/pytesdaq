import pytesdaq.utils.remote as remote
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



    def get_squid_current_bias(self, controller_channel):
        """
        Get current bias through SQUID Ib (uA)
        """

        self._remote_inst.send_command('.\\get_squid_bias.exe %d %d I\n' % (controller_channel, self._reset_active))
        s = self.listen_for(['Ib', 'ERROR', 'Error'])

        if 'Ib' in s:
            _, s = s.split('Ib = ')
            return float(s)
        else:
            print('Could not read Ib')
            return -100.



    def set_squid_current_bias(self, controller_channel, Ib):
        """
        Set current bias through SQUID Ib (uA)
        """

        self._remote_inst.send_command('.\\set_squid_bias.exe %d %d I %f\n' % (controller_channel, self._reset_active, Ib))
        s = self.listen_for(['Ib', 'ERROR', 'Error'])

        if 'Ib' in s:
            _, s = s.split('Ib = ')
            return float(s)
        else:
            print('Could not set Ib')
            return -100.




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
