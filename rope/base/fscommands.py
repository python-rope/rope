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
    if 'pysvn' in globals() and '.svn' in os.listdir(root):
        return SubversionCommands()
    if 'mercurial' in globals() and '.hg' in os.listdir(root):
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
        self.client.remove(self.ui, self.repo, path)

    def write(self, path, data):
        self.normal_actions.write(path, data)


def unicode_to_file_data(contents):
    return _TransformUnicode.get_instance().unicode_to_file_data(contents)


def file_data_to_unicode(contents):
    return _TransformUnicode.get_instance().file_data_to_unicode(contents)


class _TransformUnicode(object):

    def unicode_to_file_data(self, contents):
        encoding = self._conclude_file_encoding(contents)
        if encoding is not None and isinstance(contents, unicode):
            return contents.encode(encoding)
        try:
            return contents.encode()
        except UnicodeEncodeError:
            return contents.encode('utf-8')

    def file_data_to_unicode(self, data):
        encoding = self._conclude_file_encoding(data)
        if encoding is not None:
            return unicode(data, encoding)
        try:
            return unicode(data)
        except UnicodeDecodeError:
            # Using ``utf-8`` if guessed encoding fails
            return unicode(data, 'utf-8')

    def _find_line_end(self, source_bytes, start):
        try:
            return source_bytes.index('\n', start)
        except ValueError:
            return len(source_bytes)

    def _get_second_line_end(self, source_bytes):
        line1_end = self._find_line_end(source_bytes, 0)
        if line1_end != len(source_bytes):
            return self._find_line_end(source_bytes, line1_end)
        else:
            return line1_end

    encoding_pattern = re.compile(r'coding[=:]\s*([-\w.]+)')

    def _conclude_file_encoding(self, source_bytes):
        first_two_lines = source_bytes[:self._get_second_line_end(source_bytes)]
        match = _TransformUnicode.encoding_pattern.search(first_two_lines)
        if match is not None:
            return match.group(1)

    file_access = None

    @classmethod
    def get_instance(cls):
        if cls.file_access is None:
            cls.file_access = _TransformUnicode()
        return cls.file_access
