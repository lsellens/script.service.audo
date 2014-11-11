#temp script to facilitate upgrade from v1.1.1
import xbmc
import xbmcaddon
import xbmcvfs
import os

#kill processes from v1.1.1
os.system("kill `ps | grep -E 'python.*script.service.audo' | awk '{print $1}'`")

__addon__        = xbmcaddon.Addon(id='script.service.audo')
__addonpath__    = __addon__.getAddonInfo('path')
__start__        = xbmc.translatePath(__addonpath__ + '/service.py')

xbmcvfs.delete(xbmc.translatePath(__addonpath__ + '/justupdated'))

#restart new service.py
try:
    xbmc.executebuiltin('XBMC.RunScript(%s)' % __start__, True)
except Exception, e:
    xbmc.log('AUDO: Could not start service:', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
