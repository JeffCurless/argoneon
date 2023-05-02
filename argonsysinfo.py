#!/usr/bin/python3

#
# Misc methods to retrieve system information.
#

import os
import time
import socket
import psutil
from pathlib import Path

fanspeed = Path('/tmp/fanspeed.txt')

def checkPermission():
    """
    Determine if the user can properly execute the script.  Must have sudo or be root
    """
    if not ('SUDO_UID' in os.environ ) and os.geteuid() != 0:
        return False
    return True

#
def argonsysinfo_getCurrentFanSpeed():
    """ Get the current fanspeed of the system, by reading a file we have stored the speed in.
    This allows other applications for determine what the current fan speed is, as we cannot read
    (apparently) from the device when we set the speed.
    """
    try:
        return int(float(fanspeed.read_text()))
    except FileNotFoundError:
        return None
    except ValueError:
        return None

#
def argonsysinfo_recordCurrentFanSpeed( theSpeed ):
    """ Record the current fanspeed for external applications to use.
    """
    try:
        fanspeed.write_text(str(theSpeed))
    except:
        ...

def argonsysinfo_listcpuusage(sleepsec = 1):
    outputlist = []
    curusage_a = argonsysinfo_getcpuusagesnapshot()
    time.sleep(sleepsec)
    curusage_b = argonsysinfo_getcpuusagesnapshot()

    for cpuname in curusage_a:
        if cpuname == "cpu":
            continue
        if curusage_a[cpuname]["total"] == curusage_b[cpuname]["total"]:
            outputlist.append({"title": cpuname, "value": "0%"})
        else:
            total = curusage_b[cpuname]["total"]-curusage_a[cpuname]["total"]
            idle = curusage_b[cpuname]["idle"]-curusage_a[cpuname]["idle"]
            outputlist.append({"title": cpuname, "value": int(100*(total-idle)/(total))})
    return outputlist

def argonsysinfo_getcpuusagesnapshot():
    cpupercent = {}
    errorflag = False
    try:
        cpuctr = 0
        # user, nice, system, idle, iowait, irc, softirq, steal, guest, guest nice
        tempfp = open("/proc/stat", "r")
        alllines = tempfp.readlines()
        for temp in alllines:
            temp = temp.replace('\t', ' ')
            temp = temp.strip()
            while temp.find("  ") >= 0:
                temp = temp.replace("  ", " ")
            if len(temp) < 3:
                cpuctr = cpuctr +1
                continue

            checkname = temp[0:3]
            if checkname == "cpu":
                infolist = temp.split(" ")
                idle = 0
                total = 0
                colctr = 1
                while colctr < len(infolist):
                    curval = int(infolist[colctr])
                    if colctr == 4 or colctr == 5:
                        idle = idle + curval
                    total = total + curval
                    colctr = colctr + 1
                if total > 0:
                    cpupercent[infolist[0]] = {"total": total, "idle": idle}
            cpuctr = cpuctr +1

        tempfp.close()
    except IOError:
        errorflag = True
    return cpupercent


def argonsysinfo_liststoragetotal():
    outputlist = []
    ramtotal = 0
    errorflag = False

    try:
        hddctr = 0
        tempfp = open("/proc/partitions", "r")
        alllines = tempfp.readlines()

        for temp in alllines:
            temp = temp.replace('\t', ' ')
            temp = temp.strip()
            while temp.find("  ") >= 0:
                temp = temp.replace("  ", " ")
            infolist = temp.split(" ")
            if len(infolist) >= 4:
                # Check if header
                if infolist[3] != "name":
                    parttype = infolist[3][0:3]
                    if parttype == "ram":
                        ramtotal = ramtotal + int(infolist[2])
                    elif parttype[0:2] == "sd" or parttype[0:2] == "hd":
                        lastchar = infolist[3][-1]
                        if lastchar.isdigit() == False:
                            outputlist.append({"title": infolist[3], "value": argonsysinfo_kbstr(int(infolist[2]))})
                    else:
                        # SD Cards
                        lastchar = infolist[3][-2]
                        if lastchar[0] != "p":
                            outputlist.append({"title": infolist[3], "value": argonsysinfo_kbstr(int(infolist[2]))})

        tempfp.close()
        #outputlist.append({"title": "ram", "value": argonsysinfo_kbstr(ramtotal)})
    except IOError:
        errorflag = True
    return outputlist

