import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
from glob import glob
import sys
from collections import Counter
import pprint
from scipy import constants
from scipy.signal import savgol_filter
from lmfit import Model

from pytesdaq.processing import _iv_didv_tools_plotting as plot
import qetpy as qp
from qetpy import IBIS, DIDV, Noise, didvinitfromdata, autocuts
from qetpy.sim import TESnoise, loadfromdidv, energy_res_estimate
from qetpy.plotting import plot_noise_sim
from qetpy.utils import align_traces, make_decreasing


__all__ = [
    "IVanalysis",
]


class Error(Exception):
    """Base class for other exceptions"""
    pass

class AnalysisError(Error):
    """
    Raised when there is an error in one of the steps in the automated
    analysis.

    """

    pass

def _check_df(df, channels=None):
    """
    Simple helper function to check number of occurences of qet bias
    values. It should be 2 per channel.

    Parameters
    ----------
    df : Pandas.core.DataFrame
        DataFrame of processed IV/dIdV sweep data.
    channels : list, optional
        The channel name to analyze. If None, then all the channels are
        checked.

    Returns
    -------
    gooddf : array
        Array of booleans corresponding to each channel in DF passing
        or failing check.

    """

    if not channels:
        channels = set(df.channels.values)

    gooddf = np.ones(shape=len(channels), dtype=bool)

    for ii, chan in enumerate(channels):
        chancut = df.channels == chan
        check_data = Counter(df.qetbias[chancut].values)
        if np.all(np.array(list(check_data.values())) == 2):
            check = True
        else:
            check = False
        gooddf[ii] = check

    return gooddf

def _remove_bad_series(df):
    """
    Helper function to remove series where the the squid lost lock, or
    the amplifier railed. This method will overwrite the parameter
    self.df with a DF that has the bad series removed. 

    Parameters
    ----------
    df : Pandas.core.DataFrame
        DataFrame of processed IV/dIdV sweep data.

    Returns
    -------
    newdf : Pandas.core.DataFrame
        New dataframe with railed events removed.

    """

    ccutfail = ~df.cut_pass 
    cstationary = np.array([len(set(trace)) for trace in df.avgtrace]) < 100
    cstd = df.offset_err == 0
    cbad = ccutfail | cstationary | cstd
    newdf = df[~cbad]

    return newdf

def _sort_df(df):
    """
    Helper function to sort data frame.

    Parameters
    ----------
    df : Pandas.core.DataFrame
        DataFrame of processed IV/dIdV sweep data.

    Returns
    -------
    sorteddf : Pandas.core.DataFrame
        New sorted dataframe.

    """

    sorteddf = df.sort_values(
        ['qetbias', 'seriesnum'], ascending=[True, True],
    )

    return sorteddf

def _flatten_psd(f, psd):
    """
    Helper function to smooth out all the spikes in a single-sided psd
    in order to more easily fit the SC and Normal state noise.

    Parameters
    ----------
    f: ndarray
        Array of frequency values.
    psd : ndarray
        Array of one sided psd values.

    Returns
    -------
    flattened_psd : ndarray
        Array of values of smoothed psd.

    """

    sav = np.zeros(psd.shape)
    div = int(.0025*len(psd))
    sav_lower = savgol_filter(psd[1:], 3, 1, mode='interp', deriv=0)
    sav_upper = savgol_filter(psd[1:], 45, 1, mode='interp', deriv=0)
    sav[1:div+1] = sav_lower[:div]
    sav[1+div:] = sav_upper[div:]
    sav[0] = psd[0]
    flattened_psd = make_decreasing(sav, x=f)

    return flattened_psd

def _normal_noise(freqs, squiddc, squidpole, squidn, rload, tload, rn, tc,
                  inductance):
    """
    Functional form of the normal state noise. Including the Johnson
    noise for the load resistor, the Johnson noise for the TES, and the
    SQUID + downstream electronics noise. See qetpy.sim.TESnoise class
    for more info.

    Parameters
    ----------
    freqs : array
        Array of frequencies.
    squiddc : float
        The average value for the white noise from the squid (ignoring
        the 1/f component).
    squidpole : float
        The knee for the 1/f component of the noise.
    squidn : float
        The factor for the 1/f^n noise.
    rload : float
        Value of the load resistor in Ohms.
    tload : float
        The temeperature of the load resistor in Kelvin.
    rn : float
        The value of the resistance of the TES when normal.
    tc : float
        The SC transistion temperature of the TES.
    inductance : float
        The inductance of the TES line.

    Returns
    -------
    s_tot : array
        Array of values corresponding to the theoretical normal state noise.

    """

    omega = 2.0 * np.pi * freqs
    dIdVnormal = 1.0 / (rload + rn + 1.0j * omega * inductance)
    s_vload = 4.0 * constants.k * tload * rload * np.ones_like(freqs)
    s_iloadnormal = s_vload * np.abs(dIdVnormal)**2.0
    s_vtesnormal = 4.0 * constants.k * tc * rn * np.ones_like(freqs)
    s_itesnormal = s_vtesnormal * np.abs(dIdVnormal)**2.0
    s_isquid = (squiddc * (1.0 + (squidpole / freqs)**squidn))**2.0
    s_tot = s_iloadnormal + s_itesnormal + s_isquid

    return s_tot

def _sc_noise(freqs, tload, squiddc, squidpole, squidn, rload, inductance):
    """
    Functional form of the Super Conducting state noise. Including
    the Johnson noise for the load resistor and the SQUID + downstream
    electronics noise. See qetpy.sim.TESnoise class for more info.

    Parameters
    ----------
    freqs : array
        Array of frequencies.
    tload : float
        The temeperature of the load resistor in Kelvin.
    squiddc : float
        The average value for the white noise from the squid (ignoring
        the 1/f component).
    squidpole : float
        The knee for the 1/f component of the noise.
    squidn : float
        The factor for the 1/f^n noise.
    rload : float
        Value of the load resistor in Ohms.
    inductance : float
        The inductance of the TES line.

    Returns
    -------
    s_tot : array
        Array of values corresponding to the theoretical SC state noise.

    """

    omega = 2.0 * np.pi * freqs
    dIdVsc = 1.0 / (rload + 1.0j * omega * inductance)
    s_vload = 4.0 * constants.k * tload * rload * np.ones_like(freqs)    
    s_iloadsc = s_vload * np.abs(dIdVsc)**2.0 
    s_isquid = (squiddc * (1.0 + (squidpole / freqs)**squidn))**2.0
    return s_iloadsc + s_isquid

