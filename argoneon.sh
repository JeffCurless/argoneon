#!/bin/bash

echo "*************"
echo " Argon Setup  "
echo "*************"

# Helper variables
ARGONDOWNLOADSERVER=https://raw.githubusercontent.com/JeffCurless/argoneon/main/
INSTALLATIONFOLDER=/etc/argon

versioninfoscript=$INSTALLATIONFOLDER/argon-versioninfo.sh

uninstallscript=$INSTALLATIONFOLDER/argon-uninstall.sh
shutdownscript=/lib/systemd/system-shutdown/argon-shutdown.sh
statusscript=$INSTALLATIONFOLDER/argon-status.py
statuscmd=argon-status
configscript=$INSTALLATIONFOLDER/argon-config
unitconfigscript=$INSTALLATIONFOLDER/argon-unitconfig.sh

setupmode="Setup"

if [ -f $configscript ]
then
    setupmode="Update"
    echo "Updating files"
else
    sudo mkdir $INSTALLATIONFOLDER
    sudo chmod 755 $INSTALLATIONFOLDER
fi


argon_check_pkg() {
    RESULT=$(dpkg-query -W -f='${Status}\n' "$1" 2> /dev/null | grep "installed")

    if [ "" == "$RESULT" ]; then
        echo "NG"
    else
        echo "OK"
    fi
}

CHECKDEVICE="eon"    # Hardcoded for EON

CHECKPLATFORM="Others"
# Check if Raspbian, otherwise Ubuntu
grep -q -F -e 'Raspbian' -e 'bullseye' /etc/os-release &> /dev/null
if [ $? -eq 0 ]
then
    CHECKPLATFORM="Raspbian"
    if [ "$CHECKDEVICE" = "eon" ]
    then
        pkglist=(raspi-gpio python3-rpi.gpio python3-smbus i2c-tools python3-psutil hddtemp)    
    else
        pkglist=(raspi-gpio python3-rpi.gpio python3-smbus i2c-tools)    
    fi
else
    # Ubuntu has serial and i2c enabled
    if [ "$CHECKDEVICE" = "eon" ]
    then
        pkglist=(raspi-gpio python3-rpi.gpio python3-smbus i2c-tools hddtemp)    
    else
        pkglist=(python3-rpi.gpio python3-smbus i2c-tools)
    fi
fi

for curpkg in ${pkglist[@]}; do
    sudo apt-get install -y $curpkg
    RESULT=$(argon_check_pkg "$curpkg")
    if [ "NG" == "$RESULT" ]
    then
        echo "********************************************************************"
        echo "Please also connect device to the internet and restart installation."
        echo "********************************************************************"
        exit
    fi
done

# Ubuntu Mate for RPi has raspi-config too
command -v raspi-config &> /dev/null
if [ $? -eq 0 ]
then
    # Enable i2c and serial
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_serial 2
fi

# Fan Setup
basename="argonone"
daemonname=$basename"d"
irconfigscript=$INSTALLATIONFOLDER/${basename}-ir
fanconfigscript=$INSTALLATIONFOLDER/${basename}-fanconfig.sh
powerbuttonscript=$INSTALLATIONFOLDER/$daemonname.py
unitconfigfile=/etc/argonunits.conf
daemonconfigfile=/etc/$daemonname.conf
daemonfanservice=/lib/systemd/system/$daemonname.service

daemonhddconfigfile=/etc/${daemonname}-hdd.conf

# Fan Config Script
sudo curl -L $ARGONDOWNLOADSERVER/argonone-fanconfig.sh -o $fanconfigscript --silent
sudo chmod 755 $fanconfigscript


# Fan Daemon/Service Files
sudo curl -L $ARGONDOWNLOADSERVER/argononed.py -o $powerbuttonscript --silent
sudo curl -L $ARGONDOWNLOADSERVER/argononed.service -o $daemonfanservice --silent
sudo chmod 644 $daemonfanservice

# IR Files
sudo curl -L $ARGONDOWNLOADSERVER/argonone-irconfig.sh -o $irconfigscript --silent
sudo chmod 755 $irconfigscript

# Other utility scripts
sudo curl -L $ARGONDOWNLOADSERVER/argon-versioninfo.sh -o $versioninfoscript --silent
sudo chmod 755 $versioninfoscript

sudo curl -L $ARGONDOWNLOADSERVER/argonsysinfo.py -o $INSTALLATIONFOLDER/argonsysinfo.py --silent

