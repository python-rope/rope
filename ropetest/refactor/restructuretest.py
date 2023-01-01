import unittest
from textwrap import dedent

from rope.refactor import restructure
from ropetest import testutils


class RestructureTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_trivial_case(self):
        refactoring = restructure.Restructure(self.project, "a = 1", "a = 0")
        self.mod.write("b = 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("b = 1\n", self.mod.read())

    def test_replacing_simple_patterns(self):
        refactoring = restructure.Restructure(self.project, "a = 1", "a = int(1)")
        self.mod.write("a = 1\nb = 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = int(1)\nb = 1\n", self.mod.read())

    def test_replacing_patterns_with_normal_names(self):
        refactoring = restructure.Restructure(
            self.project, "${a} = 1", "${a} = int(1)", args={"a": "exact"}
        )
        self.mod.write("a = 1\nb = 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = int(1)\nb = 1\n", self.mod.read())

    def test_replacing_patterns_with_any_names(self):
        refactoring = restructure.Restructure(self.project, "${a} = 1", "${a} = int(1)")
        self.mod.write("a = 1\nb = 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = int(1)\nb = int(1)\n", self.mod.read())

    def test_replacing_patterns_with_any_names2(self):
        refactoring = restructure.Restructure(self.project, "${x} + ${x}", "${x} * 2")
        self.mod.write("a = 1 + 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = 1 * 2\n", self.mod.read())

    def test_replacing_patterns_with_checks(self):
        self.mod.write(dedent("""\
            def f(p=1):
                return p
            g = f
            g()
        """))
        refactoring = restructure.Restructure(
            self.project, "${f}()", "${f}(2)", args={"f": "object=mod.f"}
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p=1):
                    return p
                g = f
                g(2)
            """),
            self.mod.read(),
        )

    def test_replacing_assignments_with_sets(self):
        refactoring = restructure.Restructure(
            self.project, "${a} = ${b}", "${a}.set(${b})"
        )
        self.mod.write("a = 1\nb = 1\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a.set(1)\nb.set(1)\n", self.mod.read())

    def test_replacing_sets_with_assignments(self):
        refactoring = restructure.Restructure(
            self.project, "${a}.set(${b})", "${a} = ${b}"
        )
        self.mod.write("a.set(1)\nb.set(1)\n")
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                a = 1
                b = 1
            """),
            self.mod.read(),
        )

    def test_using_make_checks(self):
        self.mod.write(dedent("""\
            def f(p=1):
                return p
            g = f
            g()
        """))
        refactoring = restructure.Restructure(
            self.project, "${f}()", "${f}(2)", args={"f": "object=mod.f"}
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p=1):
                    return p
                g = f
                g(2)
            """),
            self.mod.read(),
        )

    def test_using_make_checking_builtin_types(self):
        self.mod.write("a = 1 + 1\n")
        refactoring = restructure.Restructure(
            self.project, "${i} + ${i}", "${i} * 2", args={"i": "type=__builtin__.int"}
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = 1 * 2\n", self.mod.read())

    def test_auto_indentation_when_no_indentation(self):
        self.mod.write("a = 2\n")
        refactoring = restructure.Restructure(
            self.project, "${a} = 2", "${a} = 1\n${a} += 1"
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                a = 1
                a += 1
            """),
            self.mod.read(),
        )

    def test_auto_indentation(self):
        self.mod.write(dedent("""\
            def f():
                a = 2
        """))
        refactoring = restructure.Restructure(
            self.project, "${a} = 2", "${a} = 1\n${a} += 1"
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                def f():
                    a = 1
                    a += 1
            """),
            self.mod.read(),
        )

    def test_auto_indentation_and_not_indenting_blanks(self):
        self.mod.write("def f():\n    a = 2\n")
        refactoring = restructure.Restructure(
            self.project, "${a} = 2", "${a} = 1\n\n${a} += 1"
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual("def f():\n    a = 1\n\n    a += 1\n", self.mod.read())

    def test_importing_names(self):
        self.mod.write("a = 2\n")
        refactoring = restructure.Restructure(
            self.project, "${a} = 2", "${a} = myconsts.two", imports=["import myconsts"]
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                import myconsts
                a = myconsts.two
            """),
            self.mod.read(),
        )

    def test_not_importing_names_when_there_are_no_changes(self):
        self.mod.write("a = True\n")
        refactoring = restructure.Restructure(
            self.project, "${a} = 2", "${a} = myconsts.two", imports=["import myconsts"]
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = True\n", self.mod.read())

    def test_handling_containing_matches(self):
        self.mod.write("a = 1 / 2 / 3\n")
        refactoring = restructure.Restructure(
            self.project, "${a} / ${b}", "${a} // ${b}"
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = 1 // 2 // 3\n", self.mod.read())

    def test_handling_overlapping_matches(self):
        self.mod.write("a = 1\na = 1\na = 1\n")
        refactoring = restructure.Restructure(self.project, "a = 1\na = 1\n", "b = 1")
        self.project.do(refactoring.get_changes())
        self.assertEqual("b = 1\na = 1\n", self.mod.read())

    def test_preventing_stack_overflow_when_matching(self):
        self.mod.write("1\n")
        refactoring = restructure.Restructure(self.project, "${a}", "${a}")
        self.project.do(refactoring.get_changes())
        self.assertEqual("1\n", self.mod.read())

    def test_performing_a_restructuring_to_all_modules(self):
        mod2 = testutils.create_module(self.project, "mod2")
        self.mod.write("a = 1\n")
        mod2.write("b = 1\n")
        refactoring = restructure.Restructure(self.project, "1", "2 / 1")
        self.project.do(refactoring.get_changes())
        self.assertEqual("a = 2 / 1\n", self.mod.read())
        self.assertEqual("b = 2 / 1\n", mod2.read())

    def test_performing_a_restructuring_to_selected_modules(self):
        mod2 = testutils.create_module(self.project, "mod2")
        self.mod.write("a = 1\n")
        mod2.write("b = 1\n")
        refactoring = restructure.Restructure(self.project, "1", "2 / 1")
        self.project.do(refactoring.get_changes(resources=[mod2]))
        self.assertEqual("a = 1\n", self.mod.read())
        self.assertEqual("b = 2 / 1\n", mod2.read())

    def test_unsure_argument_of_default_wildcard(self):
        self.mod.write(dedent("""\
            def f(p):
                return p * 2
            x = "" * 2
            i = 1 * 2
        """))
        refactoring = restructure.Restructure(
            self.project,
            "${s} * 2",
            "dup(${s})",
            args={"s": {"type": "__builtins__.str", "unsure": True}},
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    return dup(p)
                x = dup("")
                i = 1 * 2
            """),
            self.mod.read(),
        )

    def test_statement_after_string_and_column(self):
        mod_text = dedent("""\
            def f(x):
              if a == "a": raise Exception("test")
        """)
        self.mod.write(mod_text)
        refactoring = restructure.Restructure(self.project, "${a}", "${a}")
        self.project.do(refactoring.get_changes())
        self.assertEqual(mod_text, self.mod.read())

    @testutils.only_for_versions_higher("3.3")
    def test_yield_from(self):
        mod_text = dedent("""\
            def f(lst):
                yield from lst
        """)
        self.mod.write(mod_text)
        refactoring = restructure.Restructure(
            self.project,
            "yield from ${a}",
            dedent("""\
                for it in ${a}:
                   yield it"""),
        )
        self.project.do(refactoring.get_changes())
        self.assertEqual(
            dedent("""\
            def f(lst):
                for it in lst:
                   yield it
            """),
            self.mod.read(),
        )
