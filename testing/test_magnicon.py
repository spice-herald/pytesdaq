import sys
sys.path.insert(0, '/data/pytesdaq/')
sys.path.insert(0, '/data/pytesdaq/pytesdaq')
sys.path.insert(0, '/data/pytesdaq/pytesdaq/instruments')
sys.path.insert(0, '/data/pytesdaq/pytesdaq/instruments/magnicon')
sys.path.insert(0, '/data/pytesdaq/pytesdaq/config')
sys.path.insert(0, '/data/pytesdaq/pytesdaq/utils')
import magnicon, remote

mag_conn_info = {'hostname': '128.32.239.62', 
    'username': 'mckinseyleidenfridge',
    'port': 22,
    'rsa_key': '/home/vvelan/.ssh/id_rsa_no_pass',
    'log_file': '/data/pytesdaq/pytesdaq/squid.log',
    'exe_location': 'C:\\Users\\McKinseyLeidenFridge\\GitRepos\\pytesdaq\\pytesdaq\\instruments\\magnicon\\dll'}

m = magnicon.Magnicon(channel_list=[1,2,3], default_active=2, reset_active=1, conn_info=mag_conn_info, remote_inst=None)
m.set_remote_inst()
m.connect()
m.chdir()
