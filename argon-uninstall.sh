#!/bin/bash
echo "----------------------"
echo " Argon Uninstall Tool"
echo "----------------------"
echo -n "Press Y to continue:"
read -n 1 confirm
echo
if [ "$confirm" = "y" ]
then
    confirm="Y"
fi

if [ "$confirm" != "Y" ]
then
    echo "Cancelled"
    exit
elif [ "$EUID" -ne 0 ]; then
  echo "Please run as root / use sudo"
  exit
fi

find /home/ -name argonone-config.desktop -type f -delete

rm /usr/share/pixmaps/ar1config.png 2> /dev/null
rm /usr/share/pixmaps/argoneon.png 2> /dev/null

INSTALLATIONFOLDER=/etc/argon

argononefanscript=$INSTALLATIONFOLDER/argononed.py

if [ -f $argononefanscript ]; then
    systemctl stop argononed.service
    systemctl disable argononed.service

    # Turn off the fan
    /usr/bin/python3 $argononefanscript FANOFF
    # Remove files
    rm /lib/systemd/system/argononed.service
fi

# Remove RTC if any
argoneonrtcscript=$INSTALLATIONFOLDER/argoneond.py
if [ -f "$argoneonrtcscript" ]
then
    # Disable Services
    systemctl stop argoneond.service
    systemctl disable argoneond.service

    # Shutdown realtime clock 
    /usr/bin/python3 $argoneonrtcscript CLEAN
    /usr/bin/python3 $argoneonrtcscript SHUTDOWN

    # Remove files
    rm /lib/systemd/system/argoneond.service
fi

rm /usr/bin/argon-config

if [ -f "/usr/bin/argonone-config" ]
then
    rm /usr/bin/argonone-config
    rm /usr/bin/argonone-uninstall      
    rm /usr/bin/argonone-ir
fi

if [ -f "/usr/bin/argon-status" ]
then
    rm /usr/bin/argon-status
fi

rm /lib/systemd/system-shutdown/argon-shutdown.sh

rm -R -f $INSTALLATIONFOLDER

echo "Removed Argon Services."
echo "Cleanup will complete after restarting the device."