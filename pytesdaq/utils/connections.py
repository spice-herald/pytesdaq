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
                        tes_channel=str(),
                        detector_channel= str(),
                        adc_id=str(), adc_channel=str()):

    return _get_info(connections,'controller',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel,
                     adc_id=adc_id, adc_channel=adc_channel)

                
        
def get_adc_info(connections,
                         tes_channel=str(),
                         detector_channel= str()):
    
    return _get_info(connections,'adc',
                     tes_channel=tes_channel,
                     detector_channel= detector_channel)
    


    
def _get_info(connections, info,
              tes_channel=str(),
              detector_channel= str(),
              adc_id=str(), adc_channel=str()):

        
    connections_indexed = []
    index_list = list()
    output_info = list()

    if tes_channel:
        connections_indexed = connections.set_index('tes_channel')
        index_list.append(re.sub(r'\s+','', str(tes_channel)))
    elif detector_channel:
        connections_indexed = connections.set_index('detector_channel')
        index_list.append(re.sub(r'\s+','', str(detector_channel)))
    elif adc_id and  adc_channel:
        connections.set_index(['adc_name','adc_channel'])
        index_list.append(re.sub(r'\s+','', str(adc_name)))
        index_list.append(re.sub(r'\s+','', str(adc_channel)))
    else:
        raise ValueError('ERROR::get_controller_info: Unable to understand input!')
                    
    index_tuple = tuple(index_list)
    
    info_tuple = tuple()
    if info=='controller':
        info_tuple = ('controller_id','controller_channel')
    elif info=='adc':
        info_tuple = ('adc_name','adc_channel')
        
    try:
        output_info = connections_indexed.loc[index_tuple,info_tuple].values[0]
    except:
        pass
        
    return output_info
       
