import numpy as np
import qetpy as qp
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm


__all__ = [
    "_make_iv_noiseplots",
    "_plot_energy_res_vs_bias",
    "_plot_rload_rn_qetbias",
    "_plot_didv_bias",
    "_plot_ztes_bias",
    "_plot_noise_model",
]


def _make_iv_noiseplots(IVanalysisOBJ, lgcsave=False):
    """
    Helper function to plot average noise/didv traces in time domain,
    as well as corresponding noise PSDs, for all QET bias points in
    IV/dIdV sweep.

    Parameters
    ----------
    IVanalysisOBJ : rqpy.IVanalysis
         The IV analysis object that contains the data to use for
         plotting.
    lgcsave : bool, optional
        If True, all the plots will be saved in the a folder
        avetrace_noise/ within the user specified directory.

    Returns
    -------
    None

    """

    for (noiseind, noiserow), (didvind, didvrow) in zip(
        IVanalysisOBJ.df[IVanalysisOBJ.noiseinds].iterrows(),
        IVanalysisOBJ.df[IVanalysisOBJ.didvinds].iterrows()
    ):
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 6))

        t = np.arange(0,len(noiserow.avgtrace))/noiserow.fs
        tdidv = np.arange(0, len(didvrow.avgtrace))/noiserow.fs
        axes[0].set_title(
            f"""{noiserow.seriesnum} Avg Trace, """
            f"""QET bias = {noiserow.qetbias*1e6:.2f} $\mu A$"""
        )
        axes[0].plot(
            t*1e6,
            noiserow.avgtrace * 1e6,
            label=f"{self.chname} Noise",
            alpha=0.5,
        )
        axes[0].plot(
            tdidv*1e6,
            didvrow.avgtrace * 1e6,
            label=f"{self.chname} dIdV",
            alpha=0.5,
        )
        axes[0].grid(which="major")
        axes[0].grid(which="minor", linestyle="dotted", alpha=0.5)
        axes[0].tick_params(
            axis="both", direction="in", top=True, right=True, which="both",
        )
        axes[0].set_ylabel("Current [μA]", fontsize = 14)
        axes[0].set_xlabel("Time [μs]", fontsize = 14)
        axes[0].legend()

        axes[1].loglog(
            noiserow.f, noiserow.psd**0.5 * 1e12, label=f"{self.chname} PSD",
        )
        axes[1].set_title(
            f"""{noiserow.seriesnum} PSD, """
            f"""QET bias = {noiserow.qetbias*1e6:.2f} $\mu A$"""
        ,)
        axes[1].grid(which="major")
        axes[1].grid(which="minor", linestyle="dotted", alpha=0.5)
        axes[1].set_ylim(1, 1e3)
        axes[1].tick_params(
            axis="both", direction="in", top=True, right=True, which="both",
        )
        axes[1].set_ylabel(r"PSD [pA/$\sqrt{\mathrm{Hz}}$]", fontsize=14)
        axes[1].set_xlabel("Frequency [Hz]", fontsize=14)
        axes[1].legend()

        plt.tight_layout()
        if lgcsave:
            if not savepath.endswith('/'):
                savepath += '/'
            fullpath = f'{IVanalysisOBJ.figsavepath}avetrace_noise/'
            if not os.path.isdir(fullpath):
                os.makedirs(fullpath)

            plt.savefig(fullpath + f'{noiserow.qetbias*1e6:.2f}_didvnoise.png')
        plt.show()

