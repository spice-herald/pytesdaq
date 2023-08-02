import time
from pymeasure.instruments.keithley import Keithley2400

# Replace 'ASRLX::INSTR' with the actual resource name of your Keithley 2400
# For example, for a USB connection, it could be 'USB0::0x05E6::0x2400::XXXXXX::INSTR'
keithley = Keithley2400('ASRLX::INSTR')

# Open the connection to the instrument
keithley.open()

# Set the output mode to current and set the compliance voltage
keithley.measure_current()
keithley.compliance_voltage = 10  # Set the compliance voltage to 10V (adjust as needed)

# Set the current to the desired value in Amperes
desired_current = 0.001  # Set the desired current value (1mA in this case)
keithley.current = desired_current

# Enable the output
keithley.enable_output()

# Wait for a moment to stabilize (optional)
time.sleep(2)

# Perform any desired measurements or operations here...

# Disable the output and close the connection
keithley.disable_output()
keithley.close()
