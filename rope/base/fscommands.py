"""Project file system commands.

This modules implements file system operations used by rope.  Different
version control systems can be supported by implementing the interface
provided by `FileSystemCommands` class.  See `SubversionCommands` and
`MercurialCommands` for example.

"""
import os
import shutil


def create_fscommands(root):
    dirlist = os.listdir(root)
    commands = {'.hg': MercurialCommands,
                '.svn': SubversionCommands,
                '_svn': SubversionCommands}
    for key in commands:
        if key in dirlist:
            try:
                return commands[key](root)
            except ImportError:
                pass
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
        file_ = open(path, 'wb')
        try:
            file_.write(data)
        finally:
            file_.close()


class SubversionCommands(object):

    def __init__(self, *args):
        self.normal_actions = FileSystemCommands()
        import pysvn
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
        self.hg = self._import_mercurial()
        self.normal_actions = FileSystemCommands()
        self.ui = self.hg.ui.ui(
            verbose=False, debug=False, quiet=True,
            interactive=False, traceback=False, report_untrusted=False)
        self.repo = self.hg.hg.repository(self.ui, root)

    def _import_mercurial(self):
        import mercurial.commands
        import mercurial.hg
        import mercurial.ui
        return mercurial

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self.hg.commands.add(self.ui, self.repo, path)

    def create_folder(self, path):
        self.normal_actions.create_folder(path)

    def move(self, path, new_location):
        self.hg.commands.rename(self.ui, self.repo, path,
                                  new_location, after=False)

    def remove(self, path):
        self.hg.commands.remove(self.ui, self.repo, path)

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
    result = _decode_data(data, encoding)
    if '\r\n' in result:
        return result.replace('\r\n', '\n')
    return result

def _decode_data(data, encoding):
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


def _find_coding(first_two_lines):
    coding = 'coding'
    try:
        start = first_two_lines.index(coding) + len(coding)
        while start < len(first_two_lines):
            if first_two_lines[start] not in '=: \t':
                break
            start += 1
        end = start
        while end < len(first_two_lines):
            c = first_two_lines[end]
            if not c.isalnum() and c not in '-_':
                break
            end += 1
        return first_two_lines[start:end]
    except ValueError:
        pass