def _plot_rload_rn_qetbias(IVanalysisOBJ, lgcsave, xlims_rl, ylims_rl,
                           xlims_rn, ylims_rn):
    """
    Helper function to plot rload and rnormal as a function of QETbias
    from the didv fits of SC and Normal data for IVanalysis object.

    Parameters
    ----------
    IVanalysisOBJ : rqpy.IVanalysis
        The IV analysis object that contains the data to use for
        plotting.
    lgcsave : bool, optional
        If True, all the plots will be saved.
    xlims_rl : NoneType, tuple, optional
        Limits to be passed to ax.set_xlim() for the  rload plot.
    ylims_rl : NoneType, tuple, optional
        Limits to be passed to ax.set_ylim() for the rload plot.
    xlims_rn : NoneType, tuple, optional
        Limits to be passed to ax.set_xlim() for the  rtot plot.
    ylims_rn : NoneType, tuple, optional
        Limits to be passed to ax.set_ylim() for the rtot plot.

    Returns
    -------
    None

    """

    fig, axes = plt.subplots(1,2, figsize = (16,6))
    fig.suptitle("Rload and Rtot from dIdV Fits", fontsize = 18)

    if xlims_rl is not None:
        axes[0].set_xlim(xlims_rl)
    if ylims_rl is not None:
        axes[0].set_ylim(ylims_rl)
    if xlims_rn is not None:
        axes[1].set_xlim(xlims_rn)
    if ylims_rn is not None:
        axes[1].set_ylim(ylis_rn)

    axes[0].errorbar(
        IVanalysisOBJ.vb[0,0,IVanalysisOBJ.scinds]*1e6,
        np.array(IVanalysisOBJ.rload_list)*1e3,
        yerr=IVanalysisOBJ.rshunt_err*1e3,
        linestyle='',
        marker='.',
        ms=10,
    )
    axes[0].grid(True, linestyle = 'dashed')
    axes[0].set_title('Rload vs Vbias', fontsize = 14)
    axes[0].set_ylabel(r'$R_\ell \, [\mathrm{m}\Omega]$', fontsize = 14)
    axes[0].set_xlabel(r'$V_\mathrm{bias} \, [\mu\mathrm{V}]$', fontsize = 14)
    axes[0].tick_params(
        axis="both", direction="in", top=True, right=True, which="both",
    )

    axes[1].errorbar(
        IVanalysisOBJ.vb[0,0,IVanalysisOBJ.norminds]*1e6,
        np.array(IVanalysisOBJ.rtot_list)*1e3,
        yerr=IVanalysisOBJ.rshunt_err*1e3,
        linestyle='',
        marker='.',
        ms=10,
    )
    axes[1].grid(True, linestyle='dashed')
    axes[1].set_title('Rtotal vs Vbias', fontsize=14)
    axes[1].set_ylabel(r'$R_N + R_\ell \, [\mathrm{m}\Omega]$', fontsize=14)
    axes[1].set_xlabel(r'$V_\mathrm{bias} \, [\mu\mathrm{V}]$', fontsize=14)
    axes[1].tick_params(
        axis="both", direction="in", top=True, right=True, which="both",
    )

    plt.tight_layout()
    if lgcsave:
        plt.savefig(IVanalysisOBJ.figsavepath + 'rload_rtot_variation.png')


