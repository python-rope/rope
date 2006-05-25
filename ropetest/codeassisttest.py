import os
import unittest

from rope.codeassist import CodeAssist, RopeSyntaxError, CompletionProposal
from rope.project import Project

def _remove_recursively(file):
    for root, dirs, files in os.walk(file, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(file)

class CodeAssistTest(unittest.TestCase):

    def setUp(self):
        super(CodeAssistTest, self).setUp()
        self.project_root = 'sample_project'
        os.mkdir(self.project_root)
        self.project = Project(self.project_root)
        self.assist = self.project.get_code_assist()
        
    def tearDown(self):
        _remove_recursively(self.project_root)
        super(CodeAssistTest, self).tearDown()

    def test_simple_assist(self):
        self.assist.assist('', 0)

    def assert_completion_in_result(self, name, kind, result):
        for proposal in result.completions:
            if proposal.name == name and proposal.kind == kind:
                return
        self.fail('completion <%s> not proposed' % name)

    def assert_completion_not_in_result(self, name, kind, result):
        for proposal in result.completions:
            if proposal.name == name and proposal.kind == kind:
                self.fail('completion <%s> was proposed' % name)

    def test_completing_global_variables(self):
        code = 'my_global = 10\nt = my'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_global', 'global_variable', result)

    def test_not_proposing_unmatched_vars(self):
        code = 'my_global = 10\nt = you'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global_variable', result)

    def test_not_proposing_unmatched_vars_with_underlined_starting(self):
        code = 'my_global = 10\nt = you_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global_variable', result)

    def test_not_proposing_local_assigns_as_global_completions(self):
        code = 'def f():    my_global = 10\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global_variable', result)

    def test_proposing_functions(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'function', result)

    def test_proposing_classes(self):
        code = 'class Sample(object):    pass\nt = Sam'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('Sample', 'class', result)

    def test_proposing_each_name_at_most_once(self):
        code = 'variable = 10\nvariable = 20\nt = vari'
        result = self.assist.assist(code, len(code))
        count = len([x for x in result.completions
                     if x.name == 'variable' and x.kind == 'global_variable'])
        self.assertEquals(1, count)

    def test_throwing_exception_in_case_of_syntax_errors(self):
        code = 'sample (sdf+)\n'
        self.assertRaises(RopeSyntaxError, 
                          lambda: self.assist.assist(code, len(code)))
    
    def test_ignoring_errors_in_current_line(self):
        code = 'def my_func():    return 2\nt = '
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'function', result)

    def test_not_reporting_variables_in_current_line(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_', 'global_variable', result)

    def test_completion_result(self):
        code = 'my_global = 10\nt = my'
        result = self.assist.assist(code, len(code))
        self.assertEquals(len(code) - 2, result.start_offset)
        self.assertEquals(len(code), result.end_offset)

    def test_completing_imported_names(self):
        code = 'import sys\na = sy'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sys', 'module', result)

    def test_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = mys'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('mysys', 'module', result)

    def test_not_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = sy'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('sys', 'module', result)

    def test_including_matching_builtins_types(self):
        code = 'my_var = Excep'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('Exception', 'class', result)
        
    def test_including_matching_builtins_functions(self):
        code = 'my_var = zi'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('zip', 'builtin_function', result)
        
    def test_including_keywords(self):
        code = 'fo'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('for', 'keyword', result)

    def test_not_reporting_proposals_after_dot(self):
        code = 'a_dict = {}\nkey = 3\na_dict.ke'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('key', 'global_variable', result)

    def test_proposing_local_variables_in_functions(self):
        code = 'def f(self):\n    my_var = 10\n    my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'local_variable', result)

    def test_local_variables_override_global_ones(self):
        code = 'my_var = 20\ndef f(self):\n    my_var = 10\n    my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'local_variable', result)

    def test_not_including_class_body_variables(self):
        code = 'class C(object):\n    my_var = 20\n    def f(self):\n        a = 20\n        my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_var', 'local_variable', result)

    def test_nested_functions(self):
        code = "def my_func():\n    func_var = 20\n    def inner_func():\n        a = 20\n        func"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('func_var', 'local_variable', result)

    def test_scope_endpoint_selection(self):
        code = "def my_func():\n    func_var = 20\n"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('func_var', 'local_variable', result)

    def test_scope_better_endpoint_selection(self):
        code = "if True:\n    def f():\n        my_var = 10\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_var', 'local_variable', result)

    def test_imports_inside_function(self):
        code = "def f():\n    import sys\n    sy"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sys', 'module', result)

    def test_imports_inside_function_dont_mix_with_globals(self):
        code = "def f():\n    import sys\nsy"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('sys', 'module', result)

    def test_nested_classes_local_names(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            func"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('func_var', 'local_variable', result)

    def test_nested_classes_global(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            globa"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('global_var', 'global_variable', result)

    def test_nested_classes_global_function(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            my_f"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'function', result)

    def test_proposing_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_param', 'local_variable', result)

    def test_proposing_function_keyword_parameters_in_functions(self):
        code = "def my_func(my_param, *my_list, **my_kws):\n    my_var = 20\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_param', 'local_variable', result)
        self.assert_completion_in_result('my_list', 'local_variable', result)
        self.assert_completion_in_result('my_kws', 'local_variable', result)

    def test_not_proposing_unmatching_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    you_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_param', 'local_variable', result)

    def test_ignoring_current_statement(self):
        code = "my_var = 10\nmy_tuple = (10, \n           my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_brackets_continuation(self):
        code = "my_var = 10\n'hello'[10:\n        my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_explicit_continuation(self):
        code = "my_var = 10\nmy_var2 = 2 + \\\n          my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_while_the_first_statement_of_the_block(self):
        code = "my_var = 10\ndef f():\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_while_current_line_ends_with_a_colon(self):
        code = "my_var = 10\nif my_:\n    pass"
        result = self.assist.assist(code, 18)
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents(self):
        code = "my_var = '('\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_comment_contents(self):
        code = "my_var = 10 #(\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_backslash_plus_quotes(self):
        code = "my_var = '\\''\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_backslash_plus_backslash(self):
        code = "my_var = '\\\\'\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_not_proposing_later_defined_variables_in_current_block(self):
        code = "my_\nmy_var = 10\n"
        result = self.assist.assist(code, 3)
        self.assert_completion_not_in_result('my_var', 'global_variable', result)

    def test_not_proposing_later_defined_variables_in_current_function(self):
        code = "def f():\n    my_\n    my_var = 10\n"
        result = self.assist.assist(code, 16)
        self.assert_completion_not_in_result('my_var', 'local_variable', result)

    def test_ignoring_string_contents_with_triple_quotes(self):
        code = "my_var = '''(\n'('''\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_with_triple_quotes_and_backslash(self):
        code = 'my_var = """\\"""("""\nmy_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_with_triple_quotes_and_double_backslash(self):
        code = 'my_var = """\\\\"""\nmy_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global_variable', result)

    def test_reporting_params_when_in_the_first_line_of_a_function(self):
        code = 'def f(param):\n    para'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('param', 'local_variable', result)

    def assert_template_in_result(self, name, result):
        for template in result.templates:
            if template.name == name:
                break
        else:
            self.fail('template <%s> was not proposed' % name)

    def assert_template_not_in_result(self, name, result):
        for template in result.templates:
            if template.name == name:
                self.fail('template <%s> was proposed' % name)

    def test_proposing_basic_templates(self):
        self.assist.add_template('my_template', 'print "hello"')
        code = 'my_te'
        result = self.assist.assist(code, len(code))
        self.assert_template_in_result('my_template', result)


class CodeAssistInProjectsTest(unittest.TestCase):

    def setUp(self):
        super(CodeAssistInProjectsTest, self).setUp()
        self.project_root = 'sample_project'
        os.mkdir(self.project_root)
        self.project = Project(self.project_root)
        samplemod = self.project.create_module(self.project.get_root_folder(), 'samplemod')
        samplemod.write("class SampleClass(object):\n    def sample_method():\n        pass" + \
                        "\n\ndef sample_func():\n    pass\nsample_var = 10\n" + \
                        "\ndef _underlined_func():\n    pass\n\n" )
        package = self.project.create_package(self.project.get_root_folder(), 'package')
        nestedmod = self.project.create_module(package, 'nestedmod')
        self.assist = self.project.get_code_assist()

    def assert_completion_in_result(self, name, kind, result):
        for proposal in result.completions:
            if proposal.name == name and proposal.kind == kind:
                return
        self.fail('completion <%s> not proposed' % name)


    def assert_completion_not_in_result(self, name, kind, result):
        for proposal in result.completions:
            if proposal.name == name and proposal.kind == kind:
                self.fail('completion <%s> was proposed' % name)

    def tearDown(self):
        _remove_recursively(self.project_root)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        code = 'import samplemod\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('samplemod', 'module', result)

    def test_from_import_class(self):
        code = 'from samplemod import SampleClass\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'class', result)

    def test_from_import_function(self):
        code = 'from samplemod import sample_func\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_func', 'function', result)

    def test_from_import_variable(self):
        code = 'from samplemod import sample_var\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_var', 'global_variable', result)

    def test_from_imports_inside_functions(self):
        code = 'def f():\n    from samplemod import SampleClass\n    Sample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'class', result)

    def test_from_import_only_imports_imported(self):
        code = 'from samplemod import sample_func\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('SampleClass', 'class', result)

    def test_from_import_star(self):
        code = 'from samplemod import *\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'class', result)

    def test_from_import_star2(self):
        code = 'from samplemod import *\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_func', 'function', result)
        self.assert_completion_in_result('sample_var', 'global_variable', result)

    def test_from_import_star_not_imporing_underlined(self):
        code = 'from samplemod import *\n_under'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('_underlined_func', 'function', result)

    def test_from_package_import_mod(self):
        code = 'from package import nestedmod\nnest'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('nestedmod', 'module', result)

    def test_from_package_import_star(self):
        code = 'from package import *\nnest'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('nestedmod', 'module', result)

    def test_unknown_when_module_cannot_be_found(self):
        code = 'from doesnotexist import nestedmod\nnest'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('nestedmod', 'unknown', result)


if __name__ == '__main__':
    unittest.main()
