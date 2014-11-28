from configobj import ConfigObj
import xbmc
import xbmcaddon
import xbmcvfs
import urllib2
import socket
import time
import datetime
import os

__scriptname__   = "audo"
__author__       = "lsellens"
__url__          = "http://code.google.com/p/repository-lsellens/"
__addon__        = xbmcaddon.Addon(id='script.service.audo')
__addonpath__    = __addon__.getAddonInfo('path')
__addonhome__    = __addon__.getAddonInfo('profile')
__dependencies__ = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-dependencies').getAddonInfo('path'))
__start__        = xbmc.translatePath(__addonpath__ + '/resources/audo.py')

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
    xbmc.executebuiltin('XBMC.RunScript(%s)' % __start__, True)
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
sabNzbdConfigFileDone = (xbmc.translatePath(__addonhome__ + 'sabnzbd.done'))

while True:
    if not xbmcvfs.exists(sabNzbdConfigFileDone):
        time.sleep(5)
    else:
        break

sabNzbdConfigFile = (xbmc.translatePath(__addonhome__ + 'sabnzbd.ini'))
sabConfiguration = ConfigObj(sabNzbdConfigFile)
sabNzbdApiKey = sabConfiguration['misc']['api_key']
sabNzbdAddress = "localhost:8081"
sabNzbdQueue = ('http://' + sabNzbdAddress + '/api?mode=queue&output=xml&apikey=' + sabNzbdApiKey)
sabNzbdHistory = ('http://' + sabNzbdAddress + '/api?mode=history&output=xml&apikey=' + sabNzbdApiKey)
sabNzbdQueueKeywords = ['<status>Downloading</status>', '<status>Fetching</status>', '<priority>Force</priority>']
sabNzbdHistoryKeywords = ['<status>Repairing</status>', '<status>Verifying</status>', '<status>Extracting</status>']

while not xbmc.abortRequested:
    # detect machine arch and setup binaries after an update
    if not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
        xbmc.log('AUDO: Update occurred. Attempting to setup binaries:', level=xbmc.LOGDEBUG)
        try:
            xbmc.executebuiltin('XBMC.RunScript(%s)' % xbmc.translatePath(__dependencies__ + '/default.py'), True)
        except Exception, e:
            xbmc.log('AUDO: Error setting up binaries:', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
        while not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + parch)):
            time.sleep(5)

    #RPI and other arm devices do not have a wakealarm
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

    time.sleep(0.250)

# Shutdown audo
os.system("kill `ps | grep -E 'python.*script.module.audo' | awk '{print $1}'`")
