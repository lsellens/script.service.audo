from configobj import ConfigObj
import socket
import os
import resources.audo as audo
import xbmc
import xbmcvfs


class MyMonitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )

    def onSettingsChanged( self ):
        audo.getaddonsettings()

# addon
__scriptname__   = "audo"
__author__       = "lsellens"
__url__          = "http://lsellens.openelec.tv"
audo.getaddonpaths()
timeOut          = 20
wakeTimes        = ['01:00', '03:00', '05:00', '07:00', '09:00', '11:00', '13:00', '15:00', '17:00', '19:00', '21:00',
                    '23:00']

defaultSuiteSettings = xbmc.translatePath(audo.__addonpath__ + '/settings-default.xml')
suiteSettings = xbmc.translatePath(audo.__addonhome__ + 'settings.xml')

if not xbmcvfs.exists(suiteSettings):
    xbmcvfs.copy(defaultSuiteSettings, suiteSettings)
audo.__addon__.setSetting(id='SHUTDOWN', value='false')
audo.getaddonsettings()

# detect machine arch and setup binaries on first run
if not xbmcvfs.exists(xbmc.translatePath(audo.__dependencies__ + '/arch.' + audo.pArch)):
    audo.updatedependencies()

# Launch audo
try:
    audo.main()
except Exception, e:
    xbmc.log('AUDO: Could not execute launch script:', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)

# start checking SABnzbd for activity and prevent sleeping if necessary
socket.setdefaulttimeout(timeOut)

# perform some initial checks and log essential settings
if not audo.pArch.startswith('arm'):
    if audo.sabnzbdKeepAwake:
        xbmc.log('AUDO: Will prevent idle sleep/shutdown while downloading from SABnzbd')
    if audo.transmissionKeepAwake:
        xbmc.log('AUDO: Will prevent idle sleep/shutdown while downloading from Transmission')
    if audo.wakePeriodically:
        xbmc.log('AUDO: Will try to wake system daily at ' + wakeTimes[audo.wakeHourIdx])

monitor = MyMonitor()

while not monitor.abortRequested():
    # detect machine arch and setup binaries after an update
    if not xbmcvfs.exists(xbmc.translatePath(audo.__dependencies__ + '/arch.' + audo.pArch)):
        audo.updatedependencies()
    
    # detect update of audo-programs and restart services
    if not xbmcvfs.exists(xbmc.translatePath(audo.__programs__ + '/.current')):
        audo.updateprograms()
    
    # RPI and other arm devices do not have a wakealarm
    if not audo.pArch.startswith('arm'):
        
        # check if SABnzbd is downloading
        if audo.sabnzbdKeepAwake and sabnzbdLaunch:
            audo.sabinhibitsleep()
        
        # check if transmission is downloading
        if audo.transmissionKeepAwake:
            audo.transinhibitsleep()
        
        # calculate and set the time to wake up at (if any)
        if audo.wakePeriodically:
            audo.writewakealarm()
        else:
            try:
                if not os.stat("/sys/class/rtc/rtc0/wakealarm").st_size == 0:
                    open("/sys/class/rtc/rtc0/wakealarm", "w").close()
            except IOError, e:
                xbmc.log('AUDO: Could not write /sys/class/rtc/rtc0/wakealarm ', level=xbmc.LOGDEBUG)
                xbmc.log(str(e), level=xbmc.LOGDEBUG)
                pass
    
    audo.getaddonsettings()
    
    if audo.audoShutdown:
        audo.shutdown()
        while audo.audoShutdown:
            xbmc.sleep(1000)
        audo.main()
    
    if monitor.waitForAbort(1):
        break

# Shutdown audo
try:
    audo.shutdown()
except Exception, e:
    xbmc.log('AUDO: Could not execute shutdown script:', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