def argonsysinfo_getram():
    totalram = 0
    totalfree = 0
    tempfp = open("/proc/meminfo", "r")
    alllines = tempfp.readlines()

    for temp in alllines:
        temp = temp.replace('\t', ' ')
        temp = temp.strip()
        while temp.find("  ") >= 0:
            temp = temp.replace("  ", " ")
        infolist = temp.split(" ")
        if len(infolist) >= 2:
            if infolist[0] == "MemTotal:":
                totalram = int(infolist[1])
            elif infolist[0] == "MemFree:":
                totalfree = totalfree + int(infolist[1])
            elif infolist[0] == "Buffers:":
                totalfree = totalfree + int(infolist[1])
            elif infolist[0] == "Cached:":
                totalfree = totalfree + int(infolist[1])
    if totalram == 0:
        return {'percent': '0', 'gb': '0'}
    return {'percent': str(int(100*totalfree/totalram)), 'gb': str((totalram+512*1024)>>20)}


def argonsysinfo_getmaxhddtemp():
    maxtempval = 0
    try:
        hddtempobj = argonsysinfo_gethddtemp()
        for curdev in hddtempobj:
            if hddtempobj[curdev] > maxtempval:
                maxtempval = hddtempobj[curdev]
        return maxtempval
    except:
        return maxtempval

def argonsysinfo_getcputemp():
    try:
        tempfp = open("/sys/class/thermal/thermal_zone0/temp", "r")
        temp = tempfp.readline()
        tempfp.close()
        return float(int(temp)/1000)
    except IOError:
        return 0

def argonsysinfo_gethddtemp():
    outputobj = {}
    hddtempcmd = "/usr/sbin/smartctl"
    #smartctl -d sat -A ${device} | grep 194 | awk -F" " '{print $10}'

    if os.path.exists(hddtempcmd):
        # try:
            command = os.popen("lsblk | grep -e '0 disk' | awk '{print $1}'")
            tmp = command.read()
            command.close()
            alllines = [l for l in tmp.split("\n") if l]
            for curdev in alllines:
                if curdev[0:2] == "sd" or curdev[0:2] == "hd":
                    # command = os.popen(hddtempcmd+" -d sat -A /dev/"+curdev+" | grep 194 | awk '{print $10}' 2>&1")
                    def getSmart(smartCmd):
                        if not checkPermission() and not smartCmd.startswith("sudo"):
                            smartCmd = "sudo " + smartCmd
                        try:
                            command = os.popen(smartCmd)
                            smartctlOutRaw = command.read()
                        except Exception as e:
                            print (e)
                        finally:
                            command.close()
                        if 'scsi error unsupported scsi opcode' in smartctlOutRaw:
                            return None

                        smartctlOut = [l for l in smartctlOutRaw.split('\n') if l]

                        for smartAttr in ["194","190"]:
                            try:
                                line = [l for l in smartctlOut if l.startswith(smartAttr)][0]
                                parts = [p for p in line.replace('\t',' ').split(' ') if p]
                                tempval = float(parts[9])
                                return tempval
                            except IndexError:
                                ## Smart Attr not found
                                ...

                        for smartAttr in ["Temperature:"]:
                            try:
                                line = [l for l in smartctlOut if l.startswith(smartAttr)][0]
                                parts = [p for p in line.replace('\t',' ').split(' ') if p]
                                tempval = float(parts[1])
                                return tempval
                            except IndexError:
                                ## Smart attrbute not found
                                ...
                        return None
                    theTemp = getSmart(f"{hddtempcmd} -d sat -n standby,0 -A /dev/{curdev}")
                    if theTemp:
                        outputobj[curdev] = theTemp
                    else: 
                        theTemp = getSmart(f"{hddtempcmd} -n standby,0 -A /dev/{curdev}")
                        if theTemp:
                            outputobj[curdev] = theTemp
    return outputobj

def argonsysinfo_getip():
    ipaddr = ""
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: 
        # Connect to nonexistent device
        st.connect(('254.255.255.255', 1))
        ipaddr = st.getsockname()[0]
    except Exception:
        ipaddr = 'N/A'
    finally:
        st.close()
    return ipaddr

def get_ip_addresses( family ):
    for interface, snics in psutil.net_if_addrs().items():
        if interface != "lo" and not interface.startswith("br"):
            for snic in snics:
                if snic.family == family:
                    yield( interface, snic.address )

