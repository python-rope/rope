from textwrap import dedent

try:
    import unittest2 as unittest
except ImportError:
    import unittest


from rope.contrib import finderrors
from ropetest import testutils


class FindErrorsTest(unittest.TestCase):
    def setUp(self):
        super(FindErrorsTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod = self.project.root.create_file("mod.py")

    def tearDown(self):
        testutils.remove_project(self.project)
        super(FindErrorsTest, self).tearDown()

    def test_unresolved_variables(self):
        self.mod.write("print(var)\n")
        result = finderrors.find_errors(self.project, self.mod)
        self.assertEqual(1, len(result))
        self.assertEqual(1, result[0].lineno)

    def test_defined_later(self):
        self.mod.write(
            dedent("""\
                print(var)
                var = 1
            """)
        )
        result = finderrors.find_errors(self.project, self.mod)
        self.assertEqual(1, len(result))
        self.assertEqual(1, result[0].lineno)

    def test_ignoring_builtins(self):
        self.mod.write("range(2)\n")
        result = finderrors.find_errors(self.project, self.mod)
        self.assertEqual(0, len(result))

    def test_ignoring_none(self):
        self.mod.write("var = None\n")
        result = finderrors.find_errors(self.project, self.mod)
        self.assertEqual(0, len(result))

    def test_bad_attributes(self):
        code = dedent("""\
            class C(object):
                pass
            c = C()
            print(c.var)
        """)
        self.mod.write(code)
        result = finderrors.find_errors(self.project, self.mod)
        self.assertEqual(1, len(result))
        self.assertEqual(4, result[0].lineno)
