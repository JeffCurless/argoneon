# Argon-EON
This repository contains modificatoions to the code distributed by Argon40 (www.argon40.com) for their EON product

## Supported OS Versions

Currently supports 32 and 64 bit versions of Raspberry PI OS, as well as:

* Ubuntu 21.04, 21.10 and 22.04
* DietPi 64 bit Bullseye based.  Make sure you have enabled I2C, and have rebooted the system.

## Install

To install, simply execute the following on the node:
```
curl -L https://raw.githubusercontent.com/JeffCurless/argoneon/main/argoneon.sh | bash
```

After intall you will want to modify the fan configuration to match your environment.  The fan will be triggered by one of two separate settings, the CPU temperatoure, or the HDD temperature.  

Default Temperature triggers:
HDD - 35, 40 and 45
CPU - 55, 60 and 65

Which ever component passes the set threashold first will cause the fan to turn on.

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