sudo curl -L $ARGONDOWNLOADSERVER/argononed.py -o $powerbuttonscript --silent

sudo curl -L $ARGONDOWNLOADSERVER/argon-unitconfig.sh -o $unitconfigscript --silent
sudo chmod 755 $unitconfigscript

# Generate default Fan config file if non-existent
if [ ! -f $daemonconfigfile ]; then
    sudo touch $daemonconfigfile
    sudo chmod 666 $daemonconfigfile

    echo '#' >> $daemonconfigfile
    echo '# Argon Fan Speed Configuration (CPU)' >> $daemonconfigfile
    echo '#' >> $daemonconfigfile
    echo '55=30' >> $daemonconfigfile
    echo '60=55' >> $daemonconfigfile
    echo '65=100' >> $daemonconfigfile
fi

if [ "$CHECKDEVICE" = "eon" ]
then
    if [ ! -f $daemonhddconfigfile ]; then
        sudo touch $daemonhddconfigfile
        sudo chmod 666 $daemonhddconfigfile

        echo '#' >> $daemonhddconfigfile
        echo '# Argon Fan Speed Configuration (HDD)' >> $daemonhddconfigfile
        echo '#' >> $daemonhddconfigfile
        echo '35=30' >> $daemonhddconfigfile
        echo '40=55' >> $daemonhddconfigfile
        echo '45=100' >> $daemonhddconfigfile
    fi
fi

# Generate default Unit config file if non-existent
if [ ! -f $unitconfigfile ]; then
    sudo touch $unitconfigfile
    sudo chmod 666 $unitconfigfile

    echo '#' >> $unitconfigfile
fi


if [ "$CHECKDEVICE" = "eon" ]
then
    # RTC Setup
    basename="argoneon"
    daemonname=$basename"d"

    rtcconfigfile=/etc/argoneonrtc.conf
    rtcconfigscript=$INSTALLATIONFOLDER/${basename}-rtcconfig.sh
    daemonrtcservice=/lib/systemd/system/$daemonname.service
    rtcdaemonscript=$INSTALLATIONFOLDER/$daemonname.py

    oledconfigscript=$INSTALLATIONFOLDER/${basename}-oledconfig.sh
    oledlibscript=$INSTALLATIONFOLDER/${basename}oled.py
    oledconfigfile=/etc/argoneonoled.conf

    # Generate default RTC config file if non-existent
    if [ ! -f $rtcconfigfile ]; then
        sudo touch $rtcconfigfile
        sudo chmod 666 $rtcconfigfile

        echo '#' >> $rtcconfigfile
        echo '# Argon RTC Configuration' >> $rtcconfigfile
        echo '#' >> $rtcconfigfile
    fi
    # Generate default OLED config file if non-existent
    if [ ! -f $oledconfigfile ]; then
        sudo touch $oledconfigfile
        sudo chmod 666 $oledconfigfile

        echo '#' >> $oledconfigfile
        echo '# Argon OLED Configuration' >> $oledconfigfile
        echo '#' >> $oledconfigfile
        echo 'switchduration=30' >> $oledconfigfile
        echo 'screenlist="clock cpu storage bandwidth raid ram temp ip"' >> $oledconfigfile
    fi


    # RTC Config Script
    sudo curl -L $ARGONDOWNLOADSERVER/argoneon-rtcconfig.sh -o $rtcconfigscript --silent
    sudo chmod 755 $rtcconfigscript

    # RTC Daemon/Service Files
    sudo curl -L $ARGONDOWNLOADSERVER/argoneond.py -o $rtcdaemonscript --silent
    sudo curl -L $ARGONDOWNLOADSERVER/argoneond.service -o $daemonrtcservice --silent
    sudo curl -L $ARGONDOWNLOADSERVER/argoneonoled.py -o $oledlibscript --silent
    sudo chmod 644 $daemonrtcservice

    # OLED Config Script
    sudo curl -L $ARGONDOWNLOADSERVER/argoneon-oledconfig.sh -o $oledconfigscript --silent 
    sudo chmod 755 $oledconfigscript


    if [ ! -d $INSTALLATIONFOLDER/oled ]
    then
        sudo mkdir $INSTALLATIONFOLDER/oled
    fi

    for binfile in font8x6 font16x12 font32x24 font64x48 font16x8 font24x16 font48x32 bgdefault bgram bgip bgtemp bgcpu bgraid bgstorage bgtime
    do
        sudo curl -L $ARGONDOWNLOADSERVER/oled/${binfile}.bin -o $INSTALLATIONFOLDER/oled/${binfile}.bin --silent 
    done
