try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.refactor.importutils import ImportTools, importinfo, add_import
from ropetest import testutils


class ImportUtilsTest(unittest.TestCase):

    def setUp(self):
        super(ImportUtilsTest, self).setUp()
        self.project = testutils.sample_project()
        self.import_tools = ImportTools(self.project)

        self.mod = testutils.create_module(self.project, 'mod')
        self.pkg1 = testutils.create_package(self.project, 'pkg1')
        self.mod1 = testutils.create_module(self.project, 'mod1', self.pkg1)
        self.pkg2 = testutils.create_package(self.project, 'pkg2')
        self.mod2 = testutils.create_module(self.project, 'mod2', self.pkg2)
        self.mod3 = testutils.create_module(self.project, 'mod3', self.pkg2)
        p1 = testutils.create_package(self.project, 'p1')
        p2 = testutils.create_package(self.project, 'p2', p1)
        p3 = testutils.create_package(self.project, 'p3', p2)
        m1 = testutils.create_module(self.project, 'm1', p3)  # noqa
        l = testutils.create_module(self.project, 'l', p3)  # noqa

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ImportUtilsTest, self).tearDown()

    def test_get_import_for_module(self):
        mod = self.project.find_module('mod')
        import_statement = self.import_tools.get_import(mod)
        self.assertEquals('import mod',
                          import_statement.get_import_statement())

    def test_get_import_for_module_in_nested_modules(self):
        mod = self.project.find_module('pkg1.mod1')
        import_statement = self.import_tools.get_import(mod)
        self.assertEquals('import pkg1.mod1',
                          import_statement.get_import_statement())

    def test_get_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child('__init__.py')
        import_statement = self.import_tools.get_import(init_dot_py)
        self.assertEquals('import pkg1',
                          import_statement.get_import_statement())

    def test_get_from_import_for_module(self):
        mod = self.project.find_module('mod')
        import_statement = self.import_tools.get_from_import(mod, 'a_func')
        self.assertEquals('from mod import a_func',
                          import_statement.get_import_statement())

    def test_get_from_import_for_module_in_nested_modules(self):
        mod = self.project.find_module('pkg1.mod1')
        import_statement = self.import_tools.get_from_import(mod, 'a_func')
        self.assertEquals('from pkg1.mod1 import a_func',
                          import_statement.get_import_statement())

    def test_get_from_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child('__init__.py')
        import_statement = self.import_tools.\
            get_from_import(init_dot_py, 'a_func')
        self.assertEquals('from pkg1 import a_func',
                          import_statement.get_import_statement())

    def test_get_import_statements(self):
        self.mod.write('import pkg1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('import pkg1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_with_alias(self):
        self.mod.write('import pkg1.mod1 as mod1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('import pkg1.mod1 as mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_for_froms(self):
        self.mod.write('from pkg1 import mod1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('from pkg1 import mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_multi_line_import_statements_for_froms(self):
        self.mod.write('from pkg1 \\\n    import mod1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('from pkg1 import mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_for_from_star(self):
        self.mod.write('from pkg1 import *\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('from pkg1 import *',
                          imports[0].import_info.get_import_statement())

    @testutils.only_for('2.5')
    def test_get_import_statements_for_new_relatives(self):
        self.mod2.write('from .mod3 import x\n')
        pymod = self.project.get_module('pkg2.mod2')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals('from .mod3 import x',
                          imports[0].import_info.get_import_statement())

    def test_ignoring_indented_imports(self):
        self.mod.write('if True:\n    import pkg1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEquals(0, len(imports))

    def test_import_get_names(self):
        self.mod.write('import pkg1 as pkg\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEquals(['pkg'],
                          imports[0].import_info.get_imported_names(context))

    def test_import_get_names_with_alias(self):
        self.mod.write('import pkg1.mod1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEquals(['pkg1'],
                          imports[0].import_info.get_imported_names(context))

    def test_import_get_names_with_alias2(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEquals(['a_func'],
                          imports[0].import_info.get_imported_names(context))

    def test_empty_getting_used_imports(self):
        self.mod.write('')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(0, len(imports))

    def test_empty_getting_used_imports2(self):
        self.mod.write('import pkg\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(0, len(imports))

    def test_simple_getting_used_imports(self):
        self.mod.write('import pkg\nprint(pkg)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(1, len(imports))
        self.assertEquals('import pkg', imports[0].get_import_statement())

    def test_simple_getting_used_imports2(self):
        self.mod.write('import pkg\ndef a_func():\n    print(pkg)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(1, len(imports))
        self.assertEquals('import pkg', imports[0].get_import_statement())

    def test_getting_used_imports_for_nested_scopes(self):
        self.mod.write('import pkg1\nprint(pkg1)\n'
                       'def a_func():\n    pass\nprint(pkg1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(
            pymod['a_func'].get_object())
        self.assertEquals(0, len(imports))

    def test_getting_used_imports_for_nested_scopes2(self):
        self.mod.write('from pkg1 import mod1\ndef a_func():'
                       '\n    print(mod1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(
            pymod['a_func'].get_object())
        self.assertEquals(1, len(imports))
        self.assertEquals('from pkg1 import mod1',
                          imports[0].get_import_statement())

    def test_empty_removing_unused_imports(self):
        self.mod.write('import pkg1\nprint(pkg1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1\nprint(pkg1)\n',
                          module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports(self):
        self.mod.write('import pkg1\n\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_froms(self):
        self.mod1.write('def a_func():\n    pass'
                        '\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func, '
                       'another_func\n\na_func()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import a_func\n\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_from_stars(self):
        self.mod.write('from pkg1.mod1 import *\n\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_nested_modules(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('import pkg1.mod1\npkg1.mod1.a_func()')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_functions_of_the_same_name(self):
        self.mod.write('def a_func():\n    pass\ndef a_func():\n    pass\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('def a_func():\n    pass\ndef a_func():\n    pass\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_for_from_import_with_as(self):
        self.mod.write('a_var = 1\n')
        self.mod1.write('from mod import a_var as myvar\na_var = myvar\n')
        pymod = self.project.get_pymodule(self.mod1)
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from mod import a_var as myvar\na_var = myvar\n',
                          module_with_imports.get_changed_source())

    def test_not_removing_imports_that_conflict_with_class_names(self):
        code = 'import pkg1\nclass A(object):\n    pkg1 = 0\n' \
               '    def f(self):\n        a_var = pkg1\n'
        self.mod.write(code)
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals(code, module_with_imports.get_changed_source())

    def test_adding_imports(self):
        self.mod.write('\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.mod1)
        module_with_imports.add_import(new_import)
        self.assertEquals('import pkg1.mod1\n',
                          module_with_imports.get_changed_source())

    def test_adding_imports_no_pull_to_top(self):
        self.mod.write('import pkg2.mod3\nclass A(object):\n    pass\n\n'
                       'import pkg2.mod2\n')
        pymod = self.project.get_module('mod')
        self.project.prefs['pull_imports_to_top'] = False
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.mod1)
        module_with_imports.add_import(new_import)
        self.assertEquals('import pkg2.mod3\nclass A(object):\n    pass\n\n'
                          'import pkg2.mod2\nimport pkg1.mod1\n',
                          module_with_imports.get_changed_source())

    def test_adding_from_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(
            self.mod1, 'another_func')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import a_func, another_func\n',
                          module_with_imports.get_changed_source())

    def test_adding_to_star_imports(self):
        self.mod1.write('def a_func():\n    pass'
                        '\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(
            self.mod1, 'another_func')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import *\n',
                          module_with_imports.get_changed_source())

    def test_adding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(self.mod1, '*')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import *\n',
                          module_with_imports.get_changed_source())

    def test_adding_imports_and_preserving_spaces_after_imports(self):
        self.mod.write('import pkg1\n\n\nprint(pkg1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.pkg2)
        module_with_imports.add_import(new_import)
        self.assertEquals('import pkg1\nimport pkg2\n\n\nprint(pkg1)\n',
                          module_with_imports.get_changed_source())

    def test_not_changing_the_format_of_unchanged_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func,\n    another_func)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        self.assertEquals(
            'from pkg1.mod1 import (a_func,\n    another_func)\n',
            module_with_imports.get_changed_source())

    def test_not_changing_the_format_of_unchanged_imports2(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func)\na_func()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import (a_func)\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_reoccuring_names(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n'
                       'from pkg1.mod1 import a_func\na_func()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import *\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_reoccuring_names2(self):
        self.mod.write('import pkg2.mod2\nimport pkg2.mod3\n'
                       'print(pkg2.mod2, pkg2.mod3)')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals(
            'import pkg2.mod2\nimport pkg2.mod3\nprint(pkg2.mod2, pkg2.mod3)',
            module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages(self):
        self.mod.write('import pkg1.mod1\nimport pkg1'
                       '\nprint(pkg1, pkg1.mod1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\nprint(pkg1, pkg1.mod1)\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages_reversed(self):
        self.mod.write('import pkg1\nimport pkg1.mod1'
                       '\nprint(pkg1, pkg1.mod1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg1.mod1\nprint(pkg1, pkg1.mod1)\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages2(self):
        self.mod.write('import pkg1.mod1\nimport pkg1.mod2\nprint(pkg1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\nprint(pkg1)\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms2(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\nfunc1()')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import func1\nfunc1()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms3(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\n'
                       'def a_func():\n    func1()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals(
            'from pkg1.mod1 import func1\ndef a_func():\n    func1()\n',
            module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms4(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\nclass A(object):\n'
                       '    def a_func(self):\n        func1()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import func1\nclass A(object):\n'
                          '    def a_func(self):\n        func1()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_getting_attributes(self):
        self.mod1.write('class A(object):\n    def f(self):\n        pass\n')
        self.mod.write('from pkg1.mod1 import A\nvar = A().f()')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import A\nvar = A().f()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_function_parameters(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('import pkg1\ndef a_func(pkg1):\n    my_var = pkg1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('def a_func(pkg1):\n    my_var = pkg1\n',
                          module_with_imports.get_changed_source())

    def test_trivial_expanding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_expanding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEquals('from pkg1.mod1 import a_func\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicate_imports(self):
        self.mod.write('import pkg1\nimport pkg1\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg1\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicates_and_reoccuring_names(self):
        self.mod.write('import pkg2.mod2\nimport pkg2.mod3\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg2.mod2\nimport pkg2.mod3\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicate_imports_for_froms(self):
        self.mod1.write(
            'def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1 import a_func\n'
                       'from pkg1 import a_func, another_func\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('from pkg1 import a_func, another_func\n',
                          module_with_imports.get_changed_source())

    def test_transforming_froms_to_normal_changing_imports(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\nprint(a_func)\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg1.mod1\nprint(pkg1.mod1.a_func)\n',
                          changed_module)

    def test_transforming_froms_to_normal_changing_occurances(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\na_func()')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()',
                          changed_module)

    def test_transforming_froms_to_normal_for_multi_imports(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\nanother_func()\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals(
            'import pkg1.mod1\npkg1.mod1.a_func()\npkg1.mod1.another_func()\n',
            changed_module)

    def test_transform_froms_to_norm_for_multi_imports_inside_parens(self):
        self.mod1.write('def a_func():\n    pass\n'
                        'def another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func, \n    another_func)'
                       '\na_func()\nanother_func()\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals(
            'import pkg1.mod1\npkg1.mod1.a_func()\npkg1.mod1.another_func()\n',
            changed_module)

    def test_transforming_froms_to_normal_from_stars(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\n',
                          changed_module)

    def test_transforming_froms_to_normal_from_stars2(self):
        self.mod1.write('a_var = 10')
        self.mod.write('import pkg1.mod1\nfrom pkg1.mod1 import a_var\n'
                       'def a_func():\n    print(pkg1.mod1, a_var)\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg1.mod1\n'
                          'def a_func():\n    '
                          'print(pkg1.mod1, pkg1.mod1.a_var)\n',
                          changed_module)

    def test_transforming_froms_to_normal_from_with_alias(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write(
            'from pkg1.mod1 import a_func as another_func\nanother_func()\n')
        pymod = self.project.get_module('mod')
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\n',
                          changed_module)

    def test_transforming_froms_to_normal_for_relatives(self):
        self.mod2.write('def a_func():\n    pass\n')
        self.mod3.write('from mod2 import *\na_func()\n')
        pymod = self.project.get_pymodule(self.mod3)
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import pkg2.mod2\npkg2.mod2.a_func()\n',
                          changed_module)

    def test_transforming_froms_to_normal_for_os_path(self):
        self.mod.write('from os import path\npath.exists(\'.\')\n')
        pymod = self.project.get_pymodule(self.mod)
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEquals('import os\nos.path.exists(\'.\')\n', changed_module)

    def test_transform_relatives_imports_to_abs_imports_doing_nothing(self):
        self.mod2.write('from pkg1 import mod1\nimport mod1\n')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('from pkg1 import mod1\nimport mod1\n',
                          self.import_tools.relatives_to_absolutes(pymod))

    def test_transform_relatives_to_absolute_imports_for_normal_imports(self):
        self.mod2.write('import mod3\n')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('import pkg2.mod3\n',
                          self.import_tools.relatives_to_absolutes(pymod))

    def test_transform_relatives_imports_to_absolute_imports_for_froms(self):
        self.mod3.write('def a_func():\n    pass\n')
        self.mod2.write('from mod3 import a_func\n')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('from pkg2.mod3 import a_func\n',
                          self.import_tools.relatives_to_absolutes(pymod))

    @testutils.only_for('2.5')
    def test_transform_rel_imports_to_abs_imports_for_new_relatives(self):
        self.mod3.write('def a_func():\n    pass\n')
        self.mod2.write('from .mod3 import a_func\n')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('from pkg2.mod3 import a_func\n',
                          self.import_tools.relatives_to_absolutes(pymod))

    def test_transform_relatives_to_absolute_imports_for_normal_imports2(self):
        self.mod2.write('import mod3\nprint(mod3)')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('import pkg2.mod3\nprint(pkg2.mod3)',
                          self.import_tools.relatives_to_absolutes(pymod))

    def test_transform_relatives_to_absolute_imports_for_aliases(self):
        self.mod2.write('import mod3 as mod3\nprint(mod3)')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals('import pkg2.mod3 as mod3\nprint(mod3)',
                          self.import_tools.relatives_to_absolutes(pymod))

    def test_organizing_imports(self):
        self.mod1.write('import mod1\n')
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEquals('', self.import_tools.organize_imports(pymod))

    def test_organizing_imports_without_deduplication(self):
        contents = 'from pkg2 import mod2\nfrom pkg2 import mod3\n'
        self.mod.write(contents)
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True
        self.assertEquals(contents,
                          self.import_tools.organize_imports(pymod,
                                                             unused=False))

    def test_splitting_imports(self):
        self.mod.write('from pkg1 import mod1\nfrom pkg2 import mod2, mod3\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True
        self.assertEquals('from pkg1 import mod1\nfrom pkg2 import mod2\n'
                          'from pkg2 import mod3\n',
                          self.import_tools.organize_imports(pymod,
                                                             unused=False))

    def test_splitting_imports_no_pull_to_top(self):
        self.mod.write('from pkg2 import mod3, mod4\n'
                       'from pkg1 import mod2\nfrom pkg1 import mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True
        self.project.prefs['pull_imports_to_top'] = False
        self.assertEquals('from pkg1 import mod2\nfrom pkg1 import mod1\n'
                          'from pkg2 import mod3\nfrom pkg2 import mod4\n',
                          self.import_tools.organize_imports(pymod,
                                                             sort=False,
                                                             unused=False))

    def test_splitting_imports_with_filter(self):
        self.mod.write('from pkg1 import mod1, mod2\n'
                       'from pkg2 import mod3, mod4\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True

        def import_filter(stmt):
          return stmt.import_info.module_name == 'pkg1'

        self.assertEquals(
            'from pkg1 import mod1\nfrom pkg1 import mod2\n'
            'from pkg2 import mod3, mod4\n',
            self.import_tools.organize_imports(pymod, unused=False,
                                               import_filter=import_filter))

    def test_splitting_duplicate_imports(self):
        self.mod.write('from pkg2 import mod1\nfrom pkg2 import mod1, mod2\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True
        self.assertEquals('from pkg2 import mod1\nfrom pkg2 import mod2\n',
                          self.import_tools.organize_imports(pymod,
                                                             unused=False))

    def test_splitting_duplicate_imports2(self):
        self.mod.write('from pkg2 import mod1, mod3\n'
                       'from pkg2 import mod1, mod2\n'
                       'from pkg2 import mod2, mod3\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['split_imports'] = True
        self.assertEquals('from pkg2 import mod1\nfrom pkg2 import mod2\n'
                          'from pkg2 import mod3\n',
                          self.import_tools.organize_imports(pymod,
                                                             unused=False))

    def test_removing_self_imports(self):
        self.mod.write('import mod\nmod.a_var = 1\nprint(mod.a_var)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports2(self):
        self.mod1.write('import pkg1.mod1\npkg1.mod1.a_var = 1\n'
                        'print(pkg1.mod1.a_var)\n')
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_as(self):
        self.mod.write('import mod as mymod\n'
                       'mymod.a_var = 1\nprint(mymod.a_var)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms(self):
        self.mod1.write('from pkg1 import mod1\n'
                        'mod1.a_var = 1\nprint(mod1.a_var)\n')
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms_with_as(self):
        self.mod1.write('from pkg1 import mod1 as mymod\n'
                        'mymod.a_var = 1\nprint(mymod.a_var)\n')
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms2(self):
        self.mod.write('from mod import a_var\na_var = 1\nprint(a_var)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms3(self):
        self.mod.write('from mod import a_var\na_var = 1\nprint(a_var)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms4(self):
        self.mod.write('from mod import a_var as myvar\n'
                       'a_var = 1\nprint(myvar)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(a_var)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_no_dot_after_mod(self):
        self.mod.write('import mod\nprint(mod)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import mod\n\n\nprint(mod)\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_no_dot_after_mod2(self):
        self.mod.write('import mod\na_var = 1\n'
                       'print(mod\\\n     \\\n     .var)\n\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(var)\n\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_from_import_star(self):
        self.mod.write('from mod import *\na_var = 1\nprint(myvar)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('a_var = 1\nprint(myvar)\n',
                          self.import_tools.organize_imports(pymod))

    def test_not_removing_future_imports(self):
        self.mod.write('from __future__ import division\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('from __future__ import division\n',
                          self.import_tools.organize_imports(pymod))

    def test_sorting_empty_imports(self):
        self.mod.write('')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('', self.import_tools.sort_imports(pymod))

    def test_sorting_one_import(self):
        self.mod.write('import pkg1.mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import pkg1.mod1\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_alphabetically(self):
        self.mod.write('import pkg2.mod2\nimport pkg1.mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import pkg1.mod1\nimport pkg2.mod2\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_purely_alphabetically(self):
        self.mod.write('from pkg2 import mod3 as mod0\n'
                       'import pkg2.mod2\nimport pkg1.mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs['sort_imports_alphabetically'] = True
        self.assertEquals('import pkg1.mod1\nimport pkg2.mod2\n'
                          'from pkg2 import mod3 as mod0\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_and_froms(self):
        self.mod.write('import pkg2.mod2\nfrom pkg1 import mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import pkg2.mod2\nfrom pkg1 import mod1\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_and_standard_modules(self):
        self.mod.write('import pkg1\nimport sys\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import sys\n\nimport pkg1\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_and_standard_modules2(self):
        self.mod.write('import sys\n\nimport time\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import sys\nimport time\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_only_standard_modules(self):
        self.mod.write('import sys\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import sys\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_third_party(self):
        self.mod.write('import pkg1\nimport a_third_party\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import a_third_party\n\nimport pkg1\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_only_third_parties(self):
        self.mod.write('import a_third_party\na_var = 1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals('import a_third_party\n\n\na_var = 1\n',
                          self.import_tools.sort_imports(pymod))

    def test_simple_handling_long_imports(self):
        self.mod.write('import pkg1.mod1\n\n\nm = pkg1.mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import pkg1.mod1\n\n\nm = pkg1.mod1\n',
            self.import_tools.handle_long_imports(pymod, maxdots=2))

    def test_handling_long_imports_for_many_dots(self):
        self.mod.write('import p1.p2.p3.m1\n\n\nm = p1.p2.p3.m1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from p1.p2.p3 import m1\n\n\nm = m1\n',
            self.import_tools.handle_long_imports(pymod, maxdots=2))

    def test_handling_long_imports_for_their_length(self):
        self.mod.write('import p1.p2.p3.m1\n\n\nm = p1.p2.p3.m1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import p1.p2.p3.m1\n\n\nm = p1.p2.p3.m1\n',
            self.import_tools.handle_long_imports(pymod, maxdots=3,
                                                  maxlength=20))

    def test_handling_long_imports_for_many_dots2(self):
        self.mod.write('import p1.p2.p3.m1\n\n\nm = p1.p2.p3.m1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from p1.p2.p3 import m1\n\n\nm = m1\n',
            self.import_tools.handle_long_imports(pymod, maxdots=3,
                                                  maxlength=10))

    def test_handling_long_imports_with_one_letter_last(self):
        self.mod.write('import p1.p2.p3.l\n\n\nm = p1.p2.p3.l\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from p1.p2.p3 import l\n\n\nm = l\n',
            self.import_tools.handle_long_imports(pymod, maxdots=2))

    def test_empty_removing_unused_imports_and_eating_blank_lines(self):
        self.mod.write('import pkg1\nimport pkg2\n\n\nprint(pkg1)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1\n\n\nprint(pkg1)\n',
                          module_with_imports.get_changed_source())

    def test_sorting_imports_moving_to_top(self):
        self.mod.write('import mod\ndef f():\n    print(mod, pkg1, pkg2)\n'
                       'import pkg1\nimport pkg2\n')
        pymod = self.project.get_module('mod')
        self.assertEquals('import mod\nimport pkg1\nimport pkg2\n\n\n'
                          'def f():\n    print(mod, pkg1, pkg2)\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_moving_to_top2(self):
        self.mod.write('def f():\n    print(mod)\nimport mod\n')
        pymod = self.project.get_module('mod')
        self.assertEquals('import mod\n\n\ndef f():\n    print(mod)\n',
                          self.import_tools.sort_imports(pymod))

    # Sort pulls imports to the top anyway
    def test_sorting_imports_no_pull_to_top(self):
        code = ('import pkg2\ndef f():\n    print(mod, pkg1, pkg2)\n'
                'import pkg1\nimport mod\n')
        self.mod.write(code)
        pymod = self.project.get_module('mod')
        self.project.prefs['pull_imports_to_top'] = False
        self.assertEquals(
            'import mod\nimport pkg1\nimport pkg2\n\n\n'
            'def f():\n    print(mod, pkg1, pkg2)\n',
            self.import_tools.sort_imports(pymod))

    def test_sorting_imports_moving_to_top_and_module_docs(self):
        self.mod.write('"""\ndocs\n"""\ndef f():'
                       '\n    print(mod)\nimport mod\n')
        pymod = self.project.get_module('mod')
        self.assertEquals(
            '"""\ndocs\n"""\nimport mod\n\n\ndef f():\n    print(mod)\n',
            self.import_tools.sort_imports(pymod))

    def test_sorting_imports_moving_to_top_and_module_docs2(self):
        self.mod.write('"""\ndocs\n"""\n\n\nimport bbb\nimport aaa\n'
                       'def f():\n    print(mod)\nimport mod\n')
        pymod = self.project.get_module('mod')
        self.assertEquals(
            '"""\ndocs\n"""\n\n\nimport aaa\nimport bbb\n\n'
            'import mod\n\n\ndef f():\n    print(mod)\n',
            self.import_tools.sort_imports(pymod))

    def test_get_changed_source_preserves_blank_lines(self):
        self.mod.write(
            '__author__ = "author"\n\nimport aaa\n\nimport bbb\n\n'
            'def f():\n    print(mod)\n')
        pymod = self.project.get_module('mod')
        module_with_imports = self.import_tools.module_imports(pymod)
        self.assertEquals(
            'import aaa\n\nimport bbb\n\n__author__ = "author"\n\n'
            'def f():\n    print(mod)\n',
            module_with_imports.get_changed_source())

    def test_sorting_future_imports(self):
        self.mod.write('import os\nfrom __future__ import devision\n')
        pymod = self.project.get_module('mod')
        self.assertEquals(
            'from __future__ import devision\n\nimport os\n',
            self.import_tools.sort_imports(pymod))

    def test_customized_import_organization(self):
        self.mod.write('import sys\nimport sys\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import sys\n',
            self.import_tools.organize_imports(pymod, unused=False))

    def test_customized_import_organization2(self):
        self.mod.write('import sys\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import sys\n',
            self.import_tools.organize_imports(pymod, unused=False))

    def test_customized_import_organization3(self):
        self.mod.write('import sys\nimport mod\n\n\nvar = 1\nprint(mod.var)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import sys\n\n\nvar = 1\nprint(var)\n',
            self.import_tools.organize_imports(pymod, unused=False))

    def test_trivial_filtered_expand_stars(self):
        self.pkg1.get_child('__init__.py').write('var1 = 1\n')
        self.pkg2.get_child('__init__.py').write('var2 = 1\n')
        self.mod.write('from pkg1 import *\nfrom pkg2 import *\n\n'
                       'print(var1, var2)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from pkg1 import *\nfrom pkg2 import *\n\nprint(var1, var2)\n',
            self.import_tools.expand_stars(pymod, lambda stmt: False))

    def _line_filter(self, lineno):
        def import_filter(import_stmt):
            return import_stmt.start_line <= lineno < import_stmt.end_line
        return import_filter

    def test_filtered_expand_stars(self):
        self.pkg1.get_child('__init__.py').write('var1 = 1\n')
        self.pkg2.get_child('__init__.py').write('var2 = 1\n')
        self.mod.write('from pkg1 import *\nfrom pkg2 import *\n\n'
                       'print(var1, var2)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from pkg1 import *\nfrom pkg2 import var2\n\nprint(var1, var2)\n',
            self.import_tools.expand_stars(pymod, self._line_filter(2)))

    def test_filtered_relative_to_absolute(self):
        self.mod3.write('var = 1')
        self.mod2.write('import mod3\n\nprint(mod3.var)\n')
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEquals(
            'import mod3\n\nprint(mod3.var)\n',
            self.import_tools.relatives_to_absolutes(
                pymod, lambda stmt: False))
        self.assertEquals(
            'import pkg2.mod3\n\nprint(pkg2.mod3.var)\n',
            self.import_tools.relatives_to_absolutes(
                pymod, self._line_filter(1)))

    def test_filtered_froms_to_normals(self):
        self.pkg1.get_child('__init__.py').write('var1 = 1\n')
        self.pkg2.get_child('__init__.py').write('var2 = 1\n')
        self.mod.write('from pkg1 import var1\nfrom pkg2 import var2\n\n'
                       'print(var1, var2)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from pkg1 import var1\nfrom pkg2 '
            'import var2\n\nprint(var1, var2)\n',
            self.import_tools.expand_stars(pymod, lambda stmt: False))
        self.assertEquals(
            'from pkg1 import var1\nimport pkg2\n\nprint(var1, pkg2.var2)\n',
            self.import_tools.froms_to_imports(pymod, self._line_filter(2)))

    def test_filtered_froms_to_normals2(self):
        self.pkg1.get_child('__init__.py').write('var1 = 1\n')
        self.pkg2.get_child('__init__.py').write('var2 = 1\n')
        self.mod.write('from pkg1 import *\nfrom pkg2 import *\n\n'
                       'print(var1, var2)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from pkg1 import *\nimport pkg2\n\nprint(var1, pkg2.var2)\n',
            self.import_tools.froms_to_imports(pymod, self._line_filter(2)))

    def test_filtered_handle_long_imports(self):
        self.mod.write('import p1.p2.p3.m1\nimport pkg1.mod1\n\n\n'
                       'm = p1.p2.p3.m1, pkg1.mod1\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'import p1.p2.p3.m1\nfrom pkg1 import mod1\n\n\n'
            'm = p1.p2.p3.m1, mod1\n',
            self.import_tools.handle_long_imports(
                pymod, maxlength=5,
                import_filter=self._line_filter(2)))

    def test_filtering_and_import_actions_with_more_than_one_phase(self):
        self.pkg1.get_child('__init__.py').write('var1 = 1\n')
        self.pkg2.get_child('__init__.py').write('var2 = 1\n')
        self.mod.write('from pkg1 import *\nfrom pkg2 import *\n\n'
                       'print(var2)\n')
        pymod = self.project.get_pymodule(self.mod)
        self.assertEquals(
            'from pkg2 import *\n\nprint(var2)\n',
            self.import_tools.expand_stars(pymod, self._line_filter(1)))

    def test_non_existent_module_and_used_imports(self):
        self.mod.write(
            'from does_not_exist import func\n\nfunc()\n')
        pymod = self.project.get_module('mod')

        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(1, len(imports))


class AddImportTest(unittest.TestCase):

    def setUp(self):
        super(AddImportTest, self).setUp()
        self.project = testutils.sample_project()

        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.mod2 = testutils.create_module(self.project, 'mod2')
        self.pkg = testutils.create_package(self.project, 'pkg')
        self.mod3 = testutils.create_module(self.project, 'mod3', self.pkg)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AddImportTest, self).tearDown()

    def test_normal_imports(self):
        self.mod2.write('myvar = None\n')
        self.mod1.write('\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'mod2', 'myvar')
        self.assertEquals('import mod2\n', result)
        self.assertEquals('mod2.myvar', name)

    def test_not_reimporting_a_name(self):
        self.mod2.write('myvar = None\n')
        self.mod1.write('from mod2 import myvar\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'mod2', 'myvar')
        self.assertEquals('from mod2 import myvar\n', result)
        self.assertEquals('myvar', name)

    def test_adding_import_when_siblings_are_imported(self):
        self.mod2.write('var1 = None\nvar2 = None\n')
        self.mod1.write('from mod2 import var1\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'mod2', 'var2')
        self.assertEquals('from mod2 import var1, var2\n', result)
        self.assertEquals('var2', name)

    def test_adding_import_when_the_package_is_imported(self):
        self.pkg.get_child('__init__.py').write('var1 = None\n')
        self.mod3.write('var2 = None\n')
        self.mod1.write('from pkg import var1\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'pkg.mod3', 'var2')
        self.assertEquals('from pkg import var1, mod3\n', result)
        self.assertEquals('mod3.var2', name)

    def test_adding_import_for_modules_instead_of_names(self):
        self.pkg.get_child('__init__.py').write('var1 = None\n')
        self.mod3.write('\n')
        self.mod1.write('from pkg import var1\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'pkg.mod3', None)
        self.assertEquals('from pkg import var1, mod3\n', result)
        self.assertEquals('mod3', name)

    def test_adding_import_for_modules_with_normal_duplicate_imports(self):
        self.pkg.get_child('__init__.py').write('var1 = None\n')
        self.mod3.write('\n')
        self.mod1.write('import pkg.mod3\n')
        pymod = self.project.get_module('mod1')
        result, name = add_import(self.project, pymod, 'pkg.mod3', None)
        self.assertEquals('import pkg.mod3\n', result)
        self.assertEquals('pkg.mod3', name)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ImportUtilsTest))
    result.addTests(unittest.makeSuite(AddImportTest))
    return result

if __name__ == '__main__':
    unittest.main()
