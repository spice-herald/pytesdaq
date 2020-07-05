#include "extcode.h"
#pragma pack(push)
#pragma pack(1)

#ifdef __cplusplus
extern "C" {
#endif

/*!
 * MA_closeUSB
 */
void __stdcall MA_closeUSB(uint16_t *error);
/*!
 * MA_initUSB
 */
void __stdcall MA_initUSB(uint16_t *error, uint32_t baudrate_usb, 
	uint32_t timeout_usb);
/*!
 * MA_read_Dummy
 */
void __stdcall MA_read_Dummy(uint16_t channel_no, uint16_t *error, 
	uint16_t *dummy);
/*!
 * MA_read_Io
 */
void __stdcall MA_read_Io(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *io);
/*!
 * MA_channelInfo
 */
void __stdcall MA_channelInfo(uint16_t channel_no, uint16_t *error, 
	uint16_t *type_id, uint16_t *version_id, uint16_t *board_id, 
	uint16_t *case_id);
/*!
 * MA_clear_OvlCount
 */
void __stdcall MA_clear_OvlCount(uint16_t channel_no, uint16_t *error);
/*!
 * MA_closeCOM
 */
void __stdcall MA_closeCOM(uint16_t *error);
/*!
 * MA_CSE_read_Amp
 */
void __stdcall MA_CSE_read_Amp(uint16_t channel_no, uint16_t *error, 
	uint16_t *amp);
/*!
 * MA_CSE_read_Iaux1
 */
void __stdcall MA_CSE_read_Iaux1(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *iaux1);
/*!
 * MA_CSE_read_Iaux2
 */
void __stdcall MA_CSE_read_Iaux2(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *iaux2);
/*!
 * MA_CSE_read_Iaux2_Discon
 */
void __stdcall MA_CSE_read_Iaux2_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t *iaux2discon);
/*!
 * MA_CSE_read_LNCS
 */
void __stdcall MA_CSE_read_LNCS(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *lncs);
/*!
 * MA_CSE_read_LNCS_BW
 */
void __stdcall MA_CSE_read_LNCS_BW(uint16_t channel_no, uint16_t *error, 
	uint16_t *lncsbw);
/*!
 * MA_CSE_read_LNCS_Discon
 */
void __stdcall MA_CSE_read_LNCS_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t *lncsdiscon);
/*!
 * MA_CSE_read_LNCS_FS
 */
void __stdcall MA_CSE_read_LNCS_FS(uint16_t channel_no, uint16_t *error, 
	uint16_t *lncsfs);
/*!
 * MA_CSE_read_SetToZero
 */
void __stdcall MA_CSE_read_SetToZero(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes1iaux, uint16_t *tes1phix, uint16_t *tes2iaux, 
	uint16_t *tes2phix, uint16_t *iaux1, uint16_t *iaux2, uint16_t *lncs);
/*!
 * MA_CSE_read_State
 */
void __stdcall MA_CSE_read_State(uint16_t channel_no, uint16_t *error, 
	uint8_t state[], int32_t len);
/*!
 * MA_CSE_read_TES1_Discon
 */
void __stdcall MA_CSE_read_TES1_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes1discon);
/*!
 * MA_CSE_read_TES1_I
 */
void __stdcall MA_CSE_read_TES1_I(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *tes1i);
/*!
 * MA_CSE_read_TES1_Irange
 */
void __stdcall MA_CSE_read_TES1_Irange(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes1irange);
/*!
 * MA_CSE_read_TES1_Phix
 */
void __stdcall MA_CSE_read_TES1_Phix(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *tes1phix);
/*!
 * MA_CSE_read_TES1mode
 */
void __stdcall MA_CSE_read_TES1mode(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes1mode);
/*!
 * MA_CSE_read_TES2_Discon
 */
void __stdcall MA_CSE_read_TES2_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes2discon);
/*!
 * MA_CSE_read_TES2_I
 */
void __stdcall MA_CSE_read_TES2_I(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *tes2i);
/*!
 * MA_CSE_read_TES2_Irange
 */
void __stdcall MA_CSE_read_TES2_Irange(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes2irange);
/*!
 * MA_CSE_read_TES2_Phix
 */
