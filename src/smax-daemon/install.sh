#!/bin/bash
#
# Install, enable and run the Compressor SMAX Daemon service with systemd
# as a user service.
# 
# Paul Grimes
# 06/29/2023
#

USER_LOCAL_LIB="/usr/local/lib"
INSTALL="$USER_LOCAL_LIB/compressor_smax_daemon"
CONFIG="/home/smauser/wsma_config"

mkdir -p $INSTALL
mkdir -p "$CONFIG/cryostat/compressor"

cp "./compressor_smax_daemon.py" $INSTALL
cp "./compressor_interface.py" $INSTALL
cp "./compressor_smax_daemon.service" $SYSDUSER
cp "./on_start.sh" $INSTALL

chmod -R 755 $INSTALL
chown -R smauser:smauser $INSTALL

ln -s "$INSTALL/compressor_smax_daemon.service" "/etc/systemd/system/compressor_smax_daemon.service"

if ! test -f "$CONFIG/smax_config.json"
then
    cp "./smax_config.json" $CONFIG
fi

if ! test -f "$CONFIG/cryostat/compressor/compressor_config.json"
then
    cp "./compressor_config.json" "$CONFIG/cryostat/compressor"
    cp "./log_keys.conf" "$CONFIG/cryostat/compressor"
else
    read -p "Overwrite compressor_config.json and log_keys.conf? " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        cp "./compressor_config.json" "$CONFIG/cryostat/compressor"
        cp "./log_keys.conf" "$CONFIG/cryostat/compressor"
    fi
fi

chmod -R 755 $CONFIG
chown -R smauser:smauser $CONFIG

read -p "Enable compressor-smax-daemon at this time? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    systemctl daemon-reload
    systemctl enable compressor-smax-daemon
    systemctl restart compressor-smax-daemon
fi

exit
