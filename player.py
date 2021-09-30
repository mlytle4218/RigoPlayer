# import external libraries
import vlc
# import standard libraries
import sys
import time
if sys.version_info[0] < 3:
    import Tkinter as Tk
    from Tkinter import ttk
    from Tkinter.filedialog import askopenfilename
    from Tkinter.tkMessageBox import showerror
else:
    import tkinter as Tk
    from tkinter import ttk
    from tkinter.filedialog import askopenfilename
    from tkinter.messagebox import showerror
# from os.path import basename, expanduser, isfile, join as joined
from os.path import expanduser
from pathlib import Path

C_Key = "Control-" 
time_end = 1000

class _Tk_Menu(Tk.Menu):
    '''Tk.Menu extended with .add_shortcut method.
       Note, this is a kludge just to get Command-key shortcuts to
       work on macOS.  Other modifiers like Ctrl-, Shift- and Option-
       are not handled in this code.
    '''
    _shortcuts_entries = {}
    _shortcuts_widget  = None

    def add_shortcut(self, label='', key='', command=None, **kwds):
        '''Like Tk.menu.add_command extended with shortcut key.
           If needed use modifiers like Shift- and Alt_ or Option-
           as before the shortcut key character.  Do not include
           the Command- or Control- modifier nor the <...> brackets
           since those are handled here, depending on platform and
           as needed for the binding.
        '''
        # <https://TkDocs.com/tutorial/menus.html>
        if not key:
            self.add_command(label=label, command=command, **kwds)

        else:  # XXX not tested, not tested, not tested
            self.add_command(label=label, underline=label.lower().index(key),
                                          command=command, **kwds)
            self.bind_shortcut(key, command, label)

    def bind_shortcut(self, key, command, label=None):
        """Bind shortcut key, default modifier Command/Control.
        """
        # The accelerator modifiers on macOS are Command-,
        # Ctrl-, Option- and Shift-, but for .bind[_all] use
        # <Command-..>, <Ctrl-..>, <Option_..> and <Shift-..>,
        # <https://www.Tcl.Tk/man/tcl8.6/TkCmd/bind.htm#M6>
        if self._shortcuts_widget:
            if C_Key.lower() not in key.lower():
                key = "<%s%s>" % (C_Key, key.lstrip('<').rstrip('>'))
            self._shortcuts_widget.bind(key, command)
            # remember the shortcut key for this menu item
            if label is not None:
                item = self.index(label)
                self._shortcuts_entries[item] = key
        # The Tk modifier for macOS' Command key is called
        # Meta, but there is only Meta_L[eft], no Meta_R[ight]
        # and both keyboard command keys generate Meta_L events.
        # Similarly for macOS' Option key, the modifier name is
        # Alt and there's only Alt_L[eft], no Alt_R[ight] and
        # both keyboard option keys generate Alt_L events.  See:
        # <https://StackOverflow.com/questions/6378556/multiple-
        # key-event-bindings-in-tkinter-control-e-command-apple-e-etc>

    def bind_shortcuts_to(self, widget):
        '''Set the widget for the shortcut keys, usually root.
        '''
        self._shortcuts_widget = widget

    def entryconfig(self, item, **kwds):
        """Update shortcut key binding if menu entry changed.
        """
        Tk.Menu.entryconfig(self, item, **kwds)
        # adjust the shortcut key binding also
        if self._shortcuts_widget:
            key = self._shortcuts_entries.get(item, None)
            if key is not None and "command" in kwds:
                self._shortcuts_widget.bind(key, kwds["command"])

