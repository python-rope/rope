import subprocess
import os
from rope.base import exceptions


class SpellChecker(object):
    """An interface to Aspell/Ispell programs"""

    def __init__(self, text, aspell=None, save_dict=True):
        self.text = text
        if aspell is None:
            self.aspell = Aspell()
        else:
            self.aspell = aspell
        self.aspell.read_line()
        self.aspell.write_line('!')
        self.line_offset = 0
        self.line_ignored = set()
        self.do_quit = False
        self.save_dict = save_dict

    def check(self):
        lines = self.text.splitlines()
        for line in lines:
            if self.do_quit:
                break
            for typo in self._check_line(line):
                yield typo
            self.line_offset += len(line) + 1
            self.line_ignored.clear()
        # PORT: Removed finally clause for python 2.4
        if self.save_dict:
            self.aspell.write_line('#')
        self.aspell.close()

    def _check_line(self, line):
        self.aspell.write_line('^%s' % line)
        while True:
            if self.do_quit:
                break
            result = self.aspell.read_line()
            if result.strip() == '':
                break
            words = result.split()
            typo = None
            if result.startswith('&'):
                suggestions = []
                for word in words[4:]:
                    suggestions.append(word.rstrip(','))
                offset = int(words[3][:-1]) - 1 + self.line_offset
                typo = self._get_typo(words[1], offset, suggestions)
            if result.startswith('#'):
                offset = int(words[2]) - 1 + self.line_offset
                typo = self._get_typo(words[1], offset)
            if typo is not None:
                yield typo

    def _get_typo(self, word, offset, suggestions=[]):
        if word not in self.line_ignored:
            return Typo(word, offset, suggestions)

    def accept_word(self, word):
        self.aspell.write_line('@%s' % word)
        self.line_ignored.add(word)

    def insert_dictionary(self, word):
        self.aspell.write_line('*%s' % word)
        self.line_ignored.add(word)

    def save_dictionary(self):
        self.aspell.write_line('#')

    def quit(self):
        self.do_quit = True


class Typo(object):

    def __init__(self, original, offset, suggestions=[]):
        self.original = original
        self.offset = offset
        self.suggestions = suggestions


class Aspell(object):

    def __init__(self):
        self.process = subprocess.Popen(
            [self._find_executable(), '-a'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)

    def _find_executable(self):
        candidates = ['/usr/bin/aspell', '/usr/local/bin/aspell',
                      '/usr/bin/ispell', '/usr/local/bin/ispell']
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        raise exceptions.RopeError('Cannot find Aspell/Ispell')

    def write_line(self, line):
        self.process.stdin.write(line + '\n')
        self.process.stdin.flush()

    def read_line(self):
        return self.process.stdout.readline()

    def close(self):
        self.process.stdin.close()
