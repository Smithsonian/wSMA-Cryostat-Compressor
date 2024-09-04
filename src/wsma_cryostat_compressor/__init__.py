__version__ = '0.2.0'

import os
from time import sleep

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from . import inverter

default_IP = os.environ.get("COMPRESSOR_IP", None)
default_port = os.environ.get("COMPRESSOR_PORT", 502)


def _status_to_string(status_code):
    """Translate compressor status code to a human readable string.

    Args:
        status_code: in: the status returned by the compressor.
    Returns:
        str: status message."""
    str_return = 'Unknown State'
    if 0 == status_code:
        str_return = 'Ready to start'
    elif 2 == status_code:
        str_return = 'Starting'
    elif 3 == status_code:
        str_return = 'Running'
    elif 5 == status_code:
        str_return = 'Stopping'
    elif 6 == status_code:
        str_return = 'Error Lockout'
    elif 7 == status_code:
        str_return = 'Error'
    elif 8 == status_code:
        str_return = 'Helium Overtemp: waiting to cool down'
    elif 9 == status_code:
        str_return = 'Power Related Error'
    elif 15 == status_code:
        str_return = 'Recovered From Error'
    return str_return


def _error_code_to_string(error_code):
    """Translate compressor error or warning status code to a human readable string.

    Args:
        error_code: int: the error/warning code returned by the compressor.
    Returns:
        str: error message."""
    str_return = '   '
    # Deal with the fact that version 3 and version 2 software use opposite signs
    # on error codes
    if error_code > 0:
        worker = -error_code
    else:
        worker = error_code
    
    if -1073741824 >= worker:
        str_return += "Inverter Comm Loss, "
        worker -= -1073741824
    if -536870912 >= worker:
        str_return += "Driver Comm Loss, "
        worker -= -536870912
    if -268435456 >= worker:
        str_return += "Inverter Error, "
        worker -= -268435456
    if -134217728 >= worker:
        str_return += "Motor Current High, "
        worker -= -134217728
    if -67108864 >= worker:
        str_return += "Motor Current Sensor, "
        worker -= -67108864
    if -33554432 >= worker:
        str_return += "Low Pressure Sensor, "
        worker -= -33554432
    if -16777216 >= worker:
        str_return += "High Pressure Sensor, "
        worker -= -16777216
    if -8388608 >= worker:
        str_return += "Oil Sensor, "
        worker -= -8388608
    if -4194304 >= worker:
        str_return += "Helium Sensor, "
        worker -= -4194304
    if -2097152 >= worker:
        str_return += "Coolant Out Sensor, "
        worker -= -2097152
    if -1048576 >= worker:
        str_return += "Coolant In Sensor, "
        worker -= -1048576
    if -524288 >= worker:
        str_return += "Cold Head Motor Stall, "
        worker -= -524288
    if -262144 >= worker:
        str_return += "Static Pressure Low, "
        worker -= -262144
    if -131072 >= worker:
        str_return += "Static Pressure High, "
        worker -= -131072
    if -65536 >= worker:
        str_return += "Power Supply Error, "
        worker -= -65536
    if -32768 >= worker:
        str_return += "Three Phase Error, "
        worker -= -32768
    if -16384 >= worker:
        str_return += "Motor Current Low, "
        worker -= -16384
    if -8192 >= worker:
        str_return += "Delta Pressure Low, "
        worker -= -8192
    if -4096 >= worker:
        str_return += "Delta Pressure High, "
        worker -= -4096
    if -2048 >= worker:
        str_return += "High Pressure Low, "
        worker -= -2048
    if -1024 >= worker:
        str_return += "High Pressure High, "
        worker -= -1024
    if -512 >= worker:
        str_return += "Low Pressure Low, "
        worker -= -512
    if -256 >= worker:
        str_return += "Low Pressure High, "
        worker -= -256
    if -128 >= worker:
        str_return += "Helium Low, "
        worker -= -128
    if -64 >= worker:
        str_return += "Helium High, "
        worker -= -64
    if -32 >= worker:
        str_return += "Oil Low, "
        worker -= -32
    if -16 >= worker:
        str_return += "Oil High, "
        worker -= -16
    if -8 >= worker:
        str_return += "Coolant Out Low, "
        worker -= -8
    if -4 >= worker:
        str_return += "Coolant Out High, "
        worker -= -4
    if -2 >= worker:
        str_return += "Coolant In Low, "
        worker -= -2
    if -1 >= worker:
        str_return += "Coolant In High, "
        worker -= -1
    # remove the final space & Comma if we have a message
    if 0 < len(str_return.strip()):
        str_return = str_return.strip()
        str_return = str_return[0:len(str_return) - 1]
    else:
        str_return = 'None'
    return str_return


