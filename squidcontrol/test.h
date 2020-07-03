/*!
 * MA_read_GBP
 */
void __stdcall MA_read_GBP(uint16_t channel_no, uint16_t *error, 
	uint16_t *gbp);
/*!
 * MA_read_GenFreq
 */
void __stdcall MA_read_GenFreq(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *gen_freq);
/*!
 * MA_read_GenOnOff
 */
void __stdcall MA_read_GenOnOff(uint16_t channel_no, uint16_t *error, 
	uint16_t *gen1_onoff, uint16_t *gen2_onoff, uint16_t *mon_onoff);
/*!
 * MA_read_GenParam
 */
void __stdcall MA_read_GenParam(uint16_t channel_no, uint16_t *error, 
	uint16_t gen_no, double ranges[], int32_t len, uint16_t *wavef, 
	uint16_t *phase, uint16_t *freq_div, uint16_t *bipolar, uint16_t *source, 
	double *peakpeak);
/*!
 * MA_read_OutCoup
 */
void __stdcall MA_read_OutCoup(uint16_t channel_no, uint16_t *error, 
	uint16_t *outcoup);
/*!
 * MA_read_Phix
 */
void __stdcall MA_read_Phix(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *phix);
/*!
 * MA_read_PhixDisc
 */
void __stdcall MA_read_PhixDisc(uint16_t channel_no, uint16_t *error, 
	uint16_t *phixdisc);
/*!
 * MA_read_PulseOnOff
 */
void __stdcall MA_read_PulseOnOff(uint16_t channel_no, uint16_t *error, 
	uint16_t *pulse_onoff);
/*!
 * MA_read_PulseParam
 */
void __stdcall MA_read_PulseParam(uint16_t channel_no, uint16_t *error, 
	double time_ranges[], double dur_ranges[], int32_t len, uint16_t *mode, 
	double *time, double *duration);
/*!
 * MA_read_RfAmp
 */
void __stdcall MA_read_RfAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t *rfamp);
/*!
 * MA_read_RfFLL
 */
void __stdcall MA_read_RfFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t *rfffl);
/*!
 * MA_read_RfxAmp
 */
void __stdcall MA_read_RfxAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t *rfxamp);
/*!
 * MA_read_RfxFLL
 */
void __stdcall MA_read_RfxFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t *rfxfll);
/*!
 * MA_read_SGain
 */
void __stdcall MA_read_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t *sgain);
/*!
 * MA_read_Temp
 */
void __stdcall MA_read_Temp(uint16_t channel_no, uint16_t *error, 
	double *temp);
/*!
 * MA_read_V_Vb
 */
void __stdcall MA_read_V_Vb(uint16_t channel_no, uint16_t *error, 
	double *v_vb);
/*!
 * MA_read_Vout
 */
void __stdcall MA_read_Vout(uint16_t channel_no, uint16_t *error, 
	double *vout);
/*!
 * MA_set_RL_Iaux
 */
void __stdcall MA_set_RL_Iaux(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_write_GBP
 */
void __stdcall MA_write_GBP(uint16_t channel_no, uint16_t *error, 
	uint16_t gbp_in);
/*!
 * MA_write_GenFreq
 */
void __stdcall MA_write_GenFreq(uint16_t channel_no, uint16_t *error, 
	double gen_freq_in, double *gen_freq_out);
/*!
 * MA_write_GenOnOff
 */
void __stdcall MA_write_GenOnOff(uint16_t channel_no, uint16_t *error, 
	uint16_t gen1_onoff, uint16_t gen2_onoff, uint16_t mon_onoff);
/*!
 * MA_write_GenParam
 */
void __stdcall MA_write_GenParam(uint16_t channel_no, uint16_t *error, 
	uint16_t gen_no, uint16_t wavef, uint16_t source, double peakpeak_in, 
	uint16_t phase, uint16_t freq_div, uint16_t bipolar, double *peakpeak_out);
/*!
 * MA_write_OutCoup
 */
void __stdcall MA_write_OutCoup(uint16_t channel_no, uint16_t *error, 
	uint16_t outcoup);
/*!
 * MA_write_PhiX
 */
void __stdcall MA_write_PhiX(uint16_t channel_no, uint16_t *error, 
	double phiX_in, double *phiX_out);
/*!
 * MA_write_PhixDisc
 */
void __stdcall MA_write_PhixDisc(uint16_t channel_no, uint16_t *error, 
	uint16_t phixdisc);
/*!
 * MA_write_PulseOnOff
 */
void __stdcall MA_write_PulseOnOff(uint16_t channel_no, uint16_t *error, 
	uint16_t pulse_onoff);
/*!
 * MA_write_PulseParam
 */
void __stdcall MA_write_PulseParam(uint16_t channel_no, uint16_t *error, 
	double duration_in, double time_in, uint16_t mode, double *duration_out, 
	double *time_out);
/*!
 * MA_write_RfAmp
 */
void __stdcall MA_write_RfAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t rfamp_in);
/*!
 * MA_write_RfFLL
 */
void __stdcall MA_write_RfFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t rffll_in);
/*!
 * MA_write_RfxAmp
 */
void __stdcall MA_write_RfxAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t rfxamp);
/*!
 * MA_write_RfxFLL
 */
void __stdcall MA_write_RfxFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t rfxfll);
/*!
 * MA_write_SGain
 */
void __stdcall MA_write_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t sgain);