class IVanalysis(object):
    """
    Class to aid in the analysis of an IV/dIdV sweep as processed by
    rqpy.proccess.process_ivsweep(). Currently only supports a single
    channel

    Attributes
    ----------
    df : Pandas.core.DataFrame
        DataFrame with the parameters returned by
        rqpy.process.process_ivsweep()
    channels : str or list
        Channel names to analyze. If only interested in a single
        channel, channels can be in the form a string.
    chname : str or list
        The corresponding name of the channels if a different label
        from channels is desired for plotting.
            Ex: PBS1 -> G147 channel 1
    figsavepath : str
        Path to where figures should be saved.
    noiseinds : ndarray
        Array of booleans corresponding to the rows of the df that are
        noise type data.
    didvinds : ndarray
        Array of booleans corresponding to the rows of the df that are
        didv type data.
    norminds : range
        python built-in range type corresponding to normal data points
        of the didv.
    scinds : range
        python built-in range type corresponding to SC data points of
        the didv.
    traninds : range
        python built-in range type corresponding to transition data
        points of the didv.
    rshunt : float
        The value of the shunt resistor in the TES circuit in Ohms.
    rshunt_err : float
        The uncertainty in the shunt resistor in the TES circuit in
        Ohms.
    rload : float
        The value of the load resistor (rshunt + rp).
    rload_err : float
        The uncertainty in the fitted load resistance.
    rp : float
        The parasitic resistance in the TES line.
    rn_didv : float
        The normal state resistance of the TES, calculated from fitting
        the dIdV.
    rn_iv : float
        The normal state resistance of the TES, calculated from the IV
        curve.
    rn_iv_err : float
        The uncertainty in the normal state resistance of the TES,
        calculated from the IV curve.
    vb : ndarray
        Array of bias voltages.
    vb_err : ndarray
        Array of uncertainties in the bais voltage.
    ibias : ndarray
        Array of bias currents.
    ibias_err : ndarray,
        Array of uncertainties in the bias current.
    dites : ndarray
        Array of DC offsets for IV/didv data.
    dites : ndarray
        Array of uncertainties in the DC offsets.
    tbath : float
        The bath temperature of the fridge.
    tc : float
        The super conducting temperature of the TESs.
    Gta : float
        The thermal conductance of the TESs to the absorber.
    squiddc : float
        The DC component of the squid+electronics noise.
    squidpole : float
        The knee for the squid 1/f noise.
    squidn : float
        The power of the 1/f^n noise for the squid.
    inductance : float
        The inductance of the TES line.
    noise_model : dict
        dictionary of arrays of the components of the noise modeling.
        See Notes for more information.

    Notes
    -----
    The noise_model dictionary is defined as:

        noise_model = {}
        noise_model['ites'] = (ites_mu, ites_upper, ites_lower)
        noise_model['iload'] = (iload_mu, iload_upper, iload_lower)
        noise_model['itfn'] = (itfn_mu, itfn_upper, itfn_lower)
        noise_model['isquid'] = (isquid_mu, isquid_upper, isquid_lower)
        noise_model['itot'] = (itot_mu, itot_upper, itot_lower)
        noise_model['ptes'] = (ptes_mu, ptes_upper, ptes_lower)
        noise_model['pload'] = (pload_mu, pload_upper, pload_lower)
        noise_model['ptfn'] = (ptfn_mu, ptfn_upper, ptfn_lower)
        noise_model['psquid'] = (psquid_mu, psquid_upper, psquid_lower)
        noise_model['ptot'] = (ptot_mu, ptot_upper, ptot_lower)
        noise_model['energy_res'] = e_res
        noise_model['energy_res_err'] = e_res_err

    where each element of the tuple is an array of shape
    (bias point, #freq bins)
        
    """
    
    def __init__(self, df, nnorm, nsc, ntran=None, channels=None,
                 channelname='', rshunt=5e-3, rshunt_err = 0.05*5e-3, tbath=0,
                 tbath_err=0, tc=0, tc_err=0, Gta=0, Gta_err=0, ib_err=None,
                 lgcremove_badseries = True, figsavepath=''):
        """
        Initialization of IVanalysis object. Note, currently only
        single channel analysis is supported.

        Parameters
        ----------
        df : Pandas.core.DataFrame
            DataFrame of a processed IV/dIdV sweep returned from 
            rqpy._process_iv_didv.process_ivsweep().
        nnorm : int
            Number bias values where the TES was normal,
            Note: count only one per noise and didv point (don't double
            count!)
        nsc : int
            Number of bias values where the TES was Super Conducting,
            Note: count only one per noise and didv point (don't double
            count!)
        ntran : range object, NoneType, optional
            The range of the transition data points.
            If ntran is None, then it is left as the total-(nnorm+nsc)
        channels : list, optional
            A list of strings correponding to the channels to analyze. 
            Note, currently only single channel analysis is supported
        channelname : str, optional
            This is used if the user wished to label the channel as
            something other than the stored channel name.
                e.g. channel = PBS1, channelname = PD2
        rshunt : float, optional
            The value of the shunt resistor in Ohms.
        rshunt_err : float, optional
            The unccertainty in the value of the shunt resistor.
        tbath : float, optional
            The temperature of the detector stack in Kelvin.
        tbath_err : float, optional
            The unccertainty in the temperature of the detector stack
            in Kelvin.
        tc : float, optional
            The temperature of the SC transition for the TES.
        tc_err : float, optional
            The unccertainty in the temperature of the SC transition
            for the TES.
        Gta : float, optional
            The theremal conductance between the TES and the absorber.
        ib_err : float, optional
            The error in the bias current
        lgcremove_badseries : bool, optional
            If True, series where the SQUID lost lock, or the amplifier
            railed are removed.
        figsavepath : str, optional
            The path to the directory where the figures should be
            saved.

        """

        df = _sort_df(df)

        check = _check_df(df, channels)
        if np.all(check):
            self.df = df
        else:
            raise ValueError(
                """The DF is not the correct shape. \nThere is either an"""
                """ extra series, or missing data on one or more channels"""
            )

        self.channels = channels
        self.chname = channelname
        self.figsavepath = figsavepath
        self.rshunt = rshunt 
        self.rshunt_err = rshunt_err
        self.rload = None
        self.rload_list = None
        self.rp = None
        self.rn_didv = None
        self.rn_iv = None
        self.rn_iv_err = None
        self.rtot_list = None
        self.squiddc = None
        self.squidpole = None
        self.squidn = None
        self.dt0_sc = None
        self.dt0_n = None

        if lgcremove_badseries:
            self.df = _remove_bad_series(df)

        self.noiseinds = (self.df.datatype == "noise")
        self.didvinds = (self.df.datatype == "didv")
        self.norminds = range(nnorm)
        self.scinds = range(len(self.df)//2-nsc, len(self.df)//2)
        if ntran is None:
            self.traninds = range(self.norminds[-1]+1, self.scinds[0])
        else:
            self.traninds = ntran
        ibias = np.zeros((1,2,self.noiseinds.sum()))
        if ib_err is None:
            ibias_err = np.zeros(ibias.shape)
        else: 
            ibias_err[0,:,:] = ib_err
        ibias[0,0,:] = self.df[self.noiseinds].qetbias.values
        ibias[0,1,:] = self.df[self.didvinds].qetbias.values
        dites = np.zeros((1,2,self.noiseinds.sum()))
        dites_err = np.zeros((1,2,self.noiseinds.sum()))
        dites[0,0,:] = self.df[self.noiseinds].offset.values
        dites_err[0,0,:] = self.df[self.noiseinds].offset_err.values
        dites[0,1,:] = self.df[self.didvinds].offset.values
        dites_err[0,1,:] = self.df[self.didvinds].offset_err.values

        self.vb = None
        self.ibias = ibias
        self.ibias_err = ibias_err
        self.dites = dites
        self.dites_err = dites_err

        self.tbath = tbath
        self.tbath_err = tbath_err
        self.tc = tc
        self.tc_err = tc_err
        self.Gta = Gta
        self.Gta_err = Gta_err
        self.rload_err = None

        tempdidv = DIDV(1,1,1,1,1)
        tempdidv_p = qp.DIDVPriors(1,1,1,1,1)
        self.df = self.df.assign(didvobj = tempdidv)
        self.df = self.df.assign(didvobj_p = tempdidv)
        self.noise_model = None

    def _fit_rload_didv(self, lgcplot=False, lgcsave=False, **kwargs):
        """
        Function to fit the SC dIdV series data and calculate rload.

        Parameters
        ----------
        lgcplot : bool, optional
            If True, the plots are shown for each fit.
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.
        **kwargs : dict
            Additional keyword arguments to be passed to
            didvinitfromdata(). See Notes for description.

        Returns
        -------
        None

        Notes
        -----
        If the fit is not good, you may need to specify an initial time
        offset using the **kwargs argument. Try passing `dt0=1.5e-6`
        (or other value) or additionally try `add180phase=False`.

        """

        rload_list = []
        dt0_list = []
        for ind in (self.scinds):
            didvsc = self.df[self.didvinds].iloc[ind]
            didvobjsc = didvinitfromdata(
                didvsc.avgtrace[:len(didvsc.didvmean)],
                didvsc.didvmean,
                didvsc.didvstd,
                didvsc.offset,
                didvsc.offset_err,
                didvsc.fs,
                didvsc.sgfreq,
                didvsc.sgamp,
                rsh=self.rshunt,
                dutycycle=didvsc.dutycycle if 'dutycycle' in didvsc.index else 0.5,
                **kwargs,
            )
            didvobjsc.dofit(1)
            rload_list.append(
                didvobjsc.fitresult(
                    1,
                )['smallsignalparams']['rp'] + self.rshunt
            )
            
            dt0_list.append(didvobjsc.fitresult(1)['smallsignalparams']['dt'])

            self.df.iat[
                int(np.flatnonzero(self.didvinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobjsc
            self.df.iat[
                int(np.flatnonzero(self.noiseinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobjsc
            
            if lgcplot:
                didvobjsc.plot_full_trace(
                    saveplot=lgcsave,
                    savepath=self.figsavepath,
                    savename=f'didv_{didvsc.qetbias:.3e}',
                )

        self.rload = np.mean(rload_list)
        self.rload_list = rload_list
        self.rload_err = np.std(rload_list)
        self.rp = self.rload - self.rshunt
        self.dt0_sc = np.median(dt0_list)

    def _fit_rn_didv(self, lgcplot=False, lgcsave=False, **kwargs):
        """
        Function to fit the Normal dIdV series data and calculate rn.

        Parameters
        ----------
        lgcplot : bool, optional
            If True, the plots are shown for each fit.
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.
        **kwargs : dict
            Additional key word arguments to be passed to
            didvinitfromdata(). See Notes for description.

        Returns
        -------
        None

        Notes
        -----
        If the fit is not good, you may need to specify an initial time
        offset using the **kwargs argument. Try passing `dt0=1.5e-6`
        (or other value) or additionally try `add180phase=False`.

        """

        if self.rload is None:
            raise ValueError(
                'rload has not been calculated yet, please fit rload first'
            )
        rtot_list = []
        dt0_list = []
        for ind in self.norminds:
            didvn = self.df[self.didvinds].iloc[ind]
            didvobjn = didvinitfromdata(
                didvn.avgtrace[:len(didvn.didvmean)],
                didvn.didvmean,
                didvn.didvstd,
                didvn.offset,
                didvn.offset_err,
                didvn.fs,
                didvn.sgfreq,
                didvn.sgamp,
                rsh=self.rshunt,
                rp=self.rp,
                dutycycle=didvn.dutycycle if 'dutycycle' in didvn.index else 0.5,
                **kwargs,
            )
            didvobjn.dofit(1)
            rtot = didvobjn.fitresult(
                1
            )['smallsignalparams']['rp'] + self.rshunt
            rtot_list.append(rtot)

            dt0_list.append(didvobjn.fitresult(1)['smallsignalparams']['dt'])

            self.df.iat[
                int(np.flatnonzero(self.didvinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobjn
            self.df.iat[
                int(np.flatnonzero(self.noiseinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobjn

            if lgcplot:
                didvobjn.plot_full_trace(
                    saveplot=lgcsave,
                    savepath=self.figsavepath,
                    savename=f'didv_{didvn.qetbias:.3e}',
                )
        self.rn_didv = np.mean(rtot_list) - self.rload
        self.rtot_list = rtot_list
        self.dt0_n = np.median(dt0_list)

    def fit_rload_rn(self, lgcplot=False, lgcsave=False, **kwargs):
        """
        Function to fit the SC dIdV series data  and the Normal dIdV
        series data and calculate rload, rp, and rn.

        This is just a wrapper function that calls _fit_rload_didv()
        and _fit_rn_didv().

        Parameters
        ----------
        lgcplot : bool, optional
            If True, the plots are shown for each fit.
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.
        **kwargs : dict
            Additional key word arguments to be passed to
            didvinitfromdata(). See Notes for description.

        Returns
        -------
        None

        Notes
        -----
        If the fit is not good, you may need to specify an initial time
        offset using the **kwargs argument. Try passing `dt0=1.5e-6`
        (or other value) or additionally try `add180phase=False`.

        """

        self._fit_rload_didv(lgcplot, lgcsave, **kwargs)
        self._fit_rn_didv(lgcplot, lgcsave, **kwargs)

    def analyze_sweep(self, lgcplot=False, lgcsave=False, fitsc=True,
                      **kwargs):
        """
        Function to correct for the offset in current and calculate R0,
        P0 and make plots of IV sweeps.

        The following parameters are added to self.df:
            ptes
            ptes_err
            r0
            r0_err
        and rn_iv and rn_iv_err are added to self. All of these
        parameters are calculated from the noise data, and the didv
        data.

        Parameters
        ----------
        lgcplot : bool, optional
            If True, the plots are shown for each fit.
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.
        fitsc : bool, optional
            If True, the SC data will be fit to get a more robust 
            estimate of Rp.
        kwargs : dict
            The keyword arguments that are passed to the
            qetpy.IBIS.analyze method.

        Returns
        -------
        None

        """

        ivobj = IBIS(
            dites=self.dites,
            dites_err=self.dites_err,
            ibias=self.ibias,
            ibias_err=self.ibias_err,
            rsh=self.rshunt,
            rsh_err=self.rshunt_err,
            rp_guess=5e-3,
            rp_err_guess=0,
            chan_names=[f'{self.chname} Noise',f'{self.chname} dIdV'],
            fitsc=fitsc,
            normalinds=self.norminds,
            scinds=self.scinds,
        )

        ivobj.analyze(**kwargs)
        self.df.loc[self.noiseinds, 'ptes'] =  ivobj.ptes[0,0]
        self.df.loc[self.didvinds, 'ptes'] =  ivobj.ptes[0,1]
        self.df.loc[self.noiseinds, 'ptes_err'] =  ivobj.ptes_err[0,0]
        self.df.loc[self.didvinds, 'ptes_err'] =  ivobj.ptes_err[0,1]
        self.df.loc[self.noiseinds, 'r0'] =  ivobj.r0[0,0]
        self.df.loc[self.didvinds, 'r0'] =  ivobj.r0[0,1]
        self.df.loc[self.noiseinds, 'r0_err'] =  ivobj.r0_err[0,0]
        self.df.loc[self.didvinds, 'r0_err'] =  ivobj.r0_err[0,1]

        self.df.loc[self.noiseinds, 'rp'] =  ivobj.rp[0,0]
        self.df.loc[self.didvinds, 'rp'] =  ivobj.rp[0,1]
        self.df.loc[self.noiseinds, 'rp_err'] =  ivobj.rp_err[0,0]
        self.df.loc[self.didvinds, 'rp_err'] =  ivobj.rp_err[0,1]

        self.df.loc[self.noiseinds, 'i0'] =  ivobj.ites[0,0]
        self.df.loc[self.didvinds, 'i0'] =  ivobj.ites[0,1]
        self.df.loc[self.noiseinds, 'i0_err'] =  ivobj.ites_err[0,0]
        self.df.loc[self.didvinds, 'i0_err'] =  ivobj.ites_err[0,1]

        self.rp_iv = ivobj.rp[0,0]
        self.rp_iv_err = ivobj.rp_err[0,0]
        self.rn_iv = ivobj.rnorm[0,0]
        self.rn_iv_err = ivobj.rnorm_err[0,0]

        self.vb = ivobj.vb
        self.vb_err = ivobj.vb_err
        self.ivobj = ivobj

        if lgcplot:
            ivobj.plot_all_curves(
                lgcsave=lgcsave,
                savepath=self.figsavepath,
                savename=self.chname,
            )


    def fit_tran_didv(self, lgcplot=False, lgcsave=False,**kwargs):
        """
        Function to fit all the didv data in the IV sweep data.

        Parameters
        ----------
        lgcplot : bool, optional
            If True, the plots are shown for each fit.
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.
        **kwargs : dict
            Additional key word arguments to be passed to
            didvinitfromdata(). See Notes for description.

        Returns
        -------
        None

        """ 

        for ind in (self.traninds):
    
            row = self.df[self.didvinds].iloc[ind]
            r0 = row.r0
 
            didvobj = didvinitfromdata(
                row.avgtrace[:len(row.didvmean)],
                row.didvmean,
                row.didvstd,
                row.offset,
                row.offset_err,
                row.fs,
                row.sgfreq,
                row.sgamp,
                rsh=self.rshunt,
                rp=self.rp_iv,
                r0=r0,
                dutycycle=row.dutycycle if 'dutycycle' in row.index else 0.5,
                **kwargs,
            )

            didvobj.dofit(poles=2)
            didvobj.dofit(poles=3)
            
            self.df.iat[
                int(np.flatnonzero(self.didvinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobj
            self.df.iat[
                int(np.flatnonzero(self.noiseinds)[ind]),
                self.df.columns.get_loc('didvobj')
            ] = didvobj

            #### Calculate correct errors
            didvobj_p = qp.DIDVPriors(
                rawtraces=None,
                fs=row.fs,
                sgfreq=row.sgfreq,
                sgamp=row.sgamp,
                rsh=self.rshunt,
                dutycycle=row.dutycycle if 'dutycycle' in row.index else 0.5,
            )

            didvobj_p._time = didvobj._time
            didvobj_p._freq = didvobj._freq
            didvobj_p._didvmean = didvobj._didvmean
            didvobj_p._didvstd = didvobj._didvstd
            didvobj_p._offset = didvobj._offset
            didvobj_p._offset_err = didvobj._offset_err
            didvobj_p._tmean = didvobj._tmean
            didvobj_p._dt0 = didvobj._dt0

            priors2 = np.ones(8)
            priors3 = np.ones(10)

            priors2[0] = didvobj.fitresult(2)['smallsignalparams']['rsh']
            priors2[1] = didvobj.fitresult(2)['smallsignalparams']['rp']
            priors2[2] = didvobj.fitresult(2)['smallsignalparams']['r0']
            priors2[3] = didvobj.fitresult(2)['smallsignalparams']['beta']
            priors2[4] = didvobj.fitresult(2)['smallsignalparams']['l']
            priors2[5] = didvobj.fitresult(2)['smallsignalparams']['L']
            priors2[6] = didvobj.fitresult(2)['smallsignalparams']['tau0']
            priors2[7] = didvobj.fitresult(2)['smallsignalparams']['dt']

            priors3[0] = didvobj.fitresult(3)['smallsignalparams']['rsh']
            priors3[1] = didvobj.fitresult(3)['smallsignalparams']['rp']
            priors3[2] = didvobj.fitresult(3)['smallsignalparams']['r0']
            priors3[3] = didvobj.fitresult(3)['smallsignalparams']['beta']
            priors3[4] = didvobj.fitresult(3)['smallsignalparams']['l']
            priors3[5] = didvobj.fitresult(3)['smallsignalparams']['L']
            priors3[6] = didvobj.fitresult(3)['smallsignalparams']['tau0']
            priors3[7] = didvobj.fitresult(3)['smallsignalparams']['gratio']
            priors3[8] = didvobj.fitresult(3)['smallsignalparams']['tau3']
            priors3[9] = didvobj.fitresult(3)['smallsignalparams']['dt']

            rp_sig = row.rp_err
            rshunt_sig = self.rshunt_err
            r0_sig = row.r0_err

            cov2 = np.zeros((8,8))
            cov3 = np.zeros((10,10))

            for ii in range(len(cov2)):
                cov2[ii,ii] = (priors2[ii]*.1)**2
            for ii in range(len(cov3)):
                cov3[ii,ii] = (priors3[ii]*.1)**2

            cov2[0,0] = rshunt_sig**2
            cov2[1,1] = rp_sig**2
            cov2[2,2] = r0_sig**2
            cov2[0,1] = cov2[1,0] = .5*rshunt_sig*rp_sig
            cov2[0,2] = cov2[2,0] = .5*rshunt_sig*r0_sig
            cov2[1,2] = cov2[2,1] = -.2*rp_sig*r0_sig

            # the priors fit is not important for the 
            # 3 pole fit since we don't use if for anything else
            # the r0 error seems to be too constrained from the IV
            # so we just consider a 15% error on the parameter
      
            r0_sig3 = priors3[2]*.15
            cov3[0,0] = rshunt_sig**2
            cov3[1,1] = rp_sig**2
            cov3[2,2] = r0_sig3**2
            cov3[0,1] = cov3[1,0] = .5*rshunt_sig*rp_sig
            cov3[0,2] = cov3[2,0] = .5*rshunt_sig*r0_sig3
            cov3[1,2] = cov3[2,1] = -.2*rp_sig*r0_sig3


            didvobj_p.dofit(poles=2, priors=priors2, priorscov=cov2)
            didvobj_p.dofit(poles=3, priors=priors3, priorscov=cov3)

            self.df.iat[
                int(np.flatnonzero(self.didvinds)[ind]),
                self.df.columns.get_loc('didvobj_p')
            ] = didvobj_p
            self.df.iat[
                int(np.flatnonzero(self.noiseinds)[ind]),
                self.df.columns.get_loc('didvobj_p')
            ] = didvobj_p

            if lgcplot:
                didvobj_p.plot_full_trace(
                    saveplot=lgcsave,
                    savepath=self.figsavepath,
                    savename=f'didv_{row.qetbias:.3e}',
                )
                didvobj_p.plot_re_im_didv(
                    poles='all',
                    saveplot=lgcsave,
                    savepath=self.figsavepath,
                    savename=f'didv_{row.qetbias:.3e}',
                )


    def fit_normal_noise(self, fit_range=(10, 3e4), squiddc0=6e-12,
                         squidpole0=200, squidn0=0.7, lgcplot=False,
                         lgcsave=False, xlims=None, ylims=None):
        """
        Function to fit the noise components of the SQUID+Electronics.
        Fits all normal noise PSDs and stores the average value for
        squiddc, squidpole, and squidn as attributes of the class.

        Parameters
        ----------
        fit_range : tuple, optional
            The frequency range over which to do the fit.
        squiddc0 : float, optional
            Initial guess for the squiddc parameter.
        squidpole0 : float, optional
            Initial guess for the squidpole parameter.
        squidn0 : float, optional
            Initial guess for the squidn parameter.
        lgcplot : bool, optional
            If True, a plot of the fit is shown.
        lgcsave : bool, optional
            If True, the figure is saved.
        xlims : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim().
        ylims : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim().

        Returns
        -------
        None

        """

        squiddc_list = []
        squidpole_list = []
        squidn_list = []

        self.normal_psd = np.mean(
            self.df[self.noiseinds].iloc[self.norminds].psd.values, axis=0,
        )[1:]

        for ind in self.norminds:
            noise_row = self.df[self.noiseinds].iloc[ind]
            f = noise_row.f
            psd = noise_row.psd

            inductance = noise_row.didvobj.fitresult(
                1
            )['smallsignalparams']['L']

            ind_lower = (np.abs(f - fit_range[0])).argmin()
            ind_upper = (np.abs(f - fit_range[1])).argmin()

            xdata = f[ind_lower:ind_upper]
            ydata = _flatten_psd(f,psd)[ind_lower:ind_upper]

            model = Model(_normal_noise, independent_vars=['freqs'])
            params = model.make_params(
                squiddc=squiddc0,
                squidpole=squidpole0,
                squidn=squidn0,
                rload=self.rload,
                tload=0.0,
                rn=self.rn_iv,
                tc=self.tc,
                inductance=inductance,
            )
            params['tc'].vary = False
            params['tload'].vary = False
            params['rload'].vary = False
            params['rn'].vary = False
            params['inductance'].vary = False
            result = model.fit(ydata, params, freqs=xdata)

            fitvals = result.values

            noise_sim = TESnoise(
                rload=self.rload,
                r0=self.rn_iv,
                rshunt=self.rshunt,
                inductance=inductance,
                beta=0,
                loopgain=0,
                tau0=0,
                G=0,
                qetbias=noise_row.qetbias,
                tc=self.tc,
                tload=0,
                tbath=self.tbath,
                squiddc=fitvals['squiddc'],
                squidpole=fitvals['squidpole'],
                squidn=fitvals['squidn'],
            )

            squiddc_list.append(fitvals['squiddc'])
            squidpole_list.append(fitvals['squidpole'])
            squidn_list.append(fitvals['squidn'])

            if lgcplot:
                plot_noise_sim(
                    f=f,
                    psd=psd,
                    noise_sim=noise_sim,
                    istype='normal',
                    qetbias=noise_row.qetbias,
                    lgcsave=lgcsave,
                    figsavepath=self.figsavepath,
                    xlims=xlims,
                    ylims=ylims,
                )

        self.squiddc = np.mean(squiddc_list)
        self.squidpole = np.mean(squidpole_list)
        self.squidn = np.mean(squidn_list)

    def fit_sc_noise(self, fit_range=(3e3, 1e5), lgcplot=False, lgcsave=False,
                     xlims=None, ylims=None):
        """
        Function to fit the components of the SC Noise. Fits all SC
        noise PSDs and stores the average value for tload as an
        attribute of the class.

        Parameters
        ----------
        fit_range : tuple, optional
            The frequency range over which to do the fit.
        lgcplot : bool, optional
            If True, a plot of the fit is shown.
        lgcsave : bool, optional
            If True, the figure is saved.
        xlims : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim().
        ylims : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim().

        Returns
        -------
        None

        """

        if self.squidpole is None:
            raise AttributeError(
                'You must fit the normal noise before fitting the SC noise'
            )

        tload_list = []


        for ind in self.scinds:
            noise_row = self.df[self.noiseinds].iloc[ind]
            f = noise_row.f
            psd = noise_row.psd
            inductance = noise_row.didvobj.fitresult(1)['smallsignalparams']['L']

            ind_lower = (np.abs(f - fit_range[0])).argmin()
            ind_upper = (np.abs(f - fit_range[1])).argmin()

            xdata = f[ind_lower:ind_upper]
            ydata = _flatten_psd(f,psd)[ind_lower:ind_upper]

            model = Model(_sc_noise, independent_vars=['freqs'])
            params = model.make_params(
                tload=0.03,
                squiddc=self.squiddc,
                squidpole=self.squidpole,
                squidn=self.squidn,
                rload=self.rload,
                inductance=inductance,
            )

            params['squiddc'].vary = False
            params['squidpole'].vary = False
            params['squidn'].vary = False
            params['rload'].vary = False
            params['inductance'].vary = False
            result = model.fit(ydata, params, freqs = xdata)

            fitvals = result.values

            noise_sim = TESnoise(
                rload=self.rload,
                r0=0.0001,
                rshunt=self.rshunt,
                inductance=inductance,
                beta=0,
                loopgain=0,
                tau0=0,
                G=0,
                qetbias=noise_row.qetbias,
                tc=self.tc,
                tload=fitvals['tload'],
                tbath=self.tbath,
                squiddc=self.squiddc,
                squidpole=self.squidpole,
                squidn=self.squidn,
            )

            tload_list.append(fitvals['tload'])

            if lgcplot:
                plot_noise_sim(
                    f=f,
                    psd=psd,
                    noise_sim=noise_sim,
                    istype='sc',
                    qetbias=noise_row.qetbias,
                    lgcsave=lgcsave,
                    figsavepath=self.figsavepath,
                    xlims=xlims,
                    ylims=ylims,
                )

        self.tload = np.mean(tload_list)

    def model_noise_simple(self, tau_collect=20e-6, collection_eff=1,
                           lgcplot=False, lgcsave=False, xlims=None,
                           ylims_current=None, ylims_power=None):
        """
        Function to plot noise PSD with all the theoretical noise
        components (calculated from the didv fits). This function also
        estimates the expected energy resolution based on the power
        noise spectrum.

        Note: This assumes a simple single body thermal model

        Parameters
        ----------
        tau_collect : float, optional
            The phonon collection time of the detector.
        collection_eff : float, optional
            The absolute phonon collection efficiency of the detector.
        lgcplot : bool, optional
            If True, a plot of the fit is shown.
        lgcsave : bool, optional
            If True, the figure is saved.
        xlims : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim().
        ylims_current : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim() for the current noise
            plots.
        ylims_power : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim() for the power noise
            plots.

        Returns
        -------
        None 

        """


        energy_res_arr = np.full(shape=sum(self.noiseinds), fill_value=np.nan)
        tau_eff_arr = np.full(shape=sum(self.noiseinds), fill_value=np.nan)
        for ind in self.traninds:
            noise_row = self.df[self.noiseinds].iloc[ind]
            f = noise_row.f
            psd = noise_row.psd
            didvobj = noise_row.didvobj

            noise_sim = loadfromdidv(
                didvobj,
                G=self.Gta,
                qetbias=noise_row.qetbias,
                tc=self.tc,
                tload=self.tload,
                tbath=self.tbath,
                squiddc=self.squiddc,
                squidpole=self.squidpole,
                squidn=self.squidn,
                noisetype='transition',
            )
            if lgcplot:
                plot_noise_sim(
                    f=f,
                    psd=psd,
                    noise_sim=noise_sim,
                    istype='current',
                    qetbias=noise_row.qetbias,
                    lgcsave=lgcsave,
                    figsavepath=self.figsavepath,
                    xlims=xlims,
                    ylims=ylims_current,
                )

                plot_noise_sim(
                    f=f,
                    psd=psd,
                    noise_sim=noise_sim,
                    istype='power',
                    qetbias=noise_row.qetbias,
                    lgcsave=lgcsave,
                    figsavepath=self.figsavepath,
                    xlims=xlims,
                    ylims=ylims_power,
                )


            res = energy_res_estimate(
                freqs=f,
                tau_collect=tau_collect,
                Sp=psd/(np.abs(noise_sim.dIdP(f))**2),
                collection_eff=collection_eff,
            )
            energy_res_arr[ind] = res

            tau_eff = didvobj.fitresult(2)['falltimes'][-1]
            tau_eff_arr[ind] = tau_eff


        self.df.loc[self.noiseinds, 'energy_res'] =  energy_res_arr
        self.df.loc[self.didvinds, 'energy_res'] =  energy_res_arr
        self.df.loc[self.noiseinds, 'tau_eff'] =  tau_eff_arr
        self.df.loc[self.didvinds, 'tau_eff'] =  tau_eff_arr

    def _get_tes_params(self, didvobj, nsamples=100):
        """
        Function to return parameters sampled from multivariate
        normal distribution based on TES fitted parameters.

        Parameters
        ----------
        didvobj : DIDVPriors object
            DIDVPriors object after fit has been done.
        nsamples : int
            Number of samples to generate.

        Returns
        -------
        rload : Array
            Array of rload samples of length nsamples.
        r0 : Array
            Array of r0 samples of length nsamples.
        beta : Array
            Array of beta samples of length nsamples.
        l : Array
            Array of irwins loop gain samples of length nsamples.
        L : Array
            Array of inductance samples of length nsamples.
        tau0 : Array
            Array of tau0 samples of length nsamples.
        tc : Array
            Array of tc samples of length nsamples.
        tb : Array
            Array of tb samples of length nsamples.

        """

        # didv params are in the following order
        #('rshunt0','rp0','r0','beta0','l0','L0','tau0' dt)

        cov = didvobj.fitresult(2)['cov'][:-1, :-1]
        mu = np.ones(7)

        mu[0] = didvobj.fitresult(2)['params']['rsh']
        mu[1] = didvobj.fitresult(2)['params']['rp']
        mu[2] = didvobj.fitresult(2)['params']['r0']
        mu[3] = didvobj.fitresult(2)['params']['beta']
        mu[4] = didvobj.fitresult(2)['params']['l']
        mu[5] = didvobj.fitresult(2)['params']['L']
        mu[6] = didvobj.fitresult(2)['params']['tau0']


        full_cov = np.zeros((cov.shape[0]+3, cov.shape[1]+3))
        full_mu = np.zeros((mu.shape[0]+3))
        full_mu[:-3] = mu
        full_mu[-3] = self.tc
        full_mu[-2] = self.tbath
        full_mu[-1] = self.Gta

        full_cov[:-3,:-3] = cov
        full_cov[-3,-3] = self.tc_err**2
        full_cov[-2,-2] = self.tbath_err**2
        full_cov[-1,-1] = self.Gta_err**2
        
        
        ### If issues are had where the covariance
        ### matrix is poorly conditioned, these scale 
        ### factors may help. 
        
        #scale = 1 / np.sqrt(np.diag(full_cov))
        #scale_cov = scale[np.newaxis].T.dot(scale[np.newaxis])
        scale = 1
        scale_cov = 1
   
        rand_data = np.random.multivariate_normal(
            full_mu * scale,
            full_cov * scale_cov,
            nsamples,
        )
        rand_data = rand_data/scale
        rshunt = rand_data[:,0]
        rp = rand_data[:,1]
        r0 = rand_data[:,2]
        beta = rand_data[:,3]
        l = rand_data[:,4]
        L = rand_data[:,5]
        tau0 = rand_data[:,6]
        tc = rand_data[:,7]
        tb = rand_data[:,8]
        gta = rand_data[:,9]

        return rshunt, rp, r0, beta, l, L, tau0, tc, tb, gta

    @staticmethod    
    def _err_bounds(arr, perc):
        """
        Helper function to calculate asymmetric error bounds.

        Parameters
        ----------
        arr : array
            Array of shape (#samples, #frequency bins)
        perc : tuple
            (upper, lower percentiles). If calculating 95 percentile,
            pass (5, 95).

        Returns
        -------
        median : array
            The median value for each frequency.
        p_upper : array
            Upper bound, same shape as median.
        p_lower : array
            Lower bound, same shape as median.

        """

        median = np.median(arr, axis=0)
        p_lower = np.percentile(arr, q=perc[0], axis=0)
        p_upper = np.percentile(arr, q=perc[1], axis=0)

        return median, p_upper, p_lower

    def estimate_noise_errors(self, tau_collect=0, collection_eff=1,
                              inds='all', nsamples=500, perc=(10,90)):
        """
        Function to estimate the errors in the theoretical noise model.

        Parameters
        ----------
        tau_collect : float, optional
            The phonon collection time of the detector.
        collection_eff : float, optional
            The absolute phonon collection efficiency of the detector.
        inds : range, list, int, str, optional
            The indices of the transistion state bias points to model
            the noise errors with.
        nsamples : int, optional
            The number of samples to generate.
        perc : tuple, optional
            (upper, lower percentiales). If calculating 95 percentile,
            pass (5, 95).

        Returns
        -------
        None

        """

        if inds == 'all':
            inds = np.arange(len(self.traninds))
        elif not isinstance(inds, list):
            inds = [inds]

        f = self.df[self.noiseinds].iloc[self.traninds].iloc[0].f[1:]

        ites_mu = np.zeros((len(inds), len(f)))
        ites_upper = np.zeros((len(inds), len(f)))
        ites_lower = np.zeros((len(inds), len(f)))
        iload_mu = np.zeros((len(inds), len(f)))
        iload_upper = np.zeros((len(inds), len(f)))
        iload_lower = np.zeros((len(inds), len(f)))
        itfn_mu = np.zeros((len(inds), len(f)))
        itfn_upper = np.zeros((len(inds), len(f)))
        itfn_lower = np.zeros((len(inds), len(f)))
        itot_mu = np.zeros((len(inds), len(f)))
        itot_upper = np.zeros((len(inds), len(f)))
        itot_lower = np.zeros((len(inds), len(f)))
        isquid_mu = np.zeros((len(inds), len(f)))
        isquid_upper = np.zeros((len(inds), len(f)))
        isquid_lower = np.zeros((len(inds), len(f)))

        ptes_mu = np.zeros((len(inds), len(f)))
        ptes_upper = np.zeros((len(inds), len(f)))
        ptes_lower = np.zeros((len(inds), len(f)))
        pload_mu = np.zeros((len(inds), len(f)))
        pload_upper = np.zeros((len(inds), len(f)))
        pload_lower = np.zeros((len(inds), len(f)))
        ptfn_mu = np.zeros((len(inds), len(f)))
        ptfn_upper = np.zeros((len(inds), len(f)))
        ptfn_lower = np.zeros((len(inds), len(f)))
        ptot_mu = np.zeros((len(inds), len(f)))
        ptot_upper = np.zeros((len(inds), len(f)))
        ptot_lower = np.zeros((len(inds), len(f)))
        psquid_mu = np.zeros((len(inds), len(f)))
        psquid_upper = np.zeros((len(inds), len(f)))
        psquid_lower = np.zeros((len(inds), len(f)))
        s_psd_mu = np.zeros((len(inds), len(f)))
        s_psd_upper = np.zeros((len(inds), len(f)))
        s_psd_lower = np.zeros((len(inds), len(f)))

        e_res = np.zeros((len(inds)))
        e_res_upper = np.zeros((len(inds)))
        e_res_lower = np.zeros((len(inds)))

        for ind in inds:

            noise_row = self.df[self.noiseinds].iloc[self.traninds].iloc[ind]
            f = noise_row.f[1:]
            psd = noise_row.psd[1:]
            didvobj = noise_row.didvobj_p
            tes_params = self._get_tes_params(
                didvobj, nsamples=nsamples,
            )

            rshunt, rp, r0, beta, l, L, tau0, tc, tb, gta = tes_params

            s_ites = np.zeros((nsamples, len(f)))
            s_iload = np.zeros((nsamples, len(f)))
            s_itfn = np.zeros((nsamples, len(f)))
            s_itot = np.zeros((nsamples, len(f)))
            s_isquid = np.zeros((nsamples, len(f)))

            s_ptes = np.zeros((nsamples, len(f)))
            s_pload = np.zeros((nsamples, len(f)))
            s_ptfn = np.zeros((nsamples, len(f)))
            s_ptot = np.zeros((nsamples, len(f)))
            s_psquid = np.zeros((nsamples, len(f)))
            s_psd = np.zeros((nsamples, len(f)))
            energy_res = []

            for ii in range(nsamples):
                tesnoise = TESnoise(
                    freqs=f,
                    rload=rp[ii] + rshunt[ii],
                    r0=r0[ii],
                    rshunt=rshunt[ii],
                    beta=beta[ii],
                    loopgain=l[ii],
                    inductance=L[ii],
                    tau0=tau0[ii],
                    G=gta[ii],
                    qetbias=noise_row.qetbias,
                    tc=tc[ii],
                    tload=self.tload,
                    tbath=tb[ii],
                    n=5.0,
                    lgcb=True,
                    squiddc=self.squiddc,
                    squidpole=self.squidpole,
                    squidn=self.squidn,
                )

                res = qp.sim.energy_res_estimate(
                    freqs=f,
                    tau_collect=tau_collect,
                    Sp=psd/(np.abs(tesnoise.dIdP(f))**2),
                    collection_eff=collection_eff,
                )
                energy_res.append(res)

                s_ites[ii] = tesnoise.s_ites()
                s_iload[ii] = tesnoise.s_iload()
                s_itfn[ii] = tesnoise.s_itfn()
                s_isquid[ii] = self.normal_psd
                s_itot[ii] = (
                    tesnoise.s_ites(
                    ) + tesnoise.s_iload(
                    ) + tesnoise.s_itfn(
                    ) + self.normal_psd
                )
#                 s_itot[ii] = tesnoise.s_itot()
#                 s_isquid[ii] = tesnoise.s_isquid()

                s_ptes[ii] = tesnoise.s_ptes()
                s_pload[ii] = tesnoise.s_pload()
                s_ptfn[ii] = tesnoise.s_ptfn()
                #s_ptot[ii] = tesnoise.s_ptot()
                #s_psquid[ii] = tesnoise.s_psquid()
                s_psquid[ii] = self.normal_psd / (np.abs(tesnoise.dIdP(f))**2)
                s_ptot[ii] = (
                    tesnoise.s_ptes(
                    ) + tesnoise.s_pload(
                    ) +tesnoise.s_ptfn(
                    ) + self.normal_psd/(np.abs(tesnoise.dIdP(f))**2)
                )

                s_psd[ii] = psd/(np.abs(tesnoise.dIdP(f))**2)

            #return s_ites, s_iload, s_itfn, s_itot, s_isquid
        
            (
                ites_mu[ind], ites_upper[ind], ites_lower[ind],
            ) = IVanalysis._err_bounds(s_ites, perc)
            (
                iload_mu[ind], iload_upper[ind], iload_lower[ind],
            ) = IVanalysis._err_bounds(s_iload, perc)
            (
                itfn_mu[ind], itfn_upper[ind], itfn_lower[ind],
            ) = IVanalysis._err_bounds(s_itfn, perc)
            (
                itot_mu[ind], itot_upper[ind], itot_lower[ind],
            ) = IVanalysis._err_bounds(s_itot, perc)
            (
                isquid_mu[ind], isquid_upper[ind], isquid_lower[ind],
            ) = IVanalysis._err_bounds(s_isquid, perc)

            (
                ptes_mu[ind], ptes_upper[ind], ptes_lower[ind],
            ) = IVanalysis._err_bounds(s_ptes, perc)
            (
                pload_mu[ind], pload_upper[ind], pload_lower[ind],
            ) = IVanalysis._err_bounds(s_pload, perc)
            (
                ptfn_mu[ind], ptfn_upper[ind], ptfn_lower[ind],
            ) = IVanalysis._err_bounds(s_ptfn, perc)
            (
                ptot_mu[ind], ptot_upper[ind], ptot_lower[ind],
            ) = IVanalysis._err_bounds(s_ptot, perc)
            (
                psquid_mu[ind], psquid_upper[ind], psquid_lower[ind],
            ) = IVanalysis._err_bounds(s_psquid, perc)
            (
                s_psd_mu[ind], s_psd_upper[ind], s_psd_lower[ind],
            ) = IVanalysis._err_bounds(s_psd, perc)

            (
                e_res[ind], e_res_upper[ind], e_res_lower[ind],
            )= IVanalysis._err_bounds(energy_res, perc)
#             e_res[ind] = np.mean(energy_res)
#             e_res_err[ind] = np.std(energy_res)

        noise_model = {}
        noise_model['ites'] = (ites_mu, ites_upper, ites_lower)
        noise_model['iload'] = (iload_mu, iload_upper, iload_lower)
        noise_model['itfn'] = (itfn_mu, itfn_upper, itfn_lower)
        noise_model['isquid'] = (isquid_mu, isquid_upper, isquid_lower)
        noise_model['itot'] = (itot_mu, itot_upper, itot_lower)
        noise_model['ptes'] = (ptes_mu, ptes_upper, ptes_lower)
        noise_model['pload'] = (pload_mu, pload_upper, pload_lower)
        noise_model['ptfn'] = (ptfn_mu, ptfn_upper, ptfn_lower)
        noise_model['psquid'] = (psquid_mu, psquid_upper, psquid_lower)
        noise_model['ptot'] = (ptot_mu, ptot_upper, ptot_lower)
        noise_model['s_psd'] = (s_psd_mu, s_psd_upper, s_psd_lower)
        noise_model['energy_res'] = (e_res, e_res_upper, e_res_lower)
        #noise_model['energy_res_err'] = e_res_err

        self.noise_model = noise_model

 
    def find_optimum_bias(self, lgcplot=False, lgcsave=False, xlims=None,
                          ylims=None, lgctau=False, lgcoptimum=False,
                          energyscale=None):
        """
        Function to find the QET bias with the lowest energy
        resolution.

        Parameters
        ----------
        lgcplot : bool, optional
            If True, a plot of the fit is shown.
        lgcsave : bool, optional
            If True, the figure is saved
        xlims : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim(), units of mOhms.
        ylims : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim(), units of meV.
        lgctau : bool, optional
            If True, tau_minus is plotted as function of R0 and
            QETbias.
        lgcoptimum : bool, optional
            If True, the optimum energy res (and tau_minus if
            lgctau=True)
        energyscale : char, NoneType, optional
            The metric prefix for how the energy resolution should be
            scaled. Defaults to None, which will be base units [eV]
            Can be: n->nano, u->micro, m->milli, k->kilo, M->Mega,
            or G->Giga.

        Returns
        -------
        optimum_bias_e : float
            The QET bias (in Amperes) corresponding to the lowest
            energy resolution.
        optimum_r0_e : float
            The resistance of the TES (in Ohms) corresponding to the
            lowest energy resolution.
        optimum_e : float
            The energy resolution (in eV) at the optimum bias point.
        optimum_bias_t : float
            The QET bias (in Amperes) corresponding to the fastest tau
            minus.
        optimum_r0_t : float
            The resistance of the TES (in Ohms) corresponding to the
            fastest tau minus.
        optimum_t : float
            The fastest tau minus (in seconds).

        """

        trandf = self.df.loc[self.noiseinds].iloc[self.traninds]
        r0s = trandf.r0.values/self.rn_iv
        energy_res = self.noise_model['energy_res'][0]
        energy_res_err = np.vstack(
            (
                self.noise_model['energy_res'][1],
                self.noise_model['energy_res'][2],
            ),
        )
        qets = trandf.qetbias.values
        taus = trandf.tau_eff.values

        eminind = np.argmin(energy_res)
        tauminind = np.argmin(taus)
        optimum_bias_e = qets[eminind]
        optimum_r0_e = r0s[eminind]
        optimum_bias_t = qets[tauminind]
        optimum_r0_t = r0s[tauminind]
        optimum_e = energy_res[eminind]
        optimum_t = energy_res[tauminind]

        if lgcplot:
            plot._plot_energy_res_vs_bias(
                r0s,
                energy_res,
                energy_res_err,
                qets,
                taus,
                xlims,
                ylims,
                lgcoptimum=lgcoptimum,
                lgctau=lgctau,
                energyscale=energyscale,
            )
        if lgctau:
            return (
                optimum_bias_e,
                optimum_r0_e,
                optimum_e,
                optimum_bias_t,
                optimum_r0_t,
                optimum_t,
            )
        else:
            return optimum_bias_e, optimum_r0_e, optimum_e

    def make_noiseplots(self, lgcsave=False):
        """
        Helper function to plot average noise/didv traces in time
        domain, as well as corresponding noise PSDs, for all QET bias
        points in IV/dIdV sweep.

        Parameters
        ----------
        lgcsave : bool, optional
            If True, all the plots will be saved in the a folder
            Avetrace_noise/ within the user specified directory.

        Returns
        -------
        None

        """

        plot._make_iv_noiseplots(self, lgcsave)

    def plot_rload_rn_qetbias(self, lgcsave=False, xlims_rl=None,
                              ylims_rl=None, xlims_rn=None, ylims_rn=None):
        """
        Helper function to plot rload and rnormal as a function of
        QETbias from the didv fits of SC and Normal data.

        Parameters
        ----------
        lgcsave : bool, optional
            If True, all the plots will be saved.
        xlims_rl : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim() for the rload plot.
        ylims_rl : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim() for the rload plot.
        xlims_rn : NoneType, tuple, optional
            Limits to be passed to ax.set_xlim() for the rtot plot.
        ylims_rn : NoneType, tuple, optional
            Limits to be passed to ax.set_ylim() for the rtot plot.

        Returns
        -------
        None

        """

        plot._plot_rload_rn_qetbias(
            self, lgcsave, xlims_rl, ylims_rl, xlims_rn, ylims_rn,
        )
        
    def plot_didv_bias(self, xlims=(-.15,0.025), ylims=(0,.08), cmap='magma'):
        """
        Helper function to plot the real vs imaginary part of the didv
        for different QET bias values for an IVanalysis object.

        Parameters
        ----------
        data : IVanalysis object
            The IVanalysis object with the didv fits already done.
        xlims : tuple, optional
            The xlimits of the plot.
        ylims : tuple, optional
            The ylimits of the plot.
        cmap : str, optional
            The colormap to use for the plot.

        Returns
        -------
        None

        """

        plot._plot_didv_bias(self, xlims=xlims, ylims=ylims, cmap=cmap)

    def plot_ztes_bias(self, xlims=(-110,110), ylims=(-120, 0),
                   cmap='magma_r'):
        """
        Helper function to plot the imaginary vs real part of the
        complex impedance for different QET bias values for an
        IVanalysis object

        Parameters
        ----------
        data : IVanalysis object
            The IVanalysis object with the didv fits already done.
        xlims : tuple, optional
            The xlimits of the plot.
        ylims : tuple, optional
            The ylimits of the plot.
        cmap : str, optional
            The colormap to use for the plot.

        Returns
        -------
        None

        """

        plot._plot_ztes_bias(self, xlims=xlims, ylims=ylims, cmap=cmap)

    def plot_noise_model(self, idx='all', xlims=(10, 2e5), ylims_current=None, 
                         ylims_power=None):
        """
        Function to plot noise models with errors for IVanalysis
        object.

        Parameters
        ----------
        data : IVanalysis object
            The IVanalysis object to plot.
        idx : range, str, optional
            The range of indeces to plot must be either a range()
            object or 'all'. If 'all', it defaults to all the
            transition data.
        xlims : tuple, optional
            The xlimits for all the plots.
        ylims_current : tuple, NoneType, optional
            The ylimits for all the current noise plots.
        ylims_power : tuple, NoneType, optional
            The ylimits for all the power noise plots.

        Returns
        -------
        None

        """

        plot._plot_noise_model(
            data=self,
            idx=idx,
            xlims=xlims,
            ylims_current=ylims_current,
            ylims_power=ylims_power,
        )
