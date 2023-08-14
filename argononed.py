#!/usr/bin/python3

#
# This script set fan speed and monitor power button events.
#
# Fan Speed is set by sending 0 to 100 to the MCU (Micro Controller Unit)
# The values will be interpreted as the percentage of fan speed, 100% being maximum
#
# Power button events are sent as a pulse signal to BCM Pin 4 (BOARD P7)
# A pulse width of 20-30ms indicates reboot request (double-tap)
# A pulse width of 40-50ms indicates shutdown request (hold and release after 3 secs)
#
# Additional comments are found in each function below
#
# Standard Deployment/Triggers:
#  * Raspbian, OSMC: Runs as service via /lib/systemd/system/argononed.service
#  * lakka, libreelec: Runs as service via /storage/.config/system.d/argononed.service
#  * recalbox: Runs as service via /etc/init.d/
#

# For Libreelec/Lakka, note that we need to add system paths
# import sys
# sys.path.append('/storage/.kodi/addons/virtual.rpi-tools/lib')
import RPi.GPIO as GPIO


from pathlib import Path
import sys
import os
import time

from threading import Thread
from queue import Queue

sys.path.append("/etc/argon/")
from argonsysinfo import *
from argonlogging import *
from argonconfig import *
from version import *

# Initialize I2C Bus
import smbus

rev = GPIO.RPI_REVISION
if rev == 2 or rev == 3:
    bus=smbus.SMBus(1)
else:
    bus=smbus.SMBus(0)

CONFIG_FILE='/etc/argoneon.conf'
OLED_ENABLED=False

#
# Enable logging
#
if os.path.exists("/etc/argon/argoneonoled.py"):
    import datetime
    from argoneonoled import *
    OLED_ENABLED=True

#
# Enable debug logging if requested
#
enableLogging( loadDebugMode() )

ADDR_FAN=0x1a
PIN_SHUTDOWN=4

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_SHUTDOWN, GPIO.IN,  pull_up_down=GPIO.PUD_DOWN)

# This function is the thread that monitors activity in our shutdown pin
# The pulse width is measured, and the corresponding shell command will be issued

def shutdown_check(writeq):
    while True:
        pulsetime = 1
        GPIO.wait_for_edge(PIN_SHUTDOWN, GPIO.RISING)
        time.sleep(0.01)
        while GPIO.input(PIN_SHUTDOWN) == GPIO.HIGH:
            time.sleep(0.01)
            pulsetime += 1
        if pulsetime >=2 and pulsetime <=3:
            # Testing
            #writeq.put("OLEDSWITCH")
            writeq.put("OLEDSTOP")
            os.system("reboot")
        elif pulsetime >=4 and pulsetime <=5:
            writeq.put("OLEDSTOP")
            os.system("shutdown now -h")
        elif pulsetime >=6 and pulsetime <=7:
            writeq.put("OLEDSWITCH")

#
#
#
def get_fanspeed(tempval, configlist):
    """
    This function converts the corresponding fanspeed for the given temperature the
    configutation data is a list of strings in the form "<temperature>:<speed>"
    """
    retval = 0
    if len(configlist) > 0:
        for k in configlist.keys():
            if tempval >= float(k):
                retval=int(configlist[k])
                logDebug( "Temperature (" + str(tempval) + ") >= " + str(k) + " suggesting fanspeed of " + str(retval) )
    logDebug( "Returning fanspeed of " + str(retval))
    return retval


# This function is the thread that monitors temperature and sets the fan speed
# The value is fed to get_fanspeed to get the new fan speed
# To prevent unnecessary fluctuations, lowering fan speed is delayed by 30 seconds
#
# Location of config file varies based on OS
#

def setFanOff ():
    setFanSpeed (overrideSpeed = 0)

def setFanFlatOut ():
    setFanSpeed (overrideSpeed = 100)

