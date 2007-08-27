from rope.ui import statusbar



class SearchingState(object):

    def append_keyword(self, searcher, postfix):
        """Appends postfix to the keyword"""

    def shorten_keyword(self, searcher):
        """Deletes the last char of keyword"""

    def next_match(self, searcher):
        """Go to the next match"""


class ForwardSearching(SearchingState):

    def append_keyword(self, searcher, postfix):
        start = searcher.editor.get_relative(searcher.editor.get_insert(),
                                             -len(searcher.keyword))
        searcher.keyword += postfix
        searcher._match(start)

    def shorten_keyword(self, searcher):
        if searcher.keyword == '':
            return
        searcher.keyword = searcher.keyword[:-1]
        start = searcher.editor.get_relative(searcher.editor.get_insert(), -1)
        searcher._match(start, forward=False)

    def next_match(self, searcher):
        if not searcher.keyword:
            return
        searcher._match(searcher.editor.get_insert())

    def is_searching(self, searcher):
        return True


class BackwardSearching(SearchingState):

    def append_keyword(self, searcher, postfix):
        searcher.keyword += postfix
        start = searcher.editor.get_relative(searcher.editor.get_insert(),
                                             +len(searcher.keyword))
        searcher._match(start, forward=False, insert_side='left')

    def shorten_keyword(self, searcher):
        if not searcher.keyword:
            return
        searcher.keyword = searcher.keyword[:-1]
        searcher._match(searcher.editor.get_insert(), insert_side='left')

    def next_match(self, searcher):
        if not searcher.keyword:
            return
        searcher._match(searcher.editor.get_insert(),
                        forward=False, insert_side='left')

    def is_searching(self, searcher):
        return True


class NotSearching(SearchingState):
    """A null object for when not searching"""

    def append_keyword(self, searcher, postfix):
        pass

    def shorten_keyword(self, searcher):
        pass

    def next_match(self, searcher):
        pass

    def is_searching(self, searcher):
        return False


class Match(object):

    def __init__(self, start, end, side='right'):
        self.start = start
        self.end = end
        self.side = side


class Searcher(object):
    """A class for searching TextEditors"""

    def __init__(self, editor):
        self.editor = editor
        self.keyword = ''
        self.searching_state = NotSearching()
        self.current_match = None
        self.history = ''
        self.failing = False

    def start_searching(self):
        self.keyword = ''
        self.starting_index = self.editor.get_insert()
        self.searching_state = ForwardSearching()
        self.current_match = Match(self.starting_index, self.starting_index)
        self.status_text = None
        manager = self.editor.status_bar_manager
        if manager:
            try:
                self.status_text = manager.create_status('search')
            except statusbar.StatusBarException:
                self.status_text = manager.get_status('search')
            self.status_text.set_width(35)
        self.update_status_text()

    def _finish_searching(self):
        if self.status_text:
            self.status_text.remove()
        self.searching_state = NotSearching()
        self.editor.highlight_match(self.current_match)
        self.failing = False

    def end_searching(self, save=True):
        self.history = self.keyword
        if save:
            self.current_match = Match(self.editor.get_insert(),
                                       self.editor.get_insert())
        self._finish_searching()

    def is_searching(self):
        return self.searching_state.is_searching(self)

    def update_status_text(self):
        if self.status_text:
            direction = ''
            if isinstance(self.searching_state, BackwardSearching):
                direction = 'Backward '
            failing = ''
            if self.failing:
                failing = 'Failing '
            self.status_text.set_text('%s%sSearch: <%s>' %
                                      (failing, direction, self.keyword))

    def append_keyword(self, postfix):
        self.searching_state.append_keyword(self, postfix)
        self.update_status_text()

    def shorten_keyword(self):
        self.searching_state.shorten_keyword(self)
        self.update_status_text()

    def cancel_searching(self):
        self.current_match = Match(self.starting_index, self.starting_index)
        self._finish_searching()

    def configure_search(self, forward=True):
        if forward and self.searching_state.is_searching(self) and \
               not isinstance(self.searching_state, ForwardSearching):
            self.searching_state = ForwardSearching()
        if not forward and self.searching_state.is_searching(self) and \
               not isinstance(self.searching_state, BackwardSearching):
            self.searching_state = BackwardSearching()
        self.update_status_text()

    def next_match(self):
        if not self.keyword:
            self.keyword = self.history
        self.searching_state.next_match(self)
        self.update_status_text()

    def _match(self, start, forward=True, insert_side='right'):
        if self.keyword:
            case = False
            if not self.keyword.islower():
                case = True
            found = self.editor.search(self.keyword, start,
                                       case=case, forwards=forward)
            if found:
                found_end = self.editor.get_relative(found, len(self.keyword))
                self.current_match = Match(found, found_end, insert_side)
                self.editor.highlight_match(self.current_match)
                self.failing = False
            else:
                self.failing = True
        else:
            self.current_match = Match(self.starting_index,
                                       self.starting_index)
            self.editor.highlight_match(self.current_match)

    def get_match(self):
        return self.current_match
