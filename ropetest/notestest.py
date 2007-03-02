import unittest

from rope.base.project import Project
from rope.ide import notes
from ropetest import testutils


class CodetagsTest(unittest.TestCase):

    def setUp(self):
        super(CodetagsTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(CodetagsTest, self).tearDown()

    def test_empty_input(self):
        tags = notes.Codetags()
        self.assertEquals([], tags.tags(''))

    def test_trivial_case(self):
        tags = notes.Codetags()
        self.assertEquals([(1, 'TODO: todo')], tags.tags('# TODO: todo\n'))

    def test_two_codetags(self):
        tags = notes.Codetags()
        self.assertEquals(
            [(1, 'XXX: todo'), (3, 'FIXME: fix me')],
             tags.tags('# XXX: todo\n\n# FIXME: fix me\n'))


if __name__ == '__main__':
    unittest.main()
