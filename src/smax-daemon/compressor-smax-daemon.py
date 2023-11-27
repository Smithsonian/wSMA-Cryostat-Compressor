import logging
import os
import sys
import time
import datetime
import json

import systemd.daemon

import wsma_cryostat_compressor
import wsma_cryostat_compressor.inverter

default_CM4116_IP = "192.168.42.21"
default_port = 1
default_timeout = 10

READY = 'READY=1'
STOPPING = 'STOPPING=1'

from smax import SmaxRedisClient

def tcpip_address(ip=default_CM4116_IP, port=default_port):
    """Get a pyvisa TCPIP resource name for a CM4116 Serial to ethernet converter"""
    address = "TCPIP::{:s}::40{:02d}::SOCKET"
    return address.format(ip, port)


class CompressorReadout:
    def __init__(self, compressor, server, port):
        self._compressor = compressor
        self._server = server
        self._port = port
    
    @property
    def ls(self):
        return self._ls
    
    @ls.setter
    def ls(self, ls):
        self._ls = ls
        
    @property
    def server(self):
        return self._server

    @property
    def port(self):
        return self._port
        
    @property
    def sensors(self):
        return self._sensors

    @sensors.setter
    def sensors(self, sensors):
        self._sensors = sensors
        
    @property
    def relays(self):
        return self._relays
    
    @relays.setter
    def relays(self, relays):
        self._relays = relays
        

