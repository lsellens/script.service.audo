from xml.dom.minidom import parseString
from configobj import ConfigObj
from functools import wraps
import os
import subprocess
import urllib2
import hashlib
import time
import datetime
import xbmc
import xbmcaddon
import xbmcvfs
import transmissionrpc


sabnzbdHost = 'localhost:8081'


# addon paths
def getaddonpaths():
    global __addon__, __addonpath__, __addonhome__, __programs__, __dependencies__, __icon__, pArch
    __addon__ = xbmcaddon.Addon(id='script.service.audo')
    __addonpath__ = xbmc.translatePath(__addon__.getAddonInfo('path'))
    __addonhome__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
    __programs__ = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-programs').getAddonInfo('path'))
    __dependencies__ = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-dependencies').getAddonInfo('path'))
    __icon__ = __addon__.getAddonInfo('icon')
    pArch = os.uname()[4]


# read addon settings
def getaddonsettings():
    global user, pwd, host, sabnzbdLaunch, nzbgetLaunch, sickbeardLaunch, couchpotatoLaunch, headphonesLaunch, sabnzbdKeepAwake, transmissionKeepAwake, wakePeriodically, wakeHourIdx, audoShutdown
    xbmc.log('AUDO: Getting addon settings', level=xbmc.LOGDEBUG)
    user = (__addon__.getSetting('SABNZBD_USER').decode('utf-8'))
    pwd = (__addon__.getSetting('SABNZBD_PWD').decode('utf-8'))
    host = (__addon__.getSetting('SABNZBD_IP'))
    sabnzbdLaunch = (__addon__.getSetting('SABNZBD_LAUNCH').lower() == 'true')
    nzbgetLaunch = (__addon__.getSetting('NZBGET_LAUNCH').lower() == 'true')
    sickbeardLaunch = (__addon__.getSetting('SICKBEARD_LAUNCH').lower() == 'true')
    couchpotatoLaunch = (__addon__.getSetting('COUCHPOTATO_LAUNCH').lower() == 'true')
    headphonesLaunch = (__addon__.getSetting('HEADPHONES_LAUNCH').lower() == 'true')
    sabnzbdKeepAwake = (__addon__.getSetting('SABNZBD_KEEP_AWAKE').lower() == 'true')
    transmissionKeepAwake = (__addon__.getSetting('TRANSMISSION_KEEP_AWAKE').lower() == 'true')
    wakePeriodically = (__addon__.getSetting('PERIODIC_WAKE').lower() == 'true')
    wakeHourIdx = int(__addon__.getSetting('WAKE_AT'))
    audoShutdown = (__addon__.getSetting('SHUTDOWN').lower() == 'true')


def retry_on_exc(exceptiontocheck, tries, delay, backoff):
    def retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptiontocheck, e:
                    msg = "AUDO: %s, Retrying in %d seconds..." % (str(e), (mdelay / 1000))
                    xbmc.log(msg, level=xbmc.LOGDEBUG)
                    xbmc.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return retry


@retry_on_exc(urllib2.URLError, 5, 3000, 2)
def urlopen_with_retry(url):
    return urllib2.urlopen(url)


