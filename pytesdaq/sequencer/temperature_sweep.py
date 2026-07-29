"""
Shared MC temperature sweep used by the Gab and Gta measurements.

Both sweeps step the mixing chamber temperature downward and need the
same thing at every step: apply a setpoint, wait until the fridge
actually gets there and holds, then measure the temperature with an
uncertainty. This module owns that loop. It knows nothing about TESs.

The temperature controller driver has its own blocking wait, but it
gives no way to tell a setpoint that was reached from one that timed
out, so this module polls the thermometer itself.
"""

import time

import numpy as np
from scipy.optimize import curve_fit


def config_has(config_dict, key):
    """
    Check whether a config key is present.

    configparser lowercases every option name, so a key written with
    its proper unit capitalization (bias_min_uA, sample_rate_Hz)
    arrives lowercased. Lookups use the lowercase form while messages
    keep the canonical spelling the user wrote in the file.

    Parameters
    ----------
    config_dict : dict
        Measurement configuration dictionary.
    key : str
        Config key in its canonical capitalization.

    Returns
    -------
    present : bool
        True if the key is in the config.
    """

    return key.lower() in config_dict


def config_get(config_dict, key):
    """
    Read a config key, ignoring the case of its unit suffix.

    Parameters
    ----------
    config_dict : dict
        Measurement configuration dictionary.
    key : str
        Config key in its canonical capitalization.

    Returns
    -------
    value : object
        The raw config value.
    """

    return config_dict[key.lower()]


def build_temperature_list(config_dict=None):
    """
    Build the MC temperature setpoint list in mK from the config,
    using "temperature_vect_mK" or start/stop/step.

    Parameters
    ----------
    config_dict : dict
        Measurement configuration dictionary.

    Returns
    -------
    temperature_list : list of float
        Strictly decreasing MC temperature setpoints in mK.
    """

    use_vect = False
    if config_has(config_dict, 'use_temperature_vect'):
        use_vect = bool(config_get(config_dict, 'use_temperature_vect'))

    temperature_list = list()

    if use_vect:

        if not config_has(config_dict, 'temperature_vect_mK'):
            raise ValueError(
                'TemperatureSweep: "temperature_vect_mK" required when '
                '"use_temperature_vect" is true!'
            )

        vect = config_get(config_dict, 'temperature_vect_mK')
        if not isinstance(vect, (list, tuple)):
            vect = [vect]
        for value in vect:
            temperature_list.append(float(value))

    else:

        required_keys = ['temperature_start_mK',
                         'temperature_stop_mK',
                         'temperature_step_mK']
        for key in required_keys:
            if not config_has(config_dict, key):
                raise ValueError(
                    f'TemperatureSweep: "{key}" required when '
                    '"use_temperature_vect" is false!'
                )

        start = float(config_get(config_dict, 'temperature_start_mK'))
        stop = float(config_get(config_dict, 'temperature_stop_mK'))
        step = abs(float(config_get(config_dict, 'temperature_step_mK')))

        if step == 0:
            raise ValueError(
                'TemperatureSweep: "temperature_step_mK" must be nonzero!'
            )
        if stop >= start:
            raise ValueError(
                'TemperatureSweep: "temperature_stop_mK" must be below '
                '"temperature_start_mK" (descending sweep)!'
            )

        nb_steps = int(np.floor((start - stop) / step + 1e-9))
        for idx in range(nb_steps + 1):
            temperature_list.append(start - (idx * step))

    if len(temperature_list) == 0:
        raise ValueError('TemperatureSweep: empty temperature list!')

    for idx in range(1, len(temperature_list)):
        if temperature_list[idx] >= temperature_list[idx - 1]:
            raise ValueError(
                'TemperatureSweep: temperature list must be strictly '
                'decreasing!'
            )

    return temperature_list


