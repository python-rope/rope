import unittest

from rope.project import Project
from ropetest import testutils
from rope.importutils import ImportTools


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
        self.assertEquals('\n', module_with_imports.get_changed_source())
        
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
        self.assertEquals('\n', module_with_imports.get_changed_source())
    
    def test_adding_imports(self):
        self.mod.write('\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        new_import = self.import_tools.get_import_for_module(
            self.pycore.resource_to_pyobject(self.mod1))
        module_with_imports.add_import(new_import)
        self.assertEquals('import pkg1.mod1\n\n', module_with_imports.get_changed_source())

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

    def test_removing_duplicate_imports_for_froms(self):
        self.mod1.write('def a_func():\n    pass\ndef another_func():\n    pass\n')
        self.mod.write('from pkg1 import a_func\nfrom pkg1 import a_func, another_func\n')
        pymod = self.pycore.get_module('mod')
        module_with_imports = self.import_tools.get_module_with_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEquals('from pkg1 import a_func, another_func\n',
                          module_with_imports.get_changed_source())


if __name__ == '__main__':
    unittest.main()
