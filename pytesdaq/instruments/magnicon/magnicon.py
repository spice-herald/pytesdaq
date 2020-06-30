import pytesdaq.utils.remote as remote

class Magnicon(object):
    """
    Magnicon SQUID driver
    """

    def __init__(self, channel_list=[], default_active=1, reset_active=False, conn_info=None, remote_inst=None):
        """
        Initialize Magnicon driver.
        Arguments are: list of channels used,
        default active channel, whether to reset the active channel before doing anything
        (not necessary if Type ID and Version ID are same for all channels),
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
