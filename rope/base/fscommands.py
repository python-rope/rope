"""Project file system commands.

This modules implements file system operations used by rope.  Different
version control systems can be supported by implementing the interface
provided by `FileSystemCommands` class.  See `SubversionCommands` and
`MercurialCommands` for example.

"""

import os
import re
import shutil


try:
    import pysvn
except ImportError:
    pass

try:
    import mercurial.commands
    import mercurial.hg
    import mercurial.ui
except ImportError:
    pass


def create_fscommands(root):
    dirlist = os.listdir(root)
    if 'pysvn' in globals() and ('_svn' in dirlist or '.svn' in dirlist):
        return SubversionCommands()
    if 'mercurial' in globals() and '.hg' in dirlist:
        return MercurialCommands(root)
    return FileSystemCommands()


class FileSystemCommands(object):

    def create_file(self, path):
        open(path, 'w').close()

    def create_folder(self, path):
        os.mkdir(path)

    def move(self, path, new_location):
        shutil.move(path, new_location)

    def remove(self, path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    def write(self, path, data):
        file_ = open(path, 'w')
        try:
            file_.write(data)
        finally:
            file_.close()


class SubversionCommands(object):

    def __init__(self):
        self.normal_actions = FileSystemCommands()
        self.client = pysvn.Client()

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self.client.add(path, force=True)

    def create_folder(self, path):
        self.normal_actions.create_folder(path)
        self.client.add(path, force=True)

    def move(self, path, new_location):
        self.client.move(path, new_location, force=True)

    def remove(self, path):
        self.client.remove(path, force=True)

    def write(self, path, data):
        self.normal_actions.write(path, data)


class MercurialCommands(object):

    def __init__(self, root):
        self.normal_actions = FileSystemCommands()
        self.ui = mercurial.ui.ui(
            verbose=False, debug=False, quiet=True,
            interactive=False, traceback=False, report_untrusted=False)
        self.repo = mercurial.hg.repository(self.ui, root)

    def create_file(self, path):
        self.normal_actions.create_file(path)
        mercurial.commands.add(self.ui, self.repo, path)

    def create_folder(self, path):
        self.normal_actions.create_folder(path)

    def move(self, path, new_location):
        mercurial.commands.rename(self.ui, self.repo, path,
                                  new_location, after=False)

    def remove(self, path):
        mercurial.commands.remove(self.ui, self.repo, path)

    def write(self, path, data):
        self.normal_actions.write(path, data)


def unicode_to_file_data(contents, encoding=None):
    if not isinstance(contents, unicode):
        return contents
    if encoding is None:
        encoding = read_str_coding(contents)
    if encoding is not None:
        return contents.encode(encoding)
    try:
        return contents.encode()
    except UnicodeEncodeError:
        return contents.encode('utf-8')

def file_data_to_unicode(data, encoding=None):
    if encoding is None:
        encoding = read_str_coding(data)
    if encoding is not None:
        return unicode(data, encoding)
    try:
        return unicode(data)
    except UnicodeDecodeError:
        # Using ``utf-8`` if guessed encoding fails
        return unicode(data, 'utf-8')


def read_file_coding(path):
    file = open(path, 'b')
    count = 0
    result = []
    buffsize = 10
    while True:
        current = file.read(10)
        if not current:
            break
        count += current.count('\n')
        result.append(current)
    file.close()
    return _find_coding(''.join(result))


def read_str_coding(source):
    try:
        first = source.index('\n') + 1
        second = source.index('\n', first) + 1
    except ValueError:
        second = len(source)
    return _find_coding(source[:second])


_encoding_pattern = None

def _find_coding(first_two_lines):
    global _encoding_pattern
    if _encoding_pattern is None:
        _encoding_pattern = re.compile(r'coding[=:]\s*([-\w.]+)')
    match = _encoding_pattern.search(first_two_lines)
    if match is not None:
        return match.group(1)
