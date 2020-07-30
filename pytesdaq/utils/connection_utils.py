import pandas as pd
import re


def get_items(connections):
    
    """
    Return dictionary with indexer name and values
    """
    
    output = dict()
    connections_reset = connections.reset_index()
    for label,contents in connections_reset.items():
        output[label] = list(contents)
                
    return output




def get_controller_info(connections,
                        tes_channel=None,
                        detector_channel=None,
                        adc_id=None, adc_channel=None):

    return _get_info(connections,'controller',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel,
                     adc_id=adc_id, adc_channel=adc_channel)

                
        
def get_adc_channel_info(connections,
                         tes_channel=str(),
                         detector_channel= str()):
    
    return _get_info(connections,'adc',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel)
    


def get_adc_channel_list(connections,
                         tes_channel_list=list(),
                         detector_channel_list= list()):
    
    
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
            adc_id, adc_chan =   _get_info(connections,'adc',
                                           tes_channel=chan)
        else:
            adc_id,adc_chan =   _get_info(connections,'adc',
                                          detector_channel=chan)
    
        # add in dictionary
        if adc_chan is not None:
            if adc_id not in adc_dict:
                adc_dict[adc_id] = list()
            adc_dict[adc_id].append(int(adc_chan))
            adc_dict[adc_id].sort()
            
    
    return  adc_dict

    
            
    
def _get_info(connections, info,
              tes_channel=None,
              detector_channel= None,
              adc_id=None, adc_channel=None):

        
    connections_indexed = []
    index_list = list()
    
    loc_val = None
    if tes_channel is not None:
        connections_indexed = connections.set_index('tes_channel')
        loc_val = re.sub(r'\s+','', str(tes_channel))
    elif detector_channel is not None:
        connections_indexed = connections.set_index('detector_channel')
        loc_val = re.sub(r'\s+','', str(detector_channel))
    elif (adc_id is not None and  adc_channel is not None):
        connections_indexed = connections.set_index(['adc_id','adc_channel'])
        loc_val = (re.sub(r'\s+','', str(adc_id)),re.sub(r'\s+','', str(adc_channel)))
    else:
        raise ValueError('ERROR::get_controller_info: Unable to understand input!')
        
    try:
        output_info = connections_indexed.loc[loc_val]
    except:
        return None
        
    if info=='controller':
        return output_info['controller_id'], output_info['controller_channel']
    elif info=='adc':
        return output_info['adc_id'], output_info['adc_channel']
    else:
        return None
       
