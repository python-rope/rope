import unittest

from rope.ui.statusbar import StatusBarException
from rope.ui.searcher import Searcher
from ropetest.ui.mockeditortest import GraphicalEditorFactory, MockEditorFactory

class SearchingTest(unittest.TestCase):
    __factory = MockEditorFactory()
#    __factory = GraphicalEditorFactory()
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create()
        self.editor.set_text('sample text')
        self.searcher = Searcher(self.editor)

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def test_staring_and_stoping_searching(self):
        self.assertEquals(False, self.searcher.is_searching())
        self.searcher.start_searching()
        self.assertEquals(True, self.searcher.is_searching())
        self.assertEquals(self.editor.get_start(), self.searcher.get_match().start)
        self.searcher.end_searching()
        self.assertEquals(False, self.searcher.is_searching())
        self.assertEquals(self.editor.get_start(), self.searcher.get_match().start)

    def test_simple_one_char_searching(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('s')
        self.assertEquals(self.editor.get_index(1), self.searcher.get_match().end)
        self.assertEquals('right', self.searcher.get_match().side)

    def test_searching_two_chars(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('s')
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)
        self.assertEquals('right', self.searcher.get_match().side)

    def test_searching_not_from_the_begining(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)
        self.searcher.append_keyword('m')
        self.assertEquals(self.editor.get_index(3), self.searcher.get_match().end)

    def test_jumping_if_match_failed(self):
        self.editor.set_text('abc aba')
        self.searcher.start_searching()
        self.searcher.append_keyword('b')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(7), self.searcher.get_match().end)

    def test_shortening_keyword(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('m')
        self.assertEquals(self.editor.get_index(3), self.searcher.get_match().end)
        self.searcher.shorten_keyword()
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)

    def test_shortening_keyword2(self):
        self.editor.set_text('aa')
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)
        self.searcher.shorten_keyword()
        self.assertEquals(self.editor.get_index(1), self.searcher.get_match().end)

    def test_going_to_start_if_keyword_gets_empty(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.shorten_keyword()
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().end)

    def test_canceling_searches(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.cancel_searching()
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().end)

    def test_ending_searches(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.end_searching()
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)

    def test_next_match(self):
        self.editor.set_text('abc aba')
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)
        self.searcher.next_match()
        self.assertEquals(self.editor.get_index(6), self.searcher.get_match().end)

    def test_next_match_when_none_available(self):
        self.editor.set_text('abc aba')
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(7), self.searcher.get_match().end)
        self.searcher.next_match()
        self.assertEquals(self.editor.get_index(7), self.searcher.get_match().end)

    def test_prev_match(self):
        self.editor.set_text('abc aba')
        self.editor.set_insert(self.editor.get_index(4))
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.assertEquals(self.editor.get_index(6), self.searcher.get_match().end)
        self.searcher.configure_search(forward=False)
        self.searcher.next_match()
        self.assertEquals('left', self.searcher.get_match().side)
        self.assertEquals(self.editor.get_index(4), self.searcher.get_match().start)
        self.searcher.next_match()
        self.assertEquals('left', self.searcher.get_match().side)
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().start)

    def test_appending_in_prev_match(self):
        self.editor.set_text('abc aba')
        self.editor.set_insert(self.editor.get_index(4))
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.searcher.configure_search(forward=False)
        self.searcher.next_match()
        self.searcher.append_keyword('c')
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().start)

    def test_shortening_in_prev_match(self):
        self.editor.set_text('abc aba')
        self.editor.set_insert(self.editor.get_index(3))
        self.searcher.start_searching()
        self.searcher.configure_search(forward=False)
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().start)
        self.searcher.shorten_keyword()
        self.assertEquals(self.editor.get_index(0), self.searcher.get_match().start)

    def test_appending_in_prev_match(self):
        self.editor.set_text('aa aa aa')
        self.editor.set_insert(self.editor.get_index(2))
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(5), self.searcher.get_match().end)
        self.searcher.configure_search(forward=False)
        self.searcher.next_match()
        self.assertEquals(self.editor.get_index(3), self.searcher.get_match().start)

    def test_ignoring_case(self):
        self.editor.set_text(' aBc abc')
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('b')
        self.assertEquals(self.editor.get_index(3), self.searcher.get_match().end)

    def test_uppercase_in_keyword(self):
        self.editor.set_text(' ab aB')
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('B')
        self.assertEquals(self.editor.get_index(6), self.searcher.get_match().end)

    def test_when_keyword_is_not_found(self):
        self.searcher.start_searching()
        self.searcher.append_keyword('a')
        self.searcher.append_keyword('a')
        self.assertEquals(self.editor.get_index(2), self.searcher.get_match().end)

    def test_searching_status_bar(self):
        self.editor.status_bar_manager = PlaceholderStatusBarManager()
        manager = self.editor.status_bar_manager
        try:
            manager.get_status('search')
            self.fail('Should have failed')
        except StatusBarException:
            pass
        self.searcher.start_searching()
        status = manager.get_status('search')
        self.searcher.end_searching()
        try:
            manager.get_status('search')
            self.fail('Should have failed')
        except StatusBarException:
            pass


class PlaceholderStatusBarManager(object):
    def __init__(self):
        self.status_text = {}

    def get_status(self, kind):
        if kind not in self.status_text:
            raise StatusBarException('StatusText <%s> does not exist' % kind)
        return self.status_text[kind]

    def create_status(self, kind):
        if kind in self.status_text:
            raise StatusBarException('StatusText <%s> already exists' % kind)
        self.status_text[kind] = PlaceholderStatusText(self, kind)
        self.status_text[kind].set_text('')
        return self.status_text[kind]


    def remove_status(self, status):
        del self.status_text[status.kind]


class PlaceholderStatusText(object):
    def __init__(self, status_bar_manager, kind):
        self.manager = status_bar_manager
        self.kind = kind
        self.width = 0
        self.text = ''

    def set_width(self, width):
        self.width = width

    def set_text(self, text):
        self.text = text.ljust(self.width)

    def get_text(self):
        return self.text

    def remove(self):
        self.manager.remove_status(self)


if __name__ == '__main__':
    unittest.main()