void __stdcall MA_CSE_read_TES2_Phix(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *tes2phix);
/*!
 * MA_CSE_read_TES2mode
 */
void __stdcall MA_CSE_read_TES2mode(uint16_t channel_no, uint16_t *error, 
	uint16_t *tes2mode);
/*!
 * MA_CSE_set_RL_Iaux1
 */
void __stdcall MA_CSE_set_RL_Iaux1(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_CSE_set_RL_Iaux2
 */
void __stdcall MA_CSE_set_RL_Iaux2(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_CSE_set_RL_TES1
 */
void __stdcall MA_CSE_set_RL_TES1(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_CSE_set_RL_TES2
 */
void __stdcall MA_CSE_set_RL_TES2(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_CSE_write_Amp
 */
void __stdcall MA_CSE_write_Amp(uint16_t channel_no, uint16_t *error, 
	uint16_t amp);
/*!
 * MA_CSE_write_Iaux1
 */
void __stdcall MA_CSE_write_Iaux1(uint16_t channel_no, uint16_t *error, 
	double iaux1_in, double *iaux1_out);
/*!
 * MA_CSE_write_Iaux2
 */
void __stdcall MA_CSE_write_Iaux2(uint16_t channel_no, uint16_t *error, 
	double iaux2_in, double *iaux2_out);
/*!
 * MA_CSE_write_Iaux2_Discon
 */
void __stdcall MA_CSE_write_Iaux2_Discon(uint16_t channel_no, 
	uint16_t *error, uint16_t iaux2discon);
/*!
 * MA_CSE_write_LNCS
 */
void __stdcall MA_CSE_write_LNCS(uint16_t channel_no, uint16_t *error, 
	double lncs_in, double *lncs_out);
/*!
 * MA_CSE_write_LNCS_BW
 */
void __stdcall MA_CSE_write_LNCS_BW(uint16_t channel_no, uint16_t *error, 
	uint16_t lncsbw);
/*!
 * MA_CSE_write_LNCS_Discon
 */
void __stdcall MA_CSE_write_LNCS_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t lncsdiscon);
/*!
 * MA_CSE_write_LNCS_FS
 */
void __stdcall MA_CSE_write_LNCS_FS(uint16_t channel_no, uint16_t *error, 
	uint16_t lncsfs);
/*!
 * MA_CSE_write_SetToZero
 */
void __stdcall MA_CSE_write_SetToZero(uint16_t channel_no, uint16_t *error, 
	uint16_t tes1iaux, uint16_t tes1phix, uint16_t tes2iaux, uint16_t tes2phix, 
	uint16_t iaux1, uint16_t iaux2, uint16_t lncs);
/*!
 * MA_CSE_write_State
 */
void __stdcall MA_CSE_write_State(uint16_t channel_no, uint16_t *error, 
	uint8_t state[], int32_t len);
/*!
 * MA_CSE_write_TES1_Discon
 */
void __stdcall MA_CSE_write_TES1_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t tes1discon);
/*!
 * MA_CSE_write_TES1_I
 */
void __stdcall MA_CSE_write_TES1_I(uint16_t channel_no, uint16_t *error, 
	double tes1i_in, double *tes1i_out);
/*!
 * MA_CSE_write_TES1_Irange
 */
void __stdcall MA_CSE_write_TES1_Irange(uint16_t channel_no, uint16_t *error, 
	uint16_t tes1irange);
/*!
 * MA_CSE_write_TES1_Phix
 */
void __stdcall MA_CSE_write_TES1_Phix(uint16_t channel_no, uint16_t *error, 
	double tes1phix_in, double *tes1phix_out);
/*!
 * MA_CSE_write_TES1mode
 */
void __stdcall MA_CSE_write_TES1mode(uint16_t channel_no, uint16_t *error, 
	uint16_t tes1mode);
/*!
 * MA_CSE_write_TES2_Discon
 */
void __stdcall MA_CSE_write_TES2_Discon(uint16_t channel_no, uint16_t *error, 
	uint16_t tes2discon);
/*!
 * MA_CSE_write_TES2_I
 */
void __stdcall MA_CSE_write_TES2_I(uint16_t channel_no, uint16_t *error, 
	double tes2i_in, double *tes2i_out);
/*!
 * MA_CSE_write_TES2_Irange
 */
void __stdcall MA_CSE_write_TES2_Irange(uint16_t channel_no, uint16_t *error, 
	uint16_t tes2irange);
/*!
 * MA_CSE_write_TES2_Phix
 */
void __stdcall MA_CSE_write_TES2_Phix(uint16_t channel_no, uint16_t *error, 
	double tes2phix_in, double *tes2phix_out);
/*!
 * MA_CSE_write_TES2mode
 */
void __stdcall MA_CSE_write_TES2mode(uint16_t channel_no, uint16_t *error, 
	uint16_t tes2mode);
/*!
 * MA_Heat
 */
void __stdcall MA_Heat(uint16_t channel_no, uint16_t *error);
/*!
 * MA_initCOM
 */
void __stdcall MA_initCOM(uint16_t *error, uint16_t com_number, 
	uint32_t baudrate_com, uint32_t timeout_com);
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
 * MA_read_Iaux
 */
void __stdcall MA_read_Iaux(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, uint16_t *iaux_range, double *iaux);
/*!
 * MA_read_Ib
 */
void __stdcall MA_read_Ib(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, uint16_t *ib_range, double *ib);
/*!
 * MA_read_IbDel
 */
void __stdcall MA_read_IbDel(uint16_t channel_no, uint16_t *error, 
	uint16_t *ibdel);
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
 * MA_read_IoAdj
 */
void __stdcall MA_read_IoAdj(uint16_t channel_no, uint16_t *error, 
	uint16_t *ioadj);
/*!
 * MA_read_IoTC
 */
void __stdcall MA_read_IoTC(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *iotc);
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
 * MA_read_OvlCount
 */
void __stdcall MA_read_OvlCount(uint16_t channel_no, uint16_t *error, 
	uint16_t *dfcn, uint16_t *dfcp, uint16_t *arn, uint16_t *arp, uint16_t *ovln, 
	uint16_t *ovlp);
/*!
 * MA_read_OvlParam
 */
void __stdcall MA_read_OvlParam(uint16_t channel_no, uint16_t *error, 
	double dfc_ranges[], double ovl_ranges[], int32_t len, double *dfc_thresh, 
	double *ar_thresh, double *ovl_thresh, uint16_t *ovl_mode);
/*!
 * MA_read_Phib
 */
void __stdcall MA_read_Phib(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *phib);
/*!
 * MA_read_PhibDisc
 */
void __stdcall MA_read_PhibDisc(uint16_t channel_no, uint16_t *error, 
	uint16_t *phibdisc);
/*!
 * MA_read_Phiob
 */
void __stdcall MA_read_Phiob(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *phiob);
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
 * MA_read_Vb
 */
void __stdcall MA_read_Vb(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *vb);
/*!
 * MA_read_VbDel
 */
void __stdcall MA_read_VbDel(uint16_t channel_no, uint16_t *error, 
	uint16_t *vbdel);
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
 * MA_read_VoTC
 */
void __stdcall MA_read_VoTC(uint16_t channel_no, uint16_t *error, 
	double ranges[], int32_t len, double *votc);
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
 * MA_SetActiveChannel
 */
void __stdcall MA_SetActiveChannel(uint16_t channel_no, uint16_t *error);
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
 * MA_write_Dummy
 */
void __stdcall MA_write_Dummy(uint16_t channel_no, uint16_t *error, 
	uint16_t dummy);
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
 * MA_write_Iaux
 */
void __stdcall MA_write_Iaux(uint16_t channel_no, uint16_t *error, 
	double iaux_in, uint16_t iaux_range, double *iaux_out);
/*!
 * MA_write_Ib
 */
void __stdcall MA_write_Ib(uint16_t channel_no, uint16_t *error, 
	double ib_in, uint16_t ib_range, double *ib_out);
/*!
 * MA_write_IbDel
 */
void __stdcall MA_write_IbDel(uint16_t channel_no, uint16_t *error, 
	uint16_t ibdel);
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
 * MA_write_Io
 */
void __stdcall MA_write_Io(uint16_t channel_no, uint16_t *error, 
	double io_in, double *io_out);
/*!
 * MA_write_IoAdj
 */
void __stdcall MA_write_IoAdj(uint16_t channel_no, uint16_t *error, 
	uint16_t ioadj);
/*!
 * MA_write_IoTC
 */
void __stdcall MA_write_IoTC(uint16_t channel_no, uint16_t *error, 
	double iotc_inn, double *iotc_out);
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
 * MA_write_OvlParam
 */
void __stdcall MA_write_OvlParam(uint16_t channel_no, uint16_t *error, 
	uint16_t ovl_mode_in, double dfc_step_in, double dfc_thresh_in, 
	double ar_thresh_in, double ovl_thresh_in, double *dfc_step_out, 
	double *dfc_thresh_out, double *ar_thresh_out, double *ovl_thresh_out);
/*!
 * MA_write_Phib
 */
void __stdcall MA_write_Phib(uint16_t channel_no, uint16_t *error, 
	double phib_in, double *phib_out);
/*!
 * MA_write_PhibDisc
 */
void __stdcall MA_write_PhibDisc(uint16_t channel_no, uint16_t *error, 
	uint16_t phibdisc);
/*!
 * MA_write_Phiob
 */
void __stdcall MA_write_Phiob(uint16_t channel_no, uint16_t *error, 
	double phiob_in, double *phiob_out);
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
 * MA_write_Vb
 */
void __stdcall MA_write_Vb(uint16_t channel_no, uint16_t *error, 
	double vb_in, double *vb_out);
/*!
 * MA_write_VbDel
 */
void __stdcall MA_write_VbDel(uint16_t channel_no, uint16_t *error, 
	uint16_t vbdel);
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
 * MA_write_VoTC
 */
void __stdcall MA_write_VoTC(uint16_t channel_no, uint16_t *error, 
	double votc_in, double *votc_out);
/*!
 * MA_write_Wiring
 */
void __stdcall MA_write_Wiring(uint16_t channel_no, uint16_t *error, 
	uint16_t wire);
/*!
 * MA_CSE_K_read_sourcesetup
 */
void __stdcall MA_CSE_K_read_sourcesetup(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, uint16_t *resolution, double *min, 
	double *max);
/*!
 * MA_CSE_K_write_sourcesetup
 */
void __stdcall MA_CSE_K_write_sourcesetup(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, uint16_t resolution_in, double min_in, 
	double max_in);
/*!
 * MA_CSE_K_read_sourceswitch
 */
void __stdcall MA_CSE_K_read_sourceswitch(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, uint16_t *switch_out);
/*!
 * MA_CSE_K_write_sourceswitch
 */
void __stdcall MA_CSE_K_write_sourceswitch(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, uint16_t switch_in);
/*!
 * MA_CSE_K_read_sourcevalue
 */
void __stdcall MA_CSE_K_read_sourcevalue(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, double *i_out, double *p_out, 
	double *p_duration, double *p_pause, uint32_t *p_count);
/*!
 * MA_CSE_K_write_sourcevalue
 */
void __stdcall MA_CSE_K_write_sourcevalue(uint16_t channel_no, 
	uint16_t source_no, uint16_t *error, double i_in, double p_in, 
	double p_pause, double p_duration, uint32_t p_count, double *i_out, 
	double *p_out);
/*!
 * MA_channelInfo_2
 */
void __stdcall MA_channelInfo_2(uint16_t channel_no, uint16_t *error, 
	uint16_t *case_id, uint16_t *type_id, uint16_t *board_id, 
	uint16_t *version_id, uint8_t *status_flags, uint8_t *bl_flags);
/*!
 * MA_CSE_K_read_vshunt
 */
void __stdcall MA_CSE_K_read_vshunt(uint16_t channel_no, int16_t *error, 
	double *vshunt0, double *vshunt1, double *vshunt2, double *vshunt3, 
	double *vshunt4);

MgErr __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

#ifdef __cplusplus
} // extern "C"
#endif

#pragma pack(pop)