class CompressorSmaxService:
    def __init__(self, config="compressor_config.json"):
        """Service object initialization code"""
        self.logger = self._init_logger()
        
        self.read_config(config)

        # Compressor and Inverter objects
        self.compressor = None
        self.inverter = None
        
        self.create_compressor()
        self.create_inverter()

        # The SMAXRedisClient instance
        self.smax_client = None
        
        
        # Log that we managed to create the instance
        self.logger.info('Compressor-SMAX-Daemon instance created')
        
    def read_config(self, config):
        """Read the configuration file."""
        # Read the file
        with open(config) as fp:
            self._config = json.load(fp)
            fp.close()
        
        # parse the _config dictionary and set up values
        self.smax_server = self._config["smax_config"]["smax_server"]
        self.smax_port = self._config["smax_config"]["smax_port"]
        self.smax_db = self._config["smax_config"]["smax_db"]
        self.smax_table = self._config["smax_config"]["smax_table"]
        self.smax_compressor_key = self._config["smax_config"]["smax_key"]
        self.smax_power_control_key = self._config["smax_config"]["smax_power_control_key"]
        self.smax_inverter_freq_control_key = self._config["smax_config"]["smax_inverter_freq_control_key"]
        
        self.logging_interval = self._config["logging_interval"]
        self.serial_server = self._config["serial_server"]
        
    def create_compressor(self):
        """Read compressor configuration, and try to connect to it."""
        self._compressor_ip = self._config["compressor"]["ip_address"]
        self._compressor_port = self._config["compressor"]["port"]
        self._compressor_data = self._config["compressor"]["logged_data"]
        
        try:
            self.compressor = wsma_cryostat_compressor.Compressor(self._compressor_ip, self._compressor_port)
        except Exception as e:
            self.logger.error(f"Compressor connection exception:\n {e.__str__()}")
        
        if self.compressor is None:
            self.logger.error(f"Could not connect to Compressor")
        
    def create_inverter(self):
        self._inverter_port = self._config["inverter"]["port"]
        self._inverter_data = self._config["inverter"]["logged_data"]
        
        try:
            self.inverter = wsma_cryostat_compressor.inverter.Inverter(self.serial_server, self._inverter_port)
        except Exception as e:
            self.logger.error(f"Inverter connection exception:\n {e.__str__()}")
        
        if self.inverter is None:
            self.logger.error(f"Could not connect to Inverter")
        
    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        logger.addHandler(stdout_handler)
        return logger

    def start(self):
        """Code to be run before the service's main loop"""
        # Start up code

        # This snippet creates a connection to SMA-X that we have to close properly when the
        # service terminates
        if self.smax_client is None:
            self.smax_client = SmaxRedisClient(redis_ip=self.smax_server, redis_port=self.smax_port, redis_db=self.smax_db, program_name="example_smax_daemon")
        else:
            self.smax_client.smax_connect_to(self.smax_server, self.smax_port, self.smax_db)
        
        self.logger.info('SMA-X client connected to {self.smax_server}:{self.smax_port} DB:{self.smx_db}')
        
        # Get initial values and push to SMA-X
        self.smax_logging_action()
        
        # Push units metadata to SMA-X
        self.smax_set_units()
        
        # Set default values for pubsub channels
        try:
            self.smax_client.smax_pull(self.smax_table, self.smax_inverter_freq_control_key)
        except:
            self.smax_client.smax_share(self.smax_table, self.smax_inverter_freq_control_key, self._config["inverter"]["default_frequency"])
            self.logger.info(f'Set initial frequency for inverter to {self._config["inverter"]["default_frequency"]}')

        # Register pubsub channels
        self.smax_client.smax_subscribe(":".join([self.smax_table, self.smax_power_control_key]), self.compressor_power_control_callback)
        self.smax_client.smax_subscribe(":".join([self.smax_table, self.smax_inverter_freq_control_key]), self.inverter_freq_control_callback)
        self.logger.info('Subscribed to compressor and inverter control pubsub notifications')

        # Set up the time for the next logging action
        self._next_log_time = time.monotonic() + self.logging_interval

        # systemctl will wait until this notification is sent
        # Tell systemd that we are ready to run the service
        systemd.daemon.notify(READY)

        # Run the service's main loop
        self.run()

    def run(self):
        """Run the main service loop"""
        try:
            while True:
                # Put the service's regular activities here
                self.smax_logging_action()
                time.sleep(self.logging_interval)

        except KeyboardInterrupt:
            # Monitor for SIGINT, which we've set as the terminate signal in the
            # .service file
            self.logger.warning('SIGINT (keyboard interrupt) received...')
            self.stop()

    def smax_logging_action(self):
        """Run the code to write logging data to SMAX"""
        # Gather data
        logged_data = {}
        
        self.compressor.update()
        self.inverter.update()
        
        for data in self._compressor_data.keys():
            unit = None
            if "unit" in data.keys():
                if data["unit"] == "temp":
                    unit = self.compressor.temp_unit
                elif data["unit"] == "press":
                    unit = self.compressor.press_unit
                else:
                    unit = data["unit"]
                
            reading = self.compressor.__getattribute__(data)
            logged_data[data] = [reading, unit]
            self.logger.info(f'Got data for compressor {data}: {reading:.3f} {unit}')
            
        for data in self._inverter_data.keys():
            unit = None
            if "unit" in data.keys():
                unit = data["unit"]
                
            reading = self.inverter.__getattribute__(data)
            logged_data[data] = [reading, unit]
            self.logger.info(f'Got data for compressor {data}: {reading:.3f} {unit}')
            
        # write values to SMAX
        for data in logged_data.keys():
            self.smax_client.smax_share(f"{self.smax_table}:{self.smax_key}", data, logged_data[data][0])
        self.logger.info(f'Wrote compressor and inverter data to SMAX ')
            
    def compressor_power_control_callback(self, message):
        """Run on a pubsub notification to smax_table:smax_heater_key"""
        date = datetime.datetime.utcfromtimestamp(message.date)
        self.logger.info(f'Received PubSub notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        if message.data:
            self.compressor.on()
        else:
            self.compressor.off()
            
    def inverter_freq_control_callback(self, message):
        """Run on a pubsub notification to smax_table:smax_heater_key"""
        date = datetime.datetime.utcfromtimestamp(message.date)
        self.logger.info(f'Received PubSub notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        freq = float(message.data)
        
        if freq >= 40.0 and freq <= 70.0:
            self.inverter.set_frequency(freq)
        else:
            self.logger.warning(f'Commanded inverter frequency {freq} is out of range')
        
    def stop(self):
        """Clean up after the service's main loop"""
        # Tell systemd that we received the stop signal
        systemd.daemon.notify(STOPPING)

        # Put the service's cleanup code here.
        self.logger.info('Cleaning up...')
        if self.smax_client:
            self.smax_client.smax_unsubscribe()
            self.smax_client.smax_disconnect()
            self.logger.info('SMA-X client disconnected')
        else:
            self.logger.error('SMA-X client not found, nothing to clean up')
            
        if self.lakeshores:
            for ls in self.lakeshores:
                ls.ls._resource.close()

        # Exit to finally stop the serivce
        sys.exit(0)


if __name__ == '__main__':
    # Do start up stuff
    service = CompressorSmaxService()
    service.start()