fi


# Argon Uninstall Script
sudo  curl -L $ARGONDOWNLOADSERVER/argon-uninstall.sh -o $uninstallscript --silent
sudo chmod 755 $uninstallscript

# Argon Shutdown script
sudo curl -L $ARGONDOWNLOADSERVER/argon-shutdown.sh -o $shutdownscript --silent
sudo chmod 755 $shutdownscript

# Argon Status script
sudo curl -L $ARGONDOWNLOADSERVER/argon-status.py -o $statusscript --silent
sudo chmod 755 $statusscript
if [ -f /usr/bin/$statuscmd ]
then
    sudo rm /usr/bin/$statuscmd
fi
sudo ln -s $statusscript /usr/bin/$statuscmd

# Argon Config Script
if [ -f $configscript ]; then
    sudo rm $configscript
fi
sudo touch $configscript

# To ensure we can write the following lines
sudo chmod 666 $configscript

echo '#!/bin/bash' >> $configscript

echo 'echo "--------------------------"' >> $configscript
echo 'echo "Argon Configuration Tool"' >> $configscript
echo "$versioninfoscript simple" >> $configscript
echo 'echo "--------------------------"' >> $configscript

echo 'get_number () {' >> $configscript
echo '    read curnumber' >> $configscript
echo '    if [ -z "$curnumber" ]' >> $configscript
echo '    then' >> $configscript
echo '        echo "-2"' >> $configscript
echo '        return' >> $configscript
echo '    elif [[ $curnumber =~ ^[+-]?[0-9]+$ ]]' >> $configscript
echo '    then' >> $configscript
echo '        if [ $curnumber -lt 0 ]' >> $configscript
echo '        then' >> $configscript
echo '            echo "-1"' >> $configscript
echo '            return' >> $configscript
echo '        elif [ $curnumber -gt 100 ]' >> $configscript
echo '        then' >> $configscript
echo '            echo "-1"' >> $configscript
echo '            return' >> $configscript
echo '        fi    ' >> $configscript
echo '        echo $curnumber' >> $configscript
echo '        return' >> $configscript
echo '    fi' >> $configscript
echo '    echo "-1"' >> $configscript
echo '    return' >> $configscript
echo '}' >> $configscript
echo '' >> $configscript

echo 'mainloopflag=1' >> $configscript
echo 'while [ $mainloopflag -eq 1 ]' >> $configscript
echo 'do' >> $configscript
echo '    echo' >> $configscript
echo '    echo "Choose Option:"' >> $configscript
echo '    echo "  1. Configure Fan"' >> $configscript
echo '    echo "  2. Configure IR"' >> $configscript

uninstalloption="4"

if [ "$CHECKDEVICE" = "eon" ]
then
    # ArgonEON Has RTC
    echo '    echo "  3. Configure RTC and/or Schedule"' >> $configscript
    echo '    echo "  4. Configure OLED"' >> $configscript
    uninstalloption="6"
fi

unitsoption=$(($uninstalloption-1))
echo "    echo \"  $unitsoption. Configure Units\"" >> $configscript

echo "    echo \"  $uninstalloption. Uninstall\"" >> $configscript
echo '    echo ""' >> $configscript
echo '    echo "  0. Exit"' >> $configscript
echo "    echo -n \"Enter Number (0-$uninstalloption):\"" >> $configscript
echo '    newmode=$( get_number )' >> $configscript


echo '    if [ $newmode -eq 0 ]' >> $configscript
echo '    then' >> $configscript
echo '        echo "Thank you."' >> $configscript
echo '        mainloopflag=0' >> $configscript
echo '    elif [ $newmode -eq 1 ]' >> $configscript
echo '    then' >> $configscript

if [ "$CHECKDEVICE" = "eon" ]
then
    echo '        echo "Choose Triggers:"' >> $configscript
    echo '        echo "  1. CPU Temperature"' >> $configscript
    echo '        echo "  2. HDD Temperature"' >> $configscript
    echo '        echo ""' >> $configscript
    echo '        echo "  0. Cancel"' >> $configscript
    echo "        echo -n \"Enter Number (0-2):\"" >> $configscript
    echo '        submode=$( get_number )' >> $configscript

    echo '        if [ $submode -eq 1 ]' >> $configscript
    echo '        then' >> $configscript
    echo "            $fanconfigscript" >> $configscript
    echo '            mainloopflag=0' >> $configscript
    echo '        elif [ $submode -eq 2 ]' >> $configscript
    echo '        then' >> $configscript
    echo "            $fanconfigscript hdd" >> $configscript
    echo '            mainloopflag=0' >> $configscript
    echo '        fi' >> $configscript

