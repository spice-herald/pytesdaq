import pandas as pd
import re


def get_items(connection_table):
    
    """
    Return dictionary with indexer name and values
    """
    
    output = dict()
    connections_reset = connection_table.reset_index()
    for label,contents in connections_reset.items():
        output[label] = list(contents)
                
    return output




def get_controller_info(connection_table,
                        tes_channel=None,
                        detector_channel=None,
                        adc_id=None, adc_channel=None):

    return _get_info(connection_table,'controller',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel,
                     adc_id=adc_id, adc_channel=adc_channel)

                
        
def get_adc_channel_info(connection_table,
                         tes_channel=None,
                         detector_channel=None):
    
    return _get_info(connection_table,'adc',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel)
    


def get_adc_channel_list(connection_table,
                         tes_channel_list=list(),
                         detector_channel_list=list()):
    
    
    if tes_channel_list:
        channel_list = tes_channel_list
        channel_type = 'tes'
    elif detector_channel_list:
        channel_list = detector_channel_list
        channel_type = 'detector'
    else:
        return

    adc_dict = dict()
    for chan in channel_list:
        adc_id = None
        adc_chan = None
        if channel_type == 'tes':
            adc_id, adc_chan =   _get_info(connection_table,'adc',
                                           tes_channel=chan)
        else:
            adc_id,adc_chan =   _get_info(connection_table,'adc',
                                          detector_channel=chan)
    
        # add in dictionary
        if adc_chan is not None:
            if adc_id not in adc_dict:
                adc_dict[adc_id] = list()
            adc_dict[adc_id].append(int(adc_chan))
            #adc_dict[adc_id].sort()
            
    
    return  adc_dict


    

def extract_adc_connection(connections):
    """
    Extract connection fields from a setup file connection line.

    A line that declares "tes:" is a real TES channel controlled by the
    front end board. A line without it (TTL input, accelerometer
    readout) still gets a tes_channel synthesized from its controller
    channel, so that callers indexing on tes_channel keep working, but
    is_tes_channel reports False for it.

    The synthesized "tes:" token is also appended to the returned token
    list, which is what gets written into raw data metadata. Connection
    tables rebuilt from a raw data file therefore report
    is_tes_channel = True for every channel. Use is_tes_channel only on
    tables built from a setup file through Config.get_adc_connections.

    Parameters
    ----------
    connections : str or list
        Connection fields, comma separated string or list of tokens.

    Returns
    -------
    connection_type_val_list : list of str
        The raw "name:value" tokens.
    connection_type_list : list of str
        Field names, matching connection_val_list.
    connection_val_list : list
        Field values, matching connection_type_list.
    """
    
    
    # argument 
    connection_list = list()
    if isinstance(connections,str):
        connection_list = connections.split(',')
    elif isinstance(connections,list):
        connection_list = connections
    else:
        raise ValueError('ERROR in  extract_adc_connection_list: ARgument should be a list or string')
   

    controller_id = None
    controller_chan = None
    tes_chan = None
    detector_chan = None
    connection_type_val_list = list()
    for val in connection_list:
        val = re.sub(r'\s+','', str(val))
        connection_type_val_list.append(val)

        # split in function of ":"
        val_split = val.split(':')
        
        # controller
        if val_split[0]=='controller':
            id_chan = val_split[1].rsplit('_',1)
            if len(id_chan)!=2:
                raise ValueError('Wrong controller config format: It should be "controller:[id]_[chan]"!')
            controller_id = id_chan[0]
            controller_chan = id_chan[1]
        
        # TES
        if val_split[0]=='tes':
            tes_chan = val_split[1]

        # Detector
        if val_split[0]=='detector':
            detector_chan = val_split[1]
                    
    # a connection line that declares "tes:" is a real TES channel on
    # the front end board. Lines without it (TTL, accelerometer) still
    # get a tes_channel synthesized from the controller channel, kept
    # for backward compatibility, but they are not TES channels and
    # must never be biased
    is_tes_channel = tes_chan is not None

    if tes_chan is None:
        tes_chan = controller_chan
        connection_type_val_list.append('tes:' + str(controller_chan))

    connection_type_list = ['detector_channel', 'tes_channel', 'controller_id',
                            'controller_channel', 'is_tes_channel']
    connection_val_list = [detector_chan, tes_chan, controller_id, controller_chan,
                           is_tes_channel]
    return connection_type_val_list, connection_type_list, connection_val_list


            
    
def _get_info(connection_table, info,
              tes_channel=None,
              detector_channel= None,
              adc_id=None, adc_channel=None):

        
    connection_table_indexed = []
    index_list = list()
    
    loc_val = None
    if tes_channel is not None:
        connection_table_indexed = connection_table.set_index('tes_channel')
        loc_val = re.sub(r'\s+','', str(tes_channel))
    elif detector_channel is not None:
        connection_table_indexed = connection_table.set_index('detector_channel')
        loc_val = re.sub(r'\s+','', str(detector_channel))
    elif (adc_id is not None and  adc_channel is not None):
        connection_table_indexed = connection_table.set_index(['adc_id','adc_channel'])
        loc_val = (re.sub(r'\s+','', str(adc_id)),re.sub(r'\s+','', str(adc_channel)))
    else:
        raise ValueError('ERROR::get_controller_info: Unable to understand input!')
        
    try:
        output_info = connection_table_indexed.loc[loc_val]
    except:
        return None
        
    if info=='controller':
        controller_channel = output_info['controller_channel']
        controller_id = output_info['controller_id']
        if controller_id=='magnicon':
           controller_channel = int(controller_channel) 
        return controller_id, controller_channel
    elif info=='adc':
        return output_info['adc_id'], output_info['adc_channel']
    else:
        return None
       
