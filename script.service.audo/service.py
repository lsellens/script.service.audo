from configobj import ConfigObj
import urllib2
import socket
import time
import datetime
import os
import resources.audo as audo
import xbmc
import xbmcaddon
import xbmcvfs

__scriptname__   = "audo"
__author__       = "lsellens"
__url__          = "http://lsellens.openelec.tv"
__addon__        = xbmcaddon.Addon(id='script.service.audo')
__addonpath__    = __addon__.getAddonInfo('path')
__addonhome__    = __addon__.getAddonInfo('profile')
__dependencies__ = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-dependencies').getAddonInfo('path'))
__programs__     = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-programs').getAddonInfo('path'))

checkInterval    = 240
timeout          = 20
wake_times       = ['01:00', '03:00', '05:00', '07:00', '09:00', '11:00', '13:00', '15:00', '17:00', '19:00', '21:00',
                    '23:00']
idleTimer        = 0

# detect machine arch and setup binaries on first run
parch = os.uname()[4]

if not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
    xbmc.log('AUDO: Setting up binaries:', level=xbmc.LOGDEBUG)
    try:
        xbmc.executebuiltin('XBMC.RunScript(%s)' % xbmc.translatePath(__dependencies__ + '/default.py'), True)
    except Exception, e:
        xbmc.log('AUDO: Error setting up binaries:', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    while not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
        time.sleep(5)

# Launch audo
try:
    audo.main()
except Exception, e:
    xbmc.log('AUDO: Could not execute launch script:', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)

# start checking SABnzbd for activity and prevent sleeping if necessary
socket.setdefaulttimeout(timeout)

# perform some initial checks and log essential settings
shouldKeepAwake = 'false'
wakePeriodically = 'false'
if not parch.startswith('arm'):
    shouldKeepAwake = (__addon__.getSetting('SABNZBD_KEEP_AWAKE').lower() == 'true')
    wakePeriodically = (__addon__.getSetting('PERIODIC_WAKE').lower() == 'true')
    wakeHourIdx = int(__addon__.getSetting('WAKE_AT'))
    if shouldKeepAwake:
        xbmc.log('AUDO: Will prevent idle sleep/shutdown while downloading')
    if wakePeriodically:
        xbmc.log('AUDO: Will try to wake system daily at ' + wake_times[wakeHourIdx])

# SABnzbd addresses and api key
sabNzbdConfigFile = (xbmc.translatePath(__addonhome__ + 'sabnzbd.ini'))
sabConfiguration = ConfigObj(sabNzbdConfigFile)
sabNzbdApiKey = sabConfiguration['misc']['api_key']
sabNzbdAddress = "localhost:8081"
sabNzbdQueue = ('http://' + sabNzbdAddress + '/api?mode=queue&output=xml&apikey=' + sabNzbdApiKey)
sabNzbdHistory = ('http://' + sabNzbdAddress + '/api?mode=history&output=xml&apikey=' + sabNzbdApiKey)
sabNzbdQueueKeywords = ['<status>Downloading</status>', '<status>Fetching</status>', '<priority>Force</priority>']
sabNzbdHistoryKeywords = ['<status>Repairing</status>', '<status>Verifying</status>', '<status>Extracting</status>']

audoshutdown = (__addon__.getSetting('SHUTDOWN').lower() == 'true')

while not xbmc.Monitor.(abortRequested()) and not audoshutdown:
    # detect machine arch and setup binaries after an update
    if not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
        xbmc.log('AUDO: Update occurred. Attempting to setup binaries:', level=xbmc.LOGDEBUG)
        count1 = 1
        count2 = 2
        while count1 != count2:
            count1 = 0
            count2 = 0
            for root, dirs, files in os.walk(__dependencies__):
                count1 += len(files)
            time.sleep(3)
            for root, dirs, files in os.walk(__dependencies__):
                count2 += len(files)
        try:
            xbmc.executebuiltin('XBMC.RunScript(%s)' % xbmc.translatePath(__dependencies__ + '/default.py'), True)
        except Exception, e:
            xbmc.log('AUDO: Error setting up binaries:', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
        while not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
            time.sleep(5)
    
    # detect update of audo-programs and restart services
    if not xbmcvfs.exists(xbmc.translatePath(__programs__ + '/.current')):
        xbmc.log('AUDO: Update occurred. Attempting to restart Audo services:', level=xbmc.LOGDEBUG)
        count1 = 1
        count2 = 2
        xbmc.executebuiltin('XBMC.Notification(' + __scriptname__ + ': Update detected,Stopping services now...,5000,)')
        audo.shutdown()
        while count1 != count2:
            count1 = 0
            count2 = 0
            for root, dirs, files in os.walk(__programs__):
                count1 += len(files)
            time.sleep(3)
            for root, dirs, files in os.walk(__programs__):
                count2 += len(files)
        try:
            if (xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/SickBeard/SickBeard.py'))) and (
                    xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/Headphones/Headphones.py'))) and (
                    xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/CouchPotatoServer/CouchPotato.py'))):
                xbmc.executebuiltin(
                    'XBMC.Notification(' + __scriptname__ + ': Update detected,Restarting services now...,5000,)')
                time.sleep(3)
                audo.main()
                time.sleep(10)
        except Exception, e:
            xbmc.log('AUDO: Could not execute launch script:', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
    
    # RPI and other arm devices do not have a wakealarm
    if not parch.startswith('arm'):
        
        # reread setting in case it has changed
        shouldKeepAwake = (__addon__.getSetting('SABNZBD_KEEP_AWAKE').lower() == 'true')
        wakePeriodically = (__addon__.getSetting('PERIODIC_WAKE').lower() == 'true')
        wakeHourIdx = int(__addon__.getSetting('WAKE_AT'))
        
        # check if SABnzbd is downloading
        if shouldKeepAwake:
            idleTimer += 1
            # check SABnzbd every ~60s (240 cycles)
            if idleTimer == checkInterval:
                sabIsActive = False
                idleTimer = 0
                req = urllib2.Request(sabNzbdQueue)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    xbmc.log('AUDO: Could not determine SABnzbds queue status:', level=xbmc.LOGERROR)
                    xbmc.log(str(e), level=xbmc.LOGERROR)
                else:
                    queue = handle.read()
                    handle.close()
                    if any(x in queue for x in sabNzbdQueueKeywords):
                        sabIsActive = True
                
                req = urllib2.Request(sabNzbdHistory)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    xbmc.log('AUDO: Could not determine SABnzbds history status:', level=xbmc.LOGERROR)
                    xbmc.log(str(e), level=xbmc.LOGERROR)
                else:
                    history = handle.read()
                    handle.close()
                    if any(x in history for x in sabNzbdHistoryKeywords):
                        sabIsActive = True
                
                # reset idle timer if queue is downloading/reparing/verifying/extracting
                if sabIsActive:
                    xbmc.executebuiltin('InhibitIdleShutdown(true)')
                    xbmc.log('AUDO: Preventing sleep', level=xbmc.LOGDEBUG)
                else:
                    xbmc.executebuiltin('InhibitIdleShutdown(false)')
                    xbmc.log('AUDO: Not preventing sleep', level=xbmc.LOGDEBUG)
        
        # calculate and set the time to wake up at (if any)
        if wakePeriodically:
            wakeHour = wakeHourIdx * 2 + 1
            timeOfDay = datetime.time(hour=wakeHour)
            now = datetime.datetime.now()
            wakeTime = now.combine(now.date(), timeOfDay)
            if now.time() > timeOfDay:
                wakeTime += datetime.timedelta(days=1)
            secondsSinceEpoch = time.mktime(wakeTime.timetuple())
            try:
                open("/sys/class/rtc/rtc0/wakealarm", "w").write("0")
                open("/sys/class/rtc/rtc0/wakealarm", "w").write(str(secondsSinceEpoch))
            except IOError, e:
                xbmc.log('AUDO: Could not write /sys/class/rtc/rtc0/wakealarm ', level=xbmc.LOGERROR)
                xbmc.log(str(e), level=xbmc.LOGERROR)
        else:
            try:
                open("/sys/class/rtc/rtc0/wakealarm", "w").close()
            except IOError, e:
                xbmc.log('AUDO: Could not write /sys/class/rtc/rtc0/wakealarm ', level=xbmc.LOGERROR)
                xbmc.log(str(e), level=xbmc.LOGDEBUG)
    
    audoshutdown = (__addon__.getSetting('SHUTDOWN').lower() == 'true')
    
    time.sleep(0.250)

# Shutdown audo
try:
    audo.shutdown()
except Exception, e:
    xbmc.log('AUDO: Could not execute shutdown script:', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