def _model_code_to_string(model_code):
    """Translate model code bytes to a human readable string.

    Args:
        model_code: int: the error/warning code returned by the compressor.
    Returns:
        str: Model name."""
    high_byte = model_code[0]
    low_byte = model_code[1]
    str_return = 'CPA'
    if 1 == high_byte:
        str_return = str_return + '08'
    elif 2 == high_byte:
        str_return = str_return + '09'
    elif 3 == high_byte:
        str_return = str_return + '10'
    elif 4 == high_byte:
        str_return = str_return + '11'
    elif 5 == high_byte:
        str_return = str_return + '28'

    if 1 == low_byte:
        str_return = str_return + 'A1'
    elif 2 == low_byte:
        str_return = str_return + '01'
    elif 3 == low_byte:
        str_return = str_return + '02'
    elif 4 == low_byte:
        str_return = str_return + '03'
    elif 5 == low_byte:
        str_return = str_return + 'H3'
    elif 6 == low_byte:
        str_return = str_return + 'I3'
    elif 7 == low_byte:
        str_return = str_return + '04'
    elif 8 == low_byte:
        str_return = str_return + 'H4'
    elif 9 == low_byte:
        str_return = str_return + '05'
    elif 10 == low_byte:
        str_return = str_return + 'H5'
    elif 11 == low_byte:
        str_return = str_return + 'I6'
    elif 12 == low_byte:
        str_return = str_return + '06'
    elif 13 == low_byte:
        str_return = str_return + '07'
    elif 14 == low_byte:
        str_return = str_return + 'H7'
    elif 15 == low_byte:
        str_return = str_return + 'I7'
    elif 16 == low_byte:
        str_return = str_return + '08'
    elif 17 == low_byte:
        str_return = str_return + '09'
    elif 18 == low_byte:
        str_return = str_return + '9C'
    elif 19 == low_byte:
        str_return = str_return + '10'
    elif 20 == low_byte:
        str_return = str_return + '1I'
    elif 21 == low_byte:
        str_return = str_return + '11'
    elif 22 == low_byte:
        str_return = str_return + '12'
    elif 23 == low_byte:
        str_return = str_return + '13'
    elif 24 == low_byte:
        str_return = str_return + '14'
    return str_return

cp_v2_registers = {
    #: int: address of the controller's operating state register (int16).
    "_operating_state_addr" : 1,
    #: int: address of the controller's energized state register (int16).
    "_enabled_addr" : 2,
    #: int: address of the inverter set frequency register (int, 1/10th Hz).
    "_inverter_set_freq_addr" : None,
    #: int: address of the controller's warning register (int32).
    "_warning_addr" : 3, # and 4
    #: int: address of the controller's alarm/error register (int32).
    "_error_addr" : 5, # and 6
    #: int: address of the controller's Coolant In Temp(erature) register (float32)
    "_coolant_in_addr" : 7, # and 8
    #: int: address of the controller's Coolant Out Temp(erature) register (float32)
    "_coolant_out_addr" : 9, # and 10
    #: int: address of the controller's Oil Temp(erature) register (float32)
    "_oil_temp_addr" : 11, # and 12
    #: int: address of the controller's Helium Temp(erature) register (float32)
    "_helium_temp_addr" : 13, # and 14
    #: int: address of the controller's Low Pressure register (float32)
    "_low_press_addr" : 15, # and 16
    #: int: address of the controller's Low Pressure Average register (float32)
    "_low_press_avg_addr" : 17, # and 18
    #: int: address of the controller's High Pressure register (float32)
    "_high_press_addr" : 19, # and 20
    #: int: address of the controller's High Pressure Average register (float32)
    "_high_press_avg_addr" : 21, # and 22
    #: int: address of the controller's Delta Pressure Average register (float32)
    "_delta_press_avg_addr" : 23, # and 24
    #: int: address of the controller's Motor Current register (float32)
    "_motor_current_addr" : 25, # and 26
    #: int: address of the controller's Hours of Operation register (float32, hours)
    "_hours_addr" : 27, # and 28
    #: int: address of the controller's Pressure Scale register
    "_press_unit_addr" : 29,
    #: int: address of the controller's Temperature Scale register
    "_temp_unit_addr" : 30,
    #: int: address of the remote motor detector RPM (int, 1/100th RPM)
    "_rpm_addr" : None,
    #: int: address of the software variant (int)
    "_software_var_addr" : None,
    #: int: address of the inverter frequency (int, 1/10th Hz)
    "_inverter_freq_addr" : None,
    #: int: address of the inverter current (int, 1/10th Amps)
    "_inverter_curr_addr" : None,
    #: int: address of the controller's Enable/Disable holding register
    "_enable_addr" : 1
}

