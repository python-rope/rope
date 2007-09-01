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
        self.prefix = 'C-u'

    def add_key(self, key, function):
        self.binding.append((key, function))

    def bind(self, widget):
        level = _KeyLevel(widget, self.status_bar, prefix=self.prefix)
        for key, function in self.binding:
            level.add_key(key.split(' '), function)
        level.start()


class _KeyLevel(object):

    def __init__(self, parent, status_bar=None, prefix=None):
        self.sub_levels = {}
        self.current = {}
        self.parent = parent
        self.status_bar = status_bar
        self.prefix = prefix

    def add_key(self, keys, function):
        if len(keys) > 1:
            if keys[0] not in self.sub_levels:
                self.sub_levels[keys[0]] = _KeyLevel(self.parent,
                                                     prefix=self.prefix)
            self.sub_levels[keys[0]].add_key(keys[1:], function)
        else:
            self.current[keys[0]] = function

    def start(self):
        frame = self.parent
        if self.prefix is not None:
            frame.bind(_emacs_to_tk(self.prefix),
                       self._get_sublevel_callback(self, self.prefix))
        for key, sub_level in self.sub_levels.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_sublevel_callback(sub_level, key))
        for key, function in self.current.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_function_callback(function, key))

    def continue_(self, key_data):
        frame = Tkinter.Frame(self.parent)
        frame.pack()
        status_text = key_data.status_text
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
                       self._get_sublevel_callback(sub_level, key,
                                                   key_data, cancel))
        for key, function in self.current.items():
            frame.bind(_emacs_to_tk(key),
                       self._get_function_callback(function, key,
                                                   key_data, cancel))

    def _unrelated_key(self, cancel):
        def callback(event=None):
            if len(event.char) == 1:
                cancel()
                return 'break'
        return callback

    def _get_function_callback(self, function, key,
                               key_data=None, to_be_called=None):
        def callback(event=None, key_data=key_data):
            if to_be_called is not None:
                to_be_called()
            if key_data is None:
                key_data = self._get_key_data()
            #self._add_key_text(key_data)
            key_data.keys.append(key)
            key_data.status_text.remove()
            prefix = None
            if key_data.keys[0] == self.prefix:
                prefix = True
            print key_data.keys, self.prefix, prefix
            function(prefix)
            return 'break'
        return callback

    def _get_sublevel_callback(self, sublevel, key,
                               key_data=None, to_be_called=None):
        def callback(event=None, key_data=key_data):
            if to_be_called is not None:
                to_be_called()
            if key_data is None:
                key_data = self._get_key_data()
            key_data.keys.append(key)
            self._add_key_text(key_data)
            sublevel.continue_(key_data)
            return 'break'
        return callback

    def _add_key_text(self, key_data):
        status_text = key_data.status_text
        status_text.set_text(' '.join(key_data.keys))

    def _get_key_data(self):
        try:
            status_text = self.status_bar.create_status('key')
            status_text.set_width(11)
        except statusbar.StatusBarException:
            status_text = self.status_bar.get_status('key')
        return _KeyData(status_text)


class _KeyData(object):

    def __init__(self, status_text=None):
        self.status_text = status_text
        self.keys = []


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
        key = key.replace('/', 'slash').replace('$', 'dollar').\
              replace('<', 'less').replace('>', 'KeyPress->')
        result.append('<%s>' % (modifier + key))
    return ''.join(result)
