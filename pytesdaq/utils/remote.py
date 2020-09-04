import os
import sys
import time
import select
import socket
import termios
import time
import traceback
import getpass
from binascii import hexlify
import paramiko
from paramiko.py3compat import input, u



class Remote(object):
    """
    Use ssh connection to remote computer, using Python paramiko library
    """

    def __init__(self, hostname='', port=22, username='', auth_method='rsa', auth_val='', log_file='demo.log'):
        """
        Initialize class with hostname, port, username,
        authentication method (rsa, dss, or password),
        and Paramiko log file.
        Store auth_val if you want to set the RSA/DSS key or password.
        """
        self._hostname = hostname
        self._port = port
        self._username = username

        self._auth_method = auth_method
        if auth_val != '':
            self.set_auth_value(auth_val)

        self._log_file = log_file
        paramiko.util.log_to_file(log_file)

        self._channel = None
        self._transport = None
        self._oldtty = None



    def authenticate(self, transport):
        """
        Authenticate using the current authentication method;
        if that is not set, just use any private key available
        """
        if self._auth_method == 'rsa':
            self.authenticate_rsa(transport)
        elif self._auth_method == 'dss':
            self.authenticate_dss(transport)
        elif self._auth_method == 'password':
            self.authenticate_password(transport)
        else:
            self.authenticate_auto(transport)



    def authenticate_auto(self, transport):
        """
        Attempt to authenticate to the given transport using any of the private
        keys available from an SSH agent.
        """

        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            print("Trying ssh-agent key %s" % hexlify(key.get_fingerprint()))
            try:
                transport.auth_publickey(username, key)
                print("... success!")
                return
            except paramiko.SSHException:
                print("... nope.")

        if not transport.is_authenticated():
            print("*** Authentication failed.")
            transport.close()
            sys.exit(1)



    def authenticate_rsa(self, transport):
        """
        Attempt to authenticate to the given transport using an RSA key
        """

        try:
            key = paramiko.RSAKey.from_private_key_file(self._rsa_key)
        except paramiko.PasswordRequiredException:
            password = getpass.getpass("RSA key password: ")
            key = paramiko.RSAKey.from_private_key_file(self._rsa_key, password)
        transport.auth_publickey(self._username, key)

        if not transport.is_authenticated():
            print("*** Authentication failed.")
            transport.close()
            sys.exit(1)



    def authenticate_dss(self, transport):
        """
        Attempt to authenticate to the given transport using a DSS key
        """

        try:
            key = paramiko.DSSKey.from_private_key_file(self._rsa_key)
        except paramiko.PasswordRequiredException:
            password = getpass.getpass("DSS key password: ")
            key = paramiko.RSAKey.from_private_key_file(self._rsa_key, password)
        transport.auth_publickey(self._username, key)
        if not transport.is_authenticated():
            print("*** Authentication failed.")
            transport.close()
            sys.exit(1)



    def authenticate_password(self, transport):
        """
        Attempt to authenticate to the given transport using a password
        """
        transport.auth_password(self._username, self._password)

        if not transport.is_authenticated():
            print("*** Authentication failed.")
            transport.close()
            sys.exit(1)



    def open_connection(self):
        """
        Open ssh connection to remote computer, using the object's
        hostname, port, username, and relevant authentication details.
        Return Paramiko Channel and Transport objects.
        """

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._hostname, self._port))
        except Exception as e:
            print("*** Connection to %s failed: " % self._hostname + str(e))
            traceback.print_exc()
            sys.exit(1)

        try:
            transport = paramiko.Transport(sock)
            try:
                transport.start_client()
            except paramiko.SSHException:
                print("*** SSH negotiation failed.")
                sys.exit(1)

            try:
                keys = paramiko.util.load_host_keys(
                    os.path.expanduser("~/.ssh/known_hosts")
                )
            except IOError:
                print("*** Unable to open host keys file")
                keys = {}

            # check server's host key -- this is important.
            key = transport.get_remote_server_key()
            print('Known keys:')
            print(keys.keys())
            print('')
            print('Our key:', keys['128.32.239.62'].keys())
            print('Server key:', key.get_name())
            print('')
            if self._hostname not in keys:
                print("*** WARNING: Unknown host key!")
            elif key.get_name() not in keys[self._hostname]:
                print("*** WARNING: Unknown host key!")
            elif keys[self._hostname][key.get_name()] != key:
                print("*** WARNING: Host key has changed!!!")
                sys.exit(1)
            else:
                print("*** Host key OK.")

            self.authenticate(transport)
            if not transport.is_authenticated():
                print("*** Authentication failed. :(")
                transport.close()
                sys.exit(1)

            channel = transport.open_session()
            # channel.get_pty()
            channel.invoke_shell()
            channel.settimeout(0.0)
            self._oldtty = termios.tcgetattr(sys.stdin)

            self._channel = channel
            self._transport = transport
            return channel, transport

        except Exception as e:
            print("*** Caught exception: " + str(e.__class__) + ": " + str(e))
            traceback.print_exc()
            try:
                if self._old_tty is not None:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._oldtty)
                transport.close()
            except:
                pass
            sys.exit(1)



    def close_connection(self):
        """
        Close ssh session
        """

        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._oldtty)
            self._channel.close()
            self._transport.close()
        except:
            pass



    def send_command(self, command):
        """
        Send a command to the remote computer. Append '\n' to the command
        if not present. Returns number of bytes sent.
        """

        if not self._transport.is_active():
            print('ERROR: Cannot send command. Transport not active.')
            print('Closing connection to ' + self._hostname)
            try:
                self.close_connection()
            except:
                pass
            return 0

        if command[-1] != '\n':
            command = command + '\n'

        try:
            nb = self._channel.send(command)
            return nb
        except Exception as ex:
            print("*** Caught exception: " + str(ex.__class__) + ": " + str(ex))
            traceback.print_exc()
            print('Closing connection to ' + self._hostname)
            try:
                self.close_connection()
            except:
                pass
            return 0



    def receive_output(self):
        """
        Receive text from the remote machine (sys.stdout on that machine).
        Returns the string "EOF" if the connection is terminated. (not an actual EOF character)
        Returns the string "" if no output is recevied.
        """


        if not self._transport.is_active():
            print('ERROR: Cannot send command. Transport not active.')
            print('Closing connection to ' + self._hostname)
            try:
                self.close_connection()
            except:
                pass
            return 0

        try:
            r, w, e = select.select([self._channel, sys.stdin], [], [], 0.1)
            if self._channel in r:
                try:
                    x = u(self._channel.recv(1024))
                    if len(x) == 0:
                        sys.stdout.write("*** Received EOF from %s. Closing session. ***" % self._hostname)
                        sys.stdout.flush()
                        self.close_connection()
                        return 'EOF'
                    else:
                        return x
                except socket.timeout:
                    return ''
        except Exception as ex:
            print("*** Caught exception: " + str(ex.__class__) + ": " + str(ex))
            traceback.print_exc()
            print('Closing connection to ' + self._hostname)
            try:
                self.close_connection()
            except:
                pass
            return ''



    def check_transport_active(self):
        """
        Check if transport is active.
        Return False if transport is not a Paramiko Transport object.
        """
        try:
            return self._transport.is_active()
        except:
            return False


        
    def get_hostname(self):
        """
        Get hostname
        """
        return self._hostname



    def get_port(self):
        """
        Get SSH port
        """
        return self._port



    def get_username(self):
        """
        Get username
        """
        return self._username



    def get_auth_method(self):
        """
        Get authentication method
        """
        return self._auth_method



    def get_rsa_key(self):
        """
        Get RSA key
        """
        return self._rsa_key



    def get_dss_key(self):
        """
        Get DSS key
        """
        return self._dsa_key



    def get_log_file(self):
        """
        Get Paramiko log file
        """
        return self._log_file



    def get_transport(self):
        """
        Get Paramiko transport object
        """
        return self._transport



    def get_channel(self):
        """
        Get Paramiko SSH channel
        """
        return self._channel



    def get_oldtty(self):
        """
        Get old TTY (termios object)
        """
        return self._oldtty


    def set_hostname(self, hostname):
        """
        Set hostname
        """
        self._hostname = hostname



    def set_port(self, port):
        """
        Set SSH port
        """
        self._port = port



    def set_username(self, username):
        """
        Set username
        """
        self._username = username



    def set_auth_method(self, auth_method):
        """
        Set authentication method
        """
        self.auth_method = auth_method



    def set_auth_value(self, auth_value):
        """
        Set authentication value (RSA key DSS key, or password)
        If you want to set the password in secret text, don't use this
        """
        if self._auth_method == 'rsa':
            self.set_rsa_key(auth_value)
        elif self._auth_method == 'dss':
            self.set_dss_key(auth_value)
        elif self._auth_method == 'password':
            self.set_password(False, auth_value)
        else:
            print('Authentication method invalid. Could not set value.')



    def set_rsa_key(self, rsa_key):
        """
        Set RSA key
        """
        self._rsa_key = rsa_key



    def set_dss_key(self, dss_key):
        """
        Set DSS key
        """
        self._dss_key = dss_key



    def set_password(self, secret=True, password=''):
        """
        Set password
        If secret = True, the user will be asked to provide it manually
        """
        if secret:
            self._password = getpass.getpass("Password for %s@%s: " % (self._username, self._hostname))
        else:
            self._password = password



    def set_log_file(self, log_file):
        """
        Set Paramiko log file
        """
        self._log_file = log_file
        paramiko.util.log_to_file(log_file)



    def set_transport(self, transport):
        """
        Set Paramiko transport object
        """
        self._transport = transport



    def set_channel(self, channel):
        """
        Set Paramiko SSH channel
        """
        self._channel = channel