def setFanSpeed (overrideSpeed : int = None, instantaneous : bool = True):
    """
    Set the fanspeed.  Support override (overrideSpeed) with a specific value, and 
    an instantaneous change.  Some hardware does not like the sudden change, it wants the
    speed set to 100% THEN changed to the new value.  Not really sure why this is.
    """
    prevspeed    = argonsysinfo_getCurrentFanSpeed()
    if not prevspeed:
        prevspeed = 0
        argonsysinfo_recordCurrentFanSpeed( prevspeed )
    
    if overrideSpeed is not None:
        newspeed = overrideSpeed
    else:
        newspeed = max([get_fanspeed(argonsysinfo_getcputemp(), loadCPUFanConfig())
                       ,get_fanspeed(argonsysinfo_getmaxhddtemp(), loadHDDFanConfig())
                       ]
                      )
        if newspeed < prevspeed and not instantaneous:
            # Pause 30s before speed reduction to prevent fluctuations
            time.sleep(30)

    # Make sure the value is in 0-100 range
    newspeed = max([min([100,newspeed]),0])
    if overrideSpeed is not None or (prevspeed != newspeed):
        try:
            if newspeed > 0:
                # Spin up to prevent issues on older units
                bus.write_byte(ADDR_FAN,100)
                time.sleep(1)
            bus.write_byte(ADDR_FAN,int(newspeed))
            logging.debug( "writing to fan port, speed " + str(newspeed))
            argonsysinfo_recordCurrentFanSpeed( newspeed )
        except IOError:
            logError( "Error trying o update fan speed.")
            return prevspeed
    return newspeed

def temp_check():
    """
    Main thread for processing the temperature check functonality.  We just try and set the fan speed once
    a minute.  However we do want to start with the fan *OFF*.
    """
    setFanOff()
    while True:
        setFanSpeed (instantaneous = False)
        time.sleep(60)
