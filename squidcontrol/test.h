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
 * MA_set_RL_Iaux
 */
void __stdcall MA_set_RL_Iaux(uint16_t channel_no, uint16_t *error, 
	double iaux_rl);
/*!
 * MA_write_SGain
 */
void __stdcall MA_write_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t sgain);