def argonsysinfo_getipList():
    iplist = []
    iplist = list(get_ip_addresses( socket.AF_INET ))

    return iplist

def argonsysinfo_getrootdev():
    command = os.popen('mount')
    tmp = command.read()
    command.close()
    alllines = tmp.split("\n")

    for temp in alllines:
        temp = temp.replace('\t', ' ')
        temp = temp.strip()
        while temp.find("  ") >= 0:
            temp = temp.replace("  ", " ")
        infolist = temp.split(" ")
        if len(infolist) >= 3:

            if infolist[2] == "/":
                return infolist[0]
    return ""

def argonsysinfo_listhddusage():
    outputobj = {}
    raidlist = argonsysinfo_listraid()
    raiddevlist = []
    raidctr = 0
    while raidctr < len(raidlist['raidlist']):
        raiddevlist.append(raidlist['raidlist'][raidctr]['title'])
        raidctr = raidctr + 1

    rootdev = argonsysinfo_getrootdev()

    command = os.popen('df')
    tmp = command.read()
    command.close()
    alllines = tmp.split("\n")

    for temp in alllines:
        temp = temp.replace('\t', ' ')
        temp = temp.strip()
        while temp.find("  ") >= 0:
            temp = temp.replace("  ", " ")
        infolist = temp.split(" ")
        if len(infolist) >= 6:
            if infolist[1] == "Size":
                continue
            if len(infolist[0]) < 5:
                continue
            elif infolist[0][0:5] != "/dev/":
                continue
            curdev = infolist[0]
            mapper = None
            if curdev.startswith('/dev/mapper/'):
                from pathlib import Path
                mapper = Path(curdev).readlink().name

            if curdev == "/dev/root" and rootdev != "":
                curdev = rootdev

            tmpidx = curdev.rfind("/")
            if tmpidx >= 0:
                curdev = curdev[tmpidx+1:]
            #
            # Throw out all devices being used by raid
            #
            if curdev in raidlist['hddlist']:
                continue
            elif curdev not in raiddevlist and not mapper:
              if curdev[0:2] == "sd" or curdev[0:2] == "hd":
                  curdev = curdev[0:-1]
              else:
                  curdev = curdev[0:-2]
                  
            percent=infolist[4].split("%")[0]
            if curdev not in outputobj:
                outputobj[curdev] = {"used":0, "total":0, "percent":0}
                if  mapper:
                    outputobj[curdev]["mapper"] = mapper

            outputobj[curdev]["used"]         += int(infolist[2])
            outputobj[curdev]["total"]        += int(infolist[1])
            outputobj[curdev]["percent"]       = round(((outputobj[curdev]["used"]/outputobj[curdev]["total"]) * 100),1)
            #outputobj[curdev]["percent"]      += int(percent)
    
    return outputobj

def argonsysinfo_kbstr(kbval, wholenumbers = True):
    remainder = 0
    suffixidx = 0
    suffixlist = ["KB", "MB", "GB", "TB"]
    while kbval > 1023 and suffixidx < len(suffixlist):
        remainder = kbval & 1023
        kbval  = kbval >> 10
        suffixidx = suffixidx + 1

    #return str(kbval)+"."+str(remainder) + suffixlist[suffixidx]
    remainderstr = ""
    if kbval < 100 and wholenumbers == False:
        remainder = int((remainder+50)/100)
        if remainder > 0:
            remainderstr = "."+str(remainder)
    elif remainder >= 500:
        kbval = kbval + 1
    return str(kbval)+remainderstr + suffixlist[suffixidx]

def argonsysinfo_listraid():
    hddlist = []
    outputlist = []
    # cat /proc/mdstat
    # multiple mdxx from mdstat
    # mdadm -D /dev/md1

    ramtotal = 0
    errorflag = False
    try:
        hddctr = 0
        tempfp = open("/proc/mdstat", "r")
        alllines = tempfp.readlines()
        for temp in alllines:
            temp = temp.replace('\t', ' ')
            temp = temp.strip()
            while temp.find("  ") >= 0:
                temp = temp.replace("  ", " ")
            infolist = temp.split(" ")
            if len(infolist) >= 4:

                # Check if raid info
                if infolist[0] != "Personalities" and infolist[1] == ":":
                    devname = infolist[0]
                    raidtype = infolist[3]
                    raidstatus = infolist[2]
                    hddctr = 4
                    while hddctr < len(infolist):
                        tmpdevname = infolist[hddctr]
                        tmpidx = tmpdevname.find("[")
                        if tmpidx >= 0:
                            tmpdevname = tmpdevname[0:tmpidx]
                        hddlist.append(tmpdevname)
                        hddctr = hddctr + 1
                    devdetail = argonsysinfo_getraiddetail(devname)
                    outputlist.append({"title": devname, "value": raidtype, "info": devdetail})

        tempfp.close()
    except IOError:
        # No raid
        errorflag = True

    return {'raidlist': outputlist, 'hddlist': hddlist}


