import unittest

from rope.refactor import patchedast


class PatchedASTTest(unittest.TestCase):

    def setUp(self):
        super(PatchedASTTest, self).setUp()

    def tearDown(self):
        super(PatchedASTTest, self).tearDown()

    def test_integer_literals_and_region(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('10')
        checker.check_region('Const(10)', start, start + 2)

    def test_integer_literals_and_sorted_children(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('10')
        checker.check_children('Const(10)', ['10'])

    def test_ass_name_node(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('a')
        checker.check_region('AssName', start, start + 1)
        checker.check_children('AssName', ['a'])

    def test_assign_node(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('a')
        checker.check_region('Assign', 0, len(source) - 1)
        checker.check_children(
            'Assign', ['', 'AssName', ' ', '=', ' ', 'Const'])


class _ResultChecker(object):

    def __init__(self, test_case, ast):
        self.test_case = test_case
        self.ast = ast

    def check_region(self, text, start, end):
        node = self._find_node(text)
        self.test_case.assertEquals((start, end), node.region)

    def _find_node(self, text):
        class Search(object):
            result = None
            def __call__(self, node):
                if repr(node).startswith(text):
                    self.result = node
                return self.result is not None
        search = Search()
        patchedast.call_for_nodes(self.ast, search, recursive=True)
        return search.result

    def check_children(self, text, children):
        node = self._find_node(text)
        result = list(node.sorted_children)
        self.test_case.assertEquals(len(children), len(result))
        for expected, child in zip(children, result):
            if isinstance(child, basestring):
                self.test_case.assertEquals(expected, child)
            else:
                self.test_case.assertTrue(repr(child).startswith(expected))


if __name__ == '__main__':
    unittest.main()
