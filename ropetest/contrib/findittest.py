import unittest
from textwrap import dedent

from rope.base import exceptions
from rope.contrib.findit import find_definition, find_implementations, find_occurrences
from rope.refactor.rename import Rename
from ropetest import testutils


class FindItTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_finding_occurrences(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write("a_var = 1\n")
        result = find_occurrences(self.project, mod, 1)
        self.assertEqual(mod, result[0].resource)
        self.assertEqual(0, result[0].offset)
        self.assertEqual(False, result[0].unsure)

    def test_finding_occurrences_in_more_than_one_module(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("a_var = 1\n")
        mod2.write(dedent("""\
            import mod1
            my_var = mod1.a_var"""))
        result = find_occurrences(self.project, mod1, 1)
        self.assertEqual(2, len(result))
        modules = (result[0].resource, result[1].resource)
        self.assertTrue(mod1 in modules and mod2 in modules)

    def test_finding_occurrences_matching_when_unsure(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class C(object):
                def a_func(self):
                    pass
            def f(arg):
                arg.a_func()
        """))
        result = find_occurrences(
            self.project, mod1, mod1.read().index("a_func"), unsure=True
        )
        self.assertEqual(2, len(result))

    def test_find_occurrences_resources_parameter(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("a_var = 1\n")
        mod2.write(dedent("""\
            import mod1
            my_var = mod1.a_var"""))
        result = find_occurrences(self.project, mod1, 1, resources=[mod1])
        self.assertEqual(1, len(result))
        self.assertEqual((mod1, 0), (result[0].resource, result[0].offset))

    def test_find_occurrences_and_class_hierarchies(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class A(object):
                def f():
                    pass
            class B(A):
                def f():
                    pass
        """))
        offset = mod1.read().rindex("f")
        result1 = find_occurrences(self.project, mod1, offset)
        result2 = find_occurrences(self.project, mod1, offset, in_hierarchy=True)
        self.assertEqual(1, len(result1))
        self.assertEqual(2, len(result2))

    def test_trivial_find_implementations(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class A(object):
                def f(self):
                    pass
        """))
        offset = mod1.read().rindex("f(")
        result = find_implementations(self.project, mod1, offset)
        self.assertEqual([], result)

    def test_find_implementations_and_not_returning_parents(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class A(object):
                def f(self):
                    pass
            class B(A):
                def f(self):
                    pass
        """))
        offset = mod1.read().rindex("f(")
        result = find_implementations(self.project, mod1, offset)
        self.assertEqual([], result)

    def test_find_implementations_real_implementation(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class A(object):
                def f(self):
                    pass
            class B(A):
                def f(self):
                    pass
        """))
        offset = mod1.read().index("f(")
        result = find_implementations(self.project, mod1, offset)
        self.assertEqual(1, len(result))
        self.assertEqual(mod1.read().rindex("f("), result[0].offset)

    def test_find_implementations_real_implementation_simple(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("class A(object):\n    pass\n")
        offset = mod1.read().index("A")
        with self.assertRaises(exceptions.BadIdentifierError):
            find_implementations(self.project, mod1, offset)

    def test_trivial_find_definition(self):
        code = dedent("""\
            def a_func():
                pass
            a_func()""")
        result = find_definition(self.project, code, code.rindex("a_func"))
        start = code.index("a_func")
        self.assertEqual(start, result.offset)
        self.assertEqual(None, result.resource)
        self.assertEqual(1, result.lineno)
        self.assertEqual((start, start + len("a_func")), result.region)

    def test_find_definition_in_other_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("var = 1\n")
        code = dedent("""\
            import mod1
            print(mod1.var)
        """)
        result = find_definition(self.project, code, code.index("var"))
        self.assertEqual(mod1, result.resource)
        self.assertEqual(0, result.offset)

    # worder's is_a_class_or_function_name_in_header only recognised the
    # canonical `def`/`class` prefixes, so an `async def` method header was
    # not treated as a definition and find_definition resolved a call via
    # self to the call site itself (never the def).

    def test_find_definition_of_async_method(self):
        code = dedent("""\
            class C(object):
                async def target(self):
                    pass

                async def run(self):
                    await self.target()
        """)
        call_offset = code.rindex("target")
        result = find_definition(self.project, code, call_offset)
        def_offset = code.index("target")
        self.assertIsNotNone(result)
        self.assertEqual(def_offset, result.offset)

    def test_find_definition_of_async_method_extra_whitespace(self):
        # `async  def` (two spaces) / `async\tdef` are valid Python and must
        # be recognised too, not just canonical single-space `async def`.
        code = dedent("""\
            class C(object):
                async  def target(self):
                    pass

                async  def run(self):
                    await self.target()
        """)
        call_offset = code.rindex("target")
        result = find_definition(self.project, code, call_offset)
        def_offset = code.index("target")
        self.assertIsNotNone(result)
        self.assertEqual(def_offset, result.offset)

    def test_find_definition_of_async_method_tab_separated(self):
        # `async\tdef` (tab-separated) is valid Python; the normalised
        # predicate must recognise it too.
        code = dedent("""\
            class C(object):
                async def target(self):
                    pass

                async def run(self):
                    await self.target()
        """).replace("async def", "async\tdef")
        call_offset = code.rindex("target")
        result = find_definition(self.project, code, call_offset)
        def_offset = code.index("target")
        self.assertIsNotNone(result)
        self.assertEqual(def_offset, result.offset)

    def test_rename_heals_async_method(self):
        # Rename from the call must reach the async def, not orphan it --
        # the damaging end-to-end symptom of the unrecognised header.
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                async def target(self):
                    pass

                async def run(self):
                    await self.target()
        """)
        mod.write(code)
        call_offset = code.rindex("target")
        changes = Rename(self.project, mod, call_offset).get_changes("renamed")
        self.project.do(changes)
        result = mod.read()
        # both the call and the def must be renamed -- not silently orphaned
        self.assertEqual(0, result.count("target"))
        self.assertEqual(2, result.count("renamed"))

    def test_find_definition_of_sync_method_still_resolves(self):
        # regression control: sync methods must keep resolving
        code = dedent("""\
            class C(object):
                def target(self):
                    pass

                def run(self):
                    self.target()
        """)
        call_offset = code.rindex("target")
        result = find_definition(self.project, code, call_offset)
        def_offset = code.index("target")
        self.assertIsNotNone(result)
        self.assertEqual(def_offset, result.offset)

    def test_find_definition_of_module_level_async_function(self):
        # control: module-level async defs already resolve correctly
        code = dedent("""\
            async def target():
                pass

            async def run():
                await target()
        """)
        call_offset = code.rindex("target")
        result = find_definition(self.project, code, call_offset)
        def_offset = code.index("target")
        self.assertIsNotNone(result)
        self.assertEqual(def_offset, result.offset)