def argonsysinfo_getraiddetail(devname):
    state = ""
    raidtype = ""
    size = 0
    used = 0
    total = 0
    working = 0
    active = 0
    failed = 0
    spare = 0
    resync = ""
    hddlist =[]
    if not checkPermission():
        command = os.popen('sudo mdadm -D /dev/'+devname)
    else:
        command = os.popen('mdadm -D /dev/'+devname)
    tmp = command.read()
    command.close()
    alllines = tmp.split("\n")

    for temp in alllines:
        temp = temp.replace('\t', ' ')
        temp = temp.strip()
        while temp.find("  ") >= 0:
            temp = temp.replace("  ", " ")
        infolist = temp.split(" : ")
        if len(infolist) == 2:
            if infolist[0].lower() == "raid level":
                raidtype = infolist[1]
            elif infolist[0].lower() == "array size":
                tmpidx = infolist[1].find(" ")
                if tmpidx > 0:
                    size = (infolist[1][0:tmpidx])
            elif infolist[0].lower() == "used dev size":
                tmpidx = infolist[1].find(" ")
                if tmpidx > 0:
                    used = (infolist[1][0:tmpidx])
            elif infolist[0].lower() == "state":
                state = infolist[1]
            elif infolist[0].lower() == "total devices":
                total = infolist[1]
            elif infolist[0].lower() == "active devices":
                active = infolist[1]
            elif infolist[0].lower() == "working devices":
                working = infolist[1]
            elif infolist[0].lower() == "failed devices":
                failed = infolist[1]
            elif infolist[0].lower() == "spare devices":
                spare = infolist[1]
            elif infolist[0].lower() == "rebuild status":
                resync = infolist[1]
            elif infolist[0].lower() == "resync status":
                resync = infolist[1]
            elif infolist[0].lower() == "check status":
                resync = infolist[1]
        elif len(infolist) > 0:
            infolist = temp.split(" ")
            if len(infolist) == 7:
                hddlist.append(infolist[6])
    return {'state': state, 'raidtype': raidtype, 'size': int(size), 'used': int(used), 'devices': int(total), 'active': int(active), 'working': int(working), 'failed': int(failed), 'spare': int(spare), 'resync': resync, 'hddlist':hddlist}

def argonsysinfo_diskusagedetail( disk,mapper : str = None ):
    readsector = 0
    writesector = 0
    discardsector = 0

    if mapper:
        this = mapper
    else:
        this = disk
    command = os.popen( "cat /sys/block/" + this + "/stat" )
    tmp = command.read()
    command.close()
    tmp.replace('\t',' ')
    tmp = tmp.strip()
    while tmp.find("  ") >= 0:
        tmp = tmp.replace("  ", " ")
    data = tmp.split(" ")
    if len(data) >= 11:
        readsector = data[2]
        writesector = data[6]

    return {'disk':disk, 'readsector':int(readsector), 'writesector':int(writesector)}

def argonsysinfo_diskusage():
    usage = []
    hddlist = argonsysinfo_listhddusage()
    for disk in hddlist:
        parms = {"disk" : disk}
        if "mapper" in hddlist[disk]:
            parms["mapper"] = hddlist[disk]["mapper"]
        temp = argonsysinfo_diskusagedetail( **parms )
        usage.append( temp )
    return usage

def argonsysinfo_truncateFloat( value, dp ):
    """ make sure the value passed in has no more decimal places than the
    passed in (dp) number of places.
    """
    value *= pow( 10, dp )
    value = round( value )
    value /= pow( 10, dp )
    return value

def argonsysinfo_convertCtoF( rawTemp, dp ):
    """ Convert a raw temperature in degrees C to degrees F, and make sure the
    value is truncated to the specified number of decimal places
    """
    rawTemp = (32 + (rawTemp * 9)/5)
    rawTemp = argonsysinfo_truncateFloat( rawTemp, dp )
    return rawTemp;

