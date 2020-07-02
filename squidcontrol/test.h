
/*!
 * MA_read_AGain
 */
void __stdcall MA_read_AGain(uint16_t channel_no, uint16_t *error, 
	uint16_t *again);
/*!
 * MA_read_Amp
 */
void __stdcall MA_read_Amp(uint16_t channel_no, uint16_t *error, 
	uint16_t *ampfll);
/*!
 * MA_read_AmpMode
 */
void __stdcall MA_read_AmpMode(uint16_t channel_no, uint16_t *error, 
	uint16_t *amp_gain, uint16_t *amp_bw);
/*!
 * MA_read_AVb
 */
void __stdcall MA_read_AVb(uint16_t channel_no, uint16_t *error, 
	double avbo_ranges[], int32_t len, double *avbo, uint16_t *avb_mode);
/*!
 * MA_read_brm
 */
void __stdcall MA_read_brm(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *fb, uint16_t *biasmode);
/*!
 * MA_read_DAuxMode
 */
void __stdcall MA_read_DAuxMode(uint16_t channel_no, uint16_t *error, 
	uint16_t *dauxmode);
/*!
 * MA_read_ExtFluxAmp
 */
void __stdcall MA_read_ExtFluxAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t *extfluxamp);
/*!
 * MA_read_ExtFluxFLL
 */
void __stdcall MA_read_ExtFluxFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t *extfluxfll);
/*!
 * MA_read_ExtFluxTerm
 */
void __stdcall MA_read_ExtFluxTerm(uint16_t channel_no, uint16_t *error, 
	uint16_t *extfluxterm);
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
 * MA_read_HeaterParam
 */
void __stdcall MA_read_HeaterParam(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, uint16_t *pwm_onoff, double *pwm, 
	uint16_t *jj_heater, double *heating_time);
/*!
 * MA_read_InTermAmp
 */
void __stdcall MA_read_InTermAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t *intermamp);
/*!
 * MA_read_InTermFLL
 */
void __stdcall MA_read_InTermFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t *intermfll);
/*!
 * MA_read_IntMode
 */
void __stdcall MA_read_IntMode(uint16_t channel_no, uint16_t *error, 
	uint16_t *intmode);
/*!
 * MA_read_IntRes
 */
void __stdcall MA_read_IntRes(uint16_t channel_no, uint16_t *error, 
	uint16_t *intres);
/*!
 * MA_read_LineShunt
 */
void __stdcall MA_read_LineShunt(uint16_t channel_no, uint16_t *error, 
	uint16_t *linesh);
/*!
 * MA_read_LNCSBW
 */
void __stdcall MA_read_LNCSBW(uint16_t channel_no, uint16_t *error, 
	uint16_t *lncsbw, uint16_t *lncsfs);
/*!
 * MA_read_nV2
 */
void __stdcall MA_read_nV2(uint16_t channel_no, uint16_t *error, double *nv2);
/*!
 * MA_read_nV3
 */
void __stdcall MA_read_nV3(uint16_t channel_no, uint16_t *error, double *nv3);
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
 * MA_read_pV2
 */
void __stdcall MA_read_pV2(uint16_t channel_no, uint16_t *error, double *pv2);
/*!
 * MA_read_pV3
 */
void __stdcall MA_read_pV3(uint16_t channel_no, uint16_t *error, double *pv3);
/*!
 * MA_read_Res
 */
void __stdcall MA_read_Res(uint16_t channel_no, uint16_t *error, 
	uint16_t *raux, uint16_t *rh, uint32_t *rf);
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
 * MA_read_SEL_Vb
 */
void __stdcall MA_read_SEL_Vb(uint16_t channel_no, uint16_t *error, 
	double *vb);
/*!
 * MA_read_SetToZero
 */
void __stdcall MA_read_SetToZero(uint16_t channel_no, uint16_t *error, 
	uint16_t *ib, uint16_t *vb, uint16_t *phibsel, uint16_t *phiob, 
	uint16_t *iaux, uint16_t *phix);
/*!
 * MA_read_slave
 */
void __stdcall MA_read_slave(uint16_t channel_no, uint16_t *error, 
	uint16_t *slave);
/*!
 * MA_read_SGain
 */
void __stdcall MA_read_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t *sgain);
/*!
 * MA_read_SourceRangeMode
 */
void __stdcall MA_read_SourceRangeMode(uint16_t channel_no, uint16_t *error, 
	uint16_t *source_range);
/*!
 * MA_read_State
 */
void __stdcall MA_read_State(uint16_t channel_no, uint16_t *error, 
	uint8_t state[], int32_t len);
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
 * MA_read_Vo
 */
void __stdcall MA_read_Vo(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *vo);
/*!
 * MA_read_Vop
 */
void __stdcall MA_read_Vop(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *vop);
/*!
 * MA_read_Vout
 */
void __stdcall MA_read_Vout(uint16_t channel_no, uint16_t *error, 
	double *vout);
/*!
 * MA_read_Wiring
 */
void __stdcall MA_read_Wiring(uint16_t channel_no, uint16_t *error, 
	uint16_t *wire);
/*!
 * MA_read_XXF_V1
 */
void __stdcall MA_read_XXF_V1(uint16_t channel_no, uint16_t *error, 
	double *v1);
/*!
 * MA_recall_from_EEPROM
 */
