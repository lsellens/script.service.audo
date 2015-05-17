# Initializes and launches SABnzbd, Couchpotato, Sickbeard and Headphones
from xml.dom.minidom import parseString
from configobj import ConfigObj
from functools import wraps
import os
import subprocess
import urllib2
import hashlib
import time
import xbmc
import xbmcaddon
import xbmcvfs


def create_dir(dirname):
    if not xbmcvfs.exists(dirname):
        xbmcvfs.mkdirs(dirname)
        xbmc.log('AUDO: Created directory ' + dirname, level=xbmc.LOGDEBUG)


def retry_on_exc(exceptiontocheck, tries, delay, backoff):
    def retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptiontocheck, e:
                    msg = "AUDO: %s, Retrying in %d seconds..." % (str(e), mdelay)
                    xbmc.log(msg, level=xbmc.LOGDEBUG)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return retry


@retry_on_exc(urllib2.URLError, 5, 3, 2)
def urlopen_with_retry(url):
    return urllib2.urlopen(url)


def main():
    # addon
    __addon__        = xbmcaddon.Addon(id='script.service.audo')
    __addonpath__    = xbmc.translatePath(__addon__.getAddonInfo('path'))
    __addonhome__    = xbmc.translatePath(__addon__.getAddonInfo('profile'))
    __programs__     = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-programs').getAddonInfo('path'))
    __dependencies__ = xbmc.translatePath(xbmcaddon.Addon(id='script.module.audo-dependencies').getAddonInfo('path'))

    # settings
    pdefaultsuitesettings = xbmc.translatePath(__addonpath__ + '/settings-default.xml')
    psuitesettings        = xbmc.translatePath(__addonhome__ + 'settings.xml')
    pxbmcsettings         = xbmc.translatePath('special://home/userdata/guisettings.xml')
    psabnzbdsettings      = xbmc.translatePath(__addonhome__ + 'sabnzbd.ini')
    psickbeardsettings    = xbmc.translatePath(__addonhome__ + 'sickbeard.ini')
    pcouchpotatoserversettings = xbmc.translatePath(__addonhome__ + 'couchpotatoserver.ini')
    pheadphonessettings   = xbmc.translatePath(__addonhome__ + 'headphones.ini')
    pnzbgetsettings       = xbmc.translatePath(__addonhome__ + 'nzbget.conf')
    
    # the settings file already exists if the user set settings before the first launch
    if not xbmcvfs.exists(psuitesettings):
        xbmcvfs.copy(pdefaultsuitesettings, psuitesettings)
    
    # Get Device Home DIR
    phomedir = os.path.expanduser('~/')
    
    # directories
    psabnzbdcomplete = xbmc.translatePath(phomedir + 'downloads/')
    psabnzbdwatchdir = xbmc.translatePath(phomedir + 'downloads/watch/')
    psabnzbdcompletetv = xbmc.translatePath(phomedir + 'downloads/tvshows/')
    psabnzbdcompletemov = xbmc.translatePath(phomedir + 'downloads/movies/')
    psabnzbdcompletemusic = xbmc.translatePath(phomedir + 'downloads/music/')
    psabnzbdincomplete = xbmc.translatePath(phomedir + 'downloads/incomplete/')
    psickbeardtvscripts = xbmc.translatePath(__programs__ + '/resources/SickBeard/autoProcessTV/')
    psabnzbdscripts = xbmc.translatePath(__addonhome__ + 'scripts/')
    
    # service commands
    sabnzbd           = ['python', xbmc.translatePath(__programs__ + '/resources/SABnzbd/SABnzbd.py'),
                         '-d', '--pidfile=/var/run/sabnzbd.pid', '-f', psabnzbdsettings, '-l 0']
    sickbeard         = ['python', xbmc.translatePath(__programs__ + '/resources/SickBeard/SickBeard.py'),
                         '--daemon', '--datadir', __addonhome__, '--pidfile=/var/run/sickbeard.pid', '--config',
                         psickbeardsettings]
    couchpotatoserver = ['python', xbmc.translatePath(__programs__ + '/resources/CouchPotatoServer/CouchPotato.py'),
                         '--daemon', '--pid_file=/var/run/couchpotato.pid', '--config_file', pcouchpotatoserversettings]
    headphones        = ['python', xbmc.translatePath(__programs__ + '/resources/Headphones/Headphones.py'),
                         '-d', '--datadir', __addonhome__, '--pidfile=/var/run/headphones.pid', '--config',
                         pheadphonessettings]
    nzbget            = ['.' + xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget'), '-D', '-c', pnzbgetsettings]
    
    # Other stuff
    sabnzbdhost = 'localhost:8081'
    
    # create directories and settings on first launch
    firstlaunch = not xbmcvfs.exists(psabnzbdsettings)
    ngfirstlaunch = not xbmcvfs.exists(pnzbgetsettings)
    sbfirstlaunch = not xbmcvfs.exists(psickbeardsettings)
    cpfirstlaunch = not xbmcvfs.exists(pcouchpotatoserversettings)
    hpfirstlaunch = not xbmcvfs.exists(pheadphonessettings)
    
    xbmc.log('AUDO: Creating directories if missing', level=xbmc.LOGDEBUG)
    create_dir(__addonhome__)
    create_dir(psabnzbdcomplete)
    create_dir(psabnzbdwatchdir)
    create_dir(psabnzbdcompletetv)
    create_dir(psabnzbdcompletemov)
    create_dir(psabnzbdcompletemusic)
    create_dir(psabnzbdincomplete)
    create_dir(psabnzbdscripts)
    
    if not xbmcvfs.exists(xbmc.translatePath(psabnzbdscripts + 'sabToSickBeard.py')):
        xbmcvfs.copy(xbmc.translatePath(psickbeardtvscripts + 'sabToSickBeard.py'), psabnzbdscripts +
                     'sabToSickBeard.py')
    if not xbmcvfs.exists(xbmc.translatePath(psabnzbdscripts + 'autoProcessTV.py')):
        xbmcvfs.copy(xbmc.translatePath(psickbeardtvscripts + 'autoProcessTV.py'), psabnzbdscripts +
                     'autoProcessTV.py')
    if not os.path.exists(xbmc.translatePath(psabnzbdscripts + 'lib')):
        os.symlink(psickbeardtvscripts + 'lib', psabnzbdscripts + 'lib')
    
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
    nzbget_launch = (__addon__.getSetting('NZBGET_LAUNCH').lower() == 'true')
    sickbeard_launch = (__addon__.getSetting('SICKBEARD_LAUNCH').lower() == 'true')
    couchpotato_launch = (__addon__.getSetting('COUCHPOTATO_LAUNCH').lower() == 'true')
    headphones_launch = (__addon__.getSetting('HEADPHONES_LAUNCH').lower() == 'true')
    
    # XBMC
    fxbmcsettings = open(pxbmcsettings, 'r')
    data = fxbmcsettings.read()
    fxbmcsettings.close()
    xbmcsettings = parseString(data)
    xbmcservices = xbmcsettings.getElementsByTagName('services')[0]
    xbmcport         = xbmcservices.getElementsByTagName('webserverport')[0].firstChild.data
    try:
        xbmcuser     = xbmcservices.getElementsByTagName('webserverusername')[0].firstChild.data
    except StandardError:
        xbmcuser = ''
    try:
        xbmcpwd      = xbmcservices.getElementsByTagName('webserverpassword')[0].firstChild.data
    except StandardError:
        xbmcpwd = ''
    
    # prepare execution environment
    os.environ['PYTHONPATH'] = str(os.environ.get('PYTHONPATH')) + ':' + __dependencies__ + '/lib'
    os_env = os.environ
    os_env["PATH"] = (xbmc.translatePath(__dependencies__ + '/bin:')) + os_env["PATH"]
    
    # NZBGet Binary Install
    try:
        if not xbmcvfs.exists(xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget')):
            installnzbget = ['sh', xbmc.translatePath(__programs__ + '/resources/nzbget/nzbget-bin-linux.run'),
                             '--destdir', xbmc.translatePath(__programs__ + '/resources/nzbget/')]
            xbmc.log('AUDO: Installing NZBGet Binaries...', level=xbmc.LOGDEBUG)
            subprocess.call(installnzbget, close_fds=True, env=os_env)
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
        sabnzbdconfig = ConfigObj(psabnzbdsettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['misc'] = {}
        defaultconfig['misc']['check_new_rel']                 = '0'
        defaultconfig['misc']['auto_browser']                  = '0'
        defaultconfig['misc']['disable_api_key']               = '0'
        defaultconfig['misc']['username']                      = user
        defaultconfig['misc']['password']                      = pwd
        defaultconfig['misc']['port']                          = '8081'
        defaultconfig['misc']['https_port']                    = '9081'
        defaultconfig['misc']['https_cert']                    = 'server.cert'
        defaultconfig['misc']['https_key']                     = 'server.key'
        defaultconfig['misc']['host']                          = host
        defaultconfig['misc']['log_dir']                       = 'logs'
        defaultconfig['misc']['admin_dir']                     = 'admin'
        defaultconfig['misc']['nzb_backup_dir']                = 'backup'
        
        if firstlaunch:
            defaultconfig['misc']['script_dir']                    = 'scripts'
            defaultconfig['misc']['web_dir']                       = 'Plush'
            defaultconfig['misc']['web_dir2']                      = 'Plush'
            defaultconfig['misc']['web_color']                     = 'gold'
            defaultconfig['misc']['web_color2']                    = 'gold'
            defaultconfig['misc']['download_dir']                  = psabnzbdincomplete
            defaultconfig['misc']['complete_dir']                  = psabnzbdcomplete
            servers = {}
            servers['localhost'] = {}
            servers['localhost']['host']                           = 'localhost'
            servers['localhost']['port']                           = '119'
            servers['localhost']['enable']                         = '0'
            categories = {}
            categories['tv'] = {}
            categories['tv']['name']                               = 'tv'
            categories['tv']['script']                             = 'sabToSickBeard.py'
            categories['tv']['priority']                           = '-100'
            categories['movies'] = {}
            categories['movies']['name']                           = 'movies'
            categories['movies']['dir']                            = 'movies'
            categories['movies']['priority']                       = '-100'
            categories['music'] = {}
            categories['music']['name']                            = 'music'
            categories['music']['dir']                             = 'music'
            categories['music']['priority']                        = '-100'
            defaultconfig['servers'] = servers
            defaultconfig['categories'] = categories
        
        sabnzbdconfig.merge(defaultconfig)
        sabnzbdconfig.write()
        
        # also keep the autoProcessTV config up to date
        autoprocessconfig = ConfigObj(xbmc.translatePath(psabnzbdscripts + 'autoProcessTV.cfg'), create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['SickBeard'] = {}
        defaultconfig['SickBeard']['host']                     = 'localhost'
        defaultconfig['SickBeard']['port']                     = '8082'
        defaultconfig['SickBeard']['username']                 = user
        defaultconfig['SickBeard']['password']                 = pwd
        autoprocessconfig.merge(defaultconfig)
        autoprocessconfig.write()
        
        # launch SABnzbd and get the API key
        # ----------------------------------
        if firstlaunch or sabnzbd_launch:
            xbmc.log('AUDO: Launching SABnzbd...', level=xbmc.LOGDEBUG)
            subprocess.call(sabnzbd, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
            
            # SABnzbd will only complete the .ini file when we first access the web interface
            if firstlaunch:
                try:
                    if not (user and pwd):
                        urlopen_with_retry('http://' + sabnzbdhost)
                    else:
                        urlopen_with_retry('http://' + sabnzbdhost + '/api?mode=queue&output=xml&ma_username=' + user +
                                           '&ma_password=' + pwd)
                except Exception, e:
                    xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
                    xbmc.log(str(e), level=xbmc.LOGERROR)
            
            sabnzbdconfig.reload()
            sabnzbdapikey = sabnzbdconfig['misc']['api_key']
            
            if firstlaunch and not sabnzbd_launch:
                urlopen_with_retry('http://' + sabnzbdhost + '/api?mode=shutdown&apikey=' + sabnzbdapikey)
                xbmc.log('AUDO: Shutting SABnzbd down...', level=xbmc.LOGDEBUG)
    
    except Exception, e:
        xbmc.log('AUDO: SABnzbd exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    # SABnzbd end
    
    # NZBGet start
    try:
        # write NZBGet settings
        # ------------------------
        nzbgetconfig = ConfigObj(pnzbgetsettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['ControlIP']                             = host
        defaultconfig['ControlPort']                           = '8081'
        defaultconfig['ControlUsername']                       = user
        defaultconfig['ControlPassword']                       = pwd
        defaultconfig['LogFile']                               = __addonhome__ + 'logs/nzbget.log'
        defaultconfig['DaemonUsername']                        = 'root'
        defaultconfig['UMask']                                 = '1000'
        defaultconfig['LockFile']                              = '/var/run/nzbget.pid'
        defaultconfig['TempDir']                               = '/var/tmp'
        defaultconfig['UnrarCmd']                              = 'unrar'
        defaultconfig['WebDir']                                = __programs__ + '/resources/nzbget/webui'
        defaultconfig['ConfigTemplate']                        = __programs__ + '/resources/nzbget/webui/nzbget.conf.template'
        
        if ngfirstlaunch:
            defaultconfig['MainDir']                               = psabnzbdcomplete
            defaultconfig['DestDir']                               = psabnzbdcomplete
            defaultconfig['InterDir']                              = psabnzbdincomplete
            defaultconfig['NzbDir']                                = psabnzbdwatchdir
            defaultconfig['ScriptDir']                             = __programs__ + '/resources/nzbget/scripts'
            defaultconfig['WriteLog']                              = 'append'
            defaultconfig['RotateLog']                             = '7'
            defaultconfig['ErrorTarget']                           = 'log'
            defaultconfig['WarningTarget']                         = 'log'
            defaultconfig['InfoTarget']                            = 'log'
            defaultconfig['DetailTarget']                          = 'log'
            defaultconfig['DebugTarget']                           = 'log'
            defaultconfig['LogBufferSize']                         = '1000'
            defaultconfig['NzbLog']                                = 'yes'
            defaultconfig['BrokenLog']                             = 'yes'
            defaultconfig['DumpCore']                              = 'yes'
        
        nzbgetconfig.merge(defaultconfig)
        nzbgetconfig.writenowhitespace()
        
        # launch NZBGet
        # ----------------
        if nzbget_launch:
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
        sickbeardconfig = ConfigObj(psickbeardsettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['General'] = {}
        defaultconfig['General']['launch_browser']             = '0'
        defaultconfig['General']['version_notify']             = '0'
        defaultconfig['General']['web_port']                   = '8082'
        defaultconfig['General']['web_host']                   = host
        defaultconfig['General']['web_username']               = user
        defaultconfig['General']['web_password']               = pwd
        defaultconfig['General']['cache_dir']                  = __addonhome__ + 'sbcache'
        defaultconfig['General']['log_dir']                    = __addonhome__ + 'logs'
        defaultconfig['SABnzbd'] = {}
        defaultconfig['XBMC'] = {}
        defaultconfig['XBMC']['use_xbmc']                      = '1'
        defaultconfig['XBMC']['xbmc_host']                     = 'localhost:' + xbmcport
        defaultconfig['XBMC']['xbmc_username']                 = xbmcuser
        defaultconfig['XBMC']['xbmc_password']                 = xbmcpwd
        defaultconfig['TORRENT'] = {}
        defaultconfig['NZBget'] = {}
        
        if sabnzbd_launch:
            defaultconfig['SABnzbd']['sab_username']               = user
            defaultconfig['SABnzbd']['sab_password']               = pwd
            defaultconfig['SABnzbd']['sab_apikey']                 = sabnzbdapikey
            defaultconfig['SABnzbd']['sab_host']                   = 'http://' + sabnzbdhost + '/'
        
        if nzbget_launch:
            defaultconfig['NZBget']['nzbget_username']             = user
            defaultconfig['NZBget']['nzbget_password']             = pwd
            defaultconfig['NZBget']['nzbget_host']                 = 'http://' + sabnzbdhost + '/'
        
        if transauth:
            defaultconfig['TORRENT']['torrent_username']           = transuser
            defaultconfig['TORRENT']['torrent_password']           = transpwd
            defaultconfig['TORRENT']['torrent_host']               = 'http://localhost:9091/'
        
        if sbfirstlaunch:
            defaultconfig['TORRENT']['torrent_path']               = psabnzbdcompletetv
            defaultconfig['General']['use_api']                    = '1'
            defaultconfig['General']['tv_download_dir']            = psabnzbdcomplete
            defaultconfig['General']['metadata_xbmc_12plus']       = '0|0|0|0|0|0|0|0|0|0'
            defaultconfig['General']['nzb_method']                 = 'sabnzbd'
            defaultconfig['General']['keep_processed_dir']         = '0'
            defaultconfig['General']['use_banner']                 = '1'
            defaultconfig['General']['rename_episodes']            = '1'
            defaultconfig['General']['naming_ep_name']             = '0'
            defaultconfig['General']['naming_use_periods']         = '1'
            defaultconfig['General']['naming_sep_type']            = '1'
            defaultconfig['General']['naming_ep_type']             = '1'
            defaultconfig['General']['root_dirs']                  = '0|' + phomedir + 'tvshows'
            defaultconfig['General']['naming_custom_abd']          = '0'
            defaultconfig['General']['naming_abd_pattern']         = '%SN - %A-D - %EN'
            defaultconfig['Blackhole'] = {}
            defaultconfig['Blackhole']['torrent_dir']              = psabnzbdwatchdir
            defaultconfig['SABnzbd']['sab_category']               = 'tv'
            # workaround: on first launch, sick beard will always add
            # 'http://' and trailing '/' on its own
            defaultconfig['SABnzbd']['sab_host']                   = sabnzbdhost
            defaultconfig['XBMC']['xbmc_notify_ondownload']        = '1'
            defaultconfig['XBMC']['xbmc_update_library']           = '1'
            defaultconfig['XBMC']['xbmc_update_full']              = '1'
        
        sickbeardconfig.merge(defaultconfig)
        sickbeardconfig.write()
        
        # launch SickBeard
        # ----------------
        if sickbeard_launch:
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
        couchpotatoserverconfig = ConfigObj(pcouchpotatoserversettings, create_empty=True, list_values=False)
        defaultconfig = ConfigObj()
        defaultconfig['core'] = {}
        defaultconfig['core']['username']                      = user
        defaultconfig['core']['password']                      = md5pwd
        defaultconfig['core']['port']                          = '8083'
        defaultconfig['core']['launch_browser']                = '0'
        defaultconfig['core']['host']                          = host
        defaultconfig['core']['data_dir']                      = __addonhome__
        defaultconfig['updater'] = {}
        defaultconfig['updater']['enabled']                    = '0'
        defaultconfig['updater']['notification']               = '0'
        defaultconfig['updater']['automatic']                  = '0'
        defaultconfig['xbmc'] = {}
        defaultconfig['xbmc']['enabled']                       = '1'
        defaultconfig['xbmc']['username']                      = xbmcuser
        defaultconfig['xbmc']['password']                      = xbmcpwd
        defaultconfig['sabnzbd'] = {}
        defaultconfig['transmission'] = {}
        defaultconfig['nzbget'] = {}
        
        if sabnzbd_launch:
            defaultconfig['sabnzbd']['username']                   = user
            defaultconfig['sabnzbd']['password']                   = pwd
            defaultconfig['sabnzbd']['api_key']                    = sabnzbdapikey
            defaultconfig['sabnzbd']['host']                       = sabnzbdhost
            
        if nzbget_launch:
            defaultconfig['nzbget']['username']                    = user
            defaultconfig['nzbget']['password']                    = pwd
            defaultconfig['nzbget']['host']                        = sabnzbdhost
        
        if transauth:
            defaultconfig['transmission']['username']              = transuser
            defaultconfig['transmission']['password']              = transpwd
            defaultconfig['transmission']['host']                  = 'localhost:9091'
        
        if cpfirstlaunch:
            defaultconfig['transmission']['directory']             = psabnzbdcompletemov
            defaultconfig['xbmc']['host']                          = 'localhost:' + xbmcport
            defaultconfig['xbmc']['xbmc_update_library']           = '1'
            defaultconfig['xbmc']['xbmc_update_full']              = '1'
            defaultconfig['xbmc']['xbmc_notify_onsnatch']          = '1'
            defaultconfig['xbmc']['xbmc_notify_ondownload']        = '1'
            defaultconfig['blackhole'] = {}
            defaultconfig['blackhole']['directory']                = psabnzbdwatchdir
            defaultconfig['blackhole']['use_for']                  = 'both'
            defaultconfig['blackhole']['enabled']                  = '0'
            defaultconfig['sabnzbd']['category']                   = 'movies'
            defaultconfig['sabnzbd']['pp_directory']               = psabnzbdcompletemov
            defaultconfig['renamer'] = {}
            defaultconfig['renamer']['enabled']                    = '1'
            defaultconfig['renamer']['from']                       = psabnzbdcompletemov
            defaultconfig['renamer']['to']                         = phomedir + 'videos'
            defaultconfig['renamer']['separator']                  = '.'
            defaultconfig['renamer']['cleanup']                    = '0'
            defaultconfig['core']['permission_folder']             = '0644'
            defaultconfig['core']['permission_file']               = '0644'
            defaultconfig['core']['show_wizard']                   = '0'
            defaultconfig['core']['debug']                         = '0'
            defaultconfig['core']['development']                   = '0'
        
        couchpotatoserverconfig.merge(defaultconfig)
        couchpotatoserverconfig.write()
        
        # launch CouchPotatoServer
        # ------------------
        if couchpotato_launch:
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
        headphonesconfig = ConfigObj(pheadphonessettings, create_empty=True)
        defaultconfig = ConfigObj()
        defaultconfig['General'] = {}
        defaultconfig['General']['launch_browser']             = '0'
        defaultconfig['General']['http_port']                  = '8084'
        defaultconfig['General']['http_host']                  = host
        defaultconfig['General']['http_username']              = user
        defaultconfig['General']['http_password']              = pwd
        defaultconfig['General']['check_github']               = '0'
        defaultconfig['General']['check_github_on_startup']    = '0'
        defaultconfig['General']['cache_dir']                  = __addonhome__ + 'hpcache'
        defaultconfig['General']['log_dir']                    = __addonhome__ + 'logs'
        defaultconfig['XBMC'] = {}
        defaultconfig['XBMC']['xbmc_enabled']                  = '1'
        defaultconfig['XBMC']['xbmc_host']                     = 'localhost:' + xbmcport
        defaultconfig['XBMC']['xbmc_username']                 = xbmcuser
        defaultconfig['XBMC']['xbmc_password']                 = xbmcpwd
        defaultconfig['SABnzbd'] = {}
        defaultconfig['Transmission'] = {}
        defaultconfig['NZBget'] = {}
        
        if sabnzbd_launch:
            defaultconfig['SABnzbd']['sab_apikey']                 = sabnzbdapikey
            defaultconfig['SABnzbd']['sab_host']                   = sabnzbdhost
            defaultconfig['SABnzbd']['sab_username']               = user
            defaultconfig['SABnzbd']['sab_password']               = pwd
        
        if nzbget_launch:
            defaultconfig['NZBget']['nzbget_username']               = user
            defaultconfig['NZBget']['nzbget_password']               = pwd
            defaultconfig['NZBget']['nzbget_host']                   = sabnzbdhost
        
        if transauth:
            defaultconfig['Transmission']['transmission_username'] = transuser
            defaultconfig['Transmission']['transmission_password'] = transpwd
            defaultconfig['Transmission']['transmission_host']     = 'http://localhost:9091'
        
        if hpfirstlaunch:
            defaultconfig['Transmission']['download_torrent_dir']  = psabnzbdcompletemusic
            defaultconfig['General']['api_enabled']                = '1'
            defaultconfig['SABnzbd']['sab_category']               = 'music'
            defaultconfig['XBMC']['xbmc_update']                   = '1'
            defaultconfig['XBMC']['xbmc_notify']                   = '1'
            defaultconfig['General']['music_dir']                  = phomedir + 'music'
            defaultconfig['General']['destination_dir']            = phomedir + 'music'
            defaultconfig['General']['torrentblackhole_dir']       = psabnzbdwatchdir
            defaultconfig['General']['download_dir']               = psabnzbdcompletemusic
            defaultconfig['General']['move_files']                 = '1'
            defaultconfig['General']['rename_files']               = '1'
            defaultconfig['General']['folder_permissions']         = '0644'
        
        headphonesconfig.merge(defaultconfig)
        headphonesconfig.write()
        
        # launch Headphones
        # -----------------
        if headphones_launch:
            xbmc.log('AUDO: Launching Headphones...', level=xbmc.LOGDEBUG)
            subprocess.call(headphones, close_fds=True, env=os_env)
            xbmc.log('AUDO: ...done', level=xbmc.LOGDEBUG)
    except Exception, e:
        xbmc.log('AUDO: Headphones exception occurred', level=xbmc.LOGERROR)
        xbmc.log(str(e), level=xbmc.LOGERROR)
    # Headphones end
