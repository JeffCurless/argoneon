#!/usr/bin/python3

import sys
import os
import time
import math
sys.path.append( "/etc/argon/")
from argonsysinfo import *

usage1 = argonsysinfo_diskusage()
start = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
#
# Display CPU Utilization
# 
print( "CPU Utilization:" )
cpulist = argonsysinfo_listcpuusage()
maxcpu = 4
while maxcpu > 0 and len(cpulist) > 0:
    curline = ""
    item = cpulist.pop(0)
    curline = "    " + item["title"] + ": " + str(item["value"]) + "%"
    print( curline )
    maxcpu = maxcpu - 1

#
# Display Usage
#
print( "Storage Usage:" )
hddlist = argonsysinfo_listhddusage()
for dev in hddlist:
    total = hddlist[dev]['total']
    used  = hddlist[dev]['used']
    percent = hddlist[dev]['percent']
    print( "    Device : " + dev + " Total : " + argonsysinfo_kbstr(total) + " Used: " + argonsysinfo_kbstr(used) + " Usage: " + str(percent) + "%" ) 

#
# Display RAID
#
print( "RAID Arrays:" )
raidinfo = argonsysinfo_listraid()
raidlist = raidinfo['raidlist']
hddlist  = raidinfo['hddlist']
while len(raidlist) > 0:
    item = raidlist.pop(0)
    rebuild = ""
    if len(item['info']['resync']) > 0:
        rebuild = " Rebuild: " + item['info']['resync']
    stateArray = item['info']['state'].split( ", " )
    if len(stateArray) == 1:
        state = stateArray[0]
    if len(stateArray) == 2:
        state = stateArray[1]
    if len(stateArray) >= 3:
        state = stateArray[2]
    state = state.capitalize()
    print( "    Device: " + item['title'] + " Type: " + item['info']['raidtype'].upper() + " State: " + state + " Size: " +argonsysinfo_kbstr(item['info']['size'] ) + rebuild )

#print( "Drives used in RAID:" )
#print( hddlist )
#
# Display memory usage
#
tmp = argonsysinfo_getram()
print( "Memory:")
print( "    Total: " + tmp[1] )
print( "    Free : " + tmp[0] )

#
# Display temp
#
tmp = argonsysinfo_getcputemp()
ctemp = str(tmp)
ftemp = str(32 + (9*tmp)/5)
if len(ctemp ) > 4:
    ctemp = ctemp[0:4]
if len(ftemp) > 5:
    ftemp = ftemp[0:5]

print( "Temp: " )
print( "    " + str(ctemp) + "C")
print( "    " + str(ftemp) + "F")

#
# Display IP address
#
tmp = argonsysinfo_getipList()
print( "IP Address : " )
for item in tmp:
    print( "    " + item[0] + ": " + item[1] )

#
# Disk Utilization
# 
usage2 = argonsysinfo_diskusage()
stop = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

for istop in usage2:
    for istart in usage1:
        if istop['disk'] == istart['disk']:
            istop['readsector'] = istop['readsector'] - istart['readsector']
            istop['writesector'] = istop['writesector'] - istart['writesector']

span = ((stop - start)/1000000000)
for item in usage2:
    readbw = (item['readsector']/2)/span
    writebw = (item['writesector']/2)/span
    print( item['disk'] + " read: " + argonsysinfo_kbstr(int(readbw)) + "/Sec write: " + argonsysinfo_kbstr(int(writebw)) + "/Sec" )


