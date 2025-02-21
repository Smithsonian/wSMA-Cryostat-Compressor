# compressor-smax-daemon

A user space systemd service implemented in Python that reads values from the wSMA cryostat compressor control and readout, and writes the data to SMAx.

Configuration of the daemon is set in the JSON format config file `compressor_config.json`.  General SMA-X settings are store in `smax_config.json`.  By default, these files are stored in `~/wsma_config`, with `compressor_config.json` stored under the `cryostat/compressor` subfolder.

These config file locations additionally contain a list of SMA-X keys that can be used with smax_python_monitor to monitor and log values to a folder.

Service structure is based on tutorials at https://alexandra-zaharia.github.io/posts/stopping-python-systemd-service-cleanly/ and https://github.com/torfsen/python-systemd-tutorial

Installation as both a user and system service is described in the second tutorial.

Requires:
systemd-python (in turn requires linux packages systemd-devel, gcc, python3-devel)
psutils
smax-python
wsma_cryostat_compressor
