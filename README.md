# Argon-EON
This repository contains modificatoions to the code distributed by Argon40 (www.argon40.com) for their EON product

## Supported OS Versions

Currently supports 32 and 64 bit versions of Raspberry PI OS, as well as:

- Ubuntu 21.04, 21.10 and 22.04
- DietPi 64 bit Bullseye based.  Make sure you have enabled I2C, and have rebooted the system.

## Install

To install, simply execute the following on the node:
```
curl -L https://raw.githubusercontent.com/JeffCurless/argoneon/main/argoneon.sh | bash
```

After intall you will want to modify the fan configuration to match your environment.  You can change the triggers by using argon-config, or simply editing the files (/etc/argononed.conf, and /etc/argononed-hdd.conf)  The fan will be triggered by one of two separate settings, the CPU temperature, or the HDD temperature.  

Default Temperature triggers:
- HDD
  - 35 - 30
  - 40 - 55
  - 45 - 100
   
- CPU
  - 55 - 30
  - 60 - 55
  - 65 - 100

Which ever component passes the set threashold first will cause the fan to turn on.   For instance, if your HDD temp hits 35C, the fan will turn on at 30%, even if the CPU temp is running below 55C.

## Uninstall

Just like the original simply execute:

```
sudo /etc/argon/argon-uninstall
```

or run argon-config, and select the uninstall option.

## Put back the Original

If for some reason you don't like the changes, run argon-config and uninstall.  Then reinstall the original scripts:

```
curl http://download.argon40.com/argoneon.sh | bash
```

## argon-status

```
usage: argon-status [-h] [-v] [-a] [-c] [-d] [-f] [-i] [-m] [-r] [-s] [-t] [-u] [--hddtemp]

optional arguments:
  -h, --help     show this help message and exit
  -v, --version  Display the version of the argon scripts.
  -a, --all      Display full status of the Argon EON.
  -c, --cpu      Display the current CPU utilization.
  -d, --devices  Display informaton about devices in the EON.
  -f, --fan      Get current fan speed.
  -i, --ip       Display currently configured IP addresses.
  -m, --memory   Display memory utilization on the EON.
  -r, --raid     Display current state of the raid Array if it exists.
  -s, --storage  Display information about the storage system.
  -t, --temp     Display information about the current temperature.
  -u, --hdduse   Display disk utilization.
  --hddtemp      Display the temperature of the storage devices.
```

When used with no arguments, argon-status will display as if argon-status --devices --ip was used.  If you do not wish to have this as a default, set the ARGON_STATUS_DEFAULT to what you wish the default to be, such as 
```
export ARGON_STATUS_DEFAULT="-t --hddtemp -f"
```
