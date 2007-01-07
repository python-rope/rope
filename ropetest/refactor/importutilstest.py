import unittest

from rope.base.project import Project
from ropetest import testutils
from rope.refactor.importutils import ImportTools


class ImportUtilsTest(unittest.TestCase):

    def setUp(self):
        super(ImportUtilsTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.import_tools = ImportTools(self.pycore)

        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        self.pkg1 = self.pycore.create_package(self.project.get_root_folder(), 'pkg1')
        self.mod1 = self.pycore.create_module(self.pkg1, 'mod1')
        self.pkg2 = self.pycore.create_package(self.project.get_root_folder(), 'pkg2')
        self.mod2 = self.pycore.create_module(self.pkg2, 'mod2')
        self.mod3 = self.pycore.create_module(self.pkg2, 'mod3')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ImportUtilsTest, self).tearDown()

    def test_get_import_for_module(self):
        pymod = self.pycore.get_module('mod')
        import_statement = self.import_tools.get_import_for_module(pymod)
        self.assertEquals('import mod', import_statement.get_import_statement())

    def test_get_import_for_module_in_nested_modules(self):
        pymod = self.pycore.get_module('pkg1.mod1')
        import_statement = self.import_tools.get_import_for_module(pymod)
        self.assertEquals('import pkg1.mod1', import_statement.get_import_statement())

    def test_get_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child('__init__.py')
        pymod = self.pycore.resource_to_pyobject(init_dot_py)
        import_statement = self.import_tools.get_import_for_module(pymod)
        self.assertEquals('import pkg1', import_statement.get_import_statement())


    def test_get_from_import_for_module(self):
        pymod = self.pycore.get_module('mod')
        import_statement = self.import_tools.get_from_import_for_module(pymod, 'a_func')
        self.assertEquals('from mod import a_func',
                          import_statement.get_import_statement())

    def test_get_from_import_for_module_in_nested_modules(self):
        pymod = self.pycore.get_module('pkg1.mod1')
        import_statement = self.import_tools.get_from_import_for_module(pymod, 'a_func')
        self.assertEquals('from pkg1.mod1 import a_func',
                          import_statement.get_import_statement())

    def test_get_from_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child('__init__.py')
        pymod = self.pycore.resource_to_pyobject(init_dot_py)
        import_statement = self.import_tools.get_from_import_for_module(pymod, 'a_func')
        self.assertEquals('from pkg1 import a_func',
                          import_statement.get_import_statement())


    def test_get_import_statements(self):
        self.mod.write('import pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('import pkg1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_with_alias(self):
        self.mod.write('import pkg1.mod1 as mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('import pkg1.mod1 as mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_for_froms(self):
        self.mod.write('from pkg1 import mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('from pkg1 import mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_multi_line_import_statements_for_froms(self):
        self.mod.write('from pkg1 \\\n    import mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('from pkg1 import mod1',
                          imports[0].import_info.get_import_statement())

    def test_get_import_statements_for_from_star(self):
        self.mod.write('from pkg1 import *\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('from pkg1 import *',
                          imports[0].import_info.get_import_statement())

    @testutils.run_only_for_25
    def test_get_import_statements_for_new_relatives(self):
        self.mod2.write('from .mod3 import *\n')
        pymod = self.pycore.get_module('pkg2.mod2')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals('from .mod3 import *',
                          imports[0].import_info.get_import_statement())

    def test_ignoring_indented_imports(self):
        self.mod.write('if True:\n    import pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals(0, len(imports))

    def test_import_get_names(self):
        self.mod.write('import pkg1 as pkg\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals(['pkg'], imports[0].import_info.get_imported_names())

    def test_import_get_names_with_alias(self):
        self.mod.write('import pkg1.mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals(['pkg1'], imports[0].import_info.get_imported_names())

    def test_import_get_names_with_alias(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_import_statements()
        self.assertEquals(['a_func'], imports[0].import_info.get_imported_names())

    def test_empty_getting_used_imports(self):
        self.mod.write('')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(0, len(imports))

    def test_empty_getting_used_imports2(self):
        self.mod.write('import pkg\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(0, len(imports))

    def test_simple_getting_used_imports(self):
        self.mod.write('import pkg\nprint pkg\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(1, len(imports))
        self.assertEquals('import pkg', imports[0].get_import_statement())

    def test_simple_getting_used_imports2(self):
        self.mod.write('import pkg\ndef a_func():\n    print pkg\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEquals(1, len(imports))
        self.assertEquals('import pkg', imports[0].get_import_statement())

    def test_getting_used_imports_for_nested_scopes(self):
        self.mod.write('import pkg1\nprint pkg1\ndef a_func():\n    pass\nprint pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(
            pymod.get_attribute('a_func').get_object())
        self.assertEquals(0, len(imports))

    def test_getting_used_imports_for_nested_scopes2(self):
        self.mod.write('from pkg1 import mod1\ndef a_func():\n    print mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        imports = module_with_imports.get_used_imports(
            pymod.get_attribute('a_func').get_object())
        self.assertEquals(1, len(imports))
        self.assertEquals('from pkg1 import mod1', imports[0].get_import_statement())

    def test_empty_removing_unused_imports(self):
        self.mod.write('import pkg1\nprint pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1\nprint pkg1\n',
                          module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports(self):
        self.mod.write('import pkg1\n\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_froms(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func, another_func\n\na_func()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import a_func\n\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_from_stars(self):
        self.mod.write('from pkg1.mod1 import *\n\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_nested_modules(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('import pkg1.mod1\npkg1.mod1.a_func()')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_functions_of_the_same_name(self):
        self.mod.write('def a_func():\n    pass\ndef a_func():\n    pass\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('def a_func():\n    pass\ndef a_func():\n    pass\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_for_from_import_with_as(self):
        self.mod.write('a_var = 1\n')
        self.mod1.write('from mod import a_var as myvar\na_var = myvar\n')
        pymod = self.pycore.resource_to_pyobject(self.mod1)
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from mod import a_var as myvar\na_var = myvar\n',
                          module_with_imports.get_changed_source())

    def test_adding_imports(self):
        self.mod.write('\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        new_import = self.import_tools.get_import_for_module(
            self.pycore.resource_to_pyobject(self.mod1))
        module_with_imports.add_import(new_import)
        self.assertEquals('import pkg1.mod1\n', module_with_imports.get_changed_source())

    def test_adding_from_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        new_import = self.import_tools.get_from_import_for_module(
            self.pycore.resource_to_pyobject(self.mod1), 'another_func')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import a_func, another_func\n',
                          module_with_imports.get_changed_source())

    def test_adding_to_star_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        new_import = self.import_tools.get_from_import_for_module(
            self.pycore.resource_to_pyobject(self.mod1), 'another_func')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import *\n',
                          module_with_imports.get_changed_source())

    def test_adding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        new_import = self.import_tools.get_from_import_for_module(
            self.pycore.resource_to_pyobject(self.mod1), '*')
        module_with_imports.add_import(new_import)
        self.assertEquals('from pkg1.mod1 import *\n',
                          module_with_imports.get_changed_source())

    def test_not_changing_the_format_of_unchanged_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func,\n    another_func)\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        self.assertEquals('from pkg1.mod1 import (a_func,\n    another_func)\n',
                          module_with_imports.get_changed_source())

    def test_not_changing_the_format_of_unchanged_imports2(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func)\na_func()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import (a_func)\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_reoccuring_names(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\nfrom pkg1.mod1 import a_func\na_func()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import *\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_reoccuring_names2(self):
        self.mod.write('import pkg2.mod2\nimport pkg2.mod3\nprint pkg2.mod2, pkg2.mod3')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg2.mod2\nimport pkg2.mod3\nprint pkg2.mod2, pkg2.mod3',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages(self):
        self.mod.write('import pkg1.mod1\nimport pkg1\nprint pkg1, pkg1.mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\nprint pkg1, pkg1.mod1\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages_reversed(self):
        self.mod.write('import pkg1\nimport pkg1.mod1\nprint pkg1, pkg1.mod1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg1.mod1\nprint pkg1, pkg1.mod1\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_common_packages2(self):
        self.mod.write('import pkg1.mod1\nimport pkg1.mod2\nprint pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('import pkg1.mod1\nprint pkg1\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms2(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\nfunc1()')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import func1\nfunc1()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms3(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\ndef a_func():\n    func1()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import func1\ndef a_func():\n    func1()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms4(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('from pkg1.mod1 import func1\nclass A(object):\n'
                       '    def a_func(self):\n        func1()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import func1\nclass A(object):\n'
                          '    def a_func(self):\n        func1()\n',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_getting_attributes(self):
        self.mod1.write('class A(object):\n    def f(self):\n        pass\n')
        self.mod.write('from pkg1.mod1 import A\nvar = A().f()')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('from pkg1.mod1 import A\nvar = A().f()',
                          module_with_imports.get_changed_source())

    def test_removing_unused_imports_function_parameters(self):
        self.mod1.write('def func1():\n    pass\n')
        self.mod.write('import pkg1\ndef a_func(pkg1):\n    my_var = pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEquals('def a_func(pkg1):\n    my_var = pkg1\n',
                          module_with_imports.get_changed_source())

    def test_trivial_expanding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEquals('', module_with_imports.get_changed_source())

    def test_expanding_star_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEquals('from pkg1.mod1 import a_func\na_func()\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicate_imports(self):
        self.mod.write('import pkg1\nimport pkg1\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg1\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicates_and_reoccuring_names(self):
        self.mod.write('import pkg2.mod2\nimport pkg2.mod3\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('import pkg2.mod2\nimport pkg2.mod3\n',
                          module_with_imports.get_changed_source())

    def test_removing_duplicate_imports_for_froms(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1 import a_func\nfrom pkg1 import a_func, another_func\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('from pkg1 import a_func, another_func\n',
                          module_with_imports.get_changed_source())

    def test_transforming_froms_to_normal_changing_imports(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\nprint a_func\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\nprint pkg1.mod1.a_func\n', changed_module)

    def test_transforming_froms_to_normal_changing_occurances(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func\na_func()')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()', changed_module)

    def test_transforming_froms_to_normal_for_multi_imports(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\nanother_func()\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\npkg1.mod1.another_func()\n',
                          changed_module)

    def test_transforming_froms_to_normal_for_multi_imports_inside_parens(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import (a_func, \n    another_func)' \
                       '\na_func()\nanother_func()\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\npkg1.mod1.another_func()\n',
                          changed_module)

    def test_transforming_froms_to_normal_from_stars(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import *\na_func()\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\n', changed_module)

    def test_transforming_froms_to_normal_from_stars(self):
        self.mod1.write('a_var = 10')
        self.mod.write('import pkg1.mod1\nfrom pkg1.mod1 import a_var\n' \
                       'def a_func():\n    print pkg1.mod1, a_var\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\n' \
                          'def a_func():\n    print pkg1.mod1, pkg1.mod1.a_var\n',
                          changed_module)

    def test_transforming_froms_to_normal_from_with_alias(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod.write('from pkg1.mod1 import a_func as another_func\nanother_func()\n')
        pymod = self.pycore.get_module('mod')
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg1.mod1\npkg1.mod1.a_func()\n', changed_module)

    def test_transforming_froms_to_normal_for_relatives(self):
        self.mod2.write('def a_func():\n    pass\n')
        self.mod3.write('from mod2 import *\na_func()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod3)
        changed_module = self.import_tools.transform_froms_to_normal_imports(pymod)
        self.assertEquals('import pkg2.mod2\npkg2.mod2.a_func()\n', changed_module)

    def test_transform_relatives_imports_to_absolute_imports_doing_nothing(self):
        self.mod2.write('from pkg1 import mod1\nimport mod1\n')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('from pkg1 import mod1\nimport mod1\n',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    def test_transform_relatives_imports_to_absolute_imports_for_normal_imports(self):
        self.mod2.write('import mod3\n')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('import pkg2.mod3\n',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    def test_transform_relatives_imports_to_absolute_imports_for_froms(self):
        self.mod3.write('def a_func():\n    pass\n')
        self.mod2.write('from mod3 import a_func\n')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('from pkg2.mod3 import a_func\n',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    @testutils.run_only_for_25
    def test_transform_relatives_imports_to_absolute_imports_for_new_relatives(self):
        self.mod3.write('def a_func():\n    pass\n')
        self.mod2.write('from .mod3 import a_func\n')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('from pkg2.mod3 import a_func\n',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    def test_transform_relatives_imports_to_absolute_imports_for_normal_imports2(self):
        self.mod2.write('import mod3\nprint mod3')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('import pkg2.mod3\nprint pkg2.mod3',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    def test_transform_relatives_imports_to_absolute_imports_for_aliases(self):
        self.mod2.write('import mod3 as mod3\nprint mod3')
        pymod = self.pycore.resource_to_pyobject(self.mod2)
        self.assertEquals('import pkg2.mod3 as mod3\nprint mod3',
                          self.import_tools.transform_relative_imports_to_absolute(pymod))

    def test_organizing_imports(self):
        self.mod1.write('import mod1\n')
        pymod = self.pycore.resource_to_pyobject(self.mod1)
        self.assertEquals('', self.import_tools.organize_imports(pymod))

    def test_removing_self_imports(self):
        self.mod.write('import mod\nmod.a_var = 1\nprint mod.a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports2(self):
        self.mod1.write('import pkg1.mod1\npkg1.mod1.a_var = 1\nprint pkg1.mod1.a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod1)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_as(self):
        self.mod.write('import mod as mymod\nmymod.a_var = 1\nprint mymod.a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms(self):
        self.mod1.write('from pkg1 import mod1\nmod1.a_var = 1\nprint mod1.a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod1)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms_with_as(self):
        self.mod1.write('from pkg1 import mod1 as mymod\nmymod.a_var = 1\nprint mymod.a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod1)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms2(self):
        self.mod.write('from mod import a_var\na_var = 1\nprint a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms3(self):
        self.mod.write('from mod import a_var\na_var = 1\nprint a_var\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_for_froms3(self):
        self.mod.write('from mod import a_var as myvar\na_var = 1\nprint myvar\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_no_dot_after_mod(self):
        self.mod.write('import mod\nprint mod\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import mod\nprint mod\n',
                          self.import_tools.organize_imports(pymod))

    def test_removing_self_imports_with_no_dot_after_mod2(self):
        self.mod.write('import mod\na_var = 1\nprint mod\\\n     \\\n     .var\n\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint var\n\n',
                          self.import_tools.organize_imports(pymod))

    # XXX: causes stack overflow
    def xxx_test_removing_self_imports_for_from_import_star(self):
        self.mod.write('from mod import *\na_var = 1\nprint myvar\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('a_var = 1\nprint a_var\n',
                          self.import_tools.organize_imports(pymod))

    def test_sorting_empty_imports(self):
        self.mod.write('')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('', self.import_tools.sort_imports(pymod))

    def test_sorting_one_import(self):
        self.mod.write('import pkg1.mod1\n\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import pkg1.mod1\n\n\n', self.import_tools.sort_imports(pymod))

    def test_sorting_imports_alphabetically(self):
        self.mod.write('import pkg2.mod2\nimport pkg1.mod1\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import pkg1.mod1\nimport pkg2.mod2\n\n\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_and_froms(self):
        self.mod.write('import pkg2.mod2\nfrom pkg1 import mod1\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import pkg2.mod2\nfrom pkg1 import mod1\n\n\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_imports_and_standard_modles(self):
        self.mod.write('import pkg1\nimport sys\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import sys\n\nimport pkg1\n\n\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_only_standard_modles(self):
        self.mod.write('import sys\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import sys\n\n\n',
                          self.import_tools.sort_imports(pymod))

    def test_sorting_third_party(self):
        self.mod.write('import pkg1\nimport a_third_party\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertEquals('import a_third_party\n\nimport pkg1\n\n\n',
                          self.import_tools.sort_imports(pymod))


if __name__ == '__main__':
    unittest.main()
