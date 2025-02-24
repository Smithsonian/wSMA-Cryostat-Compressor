
from time import sleep
import os

from pymodbus.client import ModbusTcpClient, ModbusSerialClient

from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusIOException

from retrying import retry

default_address = os.environ.get("INVERTER_IP", None)
default_port = os.environ.get("INVERTER_PORT", 502)
default_serial_conf = {
                                        "baudrate":9600,
                                        "bytesize":8,
                                        "parity":"O",
                                        "stopbits":1
                                    }

def _is_modbus_io_error(exception):
    """Return True if an exception is an ModbusIOError, False otherwise.
    
    arguments:
        exception : exception to test.
        
    returns:
        boolean : is exception an IOError?"""
    return isinstance(exception, ModbusIOException)

class Inverter(object):
    """Class for communicating with the Inverter controller.

    The Inverter object wraps a pymodbus.ModbusTcpClient instance which
    communicates with the TCP/IP Modbus client on the RS485 server attached
    to the inverter
    """
    #: int: address of the inverter's frequency holding register.
    _frequency_addr = 0x1001

    #: int: address of the inverter's frequency setting holding register.
    _frequency_control_addr = 0x0001

    #: int: address of the inverter's output current monitor input register
    _current_addr = 0x1002

    #: int: address of the inverter's output voltage monitor input register
    _voltage_addr = 0x1010

    #: int: address of the inverter's output power monitor inpur register
    _power_addr = 0x1011

    #: int: unit address
    _unit_addr = 0x01

    def __init__(self, address=default_address, port=default_port, unit=1, serial_conf=default_serial_conf):
        """Create an inverter object for communication with the inverter.

        Args:
            address (str): the TCPIP address of the Modbus TCP server.
            port (int): the port of the Modbus TCP server.
            unit (int): the Modbus unit of the inverter.
        """
        self._client = None
        #: str: IP address and port for the inverter.
        self._address = address
        self._port = port
        self._unit = unit
        
        #: dict:  Serial configuration for directly connected serial inverter
        # we probably won't use this much, due to having the ethernet
        # to RS485 adapters
        self._serial_conf = serial_conf
        
        #: int: the frequency of the inverter, in units of 0.01 Hz.
        self._frequency = 0

        #: int: the output current of the inverter in units of 0.1 A.
        self._current = 0

        #: int: the output voltage of the inverter in units of 0.1 V.
        self._voltage = 0

        #: int: the output power of the inverter in units of 0.1 kW.
        self._power = 0

        #: float: time to wait for frequency setting to be updated.
        self._set_delay = 1.0

        self.verbose = False

        # Get the data from the inverter
        self.update()
        
    def connect(self, serial_conf=None):
        """set up the communications"""
        if serial_conf:
            self._serial_conf = serial_conf
            
        if self._address.startswith("/dev") or self._address.startswith("COM"):
            try:
                self._client = ModbusSerialClient(self._inverter_address, **self._serial_conf)
                self._client.connect()
            except:
                pass
        else:
            self._client = ModbusTcpClient(self._address, port=self._port)
            self._client.connect()


    @property
    def frequency(self):
        """float: The frequency of the inverter in Hz.

        Read only - set the frequency via the frequency_setting attribute."""
        return self._frequency * 0.01

    @property
    def current(self):
        """float: The output current of the inverter in Amps."""
        return self._current * 0.1

    @property
    def voltage(self):
        """float: The output voltage of the inverter in Volts."""
        return self._voltage * 0.1

    @property
    def power(self):
        """float: The output power of the inverter in kW."""
        return self._power * 0.1
    
    @property
    def frequency_setting(self):
        """float: The frequency setting of the inverter in Hz."""
        return self._frequency_setting * 0.01
    
    @frequency_setting.getter
    def frequency_setting(self, freq):
        """float: The frequency setting of the inverter in Hz"""
        self.set_frequency(freq)

    @property
    def address(self):
        """str: The address of the inverter."""
        return "{}, port {}, unit {}".format(self._address, self._port, self._unit)

    def update(self):
        """Get updated values for all monitor values from the inverter"""
        self._get_frequency()
        self._get_current()
        self._get_voltage()
        self._get_power()

    def __repr__(self):
        """Brief description of the object."""
        return "wsma_cryostat_compressor.inverter.Inverter on serial port {}.".format(self._port)

    def __str__(self):
        """Print the stored state of the inverter."""
        if self.verbose:
            return self.status
        else:
            return "\n".join(("Inverter",
                              "IP Address : {}".format(self._address),
                              "Frequency  : {} Hz".format(self.frequency)))
    
    
    @retry(retry_on_exception=_is_modbus_io_error, wait_random_min=300, wait_random_max=900, stop_max_attempt_number=5)
    def _read_registers(self, address, count=1, unit=1):
        """Read holding registers and check for errors, using the
        retrying module to retry up to 5 times."""
        r = self._client.read_holding_registers(address, count=count, slave=unit)
        if _is_modbus_io_error(r):
            raise r
        else:
            return r

    @property
    def status(self):
        """str: Detailed status of the inverter"""
        return "\n".join(("Inverter",
                          "Address : {}".format(self.address),
                          "Frequency  : {:.2f} Hz".format(self.frequency),
                          "Power      : {:.3f} kW".format(self.current*self.voltage*0.00141423),
                          "Current    : {:.1f} A".format(self.current),
                          "Voltage    : {:.1f} V".format(self.voltage)))

    def print_status(self):
        """Print all of the stored status"""
        print(self.status)

    def get_status(self):
        """Update the current state and print it"""
        self.update()
        self.print_status()

    def _get_frequency(self):
        """Get the current frequency from the inverter"""
        r = self._read_registers(self._frequency_addr, count=2, unit=1)
        self._frequency = self._client.convert_from_registers(r, data_type=self._client.DATATYPE.INT32, word_order='little')

    def _get_current(self):
        """Get the output current from the inverter"""
        r = self._read_registers(self._current_addr, count=1, unit=1)
        self._current = r.registers[0]

    def _get_voltage(self):
        """Get the output voltage from the inverter"""
        r = self._read_registers(self._voltage_addr, count=1, unit=1)
        self._voltage = r.registers[0]

    def _get_power(self):
        """Get the output power from the inverter"""
        r = self._read_registers(self._power_addr, count=1, unit=1)
        self._power = r.registers[0]

    def _set_frequency(self, freq):
        """Set the output frequency of the inverter.

        Args:
            freq: int: Frequency to set in units of 0.01 Hz"""
        response = self._client.write_register(self._frequency_control_addr, freq, count=1, unit=1)
        sleep(self._set_delay)
        self._get_frequency_setting()
        
    def _get_frequency_setting(self):
        """Get the set output frequency of the inverter."""
        r = self._read_registers(self._frequency_control_addr, count=2, unit=1)
        self._frequency_setting = self._client.convert_from_registers(r, data_type=self._client.DATATYPE.INT32, word_order='little')

    def get_frequency(self):
        """Get current frequency from the inverter and return the value.

        Returns:
            float: Frequency in Hz."""
        self._get_frequency()
        return self.frequency

    def set_frequency(self, freq):
        """Set the inverter frequency.

        Args:
            freq: float: Inverter frequency in Hz."""
        f = int(freq * 100)
        if f > 7000 or f < 4000:
            raise ValueError("Cannot set inverter frequency outside the range of 40-70 Hz")
        else:
            self._set_frequency(f)

        return self.frequency

    def get_current(self):
        """Get the output current from the inverter and return the value.

        Returns:
            float: Current in Amps."""
        self._get_current()
        return self.current

    def get_voltage(self):
        """Get the output voltage from the inverter and return the value.

        Returns:
            float: Voltage in Volts."""
        self._get_voltage()
        return self.voltage

    def get_power(self):
        """Get the output power from the inverter and return the value.

        Returns:
            float: Power in kW."""
        self._get_power()
        return self.power
    
    def get_frequency_setting(self):
        """Get the frequency setting from the inverter"""
        self._get_frequency_setting()
        return self.frequency_setting
