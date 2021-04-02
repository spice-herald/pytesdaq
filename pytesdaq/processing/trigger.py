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
                 threshold=10,
                 series_name = None,
                 data_path = '/sdata/raw',
                 negative_pulse = True,
                 save_filter=False):
        
        
        # file list
        self._file_list = file_list

        # path
        self._data_path = data_path

        # series name/num
        self._series_name = series_name
        self._series_num = self._extract_series_num(series_name)
       
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


        # threshold
        self._threshold = threshold
        
        
        # noise calculation
        self._randoms_buffer = None
        self._noise_psd = None

        # filter file
        self._filter_dict = dict()
        self._save_filter = save_filter
        self._filter_file_name = self._data_path + '/' + self._series_name  + '_filter.pickle'
        
        
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
        self._template = np.exp(-trace_time/fall_time)-np.exp(-trace_time/rise_time)
        self._template[lgc_b0] = 0.0
        self._template = self._template/max(self._template)
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
                                                                filepath=file_name,
                                                                include_metadata=True)


                # invert if negative pulse
                if self._is_negative_pulse:
                    traces *= -1

                
                # truncate
                traces = traces[:,bin_start:bin_start+self._nb_samples]

                # pt trace
                pt_trace = traces.sum(axis=0)
                if pt_trace.shape[0] != self._nb_samples:
                    continue
                              
                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['event_time'] = float(info['event_time']) + bin_start/self._sample_rate

                
                # write new file
                self._h5writer.write_event(traces, prefix='noise', data_mode = 'rand',
                                           dataset_metadata=dataset_metadata)



                # Fill noise buffer
                pt_trace = traces.sum(axis=0)
                pt_trace = np.expand_dims(pt_trace, axis=0)
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

        cut = qp.autocuts(self._randoms_buffer, fs=self._sample_rate)
        f, psd = qp.calc_psd(self._randoms_buffer[cut], fs=self._sample_rate, folded_over=False)
        f_fold, psd_fold = qp.foldpsd(psd, fs=self._sample_rate)
        self._noise_psd = psd

        
        # save psd
        if self._save_filter:
            self._filter_dict['f'] = f
            self._filter_dict['psd'] = psd
            self._filter_dict['f_fold'] = f_fold
            self._filter_dict['psd_fold'] = psd_fold
            
        # cleanup
        self._randoms_buffer = None




        
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
            if info['read_flag'] != 0:
                do_continue_loop = False
                break

            
            # invert if negative pulse
            if self._is_negative_pulse:
                traces *= -1

            
            # event time
            time_array = np.asarray([info['event_time']])

            
            # expand dimension traces
            traces = np.expand_dims(traces, axis=0)
        
            
            # find triggers
            filt = rq.process.OptimumFilt(self._sample_rate,
                                          self._template,
                                          self._noise_psd,
                                          self._nb_samples,
                                          lgcoverlap=True)

            filt.filtertraces(traces, time_array)
            filt.eventtrigger(self._threshold, positivepulses=True)

            
            # loop triggers
            for itrig in range(len(filt.pulsetimes)):


                             
                # dataset metadata
                dataset_metadata = dict()
                dataset_metadata['event_time'] = filt.pulsetimes[itrig]
                dataset_metadata['trigger_time'] = filt.pulsetimes[itrig]
                dataset_metadata['trigger_amplitude'] = filt.pulseamps[itrig]
                              
                # write new file
                self._h5writer.write_event(filt.evttraces[itrig], prefix='trigger',
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


        # series number 
        file_metadata['series_num'] = self._series_num
        

        # set to h5 writer
        self._h5writer.set_metadata(file_metadata=file_metadata,
                                    detector_config=detector_config,
                                    adc_config=adc_config)


        
    
    def _extract_series_num(self, series_name):
        """
        Extact series number for series name
        Assume series name has the following 
        naming convention:  Ix_Dyyyymmdd_Thhmmss
        
        Return:

        serie_num  with format xyyyymmddhhmmss 
        """

        if not isinstance(series_name,str):
            raise ValueError('ERROR in extract_series_num: series name should be a string')


        # split series name
        series_split = series_name.split('_')

        # check string
        if (len(series_split) != 3 or
            series_split[0][0]!= 'I' or
            series_split[1][0]!= 'D' or
            series_split[2][0]!= 'T'):
            raise ValueError('ERROR in extract_series_num: unknown series name format!')


        
        # extract series num
        series_num = series_split[0][1:] + series_split[1][1:] + series_split[2][1:]
        series_num = np.uint64(float(series_num))
        return series_num
        
        
        
        
        