cp_v3_registers = {
    #: int: address of the controller's operating state register (int16).
    "_operating_state_addr" : 1,
    #: int: address of the controller's energized state register (int16).
    "_enabled_addr" : 2,
    #: int: address of the controller's warning register (int32).
    "_warning_addr" : 52, # and 53
    #: int: address of the controller's alarm/error register (int32).
    "_error_addr" : 54, # and 55
    #: int: address of the controller's Coolant In Temp(erature) register (int16, 1/10th unit)
    "_coolant_in_addr" : 40,
    #: int: address of the controller's Coolant Out Temp(erature) register (int16, 1/10th unit)
    "_coolant_out_addr" : 41,
    #: int: address of the controller's Oil Temp(erature) register (int, 1/10th unit)
    "_oil_temp_addr" : 42,
    #: int: address of the controller's Helium Temp(erature) register (int, 1/10th unit)
    "_helium_temp_addr" : 43,
    #: int: address of the controller's Low Pressure register (int, 1/10th unit)
    "_low_press_addr" : 44,
    #: int: address of the controller's Low Pressure Average register (int, 1/10th unit)
    "_low_press_avg_addr" : 45,
    #: int: address of the controller's High Pressure register (int, 1/10th unit)
    "_high_press_addr" : 46,
    #: int: address of the controller's High Pressure Average register (int, 1/10th unit)
    "_high_press_avg_addr" : 47,
    #: int: address of the controller's Delta Pressure Average register (int, 1/10th unit)
    "_delta_press_avg_addr" : 48,
    #: int: address of the controller's Motor Current register (int, 1/10th)
    "_motor_current_addr" : 49,
    #: int: address of the controller's Hours of Operation register (int32, hours)
    "_hours_addr" : 50, # and 51
    #: int: address of the controller's Pressure Scale register
    "_press_unit_addr" : 29,
    #: int: address of the controller's Temperature Scale register
    "_temp_unit_addr" : 30,
    #: int: address of the remote motor detector RPM (int, 1/100th RPM)
    "_rpm_addr" : 34,
    #: int: address of the software variant (int)
    "_software_var_addr" : 35,
    #: int: address of the inverter frequency (int, 1/10th Hz)
    "_inverter_freq_addr" : 36,
    #: int: address of the inverter current (int, 1/10th Amps)
    "_inverter_curr_addr" : 37,
    
    #: int: address of the controller's Enable/Disable holding register (int)
    "_enable_addr" : 1,
    #: int: address of the inverter set frequency holding register (int16, 1/10th Hz).
    "_inverter_set_freq_addr" : 3
}

