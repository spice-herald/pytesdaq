import time
import socket
import pyvisa as visa
import select


class InstrumentComm:
    """
    Communication
    """
    
    def __init__(self, protocol='tcp', termination=None, timeout=2,
                 ip_address=None, visa_address=None,
                 port=None, recv_port=None,
                 visa_library=None,
                 raise_errors=True, verbose=True):

        self._protocol = protocol.lower()
        self._timeout = timeout
        self._termination = termination
        self._ip_address = ip_address
        self._visa_address = visa_address
        self._port = port
        self._recv_port  = recv_port
        if recv_port is None:
            self._recv_port = port
        self._visa_library = visa_library
        self._verbose = verbose
        self._raise_errors = raise_errors

        # instrument
        self._inst = None

        # debug
        self._debug = False
        
        
    def set_address(self, ip_address=None, visa_address=None,
                    port=None, recv_port=None):
        """
        Address
        """
        self._address = ip_address
        self._port = port
        self._recv_port  = recv_port
        if recv_port is None:
            self._recv_port = port

            
    def get_idn(self):
        """
        Query device information
        """
        return self.query('*IDN?')


    
    def write(self, command, coding=None):
        """
        Send command 
        """

        if self._debug:
            print('DEBUG: Write ' + command)

        # encode
        if coding is not None:
            command = command.encode(coding)

        # connect
        if self._inst is None:
            self.connect()

        # write
        if self._protocol=='udp':
            res = self._inst.sendto(command, (self._address, self._port))
            if res != len(command) and self._raise_errors:
                raise IOError
            self.close()
        else:        
            self._inst.write(command)
            

            
            
    def query(self, command, coding=None):
        """
        Send 'command', wait for the response and returns data
        """

        data = None

        # encode
        if coding is not None:
            command = command.encode(coding)
            
                      
        # connect
        if self._inst is None:
            self.connect()

        # query
        if self._protocol=='udp':
            # send 
            res = self._inst.sendto(command, (self._address, self._port))
            if res != len(command) and self._raise_errors:
                raise IOError
            # receive
            data = self._inst.recv(1024)
            # close
            self.close()
        else:
            data = self._inst.query(command)

        
        # decode
        if coding is not None:
            data = data.decode(coding)

        # debug
        if self._debug:
            print('DEBUG: Query ' + str(command) + ' = ' + str(data))


        return data


    
    def close(self):
        """
        Close connection to instrument
        """
        
        self._inst.close()
        if self._debug:
            print('DEBUG: Session closed!')

        self._inst = None


        
    def disconnect(self):
        """
        Close connection to instrument
        """
        self.close()
        
        
            
    def connect(self):
        """
        Connect to resource
        """

        # close if needed
        if self._inst is not None:
            self.close()

            
        if self._protocol=='udp':
            
            self._inst = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._inst.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._inst.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                # Some systems don't support SO_REUSEADDR
                pass
            self._inst.settimeout(self._timeout)
            if self._recv_port is not None:
                self._inst.bind(('', self._recv_port))

            if self._debug:
                print('DEBUG: UDP socket created!')

        else:
            rm = None
            if self._visa_library is None:
                rm = visa.ResourceManager()
            else:
                rm = visa.ResourceManager(self._visa_library)
                
            try:
                if self._verbose:
                    print('INFO: Opening VISA resource "{}"'.format(self._visa_address))

                self._inst = rm.open_resource(self._visa_address)
                if self._termination is not None:
                    self._inst.read_termination = self._termination
            
            except visa.VisaIOError as e:
            
                if self._verbose:
                    print('ERROR opening VISA resource "{}"'.format(self._visa_address))
                if self._raise_errors:
                    raise
                else:
                    return None

            
    def scan(self, message, scan_port, broadcast_address, coding='utf-8'):
        """
        """
               
        # check protocol
        if self._protocol != 'udp':
            print('WARNING: Scan only available with UDP connection!')
            return []


        # connect
        self.connect()

        # bind
        self._inst.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._inst.setblocking(False)
        self._inst.bind(('0.0.0.0', scan_port))

        # send message
        if coding is not None:
            message = message.encode(coding)

        self._inst.sendto(message,(broadcast_address, scan_port))
       
        # response
        response = []
        while True:
            readables, writable, excp = select.select([self._inst,], [], [], self._timeout)

            print(readables)
            # check timeout
            if not readables:
                break

            print(readables)
            # loop results
            for readable in readables:
                data, sender_addr = readable.recvfrom(1024)
                print(data)
                print(sender_addr)
                if data != message:
                    response.append((data, sender_addr))

        # close connection
        self._inst.close()
        
        return response

