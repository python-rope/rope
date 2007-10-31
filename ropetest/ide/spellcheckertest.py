import unittest

from ropeide.spellchecker import SpellChecker
from ropetest import testutils
from StringIO import StringIO


class SpellCheckerTest(unittest.TestCase):

    def setUp(self):
        super(SpellCheckerTest, self).setUp()
        self.aspell = _StubAspell()

    def tearDown(self):
        super(SpellCheckerTest, self).tearDown()

    def test_trivial_case(self):
        checker = SpellChecker('', aspell=self.aspell)
        self.assertEquals([], list(checker.check()))

    def test_no_errors(self):
        checker = SpellChecker('hello', aspell=self.aspell)
        self.assertEquals([], list(checker.check()))

    @testutils.assert_raises(StopIteration)
    def _assert_ended(self, iterator):
        iterator.next()

    def test_simple_error(self):
        checker = SpellChecker('hellp', aspell=self.aspell)
        result = checker.check()
        self.assertEquals('hellp', result.next().original)
        self._assert_ended(result)

    def test_offset_and_suggestions(self):
        checker = SpellChecker('hellp', aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        self.assertEquals('hellp', typo.original)
        self.assertEquals(0, typo.offset)
        self.assertTrue(len(typo.suggestions) > 0)
        self._assert_ended(result)

    def test_lines_starting_with_aspell_signs(self):
        checker = SpellChecker('* hellp', aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        self.assertEquals('hellp', typo.original)
        self.assertEquals(2, typo.offset)
        self._assert_ended(result)

    def test_multi_lines(self):
        text = 'correct\n hellp\n'
        checker = SpellChecker(text, aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        self.assertEquals('hellp', typo.original)
        self.assertEquals(text.index('hellp'), typo.offset)
        self._assert_ended(result)

    def test_more_than_one_error(self):
        text = 'hellp\n hellp\n'
        checker = SpellChecker(text, aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        self.assertEquals('hellp', typo.original)
        self.assertEquals(text.index('hellp'), typo.offset)
        typo = result.next()
        self.assertEquals('hellp', typo.original)
        self.assertEquals(text.rindex('hellp'), typo.offset)
        self._assert_ended(result)

    def test_accepting_words(self):
        text = 'hellp\nhellp\n'
        checker = SpellChecker(text, aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        checker.accept_word('hellp')
        self._assert_ended(result)

    def test_inserting_dictionary(self):
        text = 'hellp\nhellp\n'
        checker = SpellChecker(text, aspell=self.aspell, save_dict=False)
        result = checker.check()
        typo = result.next()
        checker.insert_dictionary('hellp')
        self._assert_ended(result)

    def test_accepting_words_on_the_same_line(self):
        text = 'hellp hellp\n'
        checker = SpellChecker(text, aspell=self.aspell)
        result = checker.check()
        typo = result.next()
        checker.accept_word('hellp')
        self._assert_ended(result)


class _StubAspell(object):

    def __init__(self):
        self.ignored = False
        self.output = ['_MockAspell']

    def write_line(self, line):
        if line.startswith('@') or line.startswith('*'):
            self.ignored = True
            return
        if line.startswith('#') or line.startswith('!'):
            return
        offset = 0
        while offset < len(line):
            try:
                offset = line.index('hellp', offset)
                if not self.ignored:
                    self.output.append('& hellp 3 %i: help, hello, hell' % offset)
                offset += 1
            except ValueError:
                self.output.append('')
                break

    def read_line(self):
        return self.output.pop(0)

    def close(self):
        pass


if __name__ == '__main__':
    unittest.main()