def _plot_energy_res_vs_bias(r0s, energy_res, energy_res_err, qets, taus,
                             xlims=None, ylims=None, lgctau=False,
                             lgcoptimum=False, figsavepath='', lgcsave=False,
                             energyscale=None):
    """
    Helper function for the IVanalysis class to plot the expected
    energy resolution as a function of QET bias and TES resistance.

    Parameters
    ----------
    r0s : ndarray
        Array of r0 values (in Ohms).
    energy_res : ndarray
        Array of expected energy resolutions (in eV).
    energy_res_err : ndarray, NoneType
        Array of energy resolution error bounds in eV. must be of shape
        (2, #qet bias) where the first dims are the lower and upper
        bounds.
    qets : ndarray
        Array of QET bias values (in Amps).
    taus : ndarray
        Array of tau minus values (in seconds).
    xlims : NoneType, tuple, optional
        Limits to be passed to ax.set_xlim().
    ylims : NoneType, tuple, optional
        Limits to be passed to ax.set_ylim().
    lgctau : bool, optional
        If True, tau_minus is plotted as function of R0 and QETbias.
    lgcoptimum : bool, optional
        If True, the optimum energy res (and tau_minus if lgctau=True).
    figsavepath : str, optional
        Directory to save the figure.
    lgcsave : bool, optional
        If true, the figure is saved.
    energyscale : char, NoneType, optional
        The metric prefix for how the energy resolution should be
        scaled. Defaults to None, which will be base units [eV] Can be:
        n->nano, u->micro, m->milli, k->kilo, M->Mega, or G->Giga.

    Returns
    -------
    None

    """

    metric_prefixes = {
        'n': 1e9, 'u': 1e6, 'm': 1e3, 'k': 1e-3, 'M': 1e-6, 'G': 1e-9,
    }
    if energyscale is None:
        scale = 1
        energyscale = ''
    elif energyscale not in metric_prefixes:
        raise ValueError(
            f'energyscale must be one of {metric_prefixes.keys()}'
        )
    else:
        scale = metric_prefixes[energyscale]
    if energyscale == 'u':
        energyscale = r'$\mu$'
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(9, 6))

    if xlims is None:
        xlims = (min(r0s), max(r0s))
    if ylims is None:
        ylims = (min(energy_res*scale), max(energy_res*scale))
    crangey = (energy_res > ylims[0]) & (energy_res < ylims[1])
    crangex = (r0s > xlims[0]) & (r0s < xlims[1])

    r0s = r0s[crangey & crangex]
    energy_res = energy_res[crangey & crangex]*scale
    energy_res_err = energy_res_err[:,crangey & crangex]*scale
    qets = (qets[crangey & crangex]*1e6).round().astype(int)
    taus = taus[crangey & crangex]*1e6

    ax.plot(r0s, energy_res, linestyle = ' ', marker = '.', ms = 10, c='g')
    ax.plot(
        r0s,
        energy_res,
        linestyle='-',
        marker=' ',
        linewidth=3,
        alpha=.5,
        c='g',
    )
    ax.fill_between(
        r0s, energy_res_err[0], energy_res_err[1],  alpha=.5, color='g',
    )

    ax.grid(True, which = 'both', linestyle = '--')
    ax.set_xlabel('$R_0/R_N$')
    ax.set_ylabel(r'$σ_E$'+f' [{energyscale}eV]', color='g')
    ax.tick_params('y', colors='g')
    ax.tick_params(which="both", direction="in", right=True, top=True)

    if lgcoptimum:
        plte = ax.axvline(
            r0s[np.argmin(energy_res)],
            linestyle = '--',
            color='g',
            alpha=0.5,
            label=r"""Min $\sigma_E$: """
                  f"""{np.min(energy_res):.3f} [{energyscale}eV]""",
        )

    ax2 = ax.twiny()
    ax2.spines['bottom'].set_position(('outward', 36))
    ax2.xaxis.set_ticks_position('bottom')
    ax2.xaxis.set_label_position('bottom') 
    ax2.set_xticks(r0s)
    ax2.set_xticklabels(qets)
    ax2.set_xlabel(r'QET bias [$\mu$A]')

    if lgctau:
        ax3 = ax.twinx()
        ax3.plot(r0s, taus, linestyle=' ', marker='.', ms=10, c='b')
        ax3.plot(
            r0s, taus, linestyle='-', marker=' ', linewidth=3, alpha=.5, c='b',
        )
        ax3.tick_params(which="both", direction="in", right=True, top=True)
        ax3.tick_params('y', colors = 'b')
        ax3.set_ylabel(r'$\tau_{-} [μs]$', color = 'b')

        if lgcoptimum:
            plttau = ax3.axvline(
                r0s[np.argmin(taus)],
                linestyle = '--',
                alpha=0.5,
                label=r"""Min $\tau_{-}$: """
                      f"""{np.min(taus):.3f} [μs]""",
            )
    if xlims is not None:
        ax.set_xlim(xlims)
        ax2.set_xlim(xlims)
        if lgctau:
            ax3.set_xlim(xlims)
    if ylims is not None:
        ax.set_ylim(ylims)

    ax.set_title('Expected Energy Resolution vs QET bias and $R_0/R_N$')
    if lgcoptimum:
        ax.legend()
        if lgctau:
            ax.legend(loc='upper center', handles=[plte, plttau])

    if lgcsave:
        plt.savefig(f'{figsavepath}energy_res_vs_bias.png')