#
# This function is the thread that updates OLED
#
def display_loop(readq):
    weekdaynamelist = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    monthlist = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    oledscreenwidth = oled_getmaxX()

    fontwdSml = 6    # Maps to 6x8
    fontwdReg = 8    # Maps to 8x16
    stdleftoffset = 54

    temperature="C"
    temperature = loadTempConfig()

    print( "Temperature config is " + temperature )
    screensavermode = False
    screensaversec = 120
    screensaverctr = 0

    screenenabled = ["clock", "ip"]
    prevscreen = ""
    curscreen = ""
    screenid = 0
    screenjogtime = 0
    screenjogflag = 0  # start with screenid 0
    cpuusagelist = []
    curlist = []

    tmpconfig=loadOLEDConfig()  

    if "screensaver" in tmpconfig:
        screensaversec = int(tmpconfig["screensaver"])
    if "screenduration" in tmpconfig:
        screenjogtime = int(tmpconfig["screenduration"])
    if "screenlist" in tmpconfig:
        screenenabled = tmpconfig["screenlist"].replace("\"","").split(" ")

    if "enabled" in tmpconfig:
        if tmpconfig["enabled"] == "N":
            screenenabled = []

    #
    # Setup some variables to help calculate bandwidth
    #
    timespan = 1
    prevData = argonsysinfo_diskusage()
    prevTime = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

    while len(screenenabled) > 0:
        if len(curlist) == 0 and screenjogflag == 1:
            # Reset Screen Saver
            screensavermode = False
            screensaverctr = 0

            # Update screen info
            screenid = screenid + screenjogflag
            if screenid >= len(screenenabled):
                screenid = 0
        prevscreen = curscreen
        curscreen = screenenabled[screenid]

        if screenjogtime == 0:
            # Resets jogflag (if switched manually)
            screenjogflag = 0
        else:
            screenjogflag = 1

        needsUpdate = False
        if curscreen == "cpu":
            # CPU Usage
            if len(curlist) == 0:
                try:
                    if len(cpuusagelist) == 0:
                        cpuusagelist = argonsysinfo_listcpuusage()
                    curlist = cpuusagelist
                except:
                    logError( "Error processing information for CPU display")
                    curlist = []
            if len(curlist) > 0:
                oled_loadbg("bgcpu")

                # Display List
                yoffset = 0
                tmpmax = 4
                while tmpmax > 0 and len(curlist) > 0:
                    curline = ""
                    tmpitem = curlist.pop(0)
                    curline = tmpitem["title"]+": "+str(tmpitem["value"])+"%"
                    oled_writetext(curline, stdleftoffset, yoffset, fontwdSml)
                    oled_drawfilledrectangle(stdleftoffset, yoffset+12, int((oledscreenwidth-stdleftoffset-4)*tmpitem["value"]/100), 2)
                    tmpmax = tmpmax - 1
                    yoffset = yoffset + 16

                needsUpdate = True
            else:
                # Next page due to error/no data
                screenjogflag = 1
        elif curscreen == "storage":
            # Storage Info
            if len(curlist) == 0:
                try:
                    tmpobj = argonsysinfo_listhddusage()
                    for curdev in tmpobj:
                        curlist.append({"title": curdev, "value": argonsysinfo_kbstr(tmpobj[curdev]['total']), "usage": int(tmpobj[curdev]['percent']) })
                    #curlist = argonsysinfo_liststoragetotal()
                except:
                    logError( "Error processing information for STORAGE display")
                    curlist = []
            if len(curlist) > 0:
                oled_loadbg("bgstorage")

                yoffset = 16
                tmpmax = 3
                while tmpmax > 0 and len(curlist) > 0:
                    tmpitem = curlist.pop(0)
                    # Right column first, safer to overwrite white space
                    oled_writetextaligned(tmpitem["value"], 77, yoffset, oledscreenwidth-77, 2, fontwdSml)
                    oled_writetextaligned(str(tmpitem["usage"])+"%", 50, yoffset, 74-50, 2, fontwdSml)
                    tmpname = tmpitem["title"]
                    if len(tmpname) > 8:
                        tmpname = tmpname[0:8]
                    oled_writetext(tmpname, 0, yoffset, fontwdSml)

                    tmpmax = tmpmax - 1
                    yoffset = yoffset + 16
                needsUpdate = True
            else:
                # Next page due to error/no data
                screenjogflag = 1

        elif curscreen == "bandwidth":
            # Bandwidth info
            if len(curlist) == 0:
                try:
                    diskdata = argonsysinfo_diskusage()
                    for istop in diskdata:
                        for istart in prevData:
                            if istop['disk'] == istart['disk']:
                                istart['readsector']  = istop['readsector'] - istart['readsector']
                                istart['writesector'] = istop['writesector'] - istart['writesector']
                    curlist   = prevData
                    prevData  = diskdata
                    stoptime  = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
                    timespan = (stoptime - prevTime)/1000000000
                    prevTime  = stoptime
                except:
                    logError( "Error processing data for BANDWIDTH display")
                    curlist = []
            if len(curlist) > 0:

                oled_clearbuffer()
                oled_writetextaligned( "BANDWIDTH", 0, 0, oledscreenwidth, 1, fontwdSml)
                oled_writetextaligned( "Write", 77, 16, oledscreenwidth-77, 2, fontwdSml)
                oled_writetextaligned( "Read",  50, 16, 74-50,              2, fontwdSml)
                oled_writetext( "Device", 0, 16, fontwdSml )

                itemcount = 2
                yoffset   = 32
                while itemcount > 0 and len(curlist) >0:
                    item = curlist.pop(0)
                    bandwidth = int((item['writesector']/2)/timespan)
                    oled_writetextaligned( argonsysinfo_kbstr(bandwidth), 77, yoffset, oledscreenwidth-77, 2, fontwdSml )
                    bandwidth = int((item['readsector']/2)/timespan)
                    oled_writetextaligned( argonsysinfo_kbstr(bandwidth), 50, yoffset, 74-50, 2, fontwdSml )
                    oled_writetext( item['disk'], 0, yoffset, fontwdSml )
                    itemcount = itemcount - 1
                    yoffset   = yoffset + 16

                needsUpdate = True
            else:
                # Next Page due to error/no data
                screenjogFlag = 1

        elif curscreen == "raid":
            # Raid Info
            if len(curlist) == 0:
                try:
                    tmpobj = argonsysinfo_listraid()
                    curlist = tmpobj['raidlist']
                except:
                    logError( "Error processing display of RAID information.")
                    curlist = []
            if len(curlist) > 0:
                oled_loadbg("bgraid")
                tmpitem = curlist.pop(0)
                oled_writetextaligned(tmpitem["title"], 0, 0, stdleftoffset, 1, fontwdSml)
                oled_writetextaligned(tmpitem["value"], 0, 8, stdleftoffset, 1, fontwdSml)
                oled_writetextaligned(argonsysinfo_kbstr(tmpitem["info"]["size"]), 0, 56, stdleftoffset, 1, fontwdSml)
                rebuild = tmpitem['info']['resync']
                statusList = tmpitem['info']['state'].split(", ")
                if len(statusList) == 1:
                    status = statusList[0]
                if len(statusList) == 2:
                    status = statusList[1]
                if len(statusList) >=3:
                    status = statusList[2]
                status = status.capitalize()
                oled_writetext( status, stdleftoffset, 8, fontwdSml )
                if len(rebuild) > 0:
                    percent = rebuild.split( " " )
                    if status.lower() == "checking":
                        label = "Progess: "
                    else:
                        label = "Rebuild: "
                    oled_writetext(label + percent[0], stdleftoffset, 16, fontwdSml)
                oled_writetext("Active:"+str(int(tmpitem["info"]["active"]))+"/"+str(int(tmpitem["info"]["devices"])), stdleftoffset, 32, fontwdSml)
                oled_writetext("Working:"+str(int(tmpitem["info"]["working"]))+"/"+str(int(tmpitem["info"]["devices"])), stdleftoffset, 40, fontwdSml)
                oled_writetext("Failed:"+str(int(tmpitem["info"]["failed"]))+"/"+str(int(tmpitem["info"]["devices"])), stdleftoffset, 48, fontwdSml)
                needsUpdate = True
            else:
                # Next page due to error/no data
                screenjogflag = 1

        elif curscreen == "ram":
            # RAM
            try:
                oled_loadbg("bgram")
                tmpraminfo = argonsysinfo_getram()
                oled_writetextaligned(tmpraminfo["percent"]+"%", stdleftoffset, 8, oledscreenwidth-stdleftoffset, 1, fontwdReg)
                oled_writetextaligned("of", stdleftoffset, 24, oledscreenwidth-stdleftoffset, 1, fontwdReg)
                oled_writetextaligned(tmpraminfo["gb"]+"GB", stdleftoffset, 40, oledscreenwidth-stdleftoffset, 1, fontwdReg)
                needsUpdate = True
            except:
                logError( "Error processing information for RAM display")
                needsUpdate = False
                # Next page due to error/no data
                screenjogflag = 1
        elif curscreen == "temp":
            # Temp
            try:
                oled_loadbg("bgtemp")
                hddtempctr = 0
                maxcval = 0
                mincval = 200


                # Get min/max of hdd temp
                hddtempobj = argonsysinfo_gethddtemp()
                for curdev in hddtempobj:
                    if hddtempobj[curdev] < mincval:
                        mincval = hddtempobj[curdev]
                    if hddtempobj[curdev] > maxcval:
                        maxcval = hddtempobj[curdev]
                    hddtempctr = hddtempctr + 1

                cpucval = argonsysinfo_getcputemp()
                if hddtempctr > 0:
                    alltempobj = {"cpu": cpucval,"hdd min": mincval, "hdd max": maxcval}
                    # Update max C val to CPU Temp if necessary
                    if maxcval < cpucval:
                        maxcval = cpucval

                    displayrowht = 8
                    displayrow = 8
                    for curdev in alltempobj:
                        if temperature == "C":
                            # Celsius
                            tmpstr = str(alltempobj[curdev])
                            if len(tmpstr) > 4:
                                tmpstr = tmpstr[0:4]
                        else:
                            # Fahrenheit
                            tmpstr = str(32+9*(alltempobj[curdev])/5)
                            if len(tmpstr) > 5:
                                tmpstr = tmpstr[0:5]
                        if len(curdev) <= 3:
                            oled_writetext(curdev.upper()+": "+ tmpstr+ chr(167) +temperature, stdleftoffset, displayrow, fontwdSml)

                        else:
                            oled_writetext(curdev.upper()+":", stdleftoffset, displayrow, fontwdSml)

                            oled_writetext("     "+ tmpstr+ chr(167) +temperature, stdleftoffset, displayrow+displayrowht, fontwdSml)
                        displayrow = displayrow + displayrowht*2
                else:
                    maxcval = cpucval
                    if temperature == "C":
                        # Celsius
                        tmpstr = str(cpucval)
                        if len(tmpstr) > 4:
                            tmpstr = tmpstr[0:4]
                    else:
                        # Fahrenheit
                        tmpstr = str(32+9*(cpucval)/5)
                        if len(tmpstr) > 5:
                            tmpstr = tmpstr[0:5]

                    oled_writetextaligned(tmpstr+ chr(167) +temperature, stdleftoffset, 24, oledscreenwidth-stdleftoffset, 1, fontwdReg)

                # Temperature Bar: 40C is min, 80C is max
                maxht = 21
                barht = int(maxht*(maxcval-40)/40)
                if barht > maxht:
                    barht = maxht
                elif barht < 1:
                    barht = 1
                oled_drawfilledrectangle(24, 20+(maxht-barht), 3, barht, 2)

                needsUpdate = True
            except:
                logError( "Error processing temerature information for TEMP display" )
                needsUpdate = False
                # Next page due to error/no data
                screenjogflag = 1
        elif curscreen == "ip":
            # IP Address
            try:
                if len(curlist) == 0:
                    curlist = argonsysinfo_getipList()
            except:
                logError( "Error processing information for IP display")
                curlist = []

            if len(curlist) > 0:
                item = curlist.pop(0)
                oled_loadbg("bgip")
                oled_writetextaligned(item[0], 0, 0, oledscreenwidth, 1, fontwdReg)
                oled_writetextaligned(item[1], 0,16, oledscreenwidth, 1, fontwdReg)
                needsUpdate = True
            else:
                needsUpdate = False
                # Next page due to error/no data
                screenjogflag = 1
        else:
            try:
                oled_loadbg("bgtime")
                # Date and Time HH:MM
                curtime = datetime.datetime.now()

                # Month/Day
                outstr = str(curtime.day).strip()
                if len(outstr) < 2:
                    outstr = " "+outstr
                outstr = monthlist[curtime.month-1]+outstr
                oled_writetextaligned(outstr, stdleftoffset, 8, oledscreenwidth-stdleftoffset, 1, fontwdReg)

                # Day of Week
                oled_writetextaligned(weekdaynamelist[curtime.weekday()], stdleftoffset, 24, oledscreenwidth-stdleftoffset, 1, fontwdReg)

                # Time
                outstr = str(curtime.minute).strip()
                if len(outstr) < 2:
                    outstr = "0"+outstr
                outstr = str(curtime.hour)+":"+outstr
                if len(outstr) < 5:
                    outstr = "0"+outstr
                oled_writetextaligned(outstr, stdleftoffset, 40, oledscreenwidth-stdleftoffset, 1, fontwdReg)

                needsUpdate = True
            except:
                logError( "Error processing information of TIME display" )
                needsUpdate = False
                # Next page due to error/no data
                screenjogflag = 1

        if needsUpdate == True:
            if screensavermode == False:
                # Update screen if not screen saver mode
                oled_power(True)
                oled_flushimage(prevscreen != curscreen)
                oled_reset()

            timeoutcounter = 0
            while timeoutcounter<screenjogtime or screenjogtime == 0:
                qdata = ""
                if readq.empty() == False:
                    qdata = readq.get()

                if qdata == "OLEDSWITCH":
                    # Trigger screen switch
                    screenjogflag = 1
                    # Reset Screen Saver
                    screensavermode = False
                    screensaverctr = 0

                    break
                elif qdata == "OLEDSTOP":
                    # End OLED Thread
                    display_defaultimg()
                    return
                else:
                    screensaverctr = screensaverctr + 1
                    if screensaversec <= screensaverctr and screensavermode == False:
                        screensavermode = True
                        oled_fill(0)
                        oled_reset()
                        oled_power(False)

                    if timeoutcounter == 0:
                        # Use 1 sec sleep get CPU usage
                        cpuusagelist = argonsysinfo_listcpuusage(1)
                    else:
                        time.sleep(1)

                    timeoutcounter = timeoutcounter + 1
                    if timeoutcounter >= 60 and screensavermode == False:
                        # Refresh data every minute, unless screensaver got triggered
                        screenjogflag = 0
                        break
    display_defaultimg()

