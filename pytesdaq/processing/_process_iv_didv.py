import numpy as np
import pandas as pd
import os
import multiprocessing
from itertools import repeat
from glob import glob

from qetpy import calc_psd, autocuts, DIDV
from qetpy.utils import calc_offset

import pytesdaq.io.hdf5 as h5io




__all__ = [
    "process_ivsweep",
]


def _process_ivfile(filepath, chans, autoresample_didv, dutycycle,
                    lgcverbose):
    """
    Helper function to process data from noise or dIdV series as part
    of an IV/dIdV sweep. See Notes for more details on what parameters
    are calculated.

    Parameters
    ----------
    filepath : str
        Absolute path to the series folder OR full file name
    chans : list
        List containing strings corresponding to the names of all the
        channels of interest.
    autoresample_didv : bool
        If True, the DIDV code will automatically resample
        the DIDV data so that `fs` / `sgfreq` is an integer, which
        ensures that an arbitrary number of signal-generator
        periods can fit in an integer number of time bins. See
        `qetpy.utils.resample_data` for more info.
    dutycycle : float
        The duty cycle of the signal generator, should be a float
        between 0 and 1.
    lgcverbose : bool
        If True, the series number being processed will be displayed.

    Returns
    -------
    data_list : list
        The list of calculated parameters

    Notes
    -----
    For each series passed to this function, the following parameters
    are calculated/looked up:

        Channel name,
        Series number,
        Sample rate,
        Qetbias,
        Amplitude of signal generator (referenced in terms of QET bias
            current) #If didv data,
        Frequency of signal generator #If didv data,
        DC offset,
        STD of the DC offset,
        PSD (folded over),
        Corresponding frequencies for the PSD,
        Average trace,
        dIdV mean (calculated using DIDV class),
        dIdV STD (calculated using DIDV class),
        data type ('noise' or 'didv'),
        Efficiency of the auto cuts to the data,
        The boolean cut mask,
        A boolean saying whether or not the auto cuts were successful
            or not.
        dutycycle of the square wave

    """

    if lgcverbose:
        print('\n============================')
        print(f'Processing dumps in: {filepath}')
        print('============================\n')


    # Initialize output data list
    data_list = []


        
    # =====================
    # File type
    # =====================

    if os.path.isdir(filepath):
        file_list = list()
        file_list.extend(glob(filepath+'/*.hdf5'))

        if not file_list:
            raise OSError('No hdf5 found!')

    elif os.path.isfile(filepath):
        if filepath.find('.hdf5')==-1:
            raise OSError('No hdf5 found!')

    else:
        raise OSError('Directory or file "' + filepath + '" does not exist!')


    
    # =====================
    # Get pulse data
    # and detector settings
    # =====================

    # Get detector settings (-> use first file)
    settings_file = glob(f"{filepath}*")[0]

    
    # series number (a bit sketchy...)
    if filepath[-1] == '/':
        seriesnum = filepath[:-1].split('/')[-1]
    else:     
        seriesnum = filepath.split('/')[-1]

    # channels
    if isinstance(chans, str):
        chans = [chans]
    nchan = len(chans)


    traces = []
    channels = []
    detector_settings =[]
    signal_gen_settings = []
    fs = []
    

    try:
        h5 = h5io.H5Reader()
        traces, info = h5.read_many_events(
            filepath=filepath,
            output_format=2,
            include_metadata=True,
            detector_chans=chans,
            adctovolt=True,
            nevents=100,
        )

        channels = info[0]['detector_chans']
        fs  = info[0]['sample_rate']
        detector_settings = h5.get_detector_config(file_name=settings_file)
        del h5

    except:
        raise OSError('Unable to get traces or detector settings from hdf5 data!')
        



        
    
    # =====================
    # Loop channels
    # =====================
    
    for chan in channels:

        # channel array index
        chan_index = channels.index(chan)

        if lgcverbose:
            print(f'Processing channel {chan} (ndarray index = {chan_index})')


        # check if IV or dIdV processing
        is_didv = (detector_settings[chan]['signal_gen_onoff']=='on' and
                   detector_settings[chan]['signal_gen_source']=='tes')
                 

        # convert  to amps
        convtoamps =  1/detector_settings[chan]['close_loop_norm']

        traces_amps = traces[:,chan_index]*convtoamps


        # get a few more parameters
        qetbias = float(detector_settings[chan]['tes_bias'])
        sgamp = float(detector_settings[chan]['signal_gen_current'])
        sgfreq = float(detector_settings[chan]['signal_gen_frequency'])
        rshunt_temp = detector_settings[chan]['shunt_resistance']
        if rshunt_temp:
            rshunt = float(rshunt_temp)


        if not is_didv:

            # ----------------
            # IV calculation
            # ----------------
            
            
            if lgcverbose:
                print('----\nIV processing\n----')

                
            # apply cut
            cut_pass = True
            try:
                cut = autocuts(traces_amps, fs=fs)
            except:
                cut = np.ones(shape = traces_amps.shape[0], dtype=bool)
                cut_pass = False 

            # PSD calculation
            f, psd = calc_psd(traces_amps[cut], fs=fs)

            # Offset calculation
            offset, offset_err = calc_offset(traces_amps[cut], fs=fs)

            # Pulse average
            avgtrace = np.mean(traces_amps[cut], axis = 0)

            # Store data
            sgamp = None
            sgfreq = None
            datatype = 'noise'
            cut_eff = np.sum(cut)/len(cut)
            didvmean = None
            didvstd = None

            data = [
                chan,
                seriesnum,
                fs,
                qetbias,
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

        else:

            # ----------------
            # dIdV calculation
            # ----------------
            
            if lgcverbose:
                print('----\ndIdV processing\n----')

                

            # get rid of traces that are all zero
            zerocut = np.all(traces_amps!=0, axis=1)
            traces_amps = traces_amps[zerocut]

            # pile-up cuts
            cut_pass = True
            try:
                cut = autocuts(
                    traces_amps, fs=fs, is_didv=True, sgfreq=sgfreq,
                )
            except:
                cut = np.ones(shape = traces_amps.shape[0], dtype=bool)
                cut_pass = False 

            # Offset calculation
            offset, offset_err = calc_offset(
                traces_amps[cut], fs=fs, sgfreq=sgfreq, is_didv=True,
            )

            # Average pulse
            avgtrace = np.mean(traces_amps[cut], axis = 0)

            # dIdV fit
            didvobj = DIDV(
                traces_amps[cut],
                fs,
                sgfreq,
                sgamp,
                rshunt,
                autoresample=autoresample_didv,
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
                chan,
                seriesnum,
                didvobj._fs,
                qetbias,
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

    return data_list


def process_ivsweep(ivfilepath, chans, autoresample_didv=False, dutycycle=0.5,
                    lgcverbose=False, lgcsave=True, nprocess=1, savepath='',
                    savename='IV_dIdV_DF'):
    """
    Function to process data for an IV/dIdV sweep. See Notes for
    more details on what parameters are calculated.

    Parameters
    ----------
    ivfilepath : str, list of str
        Absolute path to the directory containing all the series in the
        sweep. Can also pass a list of specific paths to the parent
        directories of files to process.
    chans : list
        List containing strings corresponding to the names of all the
        channels of interest.
    autoresample_didv : bool, optional
        If True, the DIDV code will automatically resample
        the DIDV data so that `fs` / `sgfreq` is an integer, which
        ensures that an arbitrary number of signal-generator
        periods can fit in an integer number of time bins. See
        `qetpy.utils.resample_data` for more info.
    dutycycle : float, optional
        The duty cycle of the signal generator, should be a float
        between 0 and 1.
    lgcverbose : bool, optional
        If True, the series number being processed will be displayed.
    lgcsave : bool, optional
        If True, the processed DF is saved in the user specified
        directory.
    nprocess : int, optional
        Number of jobs to use to process IV dIdV sweep.
        If nprocess = 1, only a single core will be used. If more than
        one, Pool will be used for multiprocessing. Note, if you are
        running this on a shared computer, no more than 4 jobs should
        be used, ideally 2, as it will significantly slow down the
        computer.
    lgcsave : bool, optional
        If True, the processed DataFrame will be saved.
    savepath : str, optional
        Abosolute path to save DataFrame.
    savename : str, optional
        The name of the processed DataFrame to be saved.

    Returns
    -------
    df : pandas.DataFrame
        A pandas DataFrame with all the processed parameters for the
        IV/dIdV sweep.

    Notes
    -----
    For each series in the IV/dIdV sweep, the following parameters are
    calculated/looked up:

        Channel name,
        Series number,
        Sample rate,
        Qetbias,
        Amplitude of signal generator (referenced in terms of QET bias
            current) #If didv data, 
        Frequency of signal generator #If didv data,
        DC offset,
        STD of the DC offset,
        PSD (folded over),
        Corresponding frequencies for the PSD,
        Average trace,
        dIdV mean (calculated using DIDV class),
        dIdV STD (calculated using DIDV class),
        data type ('noise' or 'didv'),
        Efficiency of the auto cuts to the data,
        The boolean cut mask,
        A boolean saying whether or not the auto cuts were successful
            or not.
        duty cycle of the square wave

    """

    # get files
    if isinstance(ivfilepath, str):
        if os.path.isdir(ivfilepath):
            ivfilepath += '/'
            files = sorted(glob(ivfilepath +'*'))
        else:
            files = [ivfilepath]
    else:
        files = ivfilepath

    if nprocess == 1:
        results = []
        for filepath in files:
            results.append(_process_ivfile(
                filepath,
                chans,
                autoresample_didv,
                dutycycle,
                lgcverbose,
            ))
    else:
        pool = multiprocessing.Pool(processes=int(nprocess))
        results = pool.starmap(
            _process_ivfile,
            zip(
                files,
                repeat(
                    chans,
                    autoresample_didv,
                    dutycycle,
                    lgcverbose,
                ),
            ),
        ) 
        pool.close()
        pool.join()

    flat_result = [item for sublist in results for item in sublist]
    df = pd.DataFrame(
        flat_result,
        columns=[
            "channels",
            "seriesnum",
            "fs",
            "qetbias",
            "sgamp",
            "sgfreq",
            "offset",
            "offset_err",
            "f",
            "psd",
            "avgtrace",
            "didvmean",
            "didvstd",
            "datatype",
            "cut_eff",
            "cut",
            "cut_pass",
            "dutycycle",
        ],
    )

    if lgcsave:
        df.to_pickle(f"{savepath}/{savename}.pkl")

    return df
