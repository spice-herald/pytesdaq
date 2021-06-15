import argparse
import numpy as np
import os
from math import log10, floor
import datetime
from glob import glob
import stat
import pickle
import qetpy as qp
import rqpy as rq
import pytesdaq.io.hdf5 as h5io

class ContinuousData:
    
    def __init__(self, file_list,
                 nb_events_randoms=500,
                 nb_events_trigger=-1,
                 trace_length_ms=None,
                 pretrigger_length_ms=None,
                 nb_samples=None,
                 nb_samples_pretrigger=None,
                 chan_to_trigger='all',
                 threshold=10,
                 series_name = None,
                 data_path = '/sdata/raw',
                 negative_pulse = True,
                 save_filter=False,
                 pileup_window=0,
                 coincident_window=50e-6):
        
        
        # file list
        self._file_list = file_list

        # path
        self._data_path = data_path

        # series name/num
        self._series_name = series_name
            
        # number of  events
        self._nb_events_randoms = nb_events_randoms
        self._nb_events_trigger = nb_events_trigger
     
        # negative pulse
        self._is_negative_pulse = negative_pulse
            
        
        # ADC device (Needs to fixed for multiple devices)
        self._adc_name = 'adc1'
        self._detector_config_name = 'detconfig1'

        # instanciate data reader
        self._h5reader = h5io.H5Reader()


        # Instantiate data writer
        self._h5writer = h5io.H5Writer()
        self._h5writer.initialize(series_name=self._series_name,
                                  data_path=self._data_path)


        # get sample rate and number of continuous samples
        rate, samples  = self._get_adc_config()
        if rate is None:
            raise ValueError('ERROR: Unable to find sample rate from metadata')
        
        if samples is None:
            raise ValueError('ERROR: Unable to find number samples from metadata')

        self._sample_rate  = rate
        self._nb_samples_continuous  = samples


        # trace length triggered data
        if nb_samples is not None:
            self._nb_samples = nb_samples
        elif trace_length_ms is not None:
            self._nb_samples = int(floor(trace_length_ms*self._sample_rate/1000))
        else:
            raise ValueError('ERROR: Trace length not available!')

        if nb_samples_pretrigger is not None:
            self._nb_samples_pretrigger = nb_samples_pretrigger
        elif pretrigger_length_ms is not None:
            self._nb_samples_pretrigger =  int(floor(pretrigger_length_ms*self._sample_rate/1000))
        else:
            self._nb_samples_pretrigger = int(floor(self._nb_samples/2))

              
        
        # set metadata
        self._set_metadata()


        # channels to trigger on (same implementation as RQpy)
        self._chan = chan_to_trigger
        
        
        # threshold
        self._threshold = threshold
        
        
        # noise calculation
        self._randoms_buffer = None
        self._noise_psd = None

        # filter file
        self._filter_dict = dict()
        self._save_filter = save_filter
        self._filter_file_name = self._data_path + '/' + self._series_name  + '_filter.pickle'
        
        # pileup and coincidence windows
        self._pileup_window = pileup_window
        self._coincident_window = coincident_window

    def create_template(self, rise_time, fall_time):
        """
        Create template
        """
        if self._sample_rate is None:
            raise ValueError('ERROR: No sample rate available!')
        
        if self._nb_samples is None or self._nb_samples_pretrigger is None:
            raise ValueError('ERROR: No trace length  available!')
        
        
        trace_time = 1.0/self._sample_rate *(np.arange(1,self._nb_samples+1)-self._nb_samples_pretrigger)
        lgc_b0 = trace_time < 0.0

        self._template = []
        for i, r in enumerate(rise_time):
            template= np.exp(-trace_time/fall_time[i])-np.exp(-trace_time/r)
            template[lgc_b0] = 0.0
            template = template/max(template)
            self._template.append(template)

        self._filter_dict['template'] = self._template

        
        
    def acquire_randoms(self, save_psd=False, verbose=True):
        """
        Function for acquiring random traces from continuous data
        """
        
        if verbose:
            print('INFO: Checking continuous data files')

            
        # get number of possible randoms in each continuous data file
        # then store dictionary {file_index: chunk_index} in a list, which
        # will be randomly shuffled
        choice_events = list()
        for ifile in range(len(self._file_list)):
            metadata = self._h5reader.get_metadata(file_name=self._file_list[ifile])
            nb_events_file = metadata['groups'][self._adc_name]['nb_events']
            nb_samples_file = metadata['groups'][self._adc_name]['nb_samples']
            if nb_samples_file != self._nb_samples_continuous:
                raise ValueError('ERROR: All the files should have the same number of samples per event!')
            nb_random_chunks = int(nb_events_file* nb_samples_file/self._nb_samples)
            for ichunk in range(nb_random_chunks):
                choice_events.append({ifile: ichunk})
        

        # shuffle
        if verbose:
            print('INFO: Randomly selecting ' + str(self._nb_events_randoms) + ' traces out of '
                  + str(len(choice_events)) + ' possible choices')

        np.random.shuffle(choice_events)

        # take only the number of events needed
        choice_events = choice_events[:self._nb_events_randoms]
      
        
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

        # this is a list, length of self._chans, that
        # should store the ndarrays randoms
        trace_buffer = None


        event_counter = 0
        for ifile, chunk_indices in event_dict.items():
                   
            # file
            file_name = self._file_list[ifile]

                               
            # loop chunk
            current_event_num = -1
            for chunk_index in chunk_indices:

                # Bin start
                bin_start_global = chunk_index * self._nb_samples
                bin_start = bin_start_global % self._nb_samples_continuous

                # event number 
                event_index = int(bin_start_global/nb_samples_file) + 1
                
                # get traces for all channels
                traces, info = self._h5reader.read_single_event(event_index,
                                                                file_name=file_name,
                                                                include_metadata=True)


                # invert if negative pulse
                if self._is_negative_pulse:
                    traces *= -1

                
                # truncate
                traces = traces[:,bin_start:bin_start+self._nb_samples]

                if trace_buffer is None:
                    trace_buffer =  np.expand_dims(traces, axis=0)
                else:
                    trace_buffer = np.append(trace_buffer,
                                             np.expand_dims(traces, axis=0),
                                             axis=0)


                # wap: lots of the following pt_trace lines
                # can be removed 
                # pt trace (channel sum determined by self._chan)
                if self._chan == "all":
                    pt_trace = traces.sum(axis=0)
                elif np.any(np.atleast_1d(self._chan) > traces.shape[0]):
                    raise ValueError(
                        '`chan_to_trigger` was set to a value greater than the number of channels.',
                    )
                elif np.isscalar(self._chan):
                    pt_trace = traces[self._chan]
                else:
                    pt_trace = np.sum(traces[self._chan],axis=0)

                if pt_trace.shape[0] != self._nb_samples:
                    continue

                pt_trace = np.expand_dims(pt_trace, axis=0)
                
                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['event_time'] = float(info['event_time']) + bin_start/self._sample_rate

                
                # write new file
                self._h5writer.write_event(traces, prefix='noise', data_mode = 'rand',
                                           dataset_metadata=dataset_metadata)



                if self._randoms_buffer is None:
                    self._randoms_buffer =  pt_trace
                else:
                    self._randoms_buffer = np.append(self._randoms_buffer, pt_trace, axis=0)


                #  event_counter
                event_counter += 1
                if (verbose and event_counter % 50 == 0):
                    print('INFO: Number of randoms = ' + str(event_counter))


        # cleanup
        self._h5writer.close()

        # verbose
        if verbose:
            print('INFO: Done acquiring randoms!')


        # check buffer 
        if self._randoms_buffer.shape[0]<1:
            raise ValueError('ERROR: No noise traces found!')

     
        # calc psd
        if verbose:
            print('INFO: Calculating PSD for optimal filter trigger')

        self._noise_psd = []
        for ichan, chan in enumerate(self._chan):
            chans_to_sum = self._chan[ichan]

            if np.isscalar(chans_to_sum):
                traces_red = trace_buffer[:,chans_to_sum]
            else:
                # if chan_to_sum has multiple entries (i.e. 1,2)
                # then it trace_buffer[:, chans_to_sum] has shape
                # 20,2,62500
                traces_red = np.sum(trace_buffer[:,chans_to_sum], axis=1)

            cut = qp.autocuts(traces_red, fs=self._sample_rate)
            print(f'PSD for channel/combination {chan}. Autocuts efficiency={np.sum(cut)/len(cut)}')
            f, psd = qp.calc_psd(traces_red[cut], fs=self._sample_rate, folded_over=False)
            f_fold, psd_fold = qp.foldpsd(psd, fs=self._sample_rate)

            self._noise_psd.append(psd)

        
        # save psd
        if self._save_filter:
            self._filter_dict['f'] = f
            self._filter_dict['psd'] = psd
            self._filter_dict['f_fold'] = f_fold
            self._filter_dict['psd_fold'] = psd_fold
            
        # cleanup
        self._randoms_buffer = None


    def find_close_times(self, pulsetimes, timethresh):

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


    def find_pileup(self, pulsetimes, pulseamps, timethresh, chantrig=None):
        """
        Function to find pileup
        """
        ranges = self.find_close_times(pulsetimes, timethresh)

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



    def remove_triggers(self, filt, inds_to_remove):
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

    def combine_sort_triggers(self, filt_list):

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
        filtcomb = rq.process.OptimumFilt(self._sample_rate,
                                                self._template[0],
                                                self._noise_psd,
                                                self._nb_samples,
                                                lgcoverlap=True)
        filtcomb.evttraces = evttracescomb
        filtcomb.pulseamps = pulseampscomb
        filtcomb.pulsetimes = pulsetimescomb
        filtcomb.trigamps = trigampscomb
        filtcomb.trigtimes = trigtimescomb
        filtcomb.trigtypes = trigtypescomb

        return filtcomb, chancomb

        
    def acquire_trigger(self, template=None, noise_psd=None, verbose=True):
        """
        Function to acquire trigger from continuous data
        """
        
        if verbose:
            print('INFO: Acquiring triggers!')

        # noise PSD (overwrite calculated PSD)
        if noise_psd is not None:
            self._noise_psd  = noise_psd

        # template (overwrite calculated PSD)
        if template is not None:
            self._template = template


        # save filter file
        if self._save_filter:
            with open(self._filter_file_name, 'wb') as handle:
                pickle.dump(self._filter_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
                
   

        # set file list to IO reader
        self._h5reader.clear()
        self._h5reader.set_files(self._file_list)
        

        # loop events
        do_continue_loop = True
        trigger_counter = 0
        while(do_continue_loop):

            # read next event
            traces, info = self._h5reader.read_event(include_metadata=True,
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
            # make filters for channel and store in list
            filt_list = []
            for ichan, chan in enumerate(self._chan):
                print(f'OF on channel {chan}')
                # find triggers
                filt = rq.process.OptimumFilt(self._sample_rate,
                                              self._template[ichan],
                                              self._noise_psd[ichan],
                                              self._nb_samples,
                                              chan_to_trigger=[chan],
                                              lgcoverlap=True)

                filt.filtertraces(traces, time_array)
                filt.eventtrigger(self._threshold[ichan], positivepulses=True)
                filt_list.append(filt)


            # remove pileup
            for ichan, chan in enumerate(self._chan):

                piledup_ind, _, _ = self.find_pileup(filt_list[ichan].pulsetimes,
                                                     filt_list[ichan].pulseamps,
                                                     self._pileup_window)

                print(f'Pileup on channel {chan}: len(piledup_ind) = {len(piledup_ind)}')

                lgc_verbose = False
                if lgc_verbose:
                    import inspect
                    import pprint
                    attributes = inspect.getmembers(filt_list[ichan], lambda a:not(inspect.isroutine(a)))
                    print('\n\n')
                    pprint.pprint([(a[0], type(a[1]), np.shape(a[1])) for a in attributes if not(a[0].startswith('__') and a[0].endswith('__'))])
                    print('\n\n')

                filt_list[ichan] = self.remove_triggers(filt_list[ichan], piledup_ind)

            # combine and sort the multiple
            # filt_list objects into a single one
            filtcomb, chancomb= self.combine_sort_triggers(filt_list)

            print('Combining Triggers')
            
            # find:
            # (1) coincidence triggers
            # (2) which triggers have had other channels merged into them
            # (3) which channels have been merged into the merged triggers
            coinc_ind, inds_merged, chancomb_merged = self.find_pileup(filtcomb.pulsetimes,
                                                                        filtcomb.pulseamps,
                                                                        self._coincident_window,
                                                                        chancomb)

            for i, ind in enumerate(inds_merged):
                chancomb[ind] = chancomb_merged[i]

            # remove the coincidence triggers from filtcomb
            filtcomb = self.remove_triggers(filtcomb, coinc_ind)

            # remove coincident triggers from chancomb
            for ind in sorted(coinc_ind, reverse=True):
                del chancomb[ind]


            print(f'Number of events with merged triggers = {len(inds_merged)}')
            print(f'Final number of events in this continuous data chunk = {len(chancomb)} \n')

            print(f'type(chancomb)={type(chancomb)}')
            print(f'type(chancomb[0])={type(chancomb[0])}')
            print(f'chancomb[0]={chancomb[0]}')

            # loop triggers
            for itrig in range(len(filtcomb.pulsetimes)):

                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['event_time'] = filtcomb.pulsetimes[itrig]
                dataset_metadata['trigger_time'] = filtcomb.pulsetimes[itrig]
                dataset_metadata['trigger_amplitude'] = filtcomb.pulseamps[itrig]
                dataset_metadata['trigger_channel'] = chancomb[itrig]

                # write new file
                self._h5writer.write_event(filtcomb.evttraces[itrig], prefix='trigger',
                                           data_mode = 'threshold',
                                           dataset_metadata=dataset_metadata)

                # event counter
                trigger_counter += 1
                if self._nb_events_trigger>0 and trigger_counter>=self._nb_events_trigger:
                    do_continue_loop = False
                    break

                # display
                if (verbose and trigger_counter % 50 == 0):
                    print('INFO: Number of triggers = ' + str(trigger_counter))
                    


                
    def _get_adc_config(self):
        """
        Get sample rate and number of continuous samples
        from metadata
        
        Return:
        
        sample_rate and nb_samples
        """


        # get metadata
        file_name = self._file_list[0]
        metadata = self._h5reader.get_metadata(file_name=file_name)

        # find sample rate / nb samples
        sample_rate = None
        nb_samples = None

        if self._adc_name in metadata['groups']:
            sample_rate = float(metadata['groups'][self._adc_name]['sample_rate'])
            nb_samples = int(metadata['groups'][self._adc_name]['nb_samples'])
             
        return sample_rate, nb_samples
        

        
    def _set_metadata(self):
        """
        Get file metadata and detector config 
        from first file and set to hdf5 file 

        Return:

        norm_array: numpy array with volt to amps normalization
        """

        file_name = self._file_list[0]
        file_metadata = dict()
        detector_config = dict()

        # get metadata from file
        metadata = self._h5reader.get_metadata(file_name=file_name)
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

        # set to h5 writer
        self._h5writer.set_metadata(file_metadata=file_metadata,
                                    detector_config=detector_config,
                                    adc_config=adc_config)


        
    
    
        
        
        
        
