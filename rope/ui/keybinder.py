"""A module for binding keys to Tkinter widgets

The main goal for adding this module is that Tk does not handle
multi-key keybindings well.

"""
import Tkinter
from rope.ui import statusbar


class KeyBinder(object):

    def __init__(self, status_bar):
        self.binding = []
        self.status_bar = status_bar

    def add_key(self, key, function):
        self.binding.append((key, function))

    def bind(self, widget):
        level = _RootKeyLevel(widget, self.status_bar)
        for key, function in self.binding:
            level.add_key(key.split(' '), function)
        level()


class _KeyLevel(object):

    def __init__(self, parent):
        self.sub_levels = {}
        self.current = {}
        self.parent = parent

    def add_key(self, keys, function):
        if len(keys) > 1:
            if keys[0] not in self.sub_levels:
                self.sub_levels[keys[0]] = _KeyLevel(self.parent)
            self.sub_levels[keys[0]].add_key(keys[1:], function)
        else:
            self.current[keys[0]] = function

    def __call__(self, status_text):
        frame = Tkinter.Frame(self.parent)
        frame.pack()
        def cancel(event=None):
            frame.destroy()
            self.parent.focus_set()
        def done(event=None):
            frame.destroy()
            self.parent.focus_set()
            status_text.remove()
        frame.focus_set()
        frame.bind('<Any-KeyPress>', self._unrelated_key(done))

        frame.bind('<Control-g>', done)
        frame.bind('<Escape>', done)
        frame.bind('<FocusOut>', done)
        for key, sub_level in self.sub_levels.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_sublevel_callback(cancel, sub_level,
                                                   key, status_text))
        for key, function in self.current.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_function_callback(done, function))
        return 'break'

    def _unrelated_key(self, cancel):
        def call_back(event=None):
            if len(event.char) == 1:
                cancel()
                return 'break'
        return call_back

    def _get_function_callback(self, cancel, function):
        def call_back(event=None):
            cancel()
            function()
            return 'break'
        return call_back

    def _get_sublevel_callback(self, cancel, function, key, status_text):
        def call_back(event=None):
            cancel()
            status_text.set_text(status_text.get_text() + ' ' + key)
            function(status_text)
            return 'break'
        return call_back


class _RootKeyLevel(_KeyLevel):

    def __init__(self, parent, status_bar):
        super(_RootKeyLevel, self).__init__(parent)
        self.status_bar = status_bar

    def __call__(self):
        frame = self.parent
        for key, sub_level in self.sub_levels.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_sublevel_callback(sub_level, key))
        for key, function in self.current.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_function_callback(function))
        return 'break'

    def _get_function_callback(self, function):
        def call_back(event=None):
            function()
            return 'break'
        return call_back

    def _get_sublevel_callback(self, function, key):
        def call_back(event=None):
            try:
                status_text = self.status_bar.create_status('key')
                status_text.set_width(6)
            except statusbar.StatusBarException:
                status_text = self.status_bar.get_status('key')
            status_text.set_text(key)
            function(status_text)
            return 'break'
        return call_back


def _emacs_to_tk(sequence):
    result = []
    for key in sequence.split(' '):
        tokens = key.split('-')
        key = tokens[-1]
        modifier = ''
        if len(tokens) > 1:
            modifier = '-'.join(token.capitalize() for token in tokens[:-1]) + '-'
        modifier = modifier.replace('M-', 'Alt-').replace('C-', 'Control-')
        if key.isdigit():
            key = 'KeyPress-' + key
        result.append('<%s>' % (modifier + key))
    return ''.join(result)