def fit_temperature_gaussian(samples=None):
    """
    Estimate a temperature and its uncertainty from repeated samples
    by fitting a Gaussian to their histogram.

    The Gaussian mean is the temperature estimate and its sigma the
    uncertainty. When the fit is not possible (too few samples, zero
    spread, or a failed fit) the sample mean and standard deviation
    are returned instead, flagged with fit_ok = False.

    Parameters
    ----------
    samples : array-like
        Temperature samples, any unit (output is in the same unit).

    Returns
    -------
    result : dict
        Keys: mean, sigma [same unit as samples], fit_ok, nb_samples.
    """

    samples = np.asarray(samples, dtype=float)
    nb_samples = int(samples.size)

    if nb_samples == 0:
        raise ValueError(
            'TemperatureSweep: at least one temperature sample required!'
        )

    sample_mean = float(np.mean(samples))
    sample_std = float(np.std(samples))

    result = {
        'mean': sample_mean,
        'sigma': sample_std,
        'fit_ok': False,
        'nb_samples': nb_samples,
    }

    # a histogram fit needs enough samples and a nonzero spread
    # (controllers can quantize and return identical readings)
    if nb_samples < 10 or sample_std == 0:
        return result

    nb_bins = int(round(np.sqrt(nb_samples)))
    if nb_bins < 5:
        nb_bins = 5

    counts, edges = np.histogram(samples, bins=nb_bins)
    centers = (edges[:-1] + edges[1:]) / 2.0

    def gaussian(x, amplitude, mu, sigma):
        return amplitude * np.exp(-((x - mu) ** 2) / (2.0 * sigma ** 2))

    try:
        popt, pcov = curve_fit(
            gaussian,
            centers,
            counts,
            p0=[float(np.max(counts)), sample_mean, sample_std]
        )
    except (RuntimeError, ValueError):
        return result

    fit_mean = float(popt[1])
    fit_sigma = float(abs(popt[2]))

    # reject a fit that ran away from the data
    sample_span = float(np.max(samples) - np.min(samples))
    if (not np.isfinite(fit_mean)
            or not np.isfinite(fit_sigma)
            or fit_sigma == 0
            or fit_sigma > sample_span
            or fit_mean < float(np.min(samples))
            or fit_mean > float(np.max(samples))):
        return result

    result['mean'] = fit_mean
    result['sigma'] = fit_sigma
    result['fit_ok'] = True

    return result


