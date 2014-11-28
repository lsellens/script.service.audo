# Initializes and launches SABnzbd, Couchpotato, Sickbeard and Headphones
from xml.dom.minidom import parseString
from configobj import ConfigObj
from os.path import expanduser
import subprocess
import urllib2
import hashlib
import xbmc
import xbmcaddon
import xbmcvfs

import time
import xbmcgui
import sys
import socket
import fcntl
import struct
import os

# helper functions
# ----------------


def check_connection():
        ifaces = ['eth0','eth1','wlan0','wlan1','wlan2','wlan3']
        connected = []
        i = 0
        for ifname in ifaces:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                socket.inet_ntoa(fcntl.ioctl(
                        s.fileno(),
                        0x8915,  # SIOCGIFADDR
                        struct.pack('256s', ifname[:15])
                )[20:24])
                connected.append(ifname)
                print "%s is connected" % ifname
            except:
                print "%s is not connected" % ifname
            i += 1
        return connected

def create_dir(dirname):
    if not xbmcvfs.exists(dirname):
        xbmcvfs.mkdirs(dirname)
        xbmc.log('AUDO: Created directory ' + dirname, level=xbmc.LOGDEBUG)

# define some things that we're gonna need, mainly paths
# ------------------------------------------------------

#Get host IP:
connected_ifaces = check_connection()
if len(connected_ifaces) == 0:
    print 'not connected to any network'
    hostIP = "on Port"
