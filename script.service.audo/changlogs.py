import xbmc
import xbmcgui
import xbmcaddon

__programs__ = xbmcaddon.Addon(id='%s' % (sys.argv[1]))


class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % (self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)
        self.setControls()

    def setControls(self):
        # set heading
        heading = "%s - Changelog" % (sys.argv[1])
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        root = __programs__.getAddonInfo('path')
        faq_path = xbmc.translatePath(root + '/changelog.txt')
        f = open(faq_path)
        text = f.read()
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)

TextBox()