void __stdcall MA_recall_from_EEPROM(uint16_t channel_no, uint16_t *error, 
	uint16_t selector);
/*!
 * MA_reset_uC
 */
void __stdcall MA_reset_uC(uint16_t channel_no, uint16_t *error);
/*!
 * MA_save_to_EEPROM
 */
void __stdcall MA_save_to_EEPROM(uint16_t channel_no, uint16_t *error, 
	uint16_t selector);
/*!
 * MA_set_RL_Iaux
 */
void __stdcall MA_set_RL_Iaux(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_sleep_mode
 */
void __stdcall MA_sleep_mode(uint16_t channel_no, uint16_t *error);
/*!
 * MA_write_AGain
 */
void __stdcall MA_write_AGain(uint16_t channel_no, uint16_t *error, 
	uint16_t again);
/*!
 * MA_write_Amp
 */
void __stdcall MA_write_Amp(uint16_t channel_no, uint16_t *error, 
	uint16_t ampfll);
/*!
 * MA_write_AmpMode
 */
void __stdcall MA_write_AmpMode(uint16_t channel_no, uint16_t *error, 
	uint16_t amp_gain, uint16_t amp_bw);
/*!
 * MA_write_AVb
 */
void __stdcall MA_write_AVb(uint16_t channel_no, uint16_t *error, 
	double avbo_in, uint16_t avb_mode_in, double *avbo_out);
/*!
 * MA_write_Baudrate
 */
void __stdcall MA_write_Baudrate(uint16_t channel_no, uint16_t *error, 
	uint32_t baudrate_in);
/*!
 * MA_write_brm
 */
void __stdcall MA_write_brm(uint16_t channel_no, uint16_t *error, 
	uint16_t biasmode_in, double fb_in, double *fb_out);
/*!
 * MA_write_DAuxMode
 */
void __stdcall MA_write_DAuxMode(uint16_t channel_no, uint16_t *error, 
	uint16_t dauxmode);
/*!
 * MA_write_ExtFluxAmp
 */
void __stdcall MA_write_ExtFluxAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t extfluxamp);
/*!
 * MA_write_ExtFluxFLL
 */
void __stdcall MA_write_ExtFluxFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t extfluxfll);
/*!
 * MA_write_ExtFluxTerm
 */
void __stdcall MA_write_ExtFluxTerm(uint16_t channel_no, uint16_t *error, 
	uint16_t extfluxterm);
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
 * MA_write_HeaterParam
 */
void __stdcall MA_write_HeaterParam(uint16_t channel_no, uint16_t *error, 
	double pwm, uint16_t pwm_onoff, uint16_t jj_heater, double heating_time_in, 
	double *heating_time_out);
/*!
 * MA_write_InTermAmp
 */
void __stdcall MA_write_InTermAmp(uint16_t channel_no, uint16_t *error, 
	uint16_t intermamp);
/*!
 * MA_write_InTermFLL
 */
void __stdcall MA_write_InTermFLL(uint16_t channel_no, uint16_t *error, 
	uint16_t intermfll);
/*!
 * MA_write_IntMode
 */
void __stdcall MA_write_IntMode(uint16_t channel_no, uint16_t *error, 
	uint16_t intmode);
/*!
 * MA_write_IntRes
 */
void __stdcall MA_write_IntRes(uint16_t channel_no, uint16_t *error, 
	uint16_t intres);
/*!
 * MA_write_LineShunt
 */
void __stdcall MA_write_LineShunt(uint16_t channel_no, uint16_t *error, 
	uint16_t linesh);
/*!
 * MA_write_LNCSBW
 */
void __stdcall MA_write_LNCSBW(uint16_t channel_no, uint16_t *error, 
	uint16_t lncsbw, uint16_t lncsfs);
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
 * MA_write_Res
 */
void __stdcall MA_write_Res(uint16_t channel_no, uint16_t *error, 
	uint16_t raux, uint16_t rh, uint32_t rf, uint32_t *rfOut);
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
 * MA_write_SetToZero
 */
void __stdcall MA_write_SetToZero(uint16_t channel_no, uint16_t *error, 
	uint16_t ib, uint16_t vb, uint16_t phibsel, uint16_t phiob, uint16_t iaux, 
	uint16_t phix);
/*!
 * MA_write_SGain
 */
void __stdcall MA_write_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t sgain);
/*!
 * MA_write_slave
 */
void __stdcall MA_write_slave(uint16_t channel_no, uint16_t *error, 
	uint16_t slave_in);
/*!
 * MA_write_SourceRangeMode
 */
void __stdcall MA_write_SourceRangeMode(uint16_t channel_no, uint16_t *error, 
	uint16_t source_range);
/*!
 * MA_write_State
 */
void __stdcall MA_write_State(uint16_t channel_no, uint16_t *error, 
	uint8_t state[], int32_t len);
/*!
 * MA_write_Vo
 */
void __stdcall MA_write_Vo(uint16_t channel_no, uint16_t *error, 
	double vo_in, double *vo_out);
/*!
 * MA_write_Vop
 */
void __stdcall MA_write_Vop(uint16_t channel_no, uint16_t *error, 
	double vop_in, double *vop_out);
/*!
 * MA_write_Wiring
 */
void __stdcall MA_write_Wiring(uint16_t channel_no, uint16_t *error, 
	uint16_t wire);