# Initializes and launches SABnzbd, NZBget, Couchpotato, Sickbeard and Headphones
def main():
    def create_dir(dirname):
        if not xbmcvfs.exists(dirname):
            xbmcvfs.mkdirs(dirname)
            xbmc.log('AUDO: Created directory ' + dirname, level=xbmc.LOGDEBUG)
    
    # settings
    global sabnzbdSettings, sickbeardSettings, couchpotatoSettings, headphonesSettings, nzbgetSettings
    xbmcSettings = xbmc.translatePath('special://home/userdata/guisettings.xml')
    sabnzbdSettings = xbmc.translatePath(__addonhome__ + 'sabnzbd.ini')
    sickbeardSettings = xbmc.translatePath(__addonhome__ + 'sickbeard.ini')
    couchpotatoSettings = xbmc.translatePath(__addonhome__ + 'couchpotatoserver.ini')
    headphonesSettings = xbmc.translatePath(__addonhome__ + 'headphones.ini')
    nzbgetSettings = xbmc.translatePath(__addonhome__ + 'nzbget.conf')
    
    # Get Device Home DIR
    homeDir = os.path.expanduser('~/')
    
    # directories
    sabnzbdComplete = xbmc.translatePath(homeDir + 'downloads/')
    sabnzbdWatchDir = xbmc.translatePath(homeDir + 'downloads/watch/')
    sabnzbdCompleteTv = xbmc.translatePath(homeDir + 'downloads/tvshows/')
    sabnzbdCompleteMov = xbmc.translatePath(homeDir + 'downloads/movies/')
    sabnzbdCompleteMusic = xbmc.translatePath(homeDir + 'downloads/music/')
    sabnzbdIncomplete = xbmc.translatePath(homeDir + 'downloads/incomplete/')
    sickbeardTvScripts = xbmc.translatePath(__programs__ + '/resources/SickBeard/autoProcessTV/')
    sabnzbdScripts = xbmc.translatePath(__addonhome__ + 'scripts/')
    
    # service commands
    sabnzbd = ['python', xbmc.translatePath(__programs__ + '/resources/SABnzbd/SABnzbd.py'),
               '-d', '--pidfile=/var/run/sabnzbd.pid', '-f', sabnzbdSettings, '-l 0']
    sickbeard = ['python', xbmc.translatePath(__programs__ + '/resources/SickBeard/SickBeard.py'),
                 '--daemon', '--datadir', __addonhome__, '--pidfile=/var/run/sickbeard.pid', '--config',
                 sickbeardSettings]
    couchpotatoserver = ['python', xbmc.translatePath(__programs__ + '/resources/CouchPotatoServer/CouchPotato.py'),
                         '--daemon', '--pid_file=/var/run/couchpotato.pid', '--config_file', couchpotatoSettings]
    headphones = ['python', xbmc.translatePath(__programs__ + '/resources/Headphones/Headphones.py'),
                  '-d', '--datadir', __addonhome__, '--pidfile=/var/run/headphones.pid', '--config',
                  headphonesSettings]
    nzbget = ['.' + xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget'), '-D', '-c', nzbgetSettings]
    
    # create directories and settings on first launch
    firstLaunch = not xbmcvfs.exists(sabnzbdSettings)
    ngfirstLaunch = not xbmcvfs.exists(nzbgetSettings)
    sbfirstLaunch = not xbmcvfs.exists(sickbeardSettings)
    cpfirstLaunch = not xbmcvfs.exists(couchpotatoSettings)
    hpfirstLaunch = not xbmcvfs.exists(headphonesSettings)
    
    xbmc.log('AUDO: Creating directories if missing', level=xbmc.LOGDEBUG)
    create_dir(__addonhome__)
    create_dir(sabnzbdComplete)
    create_dir(sabnzbdWatchDir)
    create_dir(sabnzbdCompleteTv)
    create_dir(sabnzbdCompleteMov)
    create_dir(sabnzbdCompleteMusic)
    create_dir(sabnzbdIncomplete)
    create_dir(sabnzbdScripts)
    
    if not xbmcvfs.exists(xbmc.translatePath(sabnzbdScripts + 'sabToSickBeard.py')):
        xbmcvfs.copy(xbmc.translatePath(sickbeardTvScripts + 'sabToSickBeard.py'), sabnzbdScripts +
                     'sabToSickBeard.py')
    if not xbmcvfs.exists(xbmc.translatePath(sabnzbdScripts + 'autoProcessTV.py')):
        xbmcvfs.copy(xbmc.translatePath(sickbeardTvScripts + 'autoProcessTV.py'), sabnzbdScripts +
                     'autoProcessTV.py')
    if not os.path.exists(xbmc.translatePath(sabnzbdScripts + 'lib')):
        os.symlink(sickbeardTvScripts + 'lib', sabnzbdScripts + 'lib')
    
    # Transmission-Daemon
    global transAuth, transUser, transPwd
    transAuth = False
    try:
        transmissionAddon = xbmcaddon.Addon(id='service.downloadmanager.transmission')
        transAuth = (transmissionAddon.getSetting('TRANSMISSION_AUTH').lower() == 'true')
    
        if transAuth:
            xbmc.log('AUDO: Transmission Authentication Enabled', level=xbmc.LOGDEBUG)
            transUser = (transmissionAddon.getSetting('TRANSMISSION_USER').decode('utf-8'))
            if transUser == '':
                transUser = None
            transPwd = (transmissionAddon.getSetting('TRANSMISSION_PWD').decode('utf-8'))
            if transPwd == '':
                transPwd = None
        else:
            xbmc.log('AUDO: Transmission Authentication Not Enabled', level=xbmc.LOGDEBUG)
    
    except Exception, e:
        xbmc.log('AUDO: Transmission Settings are not present', level=xbmc.LOGNOTICE)
        xbmc.log(str(e), level=xbmc.LOGNOTICE)
        pass
    
    # XBMC
    f = open(xbmcSettings, 'r')
    data = f.read()
    f.close()
    xbmcSettings = parseString(data)
    xbmcServices = xbmcSettings.getElementsByTagName('services')[0]
    xbmcPort = xbmcServices.getElementsByTagName('webserverport')[0].firstChild.data
    try:
        xbmcUser = xbmcServices.getElementsByTagName('webserverusername')[0].firstChild.data
    except StandardError:
        xbmcUser = ''
    try:
        xbmcPwd = xbmcServices.getElementsByTagName('webserverpassword')[0].firstChild.data
    except StandardError:
        xbmcPwd = ''
    
    # prepare execution environment
    os.environ['PYTHONPATH'] = str(os.environ.get('PYTHONPATH')) + ':' + __dependencies__ + '/lib'
    os_env = os.environ
    os_env["PATH"] = (xbmc.translatePath(__dependencies__ + '/bin:')) + os_env["PATH"]
    
    # NZBGet Binary Install
    try:
        if not xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget')):
            installNzbget = ['sh', xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget-bin-linux.run'),
                             '--destdir', xbmc.translatePath(__programs__ + '/resources/nzbget/')]
            xbmc.log('AUDO: Installing NZBGet Binaries...', level=xbmc.LOGDEBUG)
            subprocess.call(installNzbget, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
    except Exception, e:
        xbmc.log('AUDO: NZBGet Install exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    
    # Touch audo-programs folder stating they are currently loaded <-- for detecting update
    open(__programs__ + '/.current', 'a').close()
    # SABnzbd start
    try:
        # write SABnzbd settings
        # ----------------------
        sabnzbdconfig = ConfigObj(sabnzbdSettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['misc'] = {}
        defaultconfig['misc']['check_new_rel'] = '0'
        defaultconfig['misc']['auto_browser'] = '0'
        defaultconfig['misc']['disable_api_key'] = '0'
        defaultconfig['misc']['username'] = user
        defaultconfig['misc']['password'] = pwd
        defaultconfig['misc']['port'] = '8081'
        defaultconfig['misc']['https_port'] = '9081'
        defaultconfig['misc']['https_cert'] = 'server.cert'
        defaultconfig['misc']['https_key'] = 'server.key'
        defaultconfig['misc']['host'] = host
        defaultconfig['misc']['log_dir'] = 'logs'
        defaultconfig['misc']['admin_dir'] = 'admin'
        defaultconfig['misc']['nzb_backup_dir'] = 'backup'
        
        if firstLaunch:
            defaultconfig['misc']['script_dir'] = 'scripts'
            defaultconfig['misc']['web_dir'] = 'Plush'
            defaultconfig['misc']['web_dir2'] = 'Plush'
            defaultconfig['misc']['web_color'] = 'gold'
            defaultconfig['misc']['web_color2'] = 'gold'
            defaultconfig['misc']['download_dir'] = sabnzbdIncomplete
            defaultconfig['misc']['complete_dir'] = sabnzbdComplete
            servers = {}
            servers['localhost'] = {}
            servers['localhost']['host'] = 'localhost'
            servers['localhost']['port'] = '119'
            servers['localhost']['enable'] = '0'
            categories = {}
            categories['tv'] = {}
            categories['tv']['name'] = 'tv'
            categories['tv']['script'] = 'sabToSickBeard.py'
            categories['tv']['priority'] = '-100'
            categories['movies'] = {}
            categories['movies']['name'] = 'movies'
            categories['movies']['dir'] = 'movies'
            categories['movies']['priority'] = '-100'
            categories['music'] = {}
            categories['music']['name'] = 'music'
            categories['music']['dir'] = 'music'
            categories['music']['priority'] = '-100'
            defaultconfig['servers'] = servers
            defaultconfig['categories'] = categories
            
        sabnzbdconfig.merge(defaultconfig)
        sabnzbdconfig.write()
        
        # also keep the autoProcessTV config up to date
        autoprocessconfig = ConfigObj(xbmc.translatePath(sabnzbdScripts + 'autoProcessTV.cfg'), create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['SickBeard'] = {}
        defaultconfig['SickBeard']['host'] = 'localhost'
        defaultconfig['SickBeard']['port'] = '8082'
        defaultconfig['SickBeard']['username'] = user
        defaultconfig['SickBeard']['password'] = pwd
        autoprocessconfig.merge(defaultconfig)
        autoprocessconfig.write()
        
        # launch SABnzbd and get the API key
        # ----------------------------------
        if firstLaunch or sabnzbdLaunch:
            xbmc.log('AUDO: Launching SABnzbd...', level=xbmc.LOGDEBUG)
            subprocess.call(sabnzbd, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
            
            # SABnzbd will only complete the .ini file when we first access the web interface
            if firstLaunch:
                try:
                    if not (user and pwd):
                        urlopen_with_retry('http://' + sabnzbdHost)
                    else:
                        urlopen_with_retry('http://' + sabnzbdHost + '/api?mode=queue&output=xml&ma_username=' + user +
                                           '&ma_password=' + pwd)
                except Exception, e:
                    xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
                    xbmc.log(str(e), level=xbmc.LOGERROR)
            
            sabnzbdconfig.reload()
            global sabnzbdApiKey
            sabnzbdApiKey = sabnzbdconfig['misc']['api_key']
            
            if firstLaunch and not sabnzbdLaunch:
                urlopen_with_retry('http://' + sabnzbdHost + '/api?mode=shutdown&apikey=' + sabnzbdApiKey)
                xbmc.log('AUDO: Shutting SABnzbd down...', level=xbmc.LOGDEBUG)
    
    except Exception, e:
        xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    # SABnzbd end
    
    # NZBGet start
    if ngfirstLaunch and nzbgetLaunch:
        try:
            # write NZBGet settings
            # ------------------------
            nzbgetconfig = ConfigObj(nzbgetSettings, create_empty=True, write_empty_values=True)
            defaultconfig = ConfigObj()
            defaultconfig['ControlIP'] = host
            defaultconfig['ControlPort'] = '8081'
            if user:
                defaultconfig['ControlUsername'] = user
            else:
                defaultconfig['ControlUsername'] = ''
            if pwd:
                defaultconfig['ControlPassword'] = pwd
            else:
                defaultconfig['ControlPassword'] = ''
            defaultconfig['LogFile'] = __addonhome__ + 'logs/nzbget.log'
            defaultconfig['DaemonUsername'] = 'root'
            defaultconfig['UMask'] = '1000'
            defaultconfig['LockFile'] = '/var/run/nzbget.pid'
            defaultconfig['TempDir'] = '/var/tmp'
            defaultconfig['UnrarCmd'] = 'unrar'
            defaultconfig['SevenZipCmd'] = __programs__ + '/resources/nzbget/7za'
            defaultconfig['WebDir'] = __programs__ + '/resources/nzbget/webui'
            defaultconfig['ConfigTemplate'] = __programs__ + '/resources/nzbget/webui/nzbget.conf.template'
            defaultconfig['MainDir'] = sabnzbdComplete
            defaultconfig['DestDir'] = sabnzbdComplete
            defaultconfig['InterDir'] = sabnzbdIncomplete
            defaultconfig['NzbDir'] = sabnzbdWatchDir
            defaultconfig['ScriptDir'] = __programs__ + '/resources/nzbget/scripts'
            defaultconfig['WriteLog'] = 'append'
            defaultconfig['RotateLog'] = '7'
            defaultconfig['ErrorTarget'] = 'log'
            defaultconfig['WarningTarget'] = 'log'
            defaultconfig['InfoTarget'] = 'log'
            defaultconfig['DetailTarget'] = 'log'
            defaultconfig['DebugTarget'] = 'log'
            defaultconfig['LogBufferSize'] = '1000'
            defaultconfig['NzbLog'] = 'yes'
            defaultconfig['BrokenLog'] = 'yes'
            defaultconfig['DumpCore'] = 'yes'
            
            nzbgetconfig.merge(defaultconfig)
            nzbgetconfig.writenowhitespace()
            
        except Exception, e:
            xbmc.log('AUDO: NZBGet exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
    
    # launch NZBGet
    # ----------------
    try:
        if nzbgetLaunch:
            xbmc.log('AUDO: Launching NZBGet...', level=xbmc.LOGDEBUG)
            subprocess.call(nzbget, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
    except Exception, e:
        xbmc.log('AUDO: NZBGet exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    # NZBGet end
    
    # SickBeard start
    try:
        # write SickBeard settings
        # ------------------------
        sickbeardconfig = ConfigObj(sickbeardSettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['General'] = {}
        defaultconfig['General']['launch_browser'] = '0'
        defaultconfig['General']['version_notify'] = '0'
        defaultconfig['General']['web_port'] = '8082'
        defaultconfig['General']['web_host'] = host
        defaultconfig['General']['web_username'] = user
        defaultconfig['General']['web_password'] = pwd
        defaultconfig['General']['cache_dir'] = __addonhome__ + 'sbcache'
        defaultconfig['General']['log_dir'] = __addonhome__ + 'logs'
        defaultconfig['SABnzbd'] = {}
        defaultconfig['XBMC'] = {}
        defaultconfig['XBMC']['use_xbmc'] = '1'
        defaultconfig['XBMC']['xbmc_host'] = 'localhost:' + xbmcPort
        defaultconfig['XBMC']['xbmc_username'] = xbmcUser
        defaultconfig['XBMC']['xbmc_password'] = xbmcPwd
        defaultconfig['TORRENT'] = {}
        defaultconfig['NZBget'] = {}
        
        if sabnzbdLaunch:
            defaultconfig['SABnzbd']['sab_username'] = user
            defaultconfig['SABnzbd']['sab_password'] = pwd
            defaultconfig['SABnzbd']['sab_apikey'] = sabnzbdApiKey
            defaultconfig['SABnzbd']['sab_host'] = 'http://' + sabnzbdHost + '/'
        
        if nzbgetLaunch:
            defaultconfig['NZBget']['nzbget_username'] = user
            defaultconfig['NZBget']['nzbget_password'] = pwd
            defaultconfig['NZBget']['nzbget_host'] = 'http://' + sabnzbdHost + '/'
        
        if transAuth:
            defaultconfig['TORRENT']['torrent_username'] = transUser
            defaultconfig['TORRENT']['torrent_password'] = transPwd
            defaultconfig['TORRENT']['torrent_host'] = 'http://localhost:9091/'
        
        if sbfirstLaunch:
            defaultconfig['TORRENT']['torrent_path'] = sabnzbdCompleteTv
            defaultconfig['General']['use_api'] = '1'
            defaultconfig['General']['tv_download_dir'] = sabnzbdComplete
            defaultconfig['General']['metadata_xbmc_12plus'] = '0|0|0|0|0|0|0|0|0|0'
            defaultconfig['General']['nzb_method'] = 'sabnzbd'
            defaultconfig['General']['keep_processed_dir'] = '0'
            defaultconfig['General']['use_banner'] = '1'
            defaultconfig['General']['rename_episodes'] = '1'
            defaultconfig['General']['naming_ep_name'] = '0'
            defaultconfig['General']['naming_use_periods'] = '1'
            defaultconfig['General']['naming_sep_type'] = '1'
            defaultconfig['General']['naming_ep_type'] = '1'
            defaultconfig['General']['root_dirs'] = '0|' + homeDir + 'tvshows'
            defaultconfig['General']['naming_custom_abd'] = '0'
            defaultconfig['General']['naming_abd_pattern'] = '%SN - %A-D - %EN'
            defaultconfig['Blackhole'] = {}
            defaultconfig['Blackhole']['torrent_dir'] = sabnzbdWatchDir
            defaultconfig['SABnzbd']['sab_category'] = 'tv'
            # workaround: on first launch, sick beard will always add
            # 'http://' and trailing '/' on its own
            defaultconfig['SABnzbd']['sab_host'] = sabnzbdHost
            defaultconfig['XBMC']['xbmc_notify_ondownload'] = '1'
            defaultconfig['XBMC']['xbmc_update_library'] = '1'
            defaultconfig['XBMC']['xbmc_update_full'] = '1'
        
        sickbeardconfig.merge(defaultconfig)
        sickbeardconfig.write()
        
        # launch SickBeard
        # ----------------
        if sickbeardLaunch:
            xbmc.log('AUDO: Launching SickBeard...', level=xbmc.LOGDEBUG)
            subprocess.call(sickbeard, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
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
            # convert password to md5
            md5pwd = hashlib.md5(str(pwd)).hexdigest()
        
        # write CouchPotatoServer settings
        # --------------------------
        couchpotatoconfig = ConfigObj(couchpotatoSettings, create_empty=True, list_values=False)
        defaultconfig = ConfigObj()
        defaultconfig['core'] = {}
        defaultconfig['core']['username'] = user
        defaultconfig['core']['password'] = md5pwd
        defaultconfig['core']['port'] = '8083'
        defaultconfig['core']['launch_browser'] = '0'
        defaultconfig['core']['host'] = host
        defaultconfig['core']['data_dir'] = __addonhome__
        defaultconfig['updater'] = {}
        defaultconfig['updater']['enabled'] = '0'
        defaultconfig['updater']['notification'] = '0'
        defaultconfig['updater']['automatic'] = '0'
        defaultconfig['xbmc'] = {}
        defaultconfig['xbmc']['enabled'] = '1'
        defaultconfig['xbmc']['username'] = xbmcUser
        defaultconfig['xbmc']['password'] = xbmcPwd
        defaultconfig['sabnzbd'] = {}
        defaultconfig['transmission'] = {}
        defaultconfig['nzbget'] = {}
        
        if sabnzbdLaunch:
            defaultconfig['sabnzbd']['username'] = user
            defaultconfig['sabnzbd']['password'] = pwd
            defaultconfig['sabnzbd']['api_key'] = sabnzbdApiKey
            defaultconfig['sabnzbd']['host'] = sabnzbdHost
        
        if nzbgetLaunch:
            defaultconfig['nzbget']['username'] = user
            defaultconfig['nzbget']['password'] = pwd
            defaultconfig['nzbget']['host'] = sabnzbdHost
        
        if transAuth:
            defaultconfig['transmission']['username'] = transUser
            defaultconfig['transmission']['password'] = transPwd
            defaultconfig['transmission']['host'] = 'localhost:9091'
        
        if cpfirstLaunch:
            defaultconfig['transmission']['directory'] = sabnzbdCompleteMov
            defaultconfig['xbmc']['host'] = 'localhost:' + xbmcPort
            defaultconfig['xbmc']['xbmc_update_library'] = '1'
            defaultconfig['xbmc']['xbmc_update_full'] = '1'
            defaultconfig['xbmc']['xbmc_notify_onsnatch'] = '1'
            defaultconfig['xbmc']['xbmc_notify_ondownload'] = '1'
            defaultconfig['blackhole'] = {}
            defaultconfig['blackhole']['directory'] = sabnzbdWatchDir
            defaultconfig['blackhole']['use_for'] = 'both'
            defaultconfig['blackhole']['enabled'] = '0'
            defaultconfig['sabnzbd']['category'] = 'movies'
            defaultconfig['sabnzbd']['pp_directory'] = sabnzbdCompleteMov
            defaultconfig['renamer'] = {}
            defaultconfig['renamer']['enabled'] = '1'
            defaultconfig['renamer']['from'] = sabnzbdCompleteMov
            defaultconfig['renamer']['to'] = homeDir + 'videos'
            defaultconfig['renamer']['separator'] = '.'
            defaultconfig['renamer']['cleanup'] = '0'
            defaultconfig['core']['permission_folder'] = '0644'
            defaultconfig['core']['permission_file'] = '0644'
            defaultconfig['core']['show_wizard'] = '0'
            defaultconfig['core']['debug'] = '0'
            defaultconfig['core']['development'] = '0'
        
        couchpotatoconfig.merge(defaultconfig)
        couchpotatoconfig.write()
        
        # launch CouchPotatoServer
        # ------------------
        if couchpotatoLaunch:
            xbmc.log('AUDO: Launching CouchPotatoServer...', level=xbmc.LOGDEBUG)
            subprocess.call(couchpotatoserver, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
    except Exception, e:
        xbmc.log('AUDO: CouchPotatoServer exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    # CouchPotatoServer end
    
    # Headphones start
    try:
        # write Headphones settings
        # -------------------------
        headphonesconfig = ConfigObj(headphonesSettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['General'] = {}
        defaultconfig['General']['launch_browser'] = '0'
        defaultconfig['General']['http_port'] = '8084'
        defaultconfig['General']['http_host'] = host
        defaultconfig['General']['http_username'] = user
        defaultconfig['General']['http_password'] = pwd
        defaultconfig['General']['check_github'] = '0'
        defaultconfig['General']['check_github_on_startup'] = '0'
        defaultconfig['General']['cache_dir'] = __addonhome__ + 'hpcache'
        defaultconfig['General']['log_dir'] = __addonhome__ + 'logs'
        defaultconfig['XBMC'] = {}
        defaultconfig['XBMC']['xbmc_enabled'] = '1'
        defaultconfig['XBMC']['xbmc_host'] = 'localhost:' + xbmcPort
        defaultconfig['XBMC']['xbmc_username'] = xbmcUser
        defaultconfig['XBMC']['xbmc_password'] = xbmcPwd
        defaultconfig['SABnzbd'] = {}
        defaultconfig['Transmission'] = {}
        defaultconfig['NZBget'] = {}
        
        if sabnzbdLaunch:
            defaultconfig['SABnzbd']['sab_apikey'] = sabnzbdApiKey
            defaultconfig['SABnzbd']['sab_host'] = sabnzbdHost
            defaultconfig['SABnzbd']['sab_username'] = user
            defaultconfig['SABnzbd']['sab_password'] = pwd
        
        if nzbgetLaunch:
            defaultconfig['NZBget']['nzbget_username'] = user
            defaultconfig['NZBget']['nzbget_password'] = pwd
            defaultconfig['NZBget']['nzbget_host'] = sabnzbdHost
        
        if transAuth:
            defaultconfig['Transmission']['transmission_username'] = transUser
            defaultconfig['Transmission']['transmission_password'] = transPwd
            defaultconfig['Transmission']['transmission_host'] = 'http://localhost:9091'
        
        if hpfirstLaunch:
            defaultconfig['Transmission']['download_torrent_dir'] = sabnzbdCompleteMusic
            defaultconfig['General']['api_enabled'] = '1'
            defaultconfig['SABnzbd']['sab_category'] = 'music'
            defaultconfig['XBMC']['xbmc_update'] = '1'
            defaultconfig['XBMC']['xbmc_notify'] = '1'
            defaultconfig['General']['music_dir'] = homeDir + 'music'
            defaultconfig['General']['destination_dir'] = homeDir + 'music'
            defaultconfig['General']['torrentblackhole_dir'] = sabnzbdWatchDir
            defaultconfig['General']['download_dir'] = sabnzbdCompleteMusic
            defaultconfig['General']['move_files'] = '1'
            defaultconfig['General']['rename_files'] = '1'
            defaultconfig['General']['folder_permissions'] = '0644'
        
        headphonesconfig.merge(defaultconfig)
        headphonesconfig.write()
        
        # launch Headphones
        # -----------------
        if headphonesLaunch:
            xbmc.log('AUDO: Launching Headphones...', level=xbmc.LOGDEBUG)
            subprocess.call(headphones, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
    except Exception, e:
        xbmc.log('AUDO: Headphones exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
        # Headphones end

# SABnzbd addresses and api key
sabNzbdQueue = ('http://' + sabnzbdHost + '/api?mode=queue&output=xml&apikey=')
sabNzbdHistory = ('http://' + sabnzbdHost + '/api?mode=history&output=xml&apikey=')
sabNzbdQueueKeywords = ['<status>Downloading</status>', '<status>Fetching</status>', '<priority>Force</priority>']
sabNzbdHistoryKeywords = ['<status>Repairing</status>', '<status>Verifying</status>', '<status>Extracting</status>']
sabidletimer = 0


def sabinhibitsleep():
    global sabidletimer
    sabidletimer += 1
    # check SABnzbd every ~60s
    if sabidletimer == 60:
        sabisactive = False
        sabidletimer = 0
        req = urllib2.Request(sabNzbdQueue + sabnzbdApiKey)
        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            xbmc.log('AUDO: Could not determine SABnzbds queue status:', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
        else:
            queue = handle.read()
            handle.close()
            if any(x in queue for x in sabNzbdQueueKeywords):
                sabisactive = True
            
        req = urllib2.Request(sabNzbdHistory + sabnzbdApiKey)
        try:
            handle = urllib2.urlopen(req)
        except IOError, e:
            xbmc.log('AUDO: Could not determine SABnzbds history status:', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
        else:
            history = handle.read()
            handle.close()
            if any(x in history for x in sabNzbdHistoryKeywords):
                sabisactive = True
        
        # reset idle timer if queue is downloading/reparing/verifying/extracting
        if sabisactive:
            xbmc.executebuiltin('InhibitIdleShutdown(true)')
            xbmc.log('AUDO: SABnzbd active - preventing sleep', level=xbmc.LOGDEBUG)
        else:
            xbmc.executebuiltin('InhibitIdleShutdown(false)')
            xbmc.log('AUDO: SABnzbd not active - not preventing sleep', level=xbmc.LOGDEBUG)

transidletimer = 0


def transinhibitsleep():
    global transidletimer
    transidletimer += 1
    # check Transmission every ~60s
    if transidletimer == 60:
        transidletimer = 0
        if transAuth:
            tc = transmissionrpc.Client('localhost', port=9091, user=transUser, password=transPwd)
        else:
            tc = transmissionrpc.Client('localhost', port=9091)
        for i in tc.get_torrents():
            if i.status is 'downloading':
                xbmc.executebuiltin('InhibitIdleShutdown(true)')
                xbmc.log('AUDO: Transmission active - preventing sleep', level=xbmc.LOGDEBUG)
                break
        else:
            xbmc.executebuiltin('InhibitIdleShutdown(false)')
            xbmc.log('AUDO: Transmission not active - not preventing sleep', level=xbmc.LOGDEBUG)


def writewakealarm():
    wakehour = wakeHourIdx * 2 + 1
    timeofday = datetime.time(hour=wakehour)
    now = datetime.datetime.now()
    waketime = now.combine(now.date(), timeofday)
    if now.time() > timeofday:
        waketime += datetime.timedelta(days=1)
    secondssinceepoch = time.mktime(waketime.timetuple())
    try:
        if os.path.isfile("/sys/class/rtc/rtc0/wakealarm"):
            f = open("/sys/class/rtc/rtc0/wakealarm", 'r')
            data = f.read()
            f.close()
            if data != secondssinceepoch:
                open("/sys/class/rtc/rtc0/wakealarm", "w").write("0")
                open("/sys/class/rtc/rtc0/wakealarm", "w").write(str(secondssinceepoch))
        else:
            open("/sys/class/rtc/rtc0/wakealarm", "w").write("0")
            open("/sys/class/rtc/rtc0/wakealarm", "w").write(str(secondssinceepoch))
    except IOError, e:
        xbmc.log('AUDO: Could not write /sys/class/rtc/rtc0/wakealarm', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
        pass


def updateprograms():
    xbmc.log('AUDO: Update occurred. Attempting to restart audo services:', level=xbmc.LOGDEBUG)
    count1 = 1
    count2 = 2
    xbmc.executebuiltin(
        "XBMC.Notification(audo, Update detected. Stopping services now., 10000, %s)" % (__icon__))
    shutdown()
    while count1 != count2:
        count1 = 0
        count2 = 0
        for root, dirs, files in os.walk(__programs__):
            count1 += len(files)
        xbmc.sleep(3000)
        for root, dirs, files in os.walk(__programs__):
            count2 += len(files)
    try:
        while not (xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/SickBeard/SickBeard.py'))) and (
            xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/Headphones/Headphones.py'))) and (
            xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/SABnzbd/SABnzbd.py'))) and (
            xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/CouchPotatoServer/CouchPotato.py'))):
            xbmc.sleep(3000)
        xbmc.executebuiltin(
            "XBMC.Notification(audo, Update detected. Restarting services now., 10000, %s)" % (__icon__))
        main()
        xbmc.sleep(10000)
    except Exception, e:
        xbmc.log('AUDO: Could not execute launch script:', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)


def updatedependencies():
    xbmc.log('AUDO: Update occurred. Attempting to setup binaries:', level=xbmc.LOGDEBUG)
    count1 = 1
    count2 = 2
    while count1 != count2:
        count1 = 0
        count2 = 0
        for root, dirs, files in os.walk(__dependencies__):
            count1 += len(files)
        xbmc.sleep(3000)
        for root, dirs, files in os.walk(__dependencies__):
            count2 += len(files)
    try:
        xbmc.executebuiltin('XBMC.RunScript(%s)' % xbmc.translatePath(__dependencies__ + '/default.py'), True)
    except Exception, e:
        xbmc.log('AUDO: Error setting up binaries:', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    while not xbmcvfs.exists(xbmc.translatePath(__dependencies__ + '/arch.' + pArch)):
        xbmc.sleep(5000)


def shutdown():
    
    if sabnzbdLaunch:
        try:
            sabnzbdconfig = ConfigObj(sabnzbdSettings, create_empty=False)
            sabnzbdApiKey = sabnzbdconfig['misc']['api_key']
            if not sabnzbdApiKey:
                os.system("kill `ps | grep -E 'python.*script.module.audo.*SABnzbd' | awk '{print $1}'`")
            else:
                urlopen_with_retry('http://localhost:8081/api?mode=shutdown&apikey=' + sabnzbdApiKey)
            xbmc.log('AUDO: Shutting SABnzbd down...', level=xbmc.LOGDEBUG)
        except Exception, e:
            xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
            os.system("kill `ps | grep -E 'python.*script.module.audo.*SABnzbd' | awk '{print $1}'`")
            pass
    
    if nzbgetLaunch:
        try:
            os.system('.' + xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget') + ' -Q -c ' + nzbgetSettings)
            xbmc.log('AUDO: Shutting NZBGet down...', level=xbmc.LOGDEBUG)
        except Exception, e:
            xbmc.log('AUDO: NZBGet exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
            os.system("kill `ps | grep -E '.*script.module.audo.*nzbget' | awk '{print $1}'`")
            pass
    
    if sickbeardLaunch:
        try:       
            sickbeardconfig = ConfigObj(sickbeardSettings, create_empty=False)
            sickbeardapikey = sickbeardconfig['General']['api_key']
            if not sickbeardapikey:
                os.system("kill `ps | grep -E 'python.*script.module.audo.*SickBeard' | awk '{print $1}'`")
            else:
                urlopen_with_retry('http://localhost:8082/api/' + sickbeardapikey + '/?cmd=sb.shutdown')
            xbmc.log('AUDO: Shutting SickBeard down...', level=xbmc.LOGDEBUG)
        except Exception, e:
            xbmc.log('AUDO: SickBeard exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
            os.system("kill `ps | grep -E 'python.*script.module.audo.*SickBeard' | awk '{print $1}'`")
            pass
    
    if couchpotatoLaunch:
        try:
            couchpotatoconfig = ConfigObj(couchpotatoSettings, create_empty=False, list_values=False)
            couchpotatoapikey = couchpotatoconfig['core']['api_key']
            if not couchpotatoapikey:
                os.system("kill `ps | grep -E 'python.*script.module.audo.*CouchPotato' | awk '{print $1}'`")
            else:
                urlopen_with_retry('http://localhost:8083/api/' + couchpotatoapikey + '/app.shutdown')
            xbmc.log('AUDO: Shutting CouchPotato down...', level=xbmc.LOGDEBUG)
        except Exception, e:
            xbmc.log('AUDO: CouchPotato exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
            os.system("kill `ps | grep -E 'python.*script.module.audo.*CouchPotato' | awk '{print $1}'`")
            pass
    
    if headphonesLaunch:
        try:
            headphonesconfig = ConfigObj(headphonesSettings, create_empty=False)
            headphonesapikey = headphonesconfig['General']['api_key']
            if not headphonesapikey:
                os.system("kill `ps | grep -E 'python.*script.module.audo.*Headphones' | awk '{print $1}'`")
            else:
                urlopen_with_retry('http://localhost:8084/api?apikey=' + headphonesapikey + '&cmd=shutdown')
            xbmc.log('AUDO: Shutting HeadPhones down...', level=xbmc.LOGDEBUG)
        except Exception, e:
            xbmc.log('AUDO: HeadPhones exception occurred', level=xbmc.LOGERROR)
            xbmc.log(str(e), level=xbmc.LOGERROR)
            os.system("kill `ps | grep -E 'python.*script.module.audo.*Headphones' | awk '{print $1}'`")
            pass