def _plot_didv_bias(data, xlims=(-.15,0.025), ylims=(0,.08), cmap='magma'):
    """
    Helper function to plot the imaginary vs real part of the didv for
    different QET bias values for an IVanalysis object.

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
    fig : matplotlib.Figure
        Figure object for plot.
    ax : matplotlib.Axes
        Axes object for plot.

    """

    fig,ax=plt.subplots(figsize=(10,6))
    ax.set_xlabel('Re($dI/dV$) ($\Omega^{-1}$)')
    ax.set_ylabel('Im($dI/dV$) ($\Omega^{-1}$)')

    ax.set_title("Real and Imaginary Part of dIdV")
    ax.tick_params(which='both', direction='in', right=True, top=True)
    ax.grid(which='major')
    ax.grid(which='minor',linestyle='dotted',alpha=0.3)
    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    qets = np.abs(
        data.df.loc[data.didvinds, 'qetbias'].iloc[data.traninds].values
    )*1e6

    normalize = mcolors.Normalize(vmin=min(qets), vmax=max(qets))
    colormap = plt.get_cmap(cmap)
    c = colormap(np.linspace(0, 1, len(data.traninds)))
    ax.grid(True, linestyle='--')

    for ind in (data.traninds):
        ii = ind-data.traninds[0]
        row = data.df[data.didvinds].iloc[ind]

        didvobj = row.didvobj_p
        ## don't plot points with huge errors
        goodinds=np.abs(didvobj._didvmean/didvobj._didvstd) > 2.0
        fitinds = (didvobj._freq>0)# & (didvobj._freq<3e4)
        plotinds= np.logical_and(fitinds, goodinds)
        best_time_offset = didvobj._get_best_time_offset()

        time_phase = np.exp(2.0j * np.pi * best_time_offset * didvobj._freq)

        
        ax.plot(
            np.real((didvobj._didvmean * time_phase))[plotinds]*1e3,
            np.imag((didvobj._didvmean * time_phase))[plotinds]*1e3,
            linestyle=' ',
            marker ='.',
            alpha = 1,
            ms=2,
            zorder=10,
            color=c[ii],
        )
        key = 'params'
        didvfit2_freqdomain = qp.complexadmittance(
            didvobj._freq, **didvobj._2poleresult[key],
        )

        didvfit3_freqdomain = qp.complexadmittance(
            didvobj._freq, **didvobj._3poleresult[key],
        )

        ax.plot(
            np.real(didvfit2_freqdomain)[fitinds]*1e3,
            np.imag(didvfit2_freqdomain)[fitinds]*1e3,
            color=c[ii],
            linestyle='--',
            zorder = 400,
            linewidth=1.4,
            label='Simple Model',
        )
        ax.plot(
            np.real(didvfit3_freqdomain)[fitinds]*1e3,
            np.imag(didvfit3_freqdomain)[fitinds]*1e3,
            color=c[ii],
            linestyle='-',
            zorder = 500,
            linewidth=1.4,
            label='2-Block Model',
        )

    scalarmappaple = cm.ScalarMappable(norm=normalize, cmap=colormap)
    scalarmappaple.set_array(qets[:-1])
    cbar = plt.colorbar(scalarmappaple)
    cbar.set_label('QET Bias [μA]', labelpad=3) 

    return fig, ax

