from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.refactor import multiproject, rename, move
from ropetest import testutils


class MultiProjectRefactoringTest(unittest.TestCase):
    def setUp(self):
        super(MultiProjectRefactoringTest, self).setUp()
        self.project1 = testutils.sample_project(foldername="testproject1")
        self.project2 = testutils.sample_project(foldername="testproject2")
        self.mod1 = self.project1.root.create_file("mod1.py")
        self.other = self.project1.root.create_file("other.py")
        self.mod2 = self.project2.root.create_file("mod2.py")

    def tearDown(self):
        testutils.remove_project(self.project1)
        testutils.remove_project(self.project2)
        super(MultiProjectRefactoringTest, self).tearDown()

    def test_trivial_rename(self):
        self.mod1.write("var = 1\n")
        refactoring = multiproject.MultiProjectRefactoring(rename.Rename, [])
        renamer = refactoring(self.project1, self.mod1, 1)
        multiproject.perform(renamer.get_all_changes("newvar"))
        self.assertEqual("newvar = 1\n", self.mod1.read())

    def test_rename(self):
        self.mod1.write("var = 1\n")
        self.mod2.write(
            dedent("""\
                import mod1
                myvar = mod1.var
            """)
        )
        refactoring = multiproject.MultiProjectRefactoring(
            rename.Rename, [self.project2]
        )
        renamer = refactoring(self.project1, self.mod1, 1)
        multiproject.perform(renamer.get_all_changes("newvar"))
        self.assertEqual("newvar = 1\n", self.mod1.read())
        self.assertEqual(
            dedent("""\
                import mod1
                myvar = mod1.newvar
            """),
            self.mod2.read(),
        )

    def test_move(self):
        self.mod1.write(
            dedent("""\
                def a_func():
                    pass
            """)
        )
        self.mod2.write(
            dedent("""\
                import mod1
                myvar = mod1.a_func()
            """)
        )
        refactoring = multiproject.MultiProjectRefactoring(
            move.create_move, [self.project2]
        )
        renamer = refactoring(self.project1, self.mod1, self.mod1.read().index("_func"))
        multiproject.perform(renamer.get_all_changes(self.other))
        self.assertEqual("", self.mod1.read())
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
            """),
            self.other.read(),
        )
        self.assertEqual(
            dedent("""\
                import other
                myvar = other.a_func()
            """),
            self.mod2.read(),
        )

    def test_rename_from_the_project_not_containing_the_change(self):
        self.project2.get_prefs().add("python_path", self.project1.address)
        self.mod1.write("var = 1\n")
        self.mod2.write(
            dedent("""\
                import mod1
                myvar = mod1.var
            """)
        )
        refactoring = multiproject.MultiProjectRefactoring(
            rename.Rename, [self.project1]
        )
        renamer = refactoring(self.project2, self.mod2, self.mod2.read().rindex("var"))
        multiproject.perform(renamer.get_all_changes("newvar"))
        self.assertEqual(
            dedent("""\
                newvar = 1
            """),
            self.mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                myvar = mod1.newvar
            """),
            self.mod2.read(),
        )