class TemperatureSweep:

    def __init__(self, config_dict=None, instrument=None, verbose=True):
        """
        MC temperature sweep shared by the Gab and Gta measurements.

        Parameters
        ----------
        config_dict : dict
            Measurement configuration section.
        instrument : object or None
            Instrument control object. May be set later through the
            instrument property, since drivers are usually
            instantiated after the configuration is parsed.
        verbose : bool
            If True, print status messages.

        Returns
        -------
        None
        """

        self._instrument = instrument
        self._verbose = verbose

        def require(key):
            if not config_has(config_dict, key):
                raise ValueError(
                    f'TemperatureSweep: "{key}" required in config!'
                )
            return config_get(config_dict, key)

        self._thermometer_name = str(require('thermometer_name'))
        self._thermometer_instrument = str(
            require('thermometer_instrument')
        )
        self._heater_name = str(require('heater_name'))

        self._temperature_list_mk = build_temperature_list(
            config_dict=config_dict
        )

        self._poll_interval_s = float(
            require('temperature_poll_interval_s')
        )
        self._stable_time_s = float(require('temperature_stable_time_s'))
        self._max_wait_time_s = float(
            require('temperature_max_wait_time_s')
        )
        self._tolerance_frac = float(
            require('temperature_tolerance_frac')
        )

        if self._poll_interval_s <= 0:
            raise ValueError(
                'TemperatureSweep: "temperature_poll_interval_s" must '
                'be positive!'
            )
        if self._stable_time_s < 0:
            raise ValueError(
                'TemperatureSweep: "temperature_stable_time_s" must '
                'not be negative!'
            )
        if self._max_wait_time_s <= 0:
            raise ValueError(
                'TemperatureSweep: "temperature_max_wait_time_s" must '
                'be positive!'
            )
        if self._tolerance_frac <= 0:
            raise ValueError(
                'TemperatureSweep: "temperature_tolerance_frac" must '
                'be positive!'
            )

        # optional: window over which the temperature is sampled for
        # each datapoint
        self._sampling_time_s = 5.0
        if config_has(config_dict, 'temperature_sampling_time_s'):
            self._sampling_time_s = float(
                config_get(config_dict, 'temperature_sampling_time_s')
            )

        if self._sampling_time_s < 0:
            raise ValueError(
                'TemperatureSweep: "temperature_sampling_time_s" must '
                'not be negative!'
            )

    @property
    def instrument(self):
        return self._instrument

    @instrument.setter
    def instrument(self, value):
        self._instrument = value

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        self._verbose = value

    @property
    def thermometer_name(self):
        return self._thermometer_name

    @property
    def thermometer_instrument(self):
        return self._thermometer_instrument

    @property
    def heater_name(self):
        return self._heater_name

    @property
    def temperature_list_mk(self):
        return self._temperature_list_mk

    @property
    def poll_interval_s(self):
        return self._poll_interval_s

    @property
    def stable_time_s(self):
        return self._stable_time_s

    @property
    def max_wait_time_s(self):
        return self._max_wait_time_s

    @property
    def tolerance_frac(self):
        return self._tolerance_frac

    @property
    def sampling_time_s(self):
        return self._sampling_time_s

    def set_setpoint(self, temperature_mk=None):
        """
        Apply an MC temperature setpoint without blocking.

        The driver's own wait is not used, because it cannot report
        whether it reached the setpoint or simply ran out of time.
        Use wait_for_temperature to wait.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint [mK].

        Returns
        -------
        None
        """

        self._instrument.set_temperature(
            float(temperature_mk) / 1000.0,
            channel_name=self._thermometer_name,
            heater_channel_name=self._heater_name,
            instrument_name=self._thermometer_instrument,
            wait_temperature_reached=False
        )

    def wait_for_temperature(self, temperature_mk=None):
        """
        Wait until the MC temperature reaches a setpoint and holds it.

        The thermometer is polled every temperature_poll_interval_s
        and the reading must stay within temperature_tolerance_frac
        of the setpoint for temperature_stable_time_s before the
        setpoint counts as reached. How fast the fridge cools is set
        by its cooling power and the thermal conductance, so a large
        temperature step can take much longer than a small one and a
        fixed wait cannot cover both.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint [mK].

        Returns
        -------
        temperature_ok : bool
            True if the setpoint was reached and held, False on
            timeout.
        history : list of float
            All temperature readings taken [mK].
        """

        target_mk = float(temperature_mk)
        history = list()
        start_time = time.time()
        time_in_tolerance = None

        if self._verbose:
            print(f'INFO: Waiting for MC temperature to reach '
                  f'{target_mk:.6g} mK (within '
                  f'{self._tolerance_frac * 100.0:.3g} percent '
                  f'for {self._stable_time_s:.6g} s)')

        while True:

            reading_mk = 1000.0 * float(self._instrument.get_temperature(
                channel_name=self._thermometer_name,
                instrument_name=self._thermometer_instrument
            ))
            history.append(reading_mk)

            offset = abs(reading_mk - target_mk) / abs(target_mk)
            now = time.time()

            if offset <= self._tolerance_frac:
                if time_in_tolerance is None:
                    time_in_tolerance = now
                    if self._verbose:
                        print(f'INFO: MC temperature within tolerance '
                              f'at {reading_mk:.6g} mK, holding for '
                              f'{self._stable_time_s:.6g} s')
                if ((now - time_in_tolerance)
                        >= self._stable_time_s):
                    if self._verbose:
                        print(f'INFO: MC temperature {reading_mk:.6g} '
                              f'mK reached after {now - start_time:.6g} '
                              's')
                    return True, history
            else:
                # drifted back out, the hold time restarts
                time_in_tolerance = None

            if (now - start_time) > self._max_wait_time_s:
                print('WARNING: MC temperature timeout '
                      f'({self._max_wait_time_s:.6g} s), '
                      f'setpoint {target_mk:.6g} mK not reached, last '
                      f'reading {reading_mk:.6g} mK '
                      f'({offset * 100.0:+.3g} percent off), recording '
                      'the point as temperature not reached!')
                return False, history

            time.sleep(self._poll_interval_s)

    def measure_temperature(self):
        """
        Measure the MC temperature with its uncertainty: sample the
        thermometer repeatedly for temperature_sampling_time_s, then
        fit a Gaussian to the histogram of samples. The Gaussian mean
        is the temperature, its sigma the uncertainty (sample mean
        and standard deviation when the fit is not possible).

        Returns
        -------
        measurement : dict
            Keys: temperature_k, temperature_err_k [Kelvin], fit_ok,
            nb_samples, samples (list of all readings [Kelvin]).
        """

        samples = list()
        start_time = time.time()

        # always at least one sample, then keep reading as fast as
        # the instrument responds until the window closes
        while True:

            value = float(self._instrument.get_temperature(
                channel_name=self._thermometer_name,
                instrument_name=self._thermometer_instrument
            ))
            samples.append(value)

            elapsed = time.time() - start_time
            if elapsed >= self._sampling_time_s:
                break

        fit = fit_temperature_gaussian(samples=samples)

        measurement = {
            'temperature_k': fit['mean'],
            'temperature_err_k': fit['sigma'],
            'fit_ok': fit['fit_ok'],
            'nb_samples': fit['nb_samples'],
            'samples': samples,
        }

        return measurement

    def heater_to_zero(self):
        """
        Set the MC heater setpoint to zero, without waiting.

        Returns
        -------
        None
        """

        self._instrument.set_temperature(
            0,
            channel_name=self._thermometer_name,
            heater_channel_name=self._heater_name,
            instrument_name=self._thermometer_instrument,
            wait_temperature_reached=False
        )
