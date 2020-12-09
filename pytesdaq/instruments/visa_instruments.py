import pyvisa as visa



class VisaInstrument: 
    """
    Manage instruments controled using VISA
    """
    
    def __init__(self,resource_address, termination=None, raise_errors=True, verbose=False):

        self._verbose = verbose
        self._raise_errors = raise_errors
        self._inst = None
        self._debug = False
        
        # open resource
        rm = visa.ResourceManager('/usr/lib/x86_64-linux-gnu/libvisa.so.20.0.0')        
        try:
            if self._verbose:
                print('INFO: Opening VISA resource "{}"'.format(resource_address))
            self._inst=rm.open_resource(resource_address)
            if termination is not None:
                self._inst.read_termination = termination
            
        except visa.VisaIOError as e:
            
            if self._verbose:
                print('ERROR opening VISA resource "{}"'.format(resource_address))
            if raise_errors:
                raise
            else:
                return None


    def get_idn(self):
        return self._query("*IDN?")
    
    def reset(self):
        self._write("*RST")
        
    def clear(self):
        self._write("*CLR")
        

    def close(self):
        self._inst.close()
        if self._verbose:
            print('INFO: Session closed!')
        
    def _write(self, message):
        if self._debug:
            print('INFO: Write ' + message)
        
        self._inst.write(message)

    def _read(self):
        data = self._inst.read()
        return data
    
    def _query(self, message):
        data = self._inst.query(message)
        if self._debug:
            print('INFO: Query ' + message + ' = ' + str(data))
        return data
