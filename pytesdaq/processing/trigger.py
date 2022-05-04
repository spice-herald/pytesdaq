import argparse
import numpy as np
import os
from math import log10, floor
from datetime import datetime
from glob import glob
import stat
import pickle
import math
from multiprocessing import Pool
from itertools import repeat
from pathlib import Path
from scipy.signal import correlate
from numpy.fft import ifft, fft

import pytesdaq.io.hdf5 as h5io
from pytesdaq.utils import arg_utils
import qetpy as qp

__all__ = [
    'OptimumFilt',
    'ContinuousData',
]


def _getchangeslessthanthresh(x, threshold):
    """
    Helper function that returns a list of the start and ending indices
    of the ranges of inputted values that change by less than the
    specified threshold value.

    Parameters
    ----------
    x : ndarray
        1-dimensional of values.
    threshold : int
        Value to detect the different ranges of vals that change by
        less than this threshold value.

    Returns
    -------
    ranges : ndarray
        List of tuples that each store the start and ending index of
        each range. For example, vals[ranges[0][0]:ranges[0][1]] gives
        the first section of values that change by less than the
        specified threshold.
    vals : ndarray
        The corresponding starting and ending values for each range in
        x.

    """

    diff = x[1:]-x[:-1]
    a = diff>threshold
    inds = np.where(a)[0]+1

    start_inds = np.zeros(len(inds)+1, dtype = int)
    start_inds[1:] = inds

    end_inds = np.zeros(len(inds)+1, dtype = int)
    end_inds[-1] = len(x)
    end_inds[:-1] = inds

    ranges = np.array(list(zip(start_inds,end_inds)))

    if len(x)!=0:
        vals = np.array([(x[st], x[end-1]) for (st, end) in ranges])
    else:
        vals = np.array([])

    return ranges, vals


