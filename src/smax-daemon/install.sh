#!/bin/bash
#
# Install, enable and run the Compressor SMAX Daemon service with systemd
# as a user service.
# 
# Paul Grimes
# 06/29/2023
#

SYSDUSER="$HOME/.config/systemd/user"
INSTALL="$SYSDUSER/compressor-smax-daemon"
CONFIG="$HOME/wsma_config"

mkdir -p $INSTALL
mkdir -p "$CONFIG/cryostat/compressor"

cp "./compressor-smax-daemon.py" $INSTALL
cp "./compressor-smax-daemon.service" $SYSDUSER
cp "./on-start.sh" $INSTALL

if ! test -f "$CONFIG/smax_config.json"
then
    cp "./smax_config.json" $CONFIG
fi

cp "./compressor_config.json" "$CONFIG/cryostat/compressor"
cp "./log_keys.conf" "$CONFIG/cryostat/compressor"

chmod -R 755 $INSTALL

read -p "Enable compressor-smax-daemon at this time? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    systemctl --user daemon-reload
    systemctl --user enable compressor-smax-daemon
    systemctl --user restart compressor-smax-daemon
fi

exit