else
    echo "        $fanconfigscript" >> $configscript
    echo '        mainloopflag=0' >> $configscript
fi

echo '    elif [ $newmode -eq 2 ]' >> $configscript
echo '    then' >> $configscript
echo "        $irconfigscript" >> $configscript
echo '        mainloopflag=0' >> $configscript

if [ "$CHECKDEVICE" = "eon" ]
then
    echo '    elif [ $newmode -eq 3 ]' >> $configscript
    echo '    then' >> $configscript
    echo "        $rtcconfigscript" >> $configscript
    echo '        mainloopflag=0' >> $configscript
    echo '    elif [ $newmode -eq 4 ]' >> $configscript
    echo '    then' >> $configscript
    echo "        $oledconfigscript" >> $configscript
    echo '        mainloopflag=0' >> $configscript
fi

echo "    elif [ \$newmode -eq $unitsoption ]" >> $configscript
echo '    then' >> $configscript
echo "        $unitconfigscript" >> $configscript
echo '        mainloopflag=0' >> $configscript

echo "    elif [ \$newmode -eq $uninstalloption ]" >> $configscript
echo '    then' >> $configscript
echo "        $uninstallscript" >> $configscript
echo '        mainloopflag=0' >> $configscript
echo '    fi' >> $configscript
echo 'done' >> $configscript

sudo chmod 755 $configscript

# Desktop Icon
shortcutfile="/home/pi/Desktop/argonone-config.desktop"
if [ "$CHECKPLATFORM" = "Raspbian" ] && [ -d "/home/pi/Desktop" ]
then
    terminalcmd="lxterminal --working-directory=/home/pi/ -t"
    if  [ -f "/home/pi/.twisteros.twid" ]
    then
        terminalcmd="xfce4-terminal --default-working-directory=/home/pi/ -T"
    fi
    imagefile=ar1config.png
    if [ "$CHECKDEVICE" = "eon" ]
    then
        imagefile=argoneon.png
    fi
    sudo curl -L $ARGONDOWNLOADSERVER/$imagefile -o /usr/share/pixmaps/$imagefile --silent
    if [ -f $shortcutfile ]; then
        sudo rm $shortcutfile
    fi

    # Create Shortcuts
    echo "[Desktop Entry]" > $shortcutfile
    echo "Name=Argon Configuration" >> $shortcutfile
    echo "Comment=Argon Configuration" >> $shortcutfile
    echo "Icon=/usr/share/pixmaps/$imagefile" >> $shortcutfile
    echo 'Exec='$terminalcmd' "Argon Configuration" -e '$configscript >> $shortcutfile
    echo "Type=Application" >> $shortcutfile
    echo "Encoding=UTF-8" >> $shortcutfile
    echo "Terminal=false" >> $shortcutfile
    echo "Categories=None;" >> $shortcutfile
    chmod 755 $shortcutfile
fi

configcmd="$(basename -- $configscript)"

if [ "$setupmode" = "Setup" ]
then
    if [ -f "/usr/bin/$configcmd" ]
    then
        sudo rm /usr/bin/$configcmd
    fi
    sudo ln -s $configscript /usr/bin/$configcmd

    if [ "$CHECKDEVICE" = "one" ]
    then
        sudo ln -s $configscript /usr/bin/argonone-config
        sudo ln -s $uninstallscript /usr/bin/argonone-uninstall
        sudo ln -s $irconfigscript /usr/bin/argonone-ir
    fi


    # Enable and Start Service(s)
    sudo systemctl daemon-reload
    sudo systemctl enable argononed.service
    sudo systemctl start argononed.service
    if [ "$CHECKDEVICE" = "eon" ]
    then
        sudo systemctl enable argoneond.service
        sudo systemctl start argoneond.service
    fi
else
    sudo systemctl daemon-reload
    sudo systemctl restart argononed.service
    if [ "$CHECKDEVICE" = "eon" ]
    then
        sudo systemctl restart argoneond.service
    fi
fi

echo "*********************"
echo "  $setupmode Completed "
echo "*********************"
$versioninfoscript
echo 
echo "Use '$configcmd' to configure device"
echo