else:
    GetIP = ([(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1])
    hostIP = ' on '+GetIP
    print hostIP

#Create Strings for notifications:
started   = 'Service started'+hostIP
waiting   = 'Looking for Media download folders...'
disabled  = 'Service disabled for this session'
restarted = 'Service restarted'+hostIP
SAport  = ':8081'
SBport  = ':8082'
CPport  = ':8083'
HPport  = ':8084'

# addon
__addon__             = xbmcaddon.Addon(id='script.service.audo')
__addonpath__         = xbmc.translatePath(__addon__.getAddonInfo('path'))
__addonhome__         = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__addonname__         = __addon__.getAddonInfo('name')
__icon__              = __addon__.getAddonInfo('icon')
__programs__          = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-programs').getAddonInfo('path'))
__dependencies__      = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-dependencies').getAddonInfo('path'))

# settings
pDefaultSuiteSettings = xbmc.translatePath(__addonpath__ + '/settings-default.xml')
pSuiteSettings        = xbmc.translatePath(__addonhome__ + 'settings.xml')
pXbmcSettings         = xbmc.translatePath('special://home/userdata/guisettings.xml')
pSabNzbdSettings      = xbmc.translatePath(__addonhome__ + 'sabnzbd.ini')
pSickBeardSettings    = xbmc.translatePath(__addonhome__ + 'sickbeard.ini')
pCouchPotatoServerSettings  = xbmc.translatePath(__addonhome__ + 'couchpotatoserver.ini')
pHeadphonesSettings   = xbmc.translatePath(__addonhome__ + 'headphones.ini')

# the settings file already exists if the user set settings before the first launch
if not xbmcvfs.exists(pSuiteSettings):
    xbmcvfs.copy(pDefaultSuiteSettings, pSuiteSettings)

#Get Device Home DIR
pHomeDIR = expanduser('~/')

# directories
pSabNzbdComplete = pHomeDIR+'downloads'
pSabNzbdWatchDir = pHomeDIR+'downloads/watch'
pSabNzbdCompleteTV = pHomeDIR+'downloads/tvshows'
pSabNzbdCompleteMov = pHomeDIR+'downloads/movies'
pSabNzbdCompleteMusic = pHomeDIR+'downloads/music'
pSabNzbdIncomplete = pHomeDIR+'downloads/incomplete'
pSickBeardTvScripts = xbmc.translatePath(__programs__ + '/resources/SickBeard/autoProcessTV')
pSabNzbdScripts = xbmc.translatePath(__addonhome__ + 'scripts')

# service commands
sabnzbd               = ['python', xbmc.translatePath(__programs__ + '/resources/SABnzbd/SABnzbd.py'),
                         '-d', '--pidfile', xbmc.translatePath(__addonhome__ + 'sabnzbd.pid'), '-f', pSabNzbdSettings, '-l 0']
sickBeard             = ['python', xbmc.translatePath(__programs__ + '/resources/SickBeard/SickBeard.py'),
                         '--daemon', '--datadir', __addonhome__, '--pidfile', xbmc.translatePath(__addonhome__ + 'sickbeard.pid'),
                         '--config', pSickBeardSettings]
couchPotatoServer     = ['python', xbmc.translatePath(__programs__ + '/resources/CouchPotatoServer/CouchPotato.py'),
                         '--daemon', '--pid_file', xbmc.translatePath(__addonhome__ + 'couchpotato.pid'),
                         '--config_file', pCouchPotatoServerSettings]
headphones            = ['python', xbmc.translatePath(__programs__ + '/resources/Headphones/Headphones.py'),
                         '-d', '--datadir', __addonhome__, '--pidfile', xbmc.translatePath(__addonhome__ + 'headphones.pid'),
                         '--config', pHeadphonesSettings]

# Other stuff
sabNzbdHost           = 'localhost:8081'

# create directories and settings on first launch
# -----------------------------------------------

firstLaunch = not xbmcvfs.exists(pSabNzbdSettings)
sbfirstLaunch = not xbmcvfs.exists(pSickBeardSettings)
cpfirstLaunch = not xbmcvfs.exists(pCouchPotatoServerSettings)
hpfirstLaunch = not xbmcvfs.exists(pHeadphonesSettings)

xbmc.log('AUDO: Creating directories if missing', level=xbmc.LOGDEBUG)
create_dir(__addonhome__)
create_dir(pSabNzbdComplete)
create_dir(pSabNzbdWatchDir)
create_dir(pSabNzbdCompleteTV)
create_dir(pSabNzbdCompleteMov)
create_dir(pSabNzbdCompleteMusic)
create_dir(pSabNzbdIncomplete)
create_dir(pSabNzbdScripts)

if not xbmcvfs.exists(xbmc.translatePath(pSabNzbdScripts + '/sabToSickBeard.py')):
    xbmcvfs.copy(xbmc.translatePath(pSickBeardTvScripts + '/sabToSickBeard.py'), pSabNzbdScripts + '/sabToSickBeard.py')
if not xbmcvfs.exists(xbmc.translatePath(pSabNzbdScripts + '/autoProcessTV.py')):
    xbmcvfs.copy(xbmc.translatePath(pSickBeardTvScripts + '/autoProcessTV.py'), pSabNzbdScripts + '/autoProcessTV.py')

# read addon and xbmc settings
# ----------------------------

# Transmission-Daemon
transauth = False
try:
    transmissionaddon = xbmcaddon.Addon(id='service.downloadmanager.transmission')
    transauth = (transmissionaddon.getSetting('TRANSMISSION_AUTH').lower() == 'true')

    if transauth:
        xbmc.log('AUDO: Transmission Authentication Enabled', level=xbmc.LOGDEBUG)
        transuser = (transmissionaddon.getSetting('TRANSMISSION_USER').decode('utf-8'))
        if transuser == '':
            transuser = None
        transpwd = (transmissionaddon.getSetting('TRANSMISSION_PWD').decode('utf-8'))
        if transpwd == '':
            transpwd = None
    else:
        xbmc.log('AUDO: Transmission Authentication Not Enabled', level=xbmc.LOGDEBUG)

except Exception, e:
    xbmc.log('AUDO: Transmission Settings are not present', level=xbmc.LOGNOTICE)
    xbmc.log(str(e), level=xbmc.LOGNOTICE)
    pass

# audo
user = (__addon__.getSetting('SABNZBD_USER').decode('utf-8'))
pwd = (__addon__.getSetting('SABNZBD_PWD').decode('utf-8'))
host = (__addon__.getSetting('SABNZBD_IP'))
sabnzbd_launch = (__addon__.getSetting('SABNZBD_LAUNCH').lower() == 'true')
sickbeard_launch = (__addon__.getSetting('SICKBEARD_LAUNCH').lower() == 'true')
couchpotato_launch = (__addon__.getSetting('COUCHPOTATO_LAUNCH').lower() == 'true')
headphones_launch = (__addon__.getSetting('HEADPHONES_LAUNCH').lower() == 'true')

# XBMC
fXbmcSettings = open(pXbmcSettings, 'r')
data = fXbmcSettings.read()
fXbmcSettings.close()
xbmcSettings = parseString(data)
xbmcServices = xbmcSettings.getElementsByTagName('services')[0]
xbmcPort         = xbmcServices.getElementsByTagName('webserverport')[0].firstChild.data
try:
    xbmcUser     = xbmcServices.getElementsByTagName('webserverusername')[0].firstChild.data
except StandardError:
    xbmcUser = ''
try:
    xbmcPwd      = xbmcServices.getElementsByTagName('webserverpassword')[0].firstChild.data
except StandardError:
    xbmcPwd = ''

# prepare execution environment
os.environ['PYTHONPATH'] = str(os.environ.get('PYTHONPATH')) + ':' + __dependencies__ + '/lib'

# SABnzbd start
try:
    # write SABnzbd settings
    # ----------------------
    sabNzbdConfig = ConfigObj(pSabNzbdSettings, create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['misc'] = {}
    defaultConfig['misc']['check_new_rel']     = '0'
    defaultConfig['misc']['auto_browser']      = '0'
    defaultConfig['misc']['disable_api_key']   = '0'
    defaultConfig['misc']['username']          = user
    defaultConfig['misc']['password']          = pwd
    defaultConfig['misc']['port']              = '8081'
    defaultConfig['misc']['https_port']        = '9081'
    defaultConfig['misc']['https_cert']        = 'server.cert'
    defaultConfig['misc']['https_key']         = 'server.key'
    defaultConfig['misc']['host']              = host
    defaultConfig['misc']['log_dir']           = 'logs'
    defaultConfig['misc']['admin_dir']         = 'admin'
    defaultConfig['misc']['nzb_backup_dir']    = 'backup'

    if firstLaunch:
        defaultConfig['misc']['script_dir']    = 'scripts'
        defaultConfig['misc']['web_dir']       = 'Plush'
        defaultConfig['misc']['web_dir2']      = 'Plush'
        defaultConfig['misc']['web_color']     = 'gold'
        defaultConfig['misc']['web_color2']    = 'gold'
        defaultConfig['misc']['download_dir']  = pSabNzbdIncomplete
        defaultConfig['misc']['complete_dir']  = pSabNzbdComplete
        servers = {}
        servers['localhost'] = {}
        servers['localhost']['host']           = 'localhost'
        servers['localhost']['port']           = '119'
        servers['localhost']['enable']         = '0'
        categories = {}
        categories['tv'] = {}
        categories['tv']['name']               = 'tv'
        categories['tv']['script']             = 'sabToSickBeard.py'
        categories['tv']['priority']           = '-100'
        categories['movies'] = {}
        categories['movies']['name']           = 'movies'
        categories['movies']['dir']            = 'movies'
        categories['movies']['priority']       = '-100'
        categories['music'] = {}
        categories['music']['name']            = 'music'
        categories['music']['dir']             = 'music'
        categories['music']['priority']        = '-100'
        defaultConfig['servers'] = servers
        defaultConfig['categories'] = categories

    sabNzbdConfig.merge(defaultConfig)
    sabNzbdConfig.write()

    # also keep the autoProcessTV config up to date
    autoProcessConfig = ConfigObj(xbmc.translatePath(pSabNzbdScripts + '/autoProcessTV.cfg'), create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['SickBeard'] = {}
    defaultConfig['SickBeard']['host']         = 'localhost'
    defaultConfig['SickBeard']['port']         = '8082'
    defaultConfig['SickBeard']['username']     = user
    defaultConfig['SickBeard']['password']     = pwd
    autoProcessConfig.merge(defaultConfig)
    autoProcessConfig.write()

    # launch SABnzbd and get the API key
    # ----------------------------------
    if firstLaunch or sabnzbd_launch:
        xbmc.log('AUDO: Launching SABnzbd...', level=xbmc.LOGDEBUG)
        subprocess.call(sabnzbd, close_fds=True)
        xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
        xbmc.executebuiltin('XBMC.Notification(SABnzbd,'+ started + SAport +',5000,'+ __icon__ +')')

        # SABnzbd will only complete the .ini file when we first access the web interface
        if firstLaunch:
            try:
                if not (user and pwd):
                    urllib2.urlopen('http://' + sabNzbdHost)
                else:
                    urllib2.urlopen('http://' + sabNzbdHost + '/api?mode=queue&output=xml&ma_username=' + user +
                                    '&ma_password=' + pwd)
            except Exception, e:
                xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
                xbmc.log(str(e), level=xbmc.LOGERROR)

        sabNzbdConfig.reload()
        sabNzbdApiKey = sabNzbdConfig['misc']['api_key']

        if firstLaunch and not sabnzbd_launch:
            urllib2.urlopen('http://' + sabNzbdHost + '/api?mode=shutdown&apikey=' + sabNzbdApiKey)
            xbmc.log('AUDO: Shutting SABnzbd down...', level=xbmc.LOGDEBUG)

except Exception, e:
    xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
# SABnzbd end

if not xbmcvfs.exists(xbmc.translatePath(__addonhome__ + 'sabnzbd.done')):
    xbmcvfs.File(xbmc.translatePath(__addonhome__ + 'sabnzbd.done'), 'w').close()

# SickBeard start
try:
    # write SickBeard settings
    # ------------------------
    sickBeardConfig = ConfigObj(pSickBeardSettings, create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['General'] = {}
    defaultConfig['General']['launch_browser'] = '0'
    defaultConfig['General']['version_notify'] = '0'
    defaultConfig['General']['web_port']       = '8082'
    defaultConfig['General']['web_host']       = host
    defaultConfig['General']['web_username']   = user
    defaultConfig['General']['web_password']   = pwd
    defaultConfig['General']['cache_dir']      = __addonhome__ + 'sbcache'
    defaultConfig['General']['log_dir']        = __addonhome__ + 'logs'
    defaultConfig['SABnzbd'] = {}
    defaultConfig['XBMC'] = {}
    defaultConfig['XBMC']['use_xbmc']          = '1'
    defaultConfig['XBMC']['xbmc_host']         = 'localhost:' + xbmcPort
    defaultConfig['XBMC']['xbmc_username']     = xbmcUser
    defaultConfig['XBMC']['xbmc_password']     = xbmcPwd
    defaultConfig['TORRENT'] = {}

    if sabnzbd_launch:
        defaultConfig['SABnzbd']['sab_username']   = user
        defaultConfig['SABnzbd']['sab_password']   = pwd
        defaultConfig['SABnzbd']['sab_apikey']     = sabNzbdApiKey
        defaultConfig['SABnzbd']['sab_host']       = 'http://' + sabNzbdHost + '/'

    if transauth:
        defaultConfig['TORRENT']['torrent_username']      = transuser
        defaultConfig['TORRENT']['torrent_password']      = transpwd
        defaultConfig['TORRENT']['torrent_host']          = 'http://localhost:9091/'

    if sbfirstLaunch:
        defaultConfig['TORRENT']['torrent_path']          = pSabNzbdCompleteTV
        defaultConfig['General']['use_api']               = '1'
        defaultConfig['General']['tv_download_dir']       = pSabNzbdComplete
        defaultConfig['General']['metadata_xbmc_12plus']  = '0|0|0|0|0|0|0|0|0|0'
        defaultConfig['General']['nzb_method']            = 'sabnzbd'
        defaultConfig['General']['keep_processed_dir']    = '0'
        defaultConfig['General']['use_banner']            = '1'
        defaultConfig['General']['rename_episodes']       = '1'
        defaultConfig['General']['naming_ep_name']        = '0'
        defaultConfig['General']['naming_use_periods']    = '1'
        defaultConfig['General']['naming_sep_type']       = '1'
        defaultConfig['General']['naming_ep_type']        = '1'
        defaultConfig['General']['root_dirs']             = '0|'+pHomeDIR+'tvshows'
        defaultConfig['General']['naming_custom_abd']     = '0'
        defaultConfig['General']['naming_abd_pattern']    = '%SN - %A-D - %EN'
        defaultConfig['Blackhole'] = {}
        defaultConfig['Blackhole']['torrent_dir']         = pSabNzbdWatchDir
        defaultConfig['SABnzbd']['sab_category']          = 'tv'
        # workaround: on first launch, sick beard will always add 
        # 'http://' and trailing '/' on its own
        defaultConfig['SABnzbd']['sab_host']              = sabNzbdHost
        defaultConfig['XBMC']['xbmc_notify_ondownload']   = '1'
        defaultConfig['XBMC']['xbmc_update_library']      = '1'
        defaultConfig['XBMC']['xbmc_update_full']         = '1'

    sickBeardConfig.merge(defaultConfig)
    sickBeardConfig.write()

    # launch SickBeard
    # ----------------
    if sickbeard_launch:
        xbmc.log('AUDO: Launching SickBeard...', level=xbmc.LOGDEBUG)
        subprocess.call(sickBeard, close_fds=True)
        xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
        xbmc.executebuiltin('XBMC.Notification(SickBeard,'+ started + SBport +',5000,'+ __icon__ +')')
except Exception, e:
    xbmc.log('AUDO: SickBeard exception occurred', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
# SickBeard end

# CouchPotatoServer start
try:
    # empty password hack
    if pwd == '':
        md5pwd = ''
    else:
        #convert password to md5
        md5pwd = hashlib.md5(str(pwd)).hexdigest()

    # write CouchPotatoServer settings
    # --------------------------
    couchPotatoServerConfig = ConfigObj(pCouchPotatoServerSettings, create_empty=True, list_values=False)
    defaultConfig = ConfigObj()
    defaultConfig['core'] = {}
    defaultConfig['core']['username']            = user
    defaultConfig['core']['password']            = md5pwd
    defaultConfig['core']['port']                = '8083'
    defaultConfig['core']['launch_browser']      = '0'
    defaultConfig['core']['host']                = host
    defaultConfig['core']['data_dir']            = __addonhome__
    defaultConfig['updater'] = {}
    defaultConfig['updater']['enabled']          = '0'
    defaultConfig['updater']['notification']     = '0'
    defaultConfig['updater']['automatic']        = '0'
    defaultConfig['xbmc'] = {}
    defaultConfig['xbmc']['enabled']             = '1'
    defaultConfig['xbmc']['host']                = 'localhost:' + xbmcPort
    defaultConfig['xbmc']['username']            = xbmcUser
    defaultConfig['xbmc']['password']            = xbmcPwd
    defaultConfig['sabnzbd'] = {}
    defaultConfig['transmission'] = {}

    if sabnzbd_launch:
        defaultConfig['sabnzbd']['username']     = user
        defaultConfig['sabnzbd']['password']     = pwd
        defaultConfig['sabnzbd']['api_key']      = sabNzbdApiKey
        defaultConfig['sabnzbd']['host']         = sabNzbdHost

    if transauth:
        defaultConfig['transmission']['username']         = transuser
        defaultConfig['transmission']['password']         = transpwd
        defaultConfig['transmission']['host']             = 'localhost:9091'

    if cpfirstLaunch:
        defaultConfig['transmission']['directory']        = pSabNzbdCompleteMov
        defaultConfig['xbmc']['xbmc_update_library']      = '1'
        defaultConfig['xbmc']['xbmc_update_full']         = '1'
        defaultConfig['xbmc']['xbmc_notify_onsnatch']     = '1'
        defaultConfig['xbmc']['xbmc_notify_ondownload']   = '1'
        defaultConfig['blackhole'] = {}
        defaultConfig['blackhole']['directory']           = pSabNzbdWatchDir
        defaultConfig['blackhole']['use_for']             = 'both'
        defaultConfig['blackhole']['enabled']             = '0'
        defaultConfig['sabnzbd']['category']              = 'movies'
        defaultConfig['sabnzbd']['pp_directory']          = pSabNzbdCompleteMov
        defaultConfig['renamer'] = {}
        defaultConfig['renamer']['enabled']               = '1'
        defaultConfig['renamer']['from']                  = pSabNzbdCompleteMov
        defaultConfig['renamer']['to']                    = pHomeDIR+'videos'
        defaultConfig['renamer']['separator']             = '.'
        defaultConfig['renamer']['cleanup']               = '0'
        defaultConfig['core']['permission_folder']        = '0644'
        defaultConfig['core']['permission_file']          = '0644'
        defaultConfig['core']['show_wizard']              = '0'
        defaultConfig['core']['debug']                    = '0'
        defaultConfig['core']['development']              = '0'

    couchPotatoServerConfig.merge(defaultConfig)
    couchPotatoServerConfig.write()

    # launch CouchPotatoServer
    # ------------------
    if couchpotato_launch:
        xbmc.log('AUDO: Launching CouchPotatoServer...', level=xbmc.LOGDEBUG)
        subprocess.call(couchPotatoServer, close_fds=True)
        xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
        xbmc.executebuiltin('XBMC.Notification(CouchPotatoServer,'+ started + CPport +',5000,'+ __icon__ +')')
except Exception, e:
    xbmc.log('AUDO: CouchPotatoServer exception occurred', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
# CouchPotatoServer end

# Headphones start
try:
    # write Headphones settings
    # -------------------------
    headphonesConfig = ConfigObj(pHeadphonesSettings, create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['General'] = {}
    defaultConfig['General']['launch_browser']            = '0'
    defaultConfig['General']['http_port']                 = '8084'
    defaultConfig['General']['http_host']                 = host
    defaultConfig['General']['http_username']             = user
    defaultConfig['General']['http_password']             = pwd
    defaultConfig['General']['check_github']              = '0'
    defaultConfig['General']['check_github_on_startup']   = '0'
    defaultConfig['General']['cache_dir']                 = __addonhome__ + 'hpcache'
    defaultConfig['General']['log_dir']                   = __addonhome__ + 'logs'
    defaultConfig['XBMC'] = {}
    defaultConfig['XBMC']['xbmc_enabled']                 = '1'
    defaultConfig['XBMC']['xbmc_host']                    = 'localhost:' + xbmcPort
    defaultConfig['XBMC']['xbmc_username']                = xbmcUser
    defaultConfig['XBMC']['xbmc_password']                = xbmcPwd
    defaultConfig['SABnzbd'] = {}
    defaultConfig['Transmission'] = {}

    if sabnzbd_launch:
        defaultConfig['SABnzbd']['sab_apikey']         = sabNzbdApiKey
        defaultConfig['SABnzbd']['sab_host']           = sabNzbdHost
        defaultConfig['SABnzbd']['sab_username']       = user
        defaultConfig['SABnzbd']['sab_password']       = pwd

    if transauth:
        defaultConfig['Transmission']['transmission_username'] = transuser
        defaultConfig['Transmission']['transmission_password'] = transpwd
        defaultConfig['Transmission']['transmission_host']     = 'http://localhost:9091'

    if hpfirstLaunch:
        defaultConfig['Transmission']['download_torrent_dir']  = pSabNzbdCompleteMusic
        defaultConfig['General']['api_enabled']                = '1'
        defaultConfig['SABnzbd']['sab_category']               = 'music'
        defaultConfig['XBMC']['xbmc_update']                   = '1'
        defaultConfig['XBMC']['xbmc_notify']                   = '1'
        defaultConfig['General']['music_dir']                  = pHomeDIR+'music'
        defaultConfig['General']['destination_dir']            = pHomeDIR+'music'
        defaultConfig['General']['torrentblackhole_dir']       = pSabNzbdWatchDir
        defaultConfig['General']['download_dir']               = pSabNzbdCompleteMusic
        defaultConfig['General']['move_files']                 = '1'
        defaultConfig['General']['rename_files']               = '1'
        defaultConfig['General']['folder_permissions']         = '0644'

    headphonesConfig.merge(defaultConfig)
    headphonesConfig.write()

    # launch Headphones
    # -----------------
    if headphones_launch:
        xbmc.log('AUDO: Launching Headphones...', level=xbmc.LOGDEBUG)
        subprocess.call(headphones, close_fds=True)
        xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
        xbmc.executebuiltin('XBMC.Notification(Headphones,'+ started + HPport +',5000,'+ __icon__ +')')
except Exception, e:
    xbmc.log('AUDO: Headphones exception occurred', level=xbmc.LOGERROR)
    xbmc.log(str(e), level=xbmc.LOGERROR)
# Headphones end
