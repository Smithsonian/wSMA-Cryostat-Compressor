__version__ = '0.0.0'

from time import sleep
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

default_IP = "192.168.42.128"