class Player(Tk.Frame):
    """The main window has to deal with events.
    """
    def __init__(self, parent, video='',title=None):
        Tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.title(title or 'Training Plan Tool')

        menu_bar = Tk.Menu(self.parent)
        self.parent.config(menu=menu_bar)
        file_menu = _Tk_Menu(menu_bar, tearoff=0)
        file_menu.bind_shortcuts_to(parent)

        file_menu.add_shortcut('Open Video File','o',self.com_open)
        file_menu.add_shortcut('Close','o',self.com_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        
        self.videopanel = ttk.Frame(self.parent)
        self.canvas = Tk.Canvas(self.videopanel)
        self.canvas.pack(fill=Tk.BOTH, expand=1)
        self.videopanel.pack(fill=Tk.BOTH, expand=1)

        self.control_panel = ttk.Frame(self.parent)
        self.control_panel.overrideredirect = self.overrideredirect()
        self.button_play = ttk.Button(self.control_panel, text="Play", command=self.com_play)
        self.button_stop = ttk.Button(self.control_panel, text="Stop", command=self.com_stop)
        self.button_volume = ttk.Button(self.control_panel, text="Volume", command=None)
        # self.button_pause.pack(side=Tk.LEFT)
        self.button_play.pack(side=Tk.LEFT)
        self.button_stop.pack(side=Tk.LEFT)
        self.button_volume.pack(side=Tk.LEFT)
        self.control_panel.pack(side=Tk.BOTTOM)

        #slider
        timers = ttk.Frame(self.control_panel)
        self.time_var = Tk.DoubleVar()
        self.time_slider_last = 0
        self.time_slider = Tk.Scale(timers, variable=self.time_var, command=self.d_time,
                                   from_=0, to=time_end, orient=Tk.HORIZONTAL, length=500,
                                   showvalue=0)  # label='Time',
        self.time_slider.pack(side=Tk.BOTTOM, fill=Tk.X, expand=1)
        self.time_slider_update = time.time()
        timers.pack(side=Tk.BOTTOM, fill=Tk.X)

        # VLC player
        args = []
        self.Instance = vlc.Instance(args)
        self.player = self.Instance.media_player_new()

        self.parent.bind("<Configure>", self.on_configure)  # catch window resize, etc.
        self.parent.update()

        # After parent.update() otherwise panel is ignored.
        # self.control_panel.overrideredirect(True)

        # Estetic, to keep our video panel at least as wide as our buttons panel.
        self.parent.minsize(width=502, height=0)

        # self._AnchorButtonsPanel()

        self.on_tick()  # set the timer up

    def d_time(self, what):
        if self.player:
            t = self.time_var.get()
            if self.time_slider_last != int(t):
                self.player.set_time(int(t * 1e3))  # milliseconds
                self.time_slider_update = time.time()

    def com_open(self):
        self.com_stop()
        video = askopenfilename(initialdir = Path(expanduser("~")),
                                title = "Choose a video",
                                filetypes = (("all files", "*.*"),
                                             ("mp4 files", "*.mp4"),
                                             ("mov files", "*.mov")))
        m = self.Instance.media_new(str(video)) 
        self.player.set_media(m)
        h = self.videopanel.winfo_id()
        self.player.set_hwnd(h)
        self.player.play()
        self.update_play_gui(self.player.is_playing())

    def update_play_gui(self, current):
        if self.player.get_media():
            p = 'Play' if current else 'Pause'
            c = self.com_play if current is None else self.com_pause
            self.button_play.config(text=p, command=c)


    def com_play(self):
        if self.player.get_media():
            self.update_play_gui(self.player.is_playing())
            self.player.pause()

    def com_pause(self):
        if self.player.get_media():
            self.update_play_gui(self.player.is_playing())
            self.player.pause()

    def com_close(self):
        """Closes the window and quit."""
        self.parent.quit()
        self.parent.destroy()

    def com_stop(self):
        if self.player:
            self.player.stop()
            self.update_play_gui(self.player.is_playing())
            self.time_slider.set(0)

    def on_configure(self, *unused):
        self._geometry = '' 

    def overrideredirect(self, boolean=None):
        return True

    def on_tick(self):
        """Timer tick, update the time slider to the video time.
        """
        if self.player:
            # since the self.player.get_length may change while
            # playing, re-set the time_slider to the correct range
            t = self.player.get_length() * 1e-3  # to seconds
            if t > 0:
                self.time_slider.config(to=t)

                t = self.player.get_time() * 1e-3  # to seconds
                # don't change slider while user is messing with it
                if t > 0 and time.time() > (self.time_slider_update + 2):
                    self.time_slider.set(t)
                    self.time_slider_last = int(self.time_var.get())
        # start the 1 second timer again
        self.parent.after(1000, self.on_tick)
        # adjust window to video aspect ratio, done periodically
        # on purpose since the player.video_get_size() only
        # returns non-zero sizes after playing for a while
        if not self._geometry:
            self.on_resize

    def on_resize(self, *unused):
        """Adjust the window/frame to the video aspect ratio.
        """
        g = self.parent.geometry()
        if g != self._geometry and self.player:
            u, v = self.player.video_get_size()  # often (0, 0)
            if v > 0 and u > 0:
                # get window size and position
                g, x, y = g.split('+')
                w, h = g.split('x')
                # alternatively, use .winfo_...
                # w = self.parent.winfo_width()
                # h = self.parent.winfo_height()
                # x = self.parent.winfo_x()
                # y = self.parent.winfo_y()
                # use the video aspect ratio ...
                if u > v:  # ... for landscape
                    # adjust the window height
                    h = round(float(w) * v / u)
                else:  # ... for portrait
                    # adjust the window width
                    w = round(float(h) * u / v)
                self.parent.geometry("%sx%s+%s+%s" % (w, h, x, y))
                self._geometry = self.parent.geometry()  # actual


if __name__ == "__main__":
    _video = (r'C:\Users\marc.lytle\Videos\2021-09-29 16-55-39.mkv')
    root = Tk.Tk()
    player = Player(root, video=_video)
    root.protocol("WM_DELETE_WINDOW", player.com_close)
    root.mainloop()