import yaml
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import vaex as vx
import importlib
import sys
import os
from glob import glob
from pprint import pprint
from multiprocessing import Pool
from itertools import repeat
from datetime import datetime
import stat
import time
import astropy
from humanfriendly import parse_size
from itertools import groupby

from detprocess.utils import utils

import pytesdaq.io as h5io
import qetpy as qp

warnings.filterwarnings('ignore')


__all__ = [
    'IVSweepProcessing'
]



class IVSweepProcessing:
    """
    Class to manage IV/dIdV sweeps processing

    Multiple nodes can be used if data splitted in 
    different series

    """

    def __init__(self, raw_path,
                 config_file=None,
                 processing_id=None,
                 verbose=True):
        """
        Intialize data processing 
        
        Parameters
        ---------
    
        raw_path : str 
           Group directory containing IV/dIdV sweep data 
            
        config_file : str 
           Full path and file name to the YAML settings for the
           processing.

        processing_id : str, optional
            an optional processing name. This is used to be build output subdirectory name 
            and is saved as a feature in DetaFrame so it can then be used later during 
            analysis to make a cut on a specific processing when mutliple 
            datasets/processing are added together.

        verbose : bool, optional
            if True, display info


        Return
        ------
        None
        """

        # processing id
        self._processing_id = processing_id

        # display
        self._verbose = verbose

        # Raw file list
        data_dict, group_name = (
            self._get_file_list(raw_path)
        )

        self._data_dict = data_dict
        self._group_name = group_name

        

    def describe(self):
        """
        Describe data
        """
        
        print(f'IV/dIdV Sweep: {self._group_name}')
        
        for chan in self._data_dict.keys():
            print(' ')
            print(f'{chan}:')
            
            # IV 
            if self._data_dict[chan]['IV']:
                nb_points_iv = len(
                    list(self._data_dict[chan]['IV'].keys())
                )
                
                print(f' -IV: {nb_points_iv} bias points')

            # dIdV 
            if self._data_dict[chan]['dIdV']:
                nb_points_didv = len(
                    list(self._data_dict[chan]['dIdV'].keys())
                )
                print(f' -dIdV: {nb_points_didv} bias points')
         

        
        
    def process(self,
                channel,
                enable_iv=True,
                enable_didv=True,
                lgc_save=False,
                save_path='./',
                lgc_output=False,
                ncores=1):
        
        """
        Process data 
        
        Parameters
        ---------
        
        lgc_save : bool, optional
           if True, save dataframe in hdf5 files
           Default: False

        lgc_output : bool, optional
           if True, return dataframe 
           Default: False

        save_path : str, optional
           base directory where output group will be saved
           default: same base path as input data
    
        ncores: int, optional
           number of cores that will be used for processing
           default: 1

    
        """


        # channel data
        if channel not in self._data_dict.keys():
            raise ValueError(f'ERROR: channel {channel}'
                             ' not available!')

        data_chan = self._data_dict[channel]

        # processing type
        processing_types = list()
        if enable_iv and 'IV' in  data_chan.keys():
            processing_types.append('IV')
        if enable_didv and 'dIdV' in  data_chan.keys():
            processing_types.append('dIdV')

            
        # initialize output
        output_df = None

        # loop processing type
        for ptype in processing_types:

            # series list
            series_list =  list(data_chan[ptype].keys())


            # check number cores allowed
            if ncores>len(series_list):
                ncores = len(series_list)
                if self._verbose:
                    print('INFO: Changing number cores to '
                          + str(ncores) + ' (maximum allowed)')
                   
            # initialize df
            df_ptype = None

            
            # lauch pool processing
            if self._verbose:
                print('INFO: ' + ptype
                      + ' processing will be split'
                      + ' between ' + str(ncores) + ' core(s)!')
                
            # case only 1 node used for processing
            if ncores == 1:
                df_ptype = self._process(1, channel, ptype, series_list)
            else:

                # split data
                series_list_split = self._split_series(series_list, ncores)

                # launch
                node_nums = list(range(ncores+1))[1:]
                pool = Pool(processes=ncores)
                df_ptype_list = pool.starmap(
                    self._process,
                    zip(node_nums,
                        repeat(channel),
                        repeat(ptype),
                        series_list_split)
                )
                
                pool.close()
                pool.join()

                # concatenate
                df_ptype = pd.concat(df_ptype_list, ignore_index=True)

            if output_df is None:
                output_df = df_ptype
            else:
                output_df = pd.concat([output_df, df_ptype],
                                      ignore_index=True)
            
                
                    
        # processing done
        if self._verbose:
            print('INFO: IV/dIdV processing done!') 
                
        if lgc_save:

            output_dir = save_path
            if self._group_name not in output_dir:
                output_dir += '/' + self._group_name
                
            if not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError:
                    raise ValueError('\nERROR: Unable to create directory "'
                                     + output_dir  + '"!\n')
                       
            now = datetime.now()
            series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
            series_time = now.strftime('%H') + now.strftime('%M')
            series_name = ('D' + series_day + '_T'
                           + series_time + now.strftime('%S'))
            file_name = (output_dir + '/' + '_'.join(processing_types)
                         + '_processing_' + series_name + '.hdf5')
            
            output_df.to_hdf(file_name, key=channel, mode='a')
            print(f'INFO: Saving dataframe in {file_name}') 

        if lgc_output:
            return output_df 
        
       
    def _process(self, node_num,
                 channel,
                 processing_type,
                 series_list):
                 
        """
        Process data
        
        Parameters
        ---------

        node_num :  int
          node id number, used for display
       
        processing_type : str
          processing type ('IV' or 'dIdV')

 
        series_list : str
          list of series name to be processed
        
          
        """

        # node string (for display)
        node_num_str = str()
        if node_num>-1:
            node_num_str = (str(processing_type)
                            + ' node #'
                            + str(node_num))


        
        # loop series
        data_list = list()
        
        for series in series_list:

            # verbose
            if self._verbose:
                print(f'INFO {node_num_str}: starting processing series {series}')
            
            file_list = self._data_dict[channel][processing_type][series]
            if not file_list:
                raise ValueError(f'ERROR {processing_type} processing: '
                                 'No files found for series {series},'
                                 'channel {channel} ')
            
            # load data
            traces = None
            detector_settings = None
            fs = None
            
            try:
                h5 = h5io.H5Reader()
                traces, info = h5.read_many_events(
                    filepath=file_list,
                    output_format=2,
                    include_metadata=True,
                    detector_chans=channel,
                    adctoamp=True)

                traces = traces[:,0,:]
                fs  = info[0]['sample_rate']
                detector_settings = h5.get_detector_config(file_name=file_list[0])
                del h5

            except:
                raise OSError('Unable to get traces or detector settings from hdf5 data!')
        

            # detector parameters
            tes_bias = float(detector_settings[channel]['tes_bias'])
            sgamp = float(detector_settings[channel]['signal_gen_current'])
            sgfreq = float(detector_settings[channel]['signal_gen_frequency'])
            rshunt = float(detector_settings[channel]['shunt_resistance'])
            dutycycle = 0.5
            if 'dutycycle' in detector_settings[channel]:
                dutycycle = float(detector_settings[channel]['dutycycle'])

                
            if processing_type == 'IV':

                # ----------------
                # IV calculation
                # ----------------
                            
                # apply cut
                cut = qp.autocuts_noise(traces, fs=fs)
                cut_pass = True
                traces = traces[cut]
                
                # PSD calculation
                f, psd = qp.calc_psd(traces, fs=fs)
                
                # Offset calculation
                offset, offset_err = qp.utils.calc_offset(traces, fs=fs)
                
                # Pulse average
                avgtrace = np.mean(traces, axis=0)

                # store data
                sgamp = None
                sgfreq = None
                datatype = 'noise'
                cut_eff = np.sum(cut)/len(cut)
                didvmean = None
                didvstd = None

                data = [
                    channel,
                    series,
                    fs,
                    tes_bias,
                    sgamp,
                    sgfreq,
                    offset,
                    offset_err,
                    f,
                    psd,
                    avgtrace,
                    didvmean,
                    didvstd,
                    datatype,
                    cut_eff,
                    cut,
                    cut_pass,
                    dutycycle,
                ]

                data_list.append(data)

                
            elif processing_type == 'dIdV':

                # ----------------
                # dIdV calculation
                # ----------------

                # get rid of traces that are all zero
                zerocut = np.all(traces!=0, axis=1)
                traces = traces[zerocut]

                # pile-up cuts
                cut = qp.autocuts_didv(traces, fs=fs)
                cut_pass = True
                traces = traces[cut]

                # Offset calculation
                offset, offset_err = qp.utils.calc_offset(
                    traces, fs=fs, sgfreq=sgfreq, is_didv=True)
                
                # Average pulse
                avgtrace = np.mean(traces, axis=0)

                # dIdV fit
                didvobj = qp.DIDV(
                    traces,
                    fs,
                    sgfreq,
                    sgamp,
                    rshunt,
                    autoresample=False,
                    dutycycle=dutycycle,
                )
                
                didvobj.processtraces()

                # store data
                didvmean = didvobj._didvmean
                didvstd = didvobj._didvstd
                f = None
                psd = None
                datatype = 'didv'
                cut_eff = np.sum(cut)/len(cut)

                data = [
                    channel,
                    series,
                    didvobj._fs,
                    tes_bias,
                    sgamp,
                    sgfreq,
                    offset,
                    offset_err,
                    f,
                    psd,
                    avgtrace,
                    didvmean,
                    didvstd,
                    datatype,
                    cut_eff,
                    cut,
                    cut_pass,
                    dutycycle,
                ]

                data_list.append(data)

        # convert to dataframe
        df = pd.DataFrame(
            data_list,
            columns=[
                'channels',
                'seriesnum',
                'fs',
                'qetbias',
                'sgamp',
                'sgfreq',
                'offset',
                'offset_err',
                'f',
                'psd',
                'avgtrace',
                'didvmean',
                'didvstd',
                'datatype',
                'cut_eff',
                'cut',
                'cut_pass',
                'dutycycle']
        )
    
        return df
            
                
           
        
    def _get_file_list(self, raw_path):
        
        """
        Get file list from path. Return as a dictionary
        with key=series and value=list of files

        Parameters
        ----------

        raw_path : str
           raw data group directory OR full path to HDF5  file 
           (or list of files). Only a single raw data group 
           allowed 
        
              

        Return
        -------
        
        data_dict : dict 
          list of files for splitted inot series
     
        group_name : str
           group name of raw data

        """


        # check that it is a directory
        
        if not os.path.isdir(raw_path):
              raise ValueError(f'ERROR: Input path {raw_path} does not exist '
                               ' or is not a directory!')
                 
        # initialize
        data_dict = dict()
          
        # get list of files
        if raw_path[-1] == '/':
            raw_path = raw_path[0:-1]
            
        file_list = glob(raw_path + '/*_F0001.hdf5')

        # check
        if not file_list:
             raise ValueError(f'ERROR: No hdf5 files found in {raw_path}')

        # sort
        file_list.sort()

        # initialize raw reader
        h5reader = h5io.H5Reader()


        # 1. split IV/dIdV series
        series_dict = {'IV':dict(), 'dIdV':dict()}
        for a_file in file_list:

            metadata = h5reader.get_file_info(a_file)
            
            # data purpose
            data_purpose = metadata['data_purpose']

            # series name
            series_name = h5io.extract_series_name(metadata['series_num'])

            # file list
            series_file_list = glob(f'{raw_path}/*_{series_name}_F*.hdf5')
            
            if data_purpose == 'IV':
                series_dict['IV'][series_name] = series_file_list
            elif data_purpose == 'dIdV':
                series_dict['dIdV'][series_name] = series_file_list
            else:
                raise ValueError(f'ERROR: Unknow data purpose "{data_purpose}"')


        # 2. find sweep channels
        channels = list()
        channel_dict = {'IV':list(), 'dIdV':list()}
        data_types = ['IV', 'dIdV']
        for data_type in data_types:
            
            # check if data
            if not series_dict[data_type]:
                continue

            
            # first/last config
            series_list = list(series_dict[data_type].keys())
            file_first = glob(f'{raw_path}/*_{series_list[0]}_F0001.hdf5')[0]
            file_last = glob(f'{raw_path}/*_{series_list[-1]}_F0001.hdf5')[0]
            
            config_first = h5reader.get_detector_config(file_first)
            config_last = h5reader.get_detector_config(file_last)
                                                       
            # loop channels
            for chan in config_first.keys():
                qet_bias_first = round(float(config_first[chan]['tes_bias'])*1e6, 1)
                qet_bias_last = round(float(config_last[chan]['tes_bias'])*1e6, 1)
                if (qet_bias_first != qet_bias_last):
                    channels.append(chan)
                    if data_type=='IV':
                        channel_dict['IV'].append(chan)
                    else:
                        channel_dict['dIdV'].append(chan)
                        
                        
        # 3. find series for each channel
 
        # initialize
        for chan in channels:
            data_dict[chan] = {'IV':dict(), 'dIdV': dict()}

        
        # For IV data, all sweep channels are from same series
        for chan in channel_dict['IV']:
            data_dict[chan]['IV'] = series_dict['IV']

        # For dIdV, if more than 1 channel
        # we need to check if signal generator on/off
        # FIXME: add file attributes
        
                
        if len(channel_dict['dIdV']) == 1:
            data_dict[chan]['dIdV'] = series_dict['dIdV']
        else:
            # loop series
            for series_name in series_dict['dIdV']:
                file_name = glob(f'{raw_path}/*_{series_name}_F0001.hdf5')[0]
                
                # get detector config
                config = h5reader.get_detector_config(file_name)

                # check signal generator
                for chan in channel_dict['dIdV']:
                    is_didv = (config[chan]['signal_gen_onoff']=='on' and
                               config[chan]['signal_gen_source']=='tes')
                    if is_didV:
                        data_dict[chan]['dIdV'][series_name] = (
                            series_dict['dIdV'][series_name]
                        )
                    
        # group name
        group_name = str(Path(raw_path).name)
          
        return data_dict, group_name
    

    

    def _create_output_directory(self, base_path, facility):
        
        """
        Create output directory 

        Parameters
        ----------
        
        base_path :  str
           full path to base directory 
        
        facility : int
           id of facility 
    
        Return
        ------
          output_dir : str
            full path to created directory

        """

        now = datetime.now()
        series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
        series_time = now.strftime('%H') + now.strftime('%M')
        series_name = ('I' + str(facility) +'_D' + series_day + '_T'
                       + series_time + now.strftime('%S'))

        series_num = h5io.extract_series_num(series_name)
        
        # prefix
        prefix = 'feature'
        if self._processing_id is not None:
            prefix = self._processing_id + '_feature'
        if restricted:
            prefix += '_restricted'
        output_dir = base_path + '/' + prefix + '_' + series_name
        
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
                os.chmod(output_dir, stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)
            except OSError:
                raise ValueError('\nERROR: Unable to create directory "'+ output_dir  + '"!\n')
                
        return output_dir, series_num
        

    def _split_series(self, series_list, ncores):
        """
        Split data  between nodes
        following series


        Parameters
        ----------

        ncores : int
          number of cores

        Return
        ------

        output_list : list
           list of dictionaries (length=ncores) containing 
           data
         

        """

        output_list = list()
        
        # split series
        series_split = np.array_split(series_list, ncores)

        # remove empty array
        for series_sublist in series_split:
            if series_sublist.size == 0:
                continue
            output_list.append(list(series_sublist))
            

        return output_list