class OptimumFilt(object):
    """
    Class for applying a time-domain optimum filter to a long trace,
    which can be thought of as an FIR filter.

    Attributes
    ----------
    phi : ndarray 
        The optimum filter in time-domain, equal to the inverse FT of
        (FT of the template/power spectral density of noise)
    norm : float
        The normalization of the optimal amplitude.
    tracelength : int
        The desired trace length (in bins) to be saved when triggering
        on events.
    fs : float
        The sample rate of the data (Hz).
    pulse_range : int
        If detected events are this far away from one another
        (in bins), then they are to be treated as the same event.
    traces : ndarray
        All of the traces to be filtered, assumed to be an ndarray of
        shape = (# of traces, # of channels, # of trace bins). Should
        be in units of Amps.
    template : ndarray
        The template that will be used for the Optimum Filter.
    noisepsd : ndarray
        The two-sided noise PSD that will be used to create the Optimum
        Filter.
    filts : ndarray 
        The result of the FIR filter on each of the traces.
    resolution : float
        The expected energy resolution in Amps given by the template
        and the noisepsd, calculated from the Optimum Filter.
    times : ndarray
        The absolute start time of each trace (in s), should be a
        1-dimensional ndarray.
    pulsetimes : ndarray
        If we triggered on a pulse, the time of the pulse trigger in
        seconds. Otherwise this is zero.
    pulseamps : 
        If we triggered on a pulse, the optimum amplitude at the pulse
        trigger time. Otherwise this is zero.
    trigtimes : ndarray
        If we triggered due to ttl, the time of the ttl trigger in
        seconds. Otherwise this is zero.
    pulseamps : 
        If we triggered due to ttl, the optimum amplitude at the ttl
        trigger time. Otherwise this is zero.
    traces : ndarray
        The corresponding trace for each detected event.
    trigtypes: ndarray
        Array of boolean vectors each of length 3. The first value
        indicates if the trace is a random or not. The second value
        indicates if we had a pulse trigger. The third value indicates
        if we had a ttl trigger.
    lgcoverlap : bool
        If True, then all events are saved when running `eventtrigger`,
        such that overlapping traces will be saved. If False, then
        `eventtrigger` will skip events that overlap, based on
        `tracelength`, with the previous event.

    """

    def __init__(self, fs, template, noisepsd, tracelength, chan_to_trigger='all',
                 trigtemplate=None, lgcoverlap=True, merge_window=None):
        """
        Initialization of the FIR filter.

        Parameters
        ----------
        fs : float
            The sample rate of the data (Hz)
        template : ndarray
            The pulse template to be used when creating the optimum
            filter (assumed to be normalized)
        noisepsd : ndarray
            The two-sided power spectral density in units of A^2/Hz
        tracelength : int
            The desired trace length (in bins) to be saved when
            triggering on events.
        chan_to_trigger : str, int, list of int
            The specified channels to trigger events on. If 'all', then
            all channels are summed. If an integer (e.g. 0 for channel
            1), then only that channel is used. If a list of integers,
            then those channels are summed. The `noisepsd` and
            `template` passed are assumed to be correctly calculated
            for the desired setup. Default is 'all'.
        trigtemplate : NoneType, ndarray, optional
            The template for the trigger channel pulse. If left as
            None, then the trigger channel will not be analyzed.
        lgcoverlap : bool, optional
            If True, then all events are saved when running
            `eventtrigger`, such that overlapping traces will be saved.
            If False, then `eventtrigger` will skip events that
            overlap, based on `tracelength`, with the previous event.
        merge_window : NoneType, int, optional
            The window size that is used to merge events (in bins).
            If left as None, then half a tracelength is used.
        
        """
        
        self.tracelength = tracelength
        self.fs = fs
        self.template = template
        self.noisepsd = noisepsd
        self.lgcoverlap = lgcoverlap
        self.chan = chan_to_trigger
        
        # calculate the time-domain optimum filter
        phi_freq = fft(self.template) / self.noisepsd
        phi_freq[0] = 0 #ensure we do not use DC information
        self.phi = ifft(phi_freq).real
        # calculate the normalization of the optimum filter
        self.norm = np.dot(self.phi, self.template)
        
        # calculate the expected energy resolution
        self.resolution = 1/(np.dot(self.phi, self.template)/self.fs)**0.5

        if merge_window is None:
            # merge triggers within half a tracelength of one another
            self.pulse_range = tracelength / 2
        else:
            self.pulse_range = merge_window
        
        # set the trigger ttl template value
        self.trigtemplate = trigtemplate
        
        # calculate the normalization of the trigger optimum filter
        if trigtemplate is not None:
            self.trignorm = np.dot(trigtemplate, trigtemplate)
        else:
            self.trignorm = None
            
        # set these attributes to None, as they are not known yet
        self.traces = None
        self.filts = None
        self.times = None
        self.trig = None
        self.trigfilts = None
        
        self.pulsetimes = None
        self.pulseamps = None
        self.trigtimes = None
        self.trigamps = None
        self.evttraces = None
        self.trigtypes = None


    def filtertraces(self, traces, times, trig=None):
        """
        Method to apply the FIR filter the inputted traces with
        specified times.

        Parameters
        ----------
        traces : ndarray
            All of the traces to be filtered, assumed to be an ndarray
            of shape = (# of traces, # of channels, # of trace bins).
            Should be in units of Amps.
        times : ndarray
            The absolute start time of each trace (in s), should be a
            1-dimensional ndarray.
        trig : NoneType, ndarray, optional
            The trigger channel traces to be filtered using the
            trigtemplate (if it exists). If left as None, then only the
            traces are analyzed. If the trigtemplate attribute has not
            been set, but this was set, then an error is raised.

        """

        # update the traces, times, and ttl attributes
        self.traces = traces
        self.times = times
        self.trig = trig

        # calculate the total pulse by summing across channels for each trace
        if self.chan == "all":
            pulsestot = np.sum(traces, axis=1)
        elif np.any(np.atleast_1d(self.chan) > traces.shape[1]):
            raise ValueError(
                '`chan_to_trigger` was set to a value greater than the number of channels.',
            )
        elif np.isscalar(self.chan):
            pulsestot = traces[:, self.chan]
        else:
            pulsestot = np.sum(traces[:, self.chan], axis=1)

        # apply the FIR filter to each trace
        self.filts = np.array([correlate(trace, self.phi, mode="same")/self.norm for trace in pulsestot])

        # set the filtered values to zero near the edges, so as not to use the padded values in the analysis
        # also so that the traces that will be saved will be equal to the tracelength
        cut_len = np.max([len(self.phi),self.tracelength])

        self.filts[:, :cut_len//2] = 0.0
        self.filts[:, -(cut_len//2) + (cut_len+1)%2:] = 0.0

        if self.trigtemplate is None and trig is not None:
            raise ValueError("trig values have been inputted, but trigtemplate attribute has not been set, cannot filter the trig values")
        elif trig is not None:
            # apply the FIR filter to each trace
            self.trigfilts = np.array([correlate(trace, self.trigtemplate, mode="same")/self.trignorm for trace in trig])

            # set the filtered values to zero near the edges, so as not to use the padded values in the analysis
            # also so that the traces that will be saved will be equal to the tracelength
            self.trigfilts[:, :cut_len//2] = 0.0
            self.trigfilts[:, -(cut_len//2) + (cut_len+1)%2:] = 0.0

    def eventtrigger(self, thresh, trigthresh=None, positivepulses=True):
        """
        Method to detect events in the traces with an optimum amplitude
        greater than the specified threshold. Note that this may return
        duplicate events, so care should be taken in post-processing to
        get rid of such events.

        Parameters
        ----------
        thresh : float
            The number of standard deviations of the energy resolution
            to use as the threshold for which events will be detected
            as a pulse.
        trigthresh : NoneType, float, optional
            The threshold value (in units of the trigger channel) such
            that any amplitudes higher than this will be detected as
            ttl trigger event. If left as None, then only the pulses
            are analyzed.
        positivepulses : boolean, optional
            Boolean flag for which direction the pulses go in the
            traces. If they go in the positive direction, then this
            should be set to True. If they go in the negative
            direction, then this should be set to False. Default is
            True.

        """

        # initialize lists we will save
        pulseamps = []
        pulsetimes = []
        trigamps = []
        trigtimes = []
        traces = []
        trigtypes = []

        # go through each filtered trace and get the events
        for ii, filt in enumerate(self.filts):

            if self.trigfilts is None or trigthresh is None:

                # find where the filtered trace has an optimum amplitude greater than the specified amplitude
                if positivepulses:
                    evts_mask = filt>thresh*self.resolution
                else:
                    evts_mask = filt<-thresh*self.resolution

                evts = np.where(evts_mask)[0]

                # check if any left over detected events are within the specified pulse_range from each other
                ranges = _getchangeslessthanthresh(evts, self.pulse_range)[0]

                # set the trigger type to pulses
                rangetypes = np.zeros((len(ranges), 3), dtype=bool)
                rangetypes[:,1] = True

            elif trigthresh is not None:
                # find where the filtered trace has an optimum amplitude greater than the specified threshold
                if positivepulses:
                    pulseevts_mask = filt>thresh*self.resolution
                else:
                    pulseevts_mask = filt<-thresh*self.resolution

                pulseevts = np.where(pulseevts_mask)[0]

                # check if any left over detected events are within the specified pulse_range from each other
                pulseranges, pulsevals = _getchangeslessthanthresh(pulseevts, self.pulse_range)

                # make a boolean mask of the ranges of the events in the trace from the pulse triggering
                pulse_mask = np.zeros(filt.shape, dtype=bool)
                for evt_range in pulseranges:
                    if evt_range[1]>evt_range[0]:
                        evt_inds = pulseevts[evt_range[0]:evt_range[1]]
                        pulse_mask[evt_inds] = True

                # find where the ttl trigger has an optimum amplitude greater than the specified threshold
                trigevts_mask = self.trigfilts[ii]>trigthresh

                # get the mask of the total events, taking the or of the pulse and ttl trigger events
                tot_mask = np.logical_or(trigevts_mask, pulse_mask)
                evts = np.where(tot_mask)[0]
                ranges, totvals = _getchangeslessthanthresh(evts, self.pulse_range)

                tot_types = np.zeros(len(tot_mask), dtype=int)
                tot_types[pulse_mask] = 1
                tot_types[trigevts_mask] = 2

                # given the ranges, determine the trigger type based on if the total ranges overlap with
                # the pulse events and/or the ttl trigger events
                rangetypes = np.zeros((len(ranges), 3), dtype=bool)
                for ival, vals in enumerate(totvals):
                    if np.any(tot_types[vals[0]:vals[1]]==1):
                        rangetypes[ival, 1] = True
                    if np.any(tot_types[vals[0]:vals[1]]==2):
                        rangetypes[ival, 2] = True

            # for each range with changes less than the pulse_range, keep only the bin with the largest amplitude
            for irange, evt_range in enumerate(ranges):
                if evt_range[1]>evt_range[0]:

                    evt_inds = evts[evt_range[0]:evt_range[1]]

                    if rangetypes[irange][2]:
                        # use ttl as primary trigger
                        evt_ind = evt_inds[np.argmax(self.trigfilts[ii][evt_inds])]
                    else:
                        # only pulse was triggered
                        if positivepulses:
                            evt_ind = evt_inds[np.argmax(filt[evt_inds])]
                        else:
                            evt_ind = evt_inds[np.argmin(filt[evt_inds])]

                    if not self.lgcoverlap:
                        if (irange==0):
                            # save evt_ind for first event above threshold
                            # for subsequent checking for overlap
                            lastevt_ind = evt_ind
                        else:
                            # check if bins between this event and previous
                            # is smaller than tracelength
                            if ((evt_ind - lastevt_ind) < self.tracelength):
                                # skip this event
                                continue
                            else:
                                # there is no overlap so update lastevt_ind
                                # and precede with trigger code
                                lastevt_ind = evt_ind


                    if rangetypes[irange][1] and rangetypes[irange][2]:
                        # both are triggered
                        if positivepulses:
                            pulse_ind = evt_inds[np.argmax(filt[evt_inds])]
                        else:
                            pulse_ind = evt_inds[np.argmin(filt[evt_inds])]
                        # save trigger times and amplitudes
                        pulsetimes.extend([pulse_ind/self.fs + self.times[ii]])
                        pulseamps.extend([filt[pulse_ind]])
                        trigtimes.extend([evt_ind/self.fs + self.times[ii]])
                        trigamps.extend([filt[evt_ind]])
                    elif rangetypes[irange][2]:
                        # only ttl was triggered, save trigger time and amplitudes
                        pulsetimes.extend([0.0])
                        pulseamps.extend([0.0])
                        trigtimes.extend([evt_ind/self.fs + self.times[ii]])
                        trigamps.extend([filt[evt_ind]])
                    else:
                        # only pulse was triggered, save trigger time and amplitudes
                        pulsetimes.extend([evt_ind/self.fs + self.times[ii]])
                        pulseamps.extend([filt[evt_ind]])
                        trigtimes.extend([0.0])
                        trigamps.extend([0.0])

                    trigtypes.extend([rangetypes[irange]])

                    # save the traces that correspond to the detected event, including all channels, also with lengths
                    # specified by the attribute tracelength
                    traces.extend([self.traces[ii, ..., 
                                              evt_ind - self.tracelength//2:evt_ind + self.tracelength//2 \
                                              + (self.tracelength)%2]])
                    

        self.pulsetimes = pulsetimes
        self.pulseamps = pulseamps
        self.trigtimes = trigtimes
        self.trigamps = trigamps
        self.evttraces = traces
        self.trigtypes = trigtypes


class ContinuousData:
    
    def __init__(self, input_data_path,
                 input_series=None,
                 output_group_prefix=None, 
                 output_group_comment=None,
                 output_base_path=None,
                 output_group_name=None,
                 trigger_channels='all',
                 trace_length_ms=None,
                 pretrigger_length_ms=None,
                 nb_samples=None,
                 nb_samples_pretrigger=None,
                 negative_pulse=False,
                 filter_file=None):
        

        # input series
        self._input_series = input_series
        if (input_series is not None
            and isinstance(input_series, list)):
            if (input_series[0]=='even'
                or input_series[0]=='odd'):
                self._input_series =  input_series[0]
                        
        # file list
        self._file_list = self._get_file_list(input_data_path,
                                              series=self._input_series)
              
        # negative pulse
        self._is_negative_pulse = negative_pulse
            
        
        # ADC device (Needs to fixed for multiple devices)
        self._adc_name = 'adc1'
        self._detector_config_name = 'detconfig1'

        
        # and get some metadata informations
        h5reader = h5io.H5Reader()
        metadata = h5reader.get_metadata(file_name=self._file_list[0])
            
        self._facility = metadata['facility']
        if output_group_comment is not None:
            self._group_comment =  output_group_comment
        elif 'group_comment' in metadata:
            self._group_comment = 'Group extracted from continuous data:  ' + metadata['group_comment']
        self._connection_table = h5reader.get_connection_table(metadata=metadata)

        h5reader.clear()
        
        # create output directory
        self._output_path = None
              
        if output_base_path is None:
            input_path = Path(input_data_path)
            output_base_path = str(input_path.parent)

        if output_group_name is not None:
            self._output_path = output_base_path + '/' + output_group_name
            if not os.path.isdir(self._output_path):
                raise ValueError('ERROR: Directory "'
                                 + self._output_path
                                 + '" not found!')
        else:
            self._output_path = self._create_output_dir(output_base_path,
                                                        output_group_prefix)
            
    

        # get sample rate and number of continuous samples
        self._adc_config  = self._get_adc_config()
        if 'sample_rate' not in self._adc_config:
            raise ValueError('ERROR: Unable to find sample rate from metadata')
        else:
            self._sample_rate  = float(self._adc_config['sample_rate'])
        
        if 'nb_samples' not in self._adc_config:
            raise ValueError('ERROR: Unable to find number samples from metadata')
        else:
            self._nb_samples_continuous =  int(self._adc_config['nb_samples'])
            

        # trace length triggered data
        if nb_samples is not None:
            self._nb_samples = int(nb_samples)
        elif trace_length_ms is not None:
            self._nb_samples = int(floor(trace_length_ms*self._sample_rate/1000))
        else:
            raise ValueError('ERROR: Trace length not available!')

        if nb_samples_pretrigger is not None:
            self._nb_samples_pretrigger = int(nb_samples_pretrigger)
        elif pretrigger_length_ms is not None:
            self._nb_samples_pretrigger =  int(floor(pretrigger_length_ms*self._sample_rate/1000))
        else:
            self._nb_samples_pretrigger = int(floor(self._nb_samples/2))

            
        # channels to trigger on 
        self._chan = self._extract_adc_channels(trigger_channels)
        self._chan_array_ind = self._convert_adc_to_index(self._chan)
        if not isinstance(self._chan_array_ind, list):
            self._chan_array_ind = [self._chan_array_ind]
        self._nb_chan_to_trig = len(self._chan_array_ind)
        
        
        # filter file
        self._filter_dict = None
        if filter_file is None:
            self._filter_dict = dict()
            self._filter_dict['trigger_channels'] = trigger_channels
            series_name = self._create_series_name()
            self._filter_file_name = self._output_path + '/' + series_name  + '_filter.pickle'
        else:
            with open(filter_file, 'rb') as f:
                self._filter_dict = pickle.load(f)
                if 'trigger_channels' not in self._filter_dict:
                    raise ValueError('ERROR: "trigger_channels" not found in filter file!')
                else:
                    adc_chans = self._extract_adc_channels(self._filter_dict('trigger_channels'))
                    if adc_chans != self._chan:
                        raise ValueError('ERROR: "trigger_channels" in filter file ' +
                                         'is different than input channels or ' +
                                         'does not exist!')
                    
                
    def get_psd_data(self):
        """
        Get PSD and template data
        
        Return:
        ------
           dictionary
        """
        return self._filter_dict


                
        
    def create_template(self, rise_time, fall_time):
        """
        Create template
        """
        if self._sample_rate is None:
            raise ValueError('ERROR: No sample rate available!')
        
        if self._nb_samples is None or self._nb_samples_pretrigger is None:
            raise ValueError('ERROR: No trace length  available!')

        
        if not isinstance(rise_time, list):
            rise_time = [rise_time]
        if not isinstance(fall_time, list):
            fall_time = [fall_time]
        
        if self._nb_chan_to_trig>1:
            if len(rise_time)==1:
                rise_time *= self._nb_chan_to_trig
            if len(fall_time)==1:
                fall_time *= self._nb_chan_to_trig


        # convert to seconds
        rise_time = [item * 1e-6 for item in rise_time]
        fall_time = [item * 1e-6 for item in fall_time]
        
        
        trace_time = 1.0/self._sample_rate *(np.arange(1,self._nb_samples+1)
                                             -self._nb_samples_pretrigger)
        lgc_b0 = trace_time < 0.0

        self._template = []
        for i, r in enumerate(rise_time):
            template= np.exp(-trace_time/fall_time[i])-np.exp(-trace_time/r)
            template[lgc_b0] = 0.0
            template = template/max(template)
            self._template.append(template)

        self._filter_dict['template'] = self._template
              
        
        
    def acquire_randoms(self, nb_events=500, verbose=True):
        """
        Function for acquiring random traces from continuous data
        """
        
        if verbose:
            print('')
            print('INFO: Checking continuous data files')


        # Instantial data reader
        h5reader = h5io.H5Reader()  

        # Instantiate data writer
        series_name = self._create_series_name()
        h5writer = h5io.H5Writer()
        h5writer.initialize(series_name=series_name,
                            data_path=self._output_path)
        

        # write overall metadata
        output_metadata = self._fill_metadata()
        h5writer.set_metadata(file_metadata=output_metadata['file_metadata'],
                              detector_config=output_metadata['detector_config'],
                              adc_config=output_metadata['adc_config'])

        
        # get number of possible randoms in each continuous data file
        # then store dictionary {file_index: chunk_index} in a list, which
        # will be randomly shuffled
        choice_events = list()
        for ifile in range(len(self._file_list)):
            metadata = h5reader.get_metadata(file_name=self._file_list[ifile])
            nb_events_file = metadata['groups'][self._adc_name]['nb_events']
            nb_samples_file = metadata['groups'][self._adc_name]['nb_samples']
            if nb_samples_file != self._nb_samples_continuous:
                raise ValueError('ERROR: All the files should have '
                                 + 'the same number of samples per event!')
            elif nb_samples_file < self._nb_samples:
                raise ValueError('ERROR: requested # samples randoms > '
                                 + '# samples continuous data!')
            nb_random_chunks = int(nb_events_file* floor(nb_samples_file/self._nb_samples))
            for ichunk in range(nb_random_chunks):
                choice_events.append({ifile: ichunk})
        

        # shuffle
        if verbose:
            print('INFO: Randomly selecting ' + str(nb_events) + ' traces out of '
                  + str(len(choice_events)) + ' possible choices')

        np.random.shuffle(choice_events)

        # take only the number of events needed
        choice_events = choice_events[:nb_events]
      
        
        # let's group chunck indicies for same file in a dictionary {file_index: list of chunk index)
        event_dict = dict()
        for choice_dict in choice_events:
            for key, val in choice_dict.items():
                if key in event_dict:
                    event_dict[key].append(val)
                else:
                    event_dict[key] = [val]


        # let's sort chunk index 
        # FIXME: need to sort files
        for ifile in event_dict:
            event_dict[ifile] = sorted(event_dict[ifile])
        
                
        # loop file, get/save traces
        # FIXME: IOReader not able to read specific events currently
        if verbose:
            print('INFO: Acquiring randoms!')

     
        event_counter = 0
        for ifile, chunk_indices in event_dict.items():
                   
            # file
            file_name = self._file_list[ifile]

                               
            # loop chunk
            current_event_num = -1
            for chunk_index in chunk_indices:

                # find contunuous data event index and bin start from chunk index
    
                nb_chunks_per_event = floor(self._nb_samples_continuous/self._nb_samples)
                event_index = int(floor(chunk_index/nb_chunks_per_event)) + 1
                bin_start_event = self._nb_samples * (chunk_index % nb_chunks_per_event)
                bin_start_event_sec = bin_start_event/self._sample_rate
                             
                # get traces for all channels
                traces, info = h5reader.read_single_event(event_index,
                                                          file_name=file_name,
                                                          include_metadata=True)


                # invert if negative pulse
                if self._is_negative_pulse:
                    traces *= -1

                
                # truncate
                traces = traces[:,bin_start_event:bin_start_event+self._nb_samples]
               
                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['event_time'] = float(info['event_time']) + bin_start_event_sec

                # file prefix
                file_prefix = 'rand'
                if (self._input_series == 'even'
                    or  self._input_series == 'odd'):
                    file_prefix = self._input_series + '_'+ file_prefix
                            
                # write new file
                h5writer.write_event(traces, prefix=file_prefix, data_mode='rand',
                                     dataset_metadata=dataset_metadata)


                #  event_counter
                event_counter += 1
                if (verbose and event_counter % 50 == 0):
                    print('INFO: Number of randoms = ' + str(event_counter))

           
        # cleanup
        h5writer.close()
        h5reader.clear()
        
        # verbose
        if verbose:
            print('INFO: Done acquiring randoms!')


        

        
    def calc_psd(self, nb_events=-1,
                 save_filter=False,
                 verbose=True):
        """
        Calculate PSD, assume randoms have 
        been generated already
        """

        if verbose:
            print('')
            print('INFO: Starting PSD processing')

        
        # Get data
        if self._output_path is None:
            raise ValueError('ERROR: No base path and/or group name provided!'
                             + ' Unable to find raw data for calcularing PSD.')

        file_prefix = 'rand'
        if (self._input_series == 'even'
            or  self._input_series == 'odd'):
            file_prefix = self._input_series + '_' + file_prefix
        
        file_list = glob(self._output_path + '/' + file_prefix + '_*.hdf5')
        if len(file_list)<1:
            raise ValueError('ERROR: Unable to find randoms file in directory '
                             + self._output_path + '. Please check path or '
                             + 'generate randoms (--acquire-rand)')

        # Instantial data reader
        h5reader = h5io.H5Reader()  


        
        trace_buffer = None
        for file_name in file_list:
        
            traces, info = h5reader.read_many_events(filepath=file_name,
                                                           output_format=2,
                                                           include_metadata=True)

            channels = info[0]['detector_chans']
            
            if trace_buffer is None:
                trace_buffer = traces
            else:   
                trace_buffer =  np.append(trace_buffer,
                                          traces,
                                          axis=0)

            if  nb_events>-1 and int(trace_buffer.shape[0])>=nb_events:
                trace_buffer = trace_buffer[0:nb_events,:,:]
                break
                

        # calculate PSD        
        self._filter_dict['f'] = list()
        self._filter_dict['psd'] = list()
        self._filter_dict['f_fold'] = list()
        self._filter_dict['psd_fold'] = list()
                 
        for ichan, chan_ind in enumerate(self._chan_array_ind):
           
            # extract traces for trigger channel(s)
            if np.isscalar(chan_ind):
                traces_red = trace_buffer[:,chan_ind]
            else:
                traces_red = np.sum(trace_buffer[:,chan_ind], axis=1)

            # autocut
            cut = qp.autocuts(traces_red, fs=self._sample_rate)
            adc_chan = self._chan[ichan]
            if verbose:
                print(f'INFO: PSD for ADC channel/combination {adc_chan}.'
                      + f' Autocuts efficiency={np.sum(cut)/len(cut)}')
            
            # calc PSD
            f, psd = qp.calc_psd(traces_red[cut], fs=self._sample_rate, folded_over=False)
            f_fold, psd_fold = qp.foldpsd(psd, fs=self._sample_rate)
            self._filter_dict['f'].append(f)
            self._filter_dict['f_fold'].append(f_fold)
            self._filter_dict['psd'].append(psd)
            self._filter_dict['psd_fold'].append(psd_fold)
        
        # save psd
        if save_filter:
            print('INFO: Saving filter file "' + self._filter_file_name +'"')
            with open(self._filter_file_name, 'wb') as handle:
                pickle.dump(self._filter_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

        # clean up 
        h5reader.clear()

        
    def acquire_trigger(self,
                        nb_events=-1,
                        template=None, noise_psd=None,
                        threshold=10,
                        pileup_window=0,
                        coincident_window=50,
                        nb_cores=1,
                        verbose=True,
                        debug=False):

        """
        Acquire trigger
        
        Arguments
        ---------
        
        


        """
        
        # number of files
        nb_files = len(self._file_list)
        print('')
        print('INFO: Starting trigger processing!')
        print(f'INFO: Total number of files to be processed = {nb_files}')

        if  nb_cores==1:
            self._acquire_trigger(file_list=self._file_list,
                                  nb_events=nb_events,
                                  template=template,
                                  noise_psd=noise_psd,
                                  threshold=threshold,
                                  pileup_window=pileup_window,
                                  coincident_window=coincident_window,
                                  verbose=verbose,
                                  debug=debug)

        else:
            nb_files = len(self._file_list)
            file_list = list()
            if nb_files <= nb_cores:
                nb_cores = nb_files
                file_list = self._file_list
            else:
                file_list = np.array_split(self._file_list, nb_cores)

            if nb_events>0:
                nb_events = math.ceil(nb_events/nb_cores)

            # series name
            series_name = self._create_series_name()
            series_list = list()
            for iproc in range(nb_cores):
                series_list.append(series_name[:-2] + str(10+iproc))
                
            print(f'INFO: Processing with be split on {nb_cores} cores!')
            pool = Pool(processes=nb_cores)
            pool.starmap(self._acquire_trigger,
                         zip(file_list,
                             series_list,
                             repeat(nb_events),
                             repeat(template),
                             repeat(noise_psd),
                             repeat(threshold),
                             repeat(pileup_window),
                             repeat(coincident_window),
                             repeat(verbose),
                             repeat(debug)))
            
            print('INFO: Processing done!')
            pool.close()
            pool.join()
            
                
    def _convert_adc_to_index(self, adc_channels):
        """
        Convert ADC channel number to array index
    
        Arguments
        ---------
          adc_channels: int, list of (list) int 
        
        Return
        ------
          indices: same format as input
        """


        # available adc channels
        adc_list = self._adc_config['adc_channel_indices']
        if isinstance(adc_list, np.ndarray):
            adc_list = adc_list.tolist()
        elif not isinstance(adc_list, list):
            adc_list = [int(adc_list)]

            
        # case single value
        if isinstance(adc_channels, int):
            index = adc_list.index(adc_channels)
            return index

        chan_indices = list()
        # loop array
        for chan in adc_channels:
            if isinstance(chan, int):
                chan_indices.append(adc_list.index(chan))
            else:
                chan_sum_indices = list()
                for chan_sum in chan:
                    if isinstance(chan_sum, int):
                        chan_sum_indices.append(adc_list.index(chan_sum))
                    else:
                        raise ValueError('ERROR: ADC channel format unknown "'
                                         + str(chan_sum) + '": ' + str(type(chan_sum)))

                
                chan_indices.append(chan_sum_indices)


        return chan_indices
        
    

            
    def _extract_adc_channels(self, channels):
        """ 
        Extract ADC channels from detector channel name

        """
        adc_channels = list()

        # case all
        if channels == 'all':
            adc_channels = self._adc_config['adc_channel_indices']
            if isinstance(adc_channels, np.ndarray):
                adc_channels = adc_channels.tolist()
            elif not isinstance(adc_channels, list):
                adc_channels = [adc_channels]
            adc_channels = [adc_channels]
            return adc_channels
        
        # case individual channels
        if not isinstance(channels, list):
            channels = [channels]

        for chan in channels:

            # check if sum of channels
            ischannel_sum = isinstance(chan, list) or '+' in chan

            # convert to list
            chan_list = list()
            if isinstance(chan, list):
                chan_list = chan
            elif '+' in chan:
                chan_list = chan.split('+')
            else:
                chan_list = [chan]
                
            # loop sublist
            adc_channels_sublist = list()
            for chan_sum in chan_list:

                # check if ADC channels
                chan_trigger_check = chan_sum.replace('-','')
                if chan_trigger_check.isdigit():
                    adc_channels_sublist.extend(arg_utils.hyphen_range(chan_sum))
                else:
                    if self._connection_table is None:
                        raise ValueError('ERROR: Unable to find connection table in raw data!' +
                                         ' Use ADC channels for chan_to_trigger argument instead')
                    
                    adc_channel = self._connection_table.query(
                        'detector_channel == @chan_sum')["adc_channel"].values

                    if(len(adc_channel)!=1):
                        raise ValueError('ERROR: chan_to_trigger input does not match ' + 
                                         'an ADC channel. Check input or config/setup file')
                
                    adc_channels_sublist.append(int(adc_channel.astype(np.int)))

            if  ischannel_sum:
                adc_channels.append(adc_channels_sublist)
            else:
                adc_channels.extend(adc_channels_sublist)

                    
        return adc_channels
        
        


        
    def _find_close_times(self, pulsetimes, timethresh):

        piledup_bool = np.diff(pulsetimes) < timethresh
        piledup_bool = np.concatenate(([0], piledup_bool , [0]))
        absdiff = np.abs(np.diff(piledup_bool))
        ranges = np.where(absdiff == 1)[0].reshape(-1, 2)
        # wap: extend ranges last element by 1 
        # so if the pileup candidates are [45 46 47]
        # ranges will be [45 48]
        # and this way the irange variable below will be
        # [45 46 47]
        ranges[:,1] = ranges[:,1] + 1

        return ranges


    def _find_pileup(self, pulsetimes, pulseamps, timethresh, chantrig=None):
        """
        Function to find pileup
        """
        ranges = self._find_close_times(pulsetimes, timethresh)

        lgc_verbose = False

        if lgc_verbose:
            print(f'close time ranges. ranges = {ranges}')

        inds_to_remove = []
        # to keep track of which channels were merged
        inds_merged = []
        chantrig_merged = []

        if len(ranges) == 0:
            return inds_to_remove, inds_merged, chantrig_merged
        else:
            for i in range(len(ranges)):
                irange = np.arange(ranges[i][0], ranges[i][1], dtype=int)
                imax = int(np.argmax(pulseamps[ranges[i][0]:ranges[i][1]]))
                irange_mod = np.delete(irange,imax)

                if lgc_verbose:
                    print(f'irange={irange}')
                    print(f'ranges[{i}]={ranges[i]}')
                    print(f'imax = {imax}')
                    print(f'irange[imax]={irange[imax]}')
                    print(f'irange_mod = {irange_mod}')

                inds_to_remove.extend(irange_mod)
                inds_merged.append(irange[imax])

                # we know which indices are being merged to
                # and now we want to know all the 
                # channels/channels combos that triggered
                # that were merged 
                if chantrig is not None:
                    # theres a subtlrey where unique will not work 
                    chantrig_range = np.array(chantrig[ranges[i][0]:ranges[i][1]],
                                              dtype=object)
                    #chantrig_range = chantrig[ranges[i][0]:ranges[i][1]]
                    chantrig_range_u = np.unique(chantrig_range)
                    if lgc_verbose:
                        print(f'chantrig_range={chantrig_range}')
                        print(f'chantrig_range_u={chantrig_range_u}')
                    chantrig_merged.append(list(chantrig_range_u))

        if lgc_verbose:
            print(f'inds_to_remove={inds_to_remove}')
            print(f'inds_merged={inds_merged}')
            print(f'chantrig_merged={chantrig_merged}')

        return inds_to_remove, inds_merged, chantrig_merged



    def _remove_triggers(self, filt, inds_to_remove):
        """
        Remove certain triggers from OptimumFilt object which
        requires deleting elements from the following lists:
            evttraces
            pulseamps
            pulsetimes
            trigamps
            trigtimes
            trigtypes
        """ 

        lgc_verbose = False

        if lgc_verbose and (len(inds_to_remove) > 0):
            print('type(filt.evttraces)=', type(filt.evttraces))
            print('type(filt.evttraces[0])=', type(filt.evttraces[0]))
            print('len(filt.evttraces)=', len(filt.evttraces))

            print('filt.pulseamps=', filt.pulseamps)
            print('type(filt.pulseamps)=', type(filt.pulseamps))

            print('filt.pulsetimes=', filt.pulsetimes)
            print('type(filt.pulsetimes)=', type(filt.pulsetimes))

        # remove elements from all object members that
        # are lists of triggers
        for ind in sorted(inds_to_remove, reverse=True):

            if lgc_verbose:
                print('ind=',ind)
                print('pulsetimes=', filt.pulsetimes[ind])
                print('pulseamps=', filt.pulseamps[ind])

            del filt.evttraces[ind]
            del filt.pulseamps[ind]
            del filt.pulsetimes[ind]
            del filt.trigamps[ind]
            del filt.trigtimes[ind]
            del filt.trigtypes[ind]

        if lgc_verbose:
            print('after removal ...')
            print('filt.pulseamps=', filt.pulseamps)
            print('filt.pulsetimes=', filt.pulsetimes)
            print('len(filt.evttraces)=', len(filt.evttraces))

        return filt

    def _combine_sort_triggers(self, filt_list):

        # make list of filt.chan for each filter
        # and combine into single long list for filters
        chancomb = list()
        for filt in filt_list:
            chancomb.extend([filt.chan] * len(filt.pulseamps))

        # combine filt_list lists into single long list
        evttracescomb = [evt for filt in filt_list for evt in filt.evttraces]
        pulseampscomb = [amp for filt in filt_list for amp in filt.pulseamps]
        pulsetimescomb = [time for filt in filt_list for time in filt.pulsetimes]
        trigampscomb = [trigamp for filt in filt_list for trigamp in filt.trigamps]
        trigtimescomb = [trigtime for filt in filt_list for trigtime in filt.trigtimes]
        trigtypescomb = [trigtypes for filt in filt_list for trigtypes in filt.trigtypes]

        # sort by pulsetimes (not the same as trig times)
        indsort = np.argsort(pulsetimescomb)

        # reorder the lists based on sorted order
        evttracescomb = [evttracescomb[i] for i in indsort]
        pulseampscomb = [pulseampscomb[i] for i in indsort]
        pulsetimescomb = [pulsetimescomb[i] for i in indsort]
        trigampscomb = [trigampscomb[i] for i in indsort]
        trigtimescomb = [trigtimescomb[i] for i in indsort]
        trigtypescomb = [trigtypescomb[i] for i in indsort]
        # also reorder the chancomb
        chancomb = [chancomb[i] for i in indsort]

        # make new OptimumFilt object
        filtcomb = OptimumFilt(self._sample_rate,
                               self._filter_dict['template'][0],
                               self._filter_dict['psd'][0],
                               self._nb_samples,
                               lgcoverlap=True)
        filtcomb.evttraces = evttracescomb
        filtcomb.pulseamps = pulseampscomb
        filtcomb.pulsetimes = pulsetimescomb
        filtcomb.trigamps = trigampscomb
        filtcomb.trigtimes = trigtimescomb
        filtcomb.trigtypes = trigtypescomb

        return filtcomb, chancomb




    
    def _acquire_trigger(self,file_list,
                         series_name=None,
                         nb_events=-1,
                         template=None,
                         noise_psd=None,
                         threshold=10,
                         pileup_window=0,
                         coincident_window=50,            
                         verbose=True,
                         debug=False):
        """
        Function to acquire trigger from continuous data
        """


        # Instanciate data reader
        h5reader = h5io.H5Reader()

        
        # Instantiate data writer
        if series_name is None:
            series_name = self._create_series_name()
        h5writer = h5io.H5Writer()
        h5writer.initialize(series_name=series_name,
                            data_path=self._output_path)
        

        # write overall metadata
        output_metadata = self._fill_metadata()
        h5writer.set_metadata(file_metadata=output_metadata['file_metadata'],
                              detector_config=output_metadata['detector_config'],
                              adc_config=output_metadata['adc_config'])

            
        # noise PSD (overwrite calculated PSD)
        if noise_psd is not None:
            if not isinstance(noise_psd, list):
                noise_psd = [noise_psd]
            if len(noise_psd) != self._nb_chan_to_trig:
                raise ValueError('ERROR: Unexpected length of '
                                 + 'noise psd. It should match number '
                                 + 'of trigger channels')
            
            self._filter_dict['psd']  = noise_psd

        # template (overwrite calculated PSD)
        if template is not None:
            self._template = template

        # threshold
        if np.isscalar(threshold):
            threshold = [threshold]
        if self._nb_chan_to_trig>1 and len(threshold)==1:
            threshold *= self._nb_chan_to_trig

        if len(threshold) != self._nb_chan_to_trig:
            raise ValueError('ERROR: unexpected "threshold" vector length!')
        

        # convert windows to sec
        pileup_window = float(pileup_window) * 1e-6
        coincident_window = float(coincident_window) * 1e-6
        
        

        # set file list to IO reader
        h5reader.set_files(file_list)
       
        # loop events
        do_continue_loop = True
        trigger_counter = 0
        while(do_continue_loop):

            # read next event
            traces, info = h5reader.read_event(include_metadata=True,
                                               adc_name=self._adc_name)

            # check if successful
            if info['read_status'] != 0:
                do_continue_loop = False
                break

            
            # invert if negative pulse
            if self._is_negative_pulse:
                traces *= -1

            
            # event time
            time_array = np.asarray([info['event_time']])
            
            # expand dimension traces
            traces = np.expand_dims(traces, axis=0)

            # loop over channels to trigger
            # make OF filters for channel and store in list
            filt_list = []

            for ichan, chan_ind in enumerate(self._chan_array_ind):

                if debug:
                    print(f'INFO: Finding OF triggers on ADC channel(s) {self._chan[ichan]}')
                
                # find triggers
                if np.isscalar(chan_ind):
                    chan_ind = [chan_ind]
                    
                filt = OptimumFilt(self._sample_rate,
                                   self._filter_dict['template'][ichan],
                                   self._filter_dict['psd'][ichan],
                                   self._nb_samples,
                                   chan_to_trigger=chan_ind,
                                   lgcoverlap=True)

                filt.filtertraces(traces, time_array)
                filt.eventtrigger(threshold[ichan], positivepulses=True)
                filt_list.append(filt)


            # remove pileup
            for ichan, chan_ind in enumerate(self._chan_array_ind):

                piledup_ind, _, _ = self._find_pileup(filt_list[ichan].pulsetimes,
                                                      filt_list[ichan].pulseamps,
                                                      pileup_window)
                chan = self._chan[ichan]
                if debug:
                    print(f'INFO: Pileup on ADC channel {chan}: len(piledup_ind) = {len(piledup_ind)}')

                    import inspect
                    import pprint
                    attributes = inspect.getmembers(filt_list[ichan],
                                                    lambda a:not(inspect.isroutine(a)))
                    print('\n\n')
                    pprint.pprint([(a[0], type(a[1]), np.shape(a[1]))
                                   for a in attributes if not(a[0].startswith('__')
                                                              and a[0].endswith('__'))])
                    print('\n\n')

                filt_list[ichan] = self._remove_triggers(filt_list[ichan], piledup_ind)

            # combine and sort the multiple
            # filt_list objects into a single one
            filtcomb, chancomb = self._combine_sort_triggers(filt_list)
            if debug:
                print('INFO: Combining Triggers')
            
            # find:
            # (1) coincidence triggers
            # (2) which triggers have had other channels merged into them
            # (3) which channels have been merged into the merged triggers
            coinc_ind, inds_merged, chancomb_merged = self._find_pileup(filtcomb.pulsetimes,
                                                                        filtcomb.pulseamps,
                                                                        coincident_window,
                                                                        chancomb)

            for i, ind in enumerate(inds_merged):
                chancomb[ind] = chancomb_merged[i]

            # remove the coincidence triggers from filtcomb
            filtcomb = self._remove_triggers(filtcomb, coinc_ind)

            # remove coincident triggers from chancomb
            for ind in sorted(coinc_ind, reverse=True):
                del chancomb[ind]

            if debug:
                print(f'INFO: Number of events with merged triggers = {len(inds_merged)}')
                print(f'INFO: Final number of events in this continuous data chunk = {len(chancomb)}')
            
            # loop triggers
            for itrig in range(len(filtcomb.pulsetimes)):

                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['trigger_time'] = filtcomb.pulsetimes[itrig]
                dataset_metadata['event_time'] = filtcomb.pulsetimes[itrig]
                dataset_metadata['trigger_amplitude'] = filtcomb.pulseamps[itrig]
                                 
                trigger_channels = list()
                for trig_chan in chancomb[itrig]:
                    if isinstance(trig_chan, list):
                        trigger_channels.extend(trig_chan)
                    else:
                        trigger_channels.append(trig_chan)
                dataset_metadata['trigger_channel'] = trigger_channels

                # file prefix
                file_prefix = 'threshtrig'
                if (self._input_series == 'even'
                    or  self._input_series == 'odd'):
                    file_prefix = self._input_series + '_' + file_prefix

                
                # write new file
                if debug:
                    print(filtcomb.evttraces[itrig])
                    print(dataset_metadata)
                h5writer.write_event(filtcomb.evttraces[itrig], prefix=file_prefix,
                                           data_mode='threshold',
                                           dataset_metadata=dataset_metadata)
                
                # event counter
                trigger_counter += 1
                if nb_events>0 and trigger_counter>=nb_events:
                    do_continue_loop = False
                    break

                # display
                if (verbose and trigger_counter % 50 == 0):
                    print('INFO: Number of triggers = ' + str(trigger_counter))

        # cleanup
        h5reader.clear()

    def _get_file_list(self, file_path, series=None):
        """
        Get file list from directory
        path
        """
        # initialize
        file_list = []
   

        # loop file path
        if not isinstance(file_path, list):
            file_path = [file_path]
            
        for a_path in file_path:
            
            # case path is a directory
            if os.path.isdir(a_path):
                if series is not None:
                    if series == 'even' or series == 'odd':
                        file_name_wildcard = series + '_*.hdf5'
                        file_list = glob(a_path + '/' + file_name_wildcard)
                    else:
                        if not isinstance(series, list):
                            series = [series]
                        for serie in series:
                            file_name_wildcard = '*' + serie + '_*.hdf5'
                            file_list.extend(glob(a_path + '/' + file_name_wildcard))
                else:
                    file_list = glob(a_path + '/*.hdf5')
                    
            # case file
            elif os.path.exists(a_path):
                if a_path.find('.hdf5') != -1:
                    if series is not None:
                        if series == 'even' or series == 'odd':
                            if a_path.find(series) != -1:
                                file_list.append(a_path)
                        else:
                            if not isinstance(series, list):
                                series = [series]
                            for serie in series:
                                if a_path.find(serie) != -1:
                                    file_list.append(a_path)
                    else:
                        file_list.append(a_path) 
    
        if not file_list:
            raise ValueError('ERROR: No raw input data found. Check arguments!')
        else:
            file_list.sort()

        return file_list


    def _create_series_name(self):
        """
        Create series name
    
        Return
          Series name: string
        """


        now = datetime.now()
        series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
        series_time = now.strftime('%H') + now.strftime('%M')
        series_name = ('I' + str(self._facility) +'_D' + series_day + '_T'
                       + series_time + now.strftime('%S'))

        return series_name
        

    
    
    def _create_output_dir(self, base_path, prefix=None):
        """
        Create output directory
        """

        # output name
        series_name = self._create_series_name()
        
        # output directory
        if prefix is None:
            prefix = 'threshtrigger'
            
        output_dir = base_path + '/' + prefix + '_' + series_name
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
                os.chmod(output_dir, stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)
            except OSError:
                raise ValueError('\nERROR: Unable to create directory "'+ output_dir  + '"!\n')
                
        return output_dir
        
                
    def _get_adc_config(self):
        """
        Get ADC configuration 
        
        Return:
           dictionary
        """


        # get metadata
        h5reader = h5io.H5Reader()  
        file_name = self._file_list[0]
        metadata = h5reader.get_metadata(file_name=file_name)
        h5reader.clear()
        
        output_dict = dict()
        if self._adc_name in metadata['groups']:
            output_dict  = metadata['groups'][self._adc_name]

        return output_dict
    
        
    def _fill_metadata(self):
        """
        Get file metadata and detector config 
        from first file and set to hdf5 file 

        Return:

        norm_array: numpy array with volt to amps normalization
        """

        output_metadata = dict()

        
        file_name = self._file_list[0]
        file_metadata = dict()
        detector_config = dict()

        # get metadata from file
        h5reader = h5io.H5Reader()  
        metadata = h5reader.get_metadata(file_name=file_name)
        h5reader.clear()
        
        file_metadata = dict()
        detector_config = dict()
        adc_config = dict()
        for key,val in metadata.items():
                                            
            if (key == 'comment'
                or key == 'daq_version' 
                or key == 'facility' 
                or key == 'format_version'
                or key == 'run_purpose'
                or key == 'run_type'):
                
                file_metadata[key] = val
            
            if key == 'groups':
                if isinstance(val, dict):
                    for key_group, val_group in val.items():
                        if key_group.find('detconfig')!=-1:
                            detector_config[key_group] = val_group
                        if key_group.find('adc')!=-1:
                            adc_config[key_group] = val_group
                           
                            
        # modify ADC metadata
        for key in adc_config.keys():
            adc_config[key]['dataset_list'] = []
            adc_config[key]['nb_events'] = 0
            adc_config[key]['nb_samples'] = self._nb_samples
            adc_config[key]['nb_samples_pretrigger'] = self._nb_samples_pretrigger
            if 'dataset_list' in adc_config[key]:
                adc_config[key].pop('dataset_list')
            if 'nb_datasets' in adc_config[key]:
                adc_config[key].pop('nb_datasets')

        # output dictionary
        output_metadata['file_metadata'] = file_metadata
        output_metadata['detector_config'] = detector_config
        output_metadata['adc_config'] = adc_config

        return output_metadata
        

        
    
    
        
        
        
        
