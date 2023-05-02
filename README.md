# Argon-EON
This repository contains modifications to the code distributed by Argon40 (www.argon40.com) for their EON product

## Supported OS Versions

Currently supports 32 and 64 bit versions of Raspberry PI OS, as well as:

- Ubuntu 21.04, 21.10, 22.04 and 23.04
- DietPi 64 bit Bullseye based.  Make sure you have enabled I2C, and have rebooted the system.
- Manjaro Linux support has been added.

## Differences from Argon40's Scripts

### argoneon.conf

Modified the code to support one main configuration file.  All the other files, with the exception of the rtc configuration file have been moved into /etc/argoneon.conf.  If this file does not exist the code will generate a new version when the argononed.service starts.  All defaults will be set, including a better (well, I think it is) set of default fan settings.

Default ConfigFile:
```
[General]
temperature = C
debug = N

[OLED]
screenduration = 30
screensaver = 120
screenlist = clock cpu storage bandwidth raid ram temp ip
enabled = Y

[CPUFan]
55.0 = 30
60.0 = 55
65.0 = 100

[HDDFan]
40.0 = 25
44.0 = 30
46.0 = 35
48.0 = 40
50.0 = 50
52.0 = 55
54.0 = 60
60.0 = 100
```

Setting debug = Y in the General section enables debug tracking of the fan settings in the file /var/log/argoneon.log.  This is a good mechanism to determine if the fan setting are actually working.  If you have issues with fan settings, please enable the logging, restart the service and send me the log output after 10 minutes or so.

### argon-status

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

### Monitoring the NVME Temperature

This code also adds the NVME drive into the list of devices it obtains the temerature for.  You may be annoyed with this, as it will set the fan speed earlier, unless you have a good heat sync on your NVME device.
## Install

To install, simply execute the following on the node:
```
curl -L https://raw.githubusercontent.com/JeffCurless/argoneon/main/argoneon.sh | bash
```

After intall you may want to modify the fan configuration to match your environment  You can change the default temperature setting by editing the file /etc/argoneon.conf.  The fan will be triggered by one of two separate settings, the CPU temperature, or the HDD temperature.    Which ever component passes the set threashold first will cause the fan to turn on.   For instance, if your HDD temp hits 35C, the fan will turn on at 30%, even if the CPU temp is running below 55C.

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

