"""Project file system commands.

This modules implements file system operations used by rope.
Different version control systems can supported by implementing the
interface provided by `FileSystemCommands` class.

"""

import os
import shutil
import re


try:
    import pysvn
except ImportError:
    pass


def create_fscommands(root):
    if 'pysvn' in globals() and '.svn' in os.listdir(root):
        return SubversionCommands()
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


class FileAccess(object):

    def read(self, path):
        """Read the content of the file at `path`.

        Returns a `Unicode` object
        """
        source_bytes = open(path, 'U').read()
        return self._file_data_to_unicode(source_bytes)

    def _file_data_to_unicode(self, data):
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
        match = FileAccess.encoding_pattern.search(first_two_lines)
        if match is not None:
            return match.group(1)

    def write(self, path, contents):
        """Write the `contents` to the file at `path`.

        contents should be a `Unicode` object.
        """
        file_ = open(path, 'w')
        encoding = self._conclude_file_encoding(contents)
        if encoding is not None and isinstance(contents, unicode):
            contents = contents.encode(encoding)
        try:
            file_.write(contents)
        except UnicodeEncodeError:
            # Using ``utf-8`` if guessed encoding fails
            file_.write(contents.encode('utf-8'))
        file_.close()