def _plot_ztes_bias(data, xlims=(-110,110), ylims=(-120,0), cmap='magma_r'):
    """
    Helper function to plot the imaginary vs real part of the complex
    impedance for different QET bias values for an IVanalysis object.

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
    fig : matplotlib.Figure
        Figure object for plot.
    ax : matplotlib.Axes
        Axes object for plot.

    """

    fig, ax = plt.subplots(figsize=(10,6))
    ax.set_xlabel('Re($Z_{TES}$) ($\Omega$)')
    ax.set_ylabel('Im($Z_{TES}$) ($\Omega$)')

    ax.set_title("Real and Imaginary Complex Impedance")
    ax.tick_params(which='both', direction='in', right=True, top=True)
    ax.grid(which='major')
    ax.grid(which='minor',linestyle='dotted',alpha=0.3)
    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    qets = np.abs(
        data.df.loc[data.didvinds, 'qetbias'].iloc[data.traninds].values
    )*1e6

    normalize = mcolors.Normalize(vmin=min(qets), vmax=max(qets))
    colormap = plt.get_cmap(cmap)
    c = colormap(np.linspace(0, 1, len(data.traninds)))
    ax.grid(True, linestyle='--')

    for ind in (data.traninds):
        ii = ind-data.traninds[0]
        row = data.df[data.didvinds].iloc[ind]

        didvobj = row.didvobj_p
        ## don't plot points with huge errors
        goodinds=np.abs(didvobj._didvmean/didvobj._didvstd) > 2.0
        fitinds = (didvobj._freq>0)# & (didvobj._freq<3e4)
        plotinds= np.logical_and(fitinds, goodinds)
        best_time_offset = didvobj._get_best_time_offset()

        time_phase = np.exp(2.0j * np.pi * best_time_offset * didvobj._freq)

        ax.plot(
            np.real(1/(didvobj._didvmean * time_phase))[plotinds]*1e3,
            np.imag(1/(didvobj._didvmean * time_phase))[plotinds]*1e3,
            linestyle=' ',
            marker='.',
            alpha=1,
            ms=2,
            zorder=10,
            color=c[ii],
        )
        key = 'params'
        didvfit2_freqdomain = qp.complexadmittance(
            didvobj._freq, **didvobj._2poleresult[key],
        )

        didvfit3_freqdomain = qp.complexadmittance(
            didvobj._freq, **didvobj._3poleresult[key],
        )

        ax.plot(
            np.real(1/didvfit2_freqdomain)[fitinds]*1e3,
            np.imag(1/didvfit2_freqdomain)[fitinds]*1e3,
            color=c[ii],
            linestyle='--',
            zorder=400,
            linewidth=1.4,
            label='Simple Model',
        )
        ax.plot(
            np.real(1/didvfit3_freqdomain)[fitinds]*1e3,
            np.imag(1/didvfit3_freqdomain)[fitinds]*1e3,
            color=c[ii],
            linestyle='-',
            zorder=500,
            linewidth=1.4,
            label='2-Block Model',
        )


    scalarmappaple = cm.ScalarMappable(norm=normalize, cmap=colormap)
    scalarmappaple.set_array(qets[:-1])
    cbar = plt.colorbar(scalarmappaple)
    cbar.set_label('QET Bias [μA]', labelpad=3) 

    return fig, ax


