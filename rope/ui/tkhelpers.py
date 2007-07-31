from Tkinter import *


class WidgetRedirector(object):
    """Got from idlelib for redirecting messages to widgets"""

    def __init__(self, widget):
        self.dict = {}
        self.widget = widget
        self.tk = tk = widget.tk
        w = widget._w
        self.orig = w + "_orig"
        tk.call("rename", w, self.orig)
        tk.createcommand(w, self.dispatch)

    def close(self):
        for name in self.dict.keys():
            self.unregister(name)
        widget = self.widget; del self.widget
        orig = self.orig; del self.orig
        tk = widget.tk
        w = widget._w
        tk.deletecommand(w)
        tk.call("rename", orig, w)

    def register(self, name, function):
        if name in self.dict:
            previous = dict[name]
        else:
            previous = _OriginalCommand(self, name)
        self.dict[name] = function
        setattr(self.widget, name, function)
        return previous

    def unregister(self, name):
        if name in self.dict:
            function = self.dict[name]
            del self.dict[name]
            if hasattr(self.widget, name):
                delattr(self.widget, name)
            return function
        else:
            return None

    def dispatch(self, cmd, *args):
        m = self.dict.get(cmd)
        try:
            if m:
                return m(*args)
            else:
                return self.tk.call((self.orig, cmd) + args)
        except TclError, e:
            return ""


class ToolTip(object):
    """Got from idlelib for adding tooltips"""

    def __init__(self, button, text):
        self.button = button
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self._id1 = self.button.bind("<Enter>", self.enter)
        self._id2 = self.button.bind("<Leave>", self.leave)
        self._id3 = self.button.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.button.after(700, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.button.after_cancel(id)

    def showtip(self):
        if self.tipwindow:
            return
        # The tip window must be completely outside the button;
        # otherwise when the mouse enters the tip window we get
        # a leave event and it disappears, and then we get an enter
        # event and it reappears, and so on forever :-(
        x = self.button.winfo_rootx() + 20
        y = self.button.winfo_rooty() + self.button.winfo_height() + 1
        self.tipwindow = tw = Toplevel(self.button)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        self.showcontents()

    def showcontents(self):
        # Override this in derived class
        label = Label(self.tipwindow, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1)
        label.pack()

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class _OriginalCommand(object):

    def __init__(self, redir, name):
        self.redir = redir
        self.name = name
        self.tk = redir.tk
        self.orig = redir.orig
        self.tk_call = self.tk.call
        self.orig_and_name = (self.orig, self.name)

    def __call__(self, *args):
        return self.tk_call(self.orig_and_name + args)