class Compressor(object):
    """Class for communicating with the wSMA Compressor controller.

    The Compressor object wraps a pymodbus.ModbusTcpClient instance which
    communicates with the Compressor Digital Panel over TCP/IP.
    """
    #: int: address of the controller's Serial number register
    _serial_addr = 31

    #: int: address of the controller's Model number register
    _model_addr = 32

    #: int: address of the controller's Software rev register
    _software_addr = 33

    def __init__(self, ip_address=default_IP, port=default_port, inverter=None, inverter_address=None, inverter_port=None):
        """Create a Compressor object for communication with one Compressor Digital Panel controller.

        Opens a Modbus TCP connection to the Compressor Digital Panel controller at `ip_address`, and reads the
        current state.

        Args:
            ip_address (str): IP Address of the compressor controller to communicate with
            port (int): port number for the compressor modbus interface
            inverter (str or None): One of None, "internal", or "rs485". Controls the communication with
                            the compressor's inverter, if fitted.
            inverter_address (str or None): ModbusTCPClient compatible address for the inverter. Either a /dev/tty* address,
                                    com port address (rs485) or IP address (rs485_ethernet)
            inverter_port (int or None): port number for rs485_ethernet server.
        """
        #: (:obj:`ModbusTcpClient`): Client for communicating with the controller
        self._client = ModbusTcpClient(ip_address, port=port)

        #: str: IP address and port of compressor.
        self._ip_address = ip_address
        self._port = port
        
        self._inverter = inverter
        self._inverter_address = inverter_address
        self._inverter_port = inverter_port
        
        # Determine the compressor type, and populate the register
        # numbers appropriately
        
        # str: Serial Number
        self._serial = self.get_serial()

        # str: Model number
        self._model = self.get_model()

        # str: Software rev
        self.get_software_rev()
        
        if self.software_rev.startswith("3"):
            cp_registers = cp_v3_registers
            if self._model == "CPA28I6":
                self._inverter = "internal"
        else:
            cp_registers = cp_v2_registers
        for k, v in cp_registers.items():
            self.__setattr__(k, v)   
        
        #: int: Current state of the compressor
        #       values are one of:
        #           0: Idling - ready to start
        #           2: Starting
        #           3: Running
        #           5: Stopping
        #           6: Error lockout
        #           7: Error
        #           8: Helium cool down
        #           9: Power related error
        #           15: Recovered from error
        self._state = 0

        #: int: Current power state of the compressor
        #       values are one of:
        #           0: Off
        #           1: On
        self._enabled = 0

        #: int: Current warning state of the compressor
        #       values are an OR of:
        #           0: No warnings
        #           -1: Coolant IN (Temp) running High
        #           -2: Coolant IN (Temp) running Low
        #           -4: Coolant OUT (Temp) running High
        #           -8: Coolant OUT (Temp) running High
        #           -16: Oil (Temp) running High
        #           -32: Oil (Temp) running Low
        #           -64: Helium (Temp) running High
        #           -128: Helium (Temp) running Low
        #           -256: Low Pressure running High
        #           -512: Low Pressure running Low
        #           -1024: High Pressure running High
        #           -2048: High Pressure running Low
        #           -4096: Delta Pressure running High
        #           -8192: Delta Pressure running Low
        #           -131072: Static Pressure running High
        #           -262144: Static Pressure running Low
        #           -524288: Cold head motor stall
        # For software version 3 and higher compressors, the 
        # warning codes are positive, not negative
        self._warning_code = 0

        #: int: Current Error state of the compressor
        #       values are an OR of:
        #           0: No warnings
        #           -1: Coolant IN (Temp) running High
        #           -2: Coolant IN (Temp) running Low
        #           -4: Coolant OUT (Temp) running High
        #           -8: Coolant OUT (Temp) running High
        #           -16: Oil (Temp) running High
        #           -32: Oil (Temp) running Low
        #           -64: Helium (Temp) running High
        #           -128: Helium (Temp) running Low
        #           -256: Low Pressure running High
        #           -512: Low Pressure running Low
        #           -1024: High Pressure running High
        #           -2048: High Pressure running Low
        #           -4096: Delta Pressure running High
        #           -8192: Delta Pressure running Low
        #           -16384: Motor Current Low
        #           -32768: Three Phase Error
        #           -65536: Power Supply Error
        #           -131072: Static Pressure running High
        #           -262144: Static Pressure running Low
        #           -524288: Cold head motor stall
        # For software version 3 and higher compressors, the 
        # error codes are positive, not negative
        self._error_code = 0
        
        # float: Cold-head RPM (version 3 only)
        self._coldhead_rpm = 0.0
        
        # float: Inverter frequency in Hertz (version 3 only)
        self._inverter_freq = 0.0

        # float: Inverter current in Amps (version 3 only)
        self._inverter_curr = 0.0

        # float: Coolant IN temperature in self._temp_units
        self._coolant_in = 0.0

        # float: Coolant OUT temperature in self._temp_units
        self._coolant_out = 0.0

        # float: Oil temperature in self._temp_units
        self._oil_temp = 0.0

        # float: Helium temperature in self._temp_units
        self._helium_temp = 0.0

        # float: Low pressure in self._press_units
        self._low_press = 0.0

        # float: Low pressure average in self._press_units
        self._low_press_avg = 0.0

        # float: High pressure in self._press_units
        self._high_press = 0.0

        # float: High pressure average in self._press_units
        self._high_press_avg = 0.0

        # float: Delta pressure average in self._press_units
        self._delta_press_avg = 0.0

        # float: Motor current in Amps - ! Known to be garbage on CP286i
        self._motor_current = 0.0

        # float: Hours of Operation
        self._hours = 0.0

        # bool: How much info should the Compressor return (particularly in __str__)
        self.verbose = False

        # Get the values for the above attributes.
        self.update()

        # The following values are unlikely to change during operation, and so are not set by self.update()

        # int: Pressure unit
        #       values are:
        #           0: PSI
        #           1: Bar
        #           2: KPA
        self._press_scale = self.get_pressure_scale()

        # int: Temperature unit
        #       values are:
        #           0: Farenheit
        #           1: Celsius
        #           2: Kelvin
        self._temp_scale = self.get_temperature_scale()


        # int: how long to wait before checking that compressor enable/disable
        #       command worked
        self._enable_delay = 1.0
        
    @property
    def connected(self):
        """bool: State of the modbus connection to the compressor.
        
        returns:
            bool: connection status"""
        return self._client.connected
    
    def connect(self):
        """Connect to the compressor."""
        self._client.connect()
        
        # Try this once, but if the default settings are wrong,
        # it won't work.
        if self._inverter.startswith('rs485'):
            self.connect_inverter()
        
    def connect_inverter(self, unit=1, serial_conf=None):
        """Connect to the inverter if required.
        
        Parameters:
            serial_conf (dict) : configuration for the serial port to pass to ModbusSerialClient"""
        # This should just connect and work in our default rs485 over ethernet set up.
        if self._inverter and self._inverter.startswith("rs485"):
            try:
                self._inverterclient = inverter.Inverter(self._inverter_address, self._inverter_port, unit=unit, serial_conf=serial_conf)
            except:
                self._inverterclient = None
        
    def disconnect(self):
        """Disconnect from the compressor"""
        if self._inverterclient:
            self._inverterclient.disconnect()
        self._client.disconnect()

    @property
    def inverter(self):
        """int: Does compressor have an inverter."""
        if self._inverter:
            return True
        else:
            return False

    @property
    def state_code(self):
        """int: State of the compressor.
            values are one of:
                    0: Idling - ready to start
                    2: Starting
                    3: Running
                    5: Stopping
                    6: Error lockout
                    7: Error
                    8: Helium cool down
                    9: Power related error
                    15: Recovered from error"""
        return self._state

    @property
    def state(self):
        """str: Verbose description of state of the compressor"""
        return _status_to_string(self._state)

    @property
    def enabled(self):
        """int: Enable state of the compressor.
            values are one of:
                0: Off
                1: On"""
        return self._enabled

    @property
    def warning_code(self):
        """int: Warning state of the compressor.
            value is an OR of:
                0: No warnings
                -1: Coolant IN (Temp) running High
                -2: Coolant IN (Temp) running Low
                -4: Coolant OUT (Temp) running High
                -8: Coolant OUT (Temp) running High
                -16: Oil (Temp) running High
                -32: Oil (Temp) running Low
                -64: Helium (Temp) running High
                -128: Helium (Temp) running Low
                -256: Low Pressure running High
                -512: Low Pressure running Low
                -1024: High Pressure running High
                -2048: High Pressure running Low
                -4096: Delta Pressure running High
                -8192: Delta Pressure running Low
                -131072: Static Pressure running High
                -262144: Static Pressure running Low
                -524288: Cold head motor stall
        """
        return self._warning_code

    @property
    def warnings(self):
        """str: String containing all current warnings as comma separated list."""
        return _error_code_to_string(self._warning_code)

    @property
    def error_code(self):
        """int: Warning state of the compressor.
            values is an OR of:
                0: No errors
                -1: Coolant IN (Temp) running High
                -2: Coolant IN (Temp) running Low
                -4: Coolant OUT (Temp) running High
                -8: Coolant OUT (Temp) running High
                -16: Oil (Temp) running High
                -32: Oil (Temp) running Low
                -64: Helium (Temp) running High
                -128: Helium (Temp) running Low
                -256: Low Pressure running High
                -512: Low Pressure running Low
                -1024: High Pressure running High
                -2048: High Pressure running Low
                -4096: Delta Pressure running High
                -8192: Delta Pressure running Low
                -16384: Motor Current Low
                -32768: Three Phase Error
                -65536: Power Supply Error
                -131072: Static Pressure running High
                -262144: Static Pressure running Low
                -524288: Cold head motor stall
        """
        return self._error_code

    @property
    def errors(self):
        """str: Verbose error messages as comma separated list."""
        return _error_code_to_string(self._error_code)

    @property
    def temp_unit(self):
        str_return = 'F'
        if 1 == self._temp_scale:
            str_return = 'C'
        elif 2 == self._temp_scale:
            str_return = 'K'
        return str_return

    @property
    def press_unit(self):
        str_return = 'PSI'
        if 1 == self._press_scale:
            str_return = 'Bar'
        elif 2 == self._press_scale:
            str_return = 'kPa'
        return str_return

    @property
    def coolant_in(self):
        """float: Coolant IN temperature in self.temp_units"""
        return self._coolant_in

    @property
    def coolant_out(self):
        """float: Coolant OUT temperature in self.temp_units"""
        return self._coolant_out

    @property
    def oil_temp(self):
        """float: Oil temperature in self.temp_units"""
        return self._oil_temp

    @property
    def helium_temp(self):
        """float: Helium temperature in self.temp_units"""
        return self._helium_temp

    @property
    def low_pressure(self):
        """float: Low side pressure in self.press_units"""
        return self._low_press

    @property
    def low_pressure_average(self):
        """float: Average low side pressure in self.press_units"""
        return self._low_press_avg

    @property
    def high_pressure(self):
        """float: High side pressure in self.press_units"""
        return self._high_press

    @property
    def high_pressure_average(self):
        """float: Average high side pressure in self.press_units"""
        return self._high_press_avg

    @property
    def delta_pressure_average(self):
        """float: Average pressure delta in self.press_units"""
        return self._delta_press_avg

    @property
    def motor_current(self):
        """float: Motor current in Amps"""
        return self._motor_current

    @property
    def hours(self):
        """float: Hours of operation"""
        return self._hours
    
    @property
    def inverter_set_freq(self):
        """float: Inverter set frequency in Hz"""
        return self._inverter_set_freq

    @property
    def inverter_freq(self):
        """float: Inverter frequency in Hz"""
        return self._inverter_freq
    
    @property
    def inverter_curr(self):
        """float: Inverter current in Amps"""
        return self._inverter_curr

    @property
    def coldhead_rpm(self):
        """float: Coldhead remote motor RPM"""
        return self._coldhead_rpm

    @property
    def serial(self):
        """str: Serial number of the compressor"""
        return self._serial

    @property
    def model(self):
        """str: Model name of the compressor"""
        return self._model

    @property
    def software_rev(self):
        """str: Software revision of the compressor"""
        return self._software_rev

    @property
    def ip_address(self):
        """str: IP address of the compressor"""
        return self._ip_address
    
    def _read_input_register(self, addr):
        """Read from a generic register and return the value as a float.
        
        For certain registers this will give an incorrect value - the register
        number definitions at the top of this file."""
        if self.software_rev.startswith("3"):
            return self._read_int16(addr)
        else:
            return self._read_float32(addr)

    def _read_float32(self, addr):
        """Read a 32 bit float from a register on the compressor, and convert
        the return bytes to a Python float.

        Args:
            addr (int): Address of the register to read.

        Returns:
            float: Python float read from the register."""
        r = self._client.read_input_registers(addr, count=2, slave=1)
        if r.isError():
            raise RuntimeError("Could not read register {}".format(addr))
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(r.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE)
            result = decoder.decode_32bit_float()

            return result
        
    def _read_int32(self, addr):
        """Read a 32 bit integer from a register on the compressor, and convert
        the return bytes to a Python float.

        Args:
            addr (int): Address of the register to read.

        Returns:
            int: Python int read from the register."""
        r = self._client.read_input_registers(addr, count=2, slave=1)
        if r.isError():
            raise RuntimeError("Could not read register {}".format(addr))
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(r.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE)
            result = decoder.decode_32bit_int()

            return result
        
    def _read_int16(self, addr):
        """Read a 16 bit integer from a register on the compressor, and convert
        the return bytes to a Python int.

        Args:
            addr (int): Address of the register to read.

        Returns:
            int: Python int read from the register."""
        r = self._client.read_input_registers(addr, count=1, slave=1)
        if r.isError():
            raise RuntimeError("Could not read register {}".format(addr))
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(r.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE)
            result = decoder.decode_16bit_int()

            return result
        
    def _read_int8s(self, addr):
        """Read TWO 8 bit integers from a register on the compressor, and convert
        the return bytes to a tuple of Python ints.

        Args:
            addr (int): Address of the register to read.

        Returns:
            int: Python int read from the register."""
        r = self._client.read_input_registers(addr, count=1, slave=1)
        if r.isError():
            raise RuntimeError("Could not read register {}".format(addr))
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(r.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE)
            result1 = decoder.decode_8bit_int()
            result2 = decoder.decode_8bit_int()

            return result1, result2

    def update(self):
        """Read current values from all input registers."""
        self._get_state()
        self._get_enabled()
        self._get_errors()
        self._get_warnings()
        self._get_coolant_in()
        self._get_coolant_out()
        self._get_oil_temp()
        self._get_helium_temp()
        self._get_low_pressure()
        self._get_low_pressure_average()
        self._get_high_pressure()
        self._get_high_pressure_average()
        self._get_delta_pressure_average()
        self._get_motor_current()
        self._get_hours()
        if self._inverter:
            self._get_inverter_freq()
            self._get_inverter_curr()

    def __str__(self):
        """Print the stored state of the compressor."""
        if self.verbose:
            return self.status
        else:
            return "\n".join(("Cryomech {}. ser. {}".format(self.model, self.serial),
                              "IP address      : {}".format(self.ip_address),
                              "Operating State : {}".format(self.state),
                              "Enabled         : {}".format(self.enabled),
                              "Warnings        : \n {}".format("\n".join(self.warnings.split(","))),
                              "Errors          : \n {}".format("\n".join(self.errors.split(",")))))

    @property
    def status(self):
        """str: All of the stored state of the compressor."""
        status = [
            "Cryomech {}. ser. {}".format(self.model, self.serial),
            "IP address         : {}".format(self.ip_address),
            "Operating State    : {}".format(self.state),
            "Enabled            : {}".format(self.enabled),
            "Warnings           : \n {}".format("\n".join(self.warnings.split(","))),
            "Errors             : \n {}".format("\n".join(self.errors.split(","))),
            "\n"
        ]
        if self._inverter:
            status.extend(["Inverter Frequency : {:.1f} Hz".format(self.inverter_freq),
                           "Inverter Current   : {:.2f} Amps".format(self.inverter_curr)])
        
        if self.software_rev.startswith("3"):
            status.append("Coldhead RPM       : {:.2f} RPM".format(self.coldhead_rpm))
        
        status.extend(["Coolant In         : {:.2f} {}".format(self.coolant_in, self.temp_unit),
                          "Coolant Out        : {:.2f} {}".format(self.coolant_out, self.temp_unit),
                          "Oil Temperature    : {:.2f} {}".format(self.oil_temp, self.temp_unit),
                          "Helium Temp        : {:.2f} {}".format(self.helium_temp, self.temp_unit),
                          "Low side pressure  : {:.2f} {}".format(self.low_pressure, self.press_unit),
                          "Low side average   : {:.2f} {}".format(self.low_pressure_average, self.press_unit),
                          "High side pressure : {:.2f} {}".format(self.high_pressure, self.press_unit),
                          "High side average  : {:.2f} {}".format(self.high_pressure_average, self.press_unit),
                          "Pressure Delta avg : {:.2f} {}".format(self.delta_pressure_average, self.press_unit),
                          "Motor current      : {:.2f} Amps".format(self.motor_current),
                          "Hours of Operation : {:.1f}".format(self.hours)])
        return "\n".join(status)

    def print_status(self):
        """Print all of the stored status"""
        print(self.status)

    def get_status(self):
        """Update the current state and print it"""
        self.update()
        self.print_status()

    def __repr__(self):
        """Print some basic info about the compressor object."""
        return "wsma_cryostat_compressor.Compressor connected to Cryomech {}, ser. {} at {}".format(self.model,
                                                                                                    self.serial,
                                                                                                    self.ip_address)

    def _get_state(self):
        """Read the current state of the compressor."""
        self._state = self._read_input_register(self._operating_state_addr)

    def get_state(self):
        """Read the current state of the compressor.

        Returns:
            str: Current state of the compressor"""
        self._get_state()
        return self.state

    def _get_enabled(self):
        """Read the current Enable state of the compressor"""
        self._enabled = self._read_input_register(self._enabled_addr)

    def get_enabled(self):
        """Read the current Enable state of the compressor.

        Returns:
            int: current Enable state of the compressor."""
        self._get_enabled()
        return self.enabled

    def _get_warnings(self):
        """Read the current warnings from the compressor."""
        if self._software_rev.startswith("3"):
            r = self._read_int32(self._warning_addr)
        else:
            r = self._read_float32(self._warning_addr)
        self._warning_code = int(r)

    def get_warnings(self):
        """Read the current warnings from the compressor.

        Returns:
            int: warning state of the compressor."""
        self._get_warnings()
        return self.warnings

    def _get_errors(self):
        """Read the current errors from the compressor."""
        if self._software_rev.startswith("3"):
            r = self._read_int32(self._error_addr)
        else:
            r = self._read_float32(self._error_addr)
        self._error_code = int(r)

    def get_errors(self):
        """Read the current errors from the compressor.

        Returns:
            int: error state of the compressor."""
        self._get_errors()
        return self.errors

    def _get_coolant_in(self):
        """Read the current coolant inlet temperature."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._coolant_in_addr)/10.0
        else:
            temp = self._read_float32(self._coolant_in_addr)
        self._coolant_in = temp

    def get_coolant_in(self):
        """Read the current coolant inlet temperature.

        Returns:
            float: coolant inlet temperature in units of self.temp_units"""
        self._get_coolant_in()
        return self.coolant_in

    def _get_coolant_out(self):
        """Read the current coolant outlet temperature"""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._coolant_out_addr)/10.0
        else:
            temp = self._read_float32(self._coolant_out_addr)
        self._coolant_out = temp

    def get_coolant_out(self):
        """Read the current coolant outlet temperature.

        Returns:
            float: coolant inlet temperature in units of self.temp_units"""
        self._get_coolant_out()
        return self.coolant_out

    def _get_helium_temp(self):
        """Read the current helium temperature."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._helium_temp_addr)/10.0
        else:
            temp = self._read_float32(self._helium_temp_addr)
        self._helium_temp = temp

    def get_helium_temp(self):
        """Read the current helium temperature.

        Returns:
            float: helium temperature in units of self.temp_units"""
        self._get_helium_temp()
        return self.helium_temp

    def _get_oil_temp(self):
        """Read the current helium temperature."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._oil_temp_addr)/10.0
        else:
            temp = self._read_float32(self._oil_temp_addr)
        self._oil_temp = temp

    def get_oil_temp(self):
        """Read the current helium temperature.

        Returns:
            float: helium temperature in units of self.temp_units"""
        self._get_oil_temp()
        return self.oil_temp

    def _get_low_pressure(self):
        """Read the current low side pressure."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._low_press_addr)/10.0
        else:
            temp = self._read_float32(self._low_press_addr)
        self._low_press = temp

    def get_low_pressure(self):
        """Read the current low side pressure.

        Returns:
            float: low side pressure in units of self.press_units"""
        self._get_low_pressure()
        return self.low_pressure

    def _get_low_pressure_average(self):
        """Read the current average low side pressure."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._low_press_avg_addr)/10.0
        else:
            temp = self._read_float32(self._low_press_avg_addr)
        self._low_press_avg = temp

    def get_low_pressure_average(self):
        """Read the current average low side pressure.

        Returns:
            float: average low side pressure in units of self.press_units"""
        self._get_low_pressure_average()
        return self.low_pressure_average

    def _get_high_pressure(self):
        """Read the current high side pressure."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._high_press_addr)/10.0
        else:
            temp = self._read_float32(self._high_press_addr)
        self._high_press = temp

    def get_high_pressure(self):
        """Read the current high side pressure.

        Returns:
            float: high side pressure in units of self.press_units"""
        self._get_high_pressure()
        return self.high_pressure

    def _get_high_pressure_average(self):
        """Read the current average high side pressure."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._high_press_avg_addr)/10.0
        else:
            temp = self._read_float32(self._high_press_avg_addr)
        self._high_press_avg = temp

    def get_high_pressure_average(self):
        """Read the current average high side pressure.

        Returns:
            float: average high side pressure in units of self.press_units"""
        self._get_high_pressure_average()
        return self.high_pressure_average

    def _get_delta_pressure_average(self):
        """Read the current average pressure delta."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._delta_press_avg_addr)/10.0
        else:
            temp = self._read_float32(self._delta_press_avg_addr)
        self._delta_press_avg = temp

    def get_delta_pressure_average(self):
        """Read the current average pressure delta.

        Returns:
            float: average pressure delta in units of self.press_units"""
        self._get_delta_pressure_average()
        return self.delta_pressure_average

    def _get_motor_current(self):
        """Read the motor current."""
        if self._software_rev.startswith("3"):
            temp = self._read_int16(self._motor_current_addr)/10.0
        else:
            temp = self._read_float32(self._motor_current_addr)
        self._motor_current = temp

    def get_motor_current(self):
        """Read the motor current.

        ! This number is known to be garbage on the inverter compressors !
        Use the RS485 bus on the inverter unit to read the current/voltage/power consumption

        Returns:
            float: motor current in Amps"""
        self._get_motor_current()
        return self.motor_current

    def _get_hours(self):
        """Read the current hours of operation."""
        if self._software_rev.startswith("3"):
            temp = self._read_int32(self._hours_addr)/10.0
        else:
            temp = self._read_float32(self._hours_addr)
        self._hours = temp

    def get_hours(self):
        """Read the current hours of operation.

        Returns:
            float: hours of operation"""
        self._get_hours()
        return self.hours
    
    def _get_inverter_freq_setting(self):
        """Read the inverter set frequency"""
        if self._inverter is None:
            pass
        elif self._inverter=="internal":
            freq = self._read_int16(self._inverter_set_freq_addr)
            self._inverter_set_freq = freq/10.
        elif self._inverter=="rs485":
            self._inverterclient.get_frequency_setting(freq)
        
    def get_inverter_freq_setting(self):
        """Read and return the inverter set frequency"""
        self._get_inverter_freq_setting()
        return self._inverter_set_freq
    
    def set_inverter_freq(self, freq):
        """Set the inverter frequency"""
        if self._inverter is None:
            return None
        elif self._inverter=="internal":
            self._client.write_registers(self._inverter_set_freq_addr, int(freq*10), slave=1)
        elif self._inverter=="rs485":
            self._inverterclient.set_frequency(freq)
        else:
            return None
        self._get_inverter_freq_setting()
        
    def _get_inverter_freq(self):
        """Read the inverter frequency"""
        if self._inverter is None:
            pass
        elif self._inverter=="internal":
            freq = self._read_int16(self._inverter_freq_addr)
            self._inverter_freq = freq/10.
        elif self._inverter=="rs485":
            self._inverterclient.get_frequency()
        else:
            pass
        
    def get_inverter_freq(self):
        """Read and return the inverter frequency"""
        self._get_inverter_freq()
        return self._inverter_freq

    def _get_inverter_curr(self):
        """Read the inverter current"""
        if self._inverter is None:
            pass
        elif self._inverter=="internal":
            curr = self._read_int16(self._inverter_curr_addr)
            self._inverter_curr = curr/10.
        elif self._inverter=="rs485":
            self._inverterclient.get_currrent()
        else:
            pass

    def get_inverter_curr(self):
        """Read and return the inverter current"""
        self._get_inverter_curr()
        return self._inverter_curr
    
    def _get_coldhead_rpm(self):
        """Read the coldhead RPM"""
        if self._software_rev.startswith("3"):
            rpm = self._read_int16(self._rpm_addr)
            self._coldhead_rpm = rpm/100.

    def get_coldhead_rpm(self):
        """Read and return the coldhead RPM"""
        self._get_coldhead_rpm()
        return self._coldhead_rpm

    def get_pressure_scale(self):
        """Read the pressure scale.

        Returns:
            int: the pressure scale code."""
        self._press_scale = self._read_input_register(self._press_unit_addr)
        return self._press_scale

    def get_temperature_scale(self):
        """Read the temperature scale.

        Returns:
            int: the temperature scale code."""
        self._temp_scale = self._read_input_register(self._temp_unit_addr)
        return self._temp_scale

    def get_serial(self):
        """Read the serial number from the compressor

        Returns:
            str: serial number from the compressor"""
        r = self._client.read_input_registers(self._serial_addr, 1, slave=1)
        self._serial = r.registers[0]
        return self.serial

    def get_model(self):
        """Read the model name from the compressor

        Returns:
            str: model name from the compressor"""
        r = self._client.read_input_registers(self._model_addr, 2, slave=1)
        model = _model_code_to_string(r.registers[0].to_bytes(2, byteorder="big"))
        self._model = model
        return self.model

    def get_software_rev(self):
        """Read the software revision from the compressor

        Returns:
            str: software revision"""
        s, v = self._read_int8s(self._software_addr)
        self._software_rev = f"{s:d}.{v:d}"
        return self.software_rev

    def on(self):
        """Turn the compressor on."""
        w = self._client.write_registers(self._enable_addr, 0x0001, slave=1)
        if w.isError():
            raise RuntimeError("Could not command compressor to turn on")
        else:
            sleep(self._enable_delay)
            self._get_state()
            # give it some more time if needed
            if self._state != 2 and self._state != 3:
                sleep(self._enable_delay)
            if self._state != 2 and self._state != 3:
                self._get_errors()
                raise RuntimeError("Compressor is not starting. Compressor Error Code {}".format(self._error_code))
            self.update()

    def off(self):
        """Turn the compressor off."""
        w = self._client.write_registers(self._enable_addr, 0x00FF, slave=1)
        if w.isError():
            raise RuntimeError("Could not command compressor to turn off")
        else:
            sleep(self._enable_delay)
            self._get_state()
            # Give it some more time if needed
            if self._state != 5 and self._state != 0:
                sleep(self._enable_delay)
            if self._state != 5 and self._state != 0:
                raise RuntimeError("Compressor did not turn off")
            self.update()