def display_defaultimg():
    # Load default image
    #oled_power(True)
    #oled_loadbg("bgdefault")
    #oled_flushimage()
    oled_fill(0)
    oled_reset()

if len(sys.argv) > 1:
    cmd = sys.argv[1].upper()
    if cmd == "SHUTDOWN":
        # Signal poweroff
        logInfo( "SHUTDOWN requested via shutdown of command of argononed service")
        setFanOff()
        bus.write_byte(ADDR_FAN,0xFF)
        
    elif cmd == "FANOFF":
        # Turn off fan
        setFanOff()
        logInfo( "FANOFF requested via fanoff command of the argononed service")
        if OLED_ENABLED == True:
            display_defaultimg()

    elif cmd == "SERVICE":
        # Starts the power button and temperature monitor threads
        try:
            logInfo( "argononed service version " + ARGON_VERSION + " starting.")
            ipcq = Queue()
            t1 = Thread(target = shutdown_check, args =(ipcq, ))

            t2 = Thread(target = temp_check)
            if OLED_ENABLED == True:
                t3 = Thread(target = display_loop, args =(ipcq, ))

            t1.start()
            t2.start()
            if OLED_ENABLED == True:
                t3.start()
            ipcq.join()
        except:
            GPIO.cleanup()

    elif cmd == "VERSION":
        print( "Version: " + ARGON_VERSION )