def _plot_noise_model(data, idx='all', xlims=(10, 2e5), ylims_current=None,
                      ylims_power=None):
    """
    Function to plot noise models with errors for IVanalysis object.

    Paramters
    ---------
    data : IVanalysis object
        The IVanalysis object to plot.
    idx : range, str, optional
        The range of indeces to plot. Must be either a range() object
        or 'all'. If 'all', it defaults to all the transistion data.
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

    noise = data.noise_model
    if idx == 'all':
        inds = data.traninds
    else:
        inds = idx

    for ind in inds:
        if idx == 'all':
            ii = ind - data.traninds[0]
        else:
            ii = ind - idx[0]
        noise_row = data.df[data.noiseinds].iloc[ind]
        r0 = noise_row.r0
        f = noise_row.f
        psd = noise_row.psd
        didvobj = noise_row.didvobj_p

        freqs = f[1:]
        psd = psd[1:]

        fig, ax = plt.subplots(1,1, figsize=(11,6))
        if ylims_current is not None:
            ax.set_ylim(ylims_current)
        if xlims is not None:
            ax.set_xlim(xlims)


        ax.grid(which="major", linestyle='--')
        ax.grid(which="minor", linestyle="dotted", alpha=0.5)
        ax.tick_params(which="both", direction="in", right=True, top=True)
        ax.set_xlabel(r'Frequency [Hz]')

        ax.set_title(f"Current Noise For $R_0$ : {r0*1e3:.2f} $m\Omega$")
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['ites'][0][ii])),
            color='#1f77b4',
            linewidth=1.5,
            label='TES Johnson Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['ites'][1][ii])),
            np.sqrt(np.abs(data.noise_model['ites'][2][ii])),
            alpha=.5,
            color='#1f77b4',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['iload'][0][ii])),
            color='#ff7f0e',
            linewidth=1.5,
            label='Load Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['iload'][1][ii])),
            np.sqrt(np.abs(data.noise_model['iload'][2][ii])),
            alpha=.5,
            color='#ff7f0e',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['itfn'][0][ii])),
            color='#2ca02c',
            linewidth=1.5,
            label='TFN Noise'
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['itfn'][1][ii])),
            np.sqrt(np.abs(data.noise_model['itfn'][2][ii])),
            alpha=.5,
            color='#2ca02c',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['itot'][0][ii])),
            color='#d62728',
            linewidth=1.5,
            label='Total Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['itot'][1][ii])),
            np.sqrt(np.abs(data.noise_model['itot'][2][ii])),
            alpha=.5,
            color='#d62728',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['isquid'][0][ii])),
            color='#9467bd',
            linewidth=1.5,
            label='Squid & Electronics Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['isquid'][1][ii])),
            np.sqrt(np.abs(data.noise_model['isquid'][2][ii])),
            alpha=.5,
            color='#9467bd',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(psd)),
            color='#8c564b',
            alpha=0.8,
            label='Raw Data',
        )
        ax.set_ylabel(
            r'Input Referenced Current Noise [A/$\sqrt{\mathrm{Hz}}$]'
        )

        lgd = plt.legend(loc='upper right')

        fig, ax = plt.subplots(1,1, figsize=(11,6))
        if ylims_power is not None:
            ax.set_ylim(ylims_power)
        if xlims is not None:
            ax.set_xlim(xlims)


        ax.grid(which="major", linestyle='--')
        ax.grid(which="minor", linestyle="dotted", alpha=0.5)
        ax.tick_params(which="both", direction="in", right=True, top=True)
        ax.set_xlabel(r'Frequency [Hz]')

        ax.set_title(f"Power Noise For $R_0$ : {r0*1e3:.2f} $m\Omega$")
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptes'][0][ii])),
            color='#1f77b4',
            linewidth=1.5,
            label='TES Johnson Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptes'][1][ii])),
            np.sqrt(np.abs(data.noise_model['ptes'][2][ii])),
            alpha=.5,
            color='#1f77b4',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['pload'][0][ii])),
            color='#ff7f0e',
            linewidth=1.5,
            label='Load Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['pload'][1][ii])),
            np.sqrt(np.abs(data.noise_model['pload'][2][ii])),
            alpha=.5,
            color='#ff7f0e',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptfn'][0][ii])),
            color='#2ca02c',
            linewidth=1.5,
            label='TFN Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptfn'][1][ii])),
            np.sqrt(np.abs(data.noise_model['ptfn'][2][ii])),
            alpha=.5,
            color='#2ca02c',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptot'][0][ii])),
            color='#d62728',
            linewidth=1.5,
            label='Total Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['ptot'][1][ii])),
            np.sqrt(np.abs(data.noise_model['ptot'][2][ii])),
            alpha=.5,
            color='#d62728',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['psquid'][0][ii])),
            color='#9467bd',
            linewidth=1.5,
            label='Squid & Electronics Noise',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['psquid'][1][ii])),
            np.sqrt(np.abs(data.noise_model['psquid'][2][ii])),
            alpha=.5,
            color='#9467bd',
        )
        ax.loglog(
            freqs,
            np.sqrt(np.abs(data.noise_model['s_psd'][0][ii])),
            color='#8c564b',
            alpha=0.8,
            label='Raw Data',
        )
        ax.fill_between(
            freqs,
            np.sqrt(np.abs(data.noise_model['s_psd'][1][ii])),
            np.sqrt(np.abs(data.noise_model['s_psd'][2][ii])),
            alpha=.5,
            color='#8c564b',
        )
        ax.set_ylabel(
            r'Input Referenced Power Noise [W/$\sqrt{\mathrm{Hz}}$]'
        )

        lgd = plt.legend(loc='upper right')
