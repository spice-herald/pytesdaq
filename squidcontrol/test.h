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
 * MA_write_SGain
 */
void __stdcall MA_write_SGain(uint16_t channel_no, uint16_t *error, 
	uint16_t sgain);

