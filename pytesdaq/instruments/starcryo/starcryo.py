from pytesdaq.instruments.communication import InstrumentComm
import warnings



class PCI1000(object):
    """
    PCI-1000 base class to store its state
    """

    def __init__(self, transmitter_address=255):

        self._address = transmitter_address

        self._generator_enabled = None
        self._channels_enabled = None
        self._freq_Hz = None
        self._freq_N = None
        self._amp_Vpp = None
        self._amp_N = None

    @property
    def generator_enabled(self):
        """
        Is the test signal generator enabled?
        Can be 0 (OFF), 1 (ON), or None (we don't know the generator
        state because the PCI1000 object was just initialized).
        """
        return self._generator_enabled

    @generator_enabled.setter
    def generator_enabled(self, val):
        if val not in [0, 1]:
            raise ValueError('Cannot enable/disable PCI-1000 generator!')
        self._generator_enabled = val

    @property
    def channels_enabled(self):
        """
        Which channels are enabled with the signal generator?
        Can be a list of up to 8 ints, where each int is between 1-8,
        or None (we don't know which channels are enabled because
        the PCI1000 object was just initialized).
        """

        return self._channels_enabled

    @channels_enabled.setter
    def channels_enabled(self, val):
        val_unique = sorted(set(val))
        if len(val_unique) != len(val):
            warnings.warn('You listed a channel ID multiple times.')

        for i in val_unique:
            if i < 1 or i > 8:
                raise ValueError('Channel ID must be between 1-8!')

        self._channels_enabled = val_unique
            


class PFL102(object):
    """
    PFL-102 base class to store its state
    """

    pass

class StarCryo(InstrumentComm):
    """
    StarCryo SQUID driver.
    Note: currently works only for one PCI-1000 and
    up to eight PFL-102 devices.
    """

    def __init__(self, rs232_address, pfl_channel_list=[],
        raise_errors=True, verbose=True):
        """
        Initialize StarCryo driver, provided RS-232/USB address
        and list of SQUID channels (use PFL-102 channel ID).

        rs232_address: str; example "ASRL3::INSTR"
        pfl_channel_list: list of ints
        """

        super().__init__(protocol='rs232',
                         visa_address=rs232_address,
                         raise_errors=raise_errors,
                         verbose=verbose)

        self._pfl_channel_list = pfl_channel_list

        # Connect to device
        self.connect()


    def __del__(self):
        """
        Destructor
        Close SSH connection if open
        """
        self.disconnect()


