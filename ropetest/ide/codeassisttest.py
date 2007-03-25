import unittest

from rope.ide.codeassist import (PythonCodeAssist, RopeSyntaxError,
                                 Template, ProposalSorter)
from ropetest import testutils


class CodeAssistTest(unittest.TestCase):

    def setUp(self):
        super(CodeAssistTest, self).setUp()
        self.project = testutils.sample_project()
        self.assist = PythonCodeAssist(self.project)

    def tearDown(self):
        testutils.remove_project(self.project)
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
        self.assert_completion_in_result('my_global', 'global', result)

    def test_not_proposing_unmatched_vars(self):
        code = 'my_global = 10\nt = you'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_not_proposing_unmatched_vars_with_underlined_starting(self):
        code = 'my_global = 10\nt = your_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_not_proposing_local_assigns_as_global_completions(self):
        code = 'def f():    my_global = 10\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_proposing_functions(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'global', result)

    def test_proposing_classes(self):
        code = 'class Sample(object):    pass\nt = Sam'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('Sample', 'global', result)

    def test_proposing_each_name_at_most_once(self):
        code = 'variable = 10\nvariable = 20\nt = vari'
        result = self.assist.assist(code, len(code))
        count = len([x for x in result.completions
                     if x.name == 'variable' and x.kind == 'global'])
        self.assertEquals(1, count)

    def test_throwing_exception_in_case_of_syntax_errors(self):
        code = 'sample (sdf+)\n'
        self.assertRaises(RopeSyntaxError,
                          lambda: self.assist.assist(code, len(code)))

    def test_ignoring_errors_in_current_line(self):
        code = 'def my_func():\n    return 2\nt = '
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'global', result)

    def test_not_reporting_variables_in_current_line(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_', 'global', result)

    def test_completion_result(self):
        code = 'my_global = 10\nt = my'
        result = self.assist.assist(code, len(code))
        self.assertEquals(len(code) - 2, result.start_offset)

    def test_completing_imported_names(self):
        code = 'import sys\na = sy'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sys', 'global', result)

    def test_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = mys'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('mysys', 'global', result)

    def test_not_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = sy'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('sys', 'global', result)

    def test_including_matching_builtins_types(self):
        code = 'my_var = Excep'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('Exception', 'builtin', result)
        self.assert_completion_not_in_result('zip', 'builtin', result)

    def test_including_matching_builtins_functions(self):
        code = 'my_var = zi'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('zip', 'builtin', result)

    def test_including_keywords(self):
        code = 'fo'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('for', 'keyword', result)

    def test_not_reporting_proposals_after_dot(self):
        code = 'a_dict = {}\nkey = 3\na_dict.ke'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('key', 'global', result)

    def test_proposing_local_variables_in_functions(self):
        code = 'def f(self):\n    my_var = 10\n    my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'local', result)

    def test_local_variables_override_global_ones(self):
        code = 'my_var = 20\ndef f(self):\n    my_var = 10\n    my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'local', result)

    def test_not_including_class_body_variables(self):
        code = 'class C(object):\n    my_var = 20\n' \
               '    def f(self):\n        a = 20\n        my_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_nested_functions(self):
        code = 'def my_func():\n    func_var = 20\n    ' \
               'def inner_func():\n        a = 20\n        func'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('func_var', 'local', result)

    def test_scope_endpoint_selection(self):
        code = "def my_func():\n    func_var = 20\n"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('func_var', 'local', result)

    def test_scope_better_endpoint_selection(self):
        code = "if True:\n    def f():\n        my_var = 10\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_imports_inside_function(self):
        code = "def f():\n    import sys\n    sy"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sys', 'local', result)

    def test_imports_inside_function_dont_mix_with_globals(self):
        code = "def f():\n    import sys\nsy"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('sys', 'local', result)

    def test_nested_classes_local_names(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            func"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('func_var', 'local', result)

    def test_nested_classes_global(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            globa"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('global_var', 'global', result)

    def test_nested_classes_global_function(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            my_f"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_func', 'global', result)

    def test_proposing_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_param', 'local', result)

    def test_proposing_function_keyword_parameters_in_functions(self):
        code = "def my_func(my_param, *my_list, **my_kws):\n    my_var = 20\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_param', 'local', result)
        self.assert_completion_in_result('my_list', 'local', result)
        self.assert_completion_in_result('my_kws', 'local', result)

    def test_not_proposing_unmatching_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    you_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('my_param', 'local', result)

    def test_ignoring_current_statement(self):
        code = "my_var = 10\nmy_tuple = (10, \n           my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_brackets_continuation(self):
        code = "my_var = 10\n'hello'[10:\n        my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_explicit_continuation(self):
        code = "my_var = 10\nmy_var2 = 2 + \\\n          my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_while_the_first_statement_of_the_block(self):
        code = "my_var = 10\ndef f():\n    my_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_while_current_line_ends_with_a_colon(self):
        code = "my_var = 10\nif my_:\n    pass"
        result = self.assist.assist(code, 18)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents(self):
        code = "my_var = '('\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_comment_contents(self):
        code = "my_var = 10 #(\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_backslash_plus_quotes(self):
        code = "my_var = '\\''\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_backslash_plus_backslash(self):
        code = "my_var = '\\\\'\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_not_proposing_later_defined_variables_in_current_block(self):
        code = "my_\nmy_var = 10\n"
        result = self.assist.assist(code, 3)
        self.assert_completion_not_in_result('my_var', 'global', result)

    def test_not_proposing_later_defined_variables_in_current_function(self):
        code = "def f():\n    my_\n    my_var = 10\n"
        result = self.assist.assist(code, 16)
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_ignoring_string_contents_with_triple_quotes(self):
        code = "my_var = '''(\n'('''\nmy_"
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_with_triple_quotes_and_backslash(self):
        code = 'my_var = """\\"""("""\nmy_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_with_triple_quotes_and_double_backslash(self):
        code = 'my_var = """\\\\"""\nmy_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('my_var', 'global', result)

    def test_reporting_params_when_in_the_first_line_of_a_function(self):
        code = 'def f(param):\n    para'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('param', 'local', result)

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

    def test_code_assist_when_having_a_two_line_function_header(self):
        code = 'def f(param1,\n      param2):\n    para'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('param1', 'local', result)

    def test_code_assist_with_function_with_two_line_return(self):
        code = 'def f(param1, param2):\n    return(param1,\n           para'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('param2', 'local', result)

    def test_get_definition_location(self):
        code = 'def a_func():\n    pass\na_func()'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((None, 1), result)

    def test_get_definition_location_underlined_names(self):
        code = 'def a_sample_func():\n    pass\na_sample_func()'
        result = self.assist.get_definition_location(code, len(code) - 11)
        self.assertEquals((None, 1), result)

    def test_get_definition_location_dotted_names(self):
        code = 'class AClass(object):\n    ' + \
               '@staticmethod\n    def a_method():\n        pass\nAClass.a_method()'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((None, 3), result)

    def test_get_definition_location_dotted_module_names(self):
        module_resource = self.project.get_pycore().\
                          create_module(self.project.root, 'mod')
        module_resource.write('def a_func():\n    pass\n')
        code = 'import mod\nmod.a_func()'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((module_resource, 1), result)

    def test_get_definition_location_for_nested_packages(self):
        pycore = self.project.get_pycore()
        mod1 = pycore.create_module(self.project.root, 'mod1')
        pkg1 = pycore.create_package(self.project.root, 'pkg1')
        pkg2 = pycore.create_package(pkg1, 'pkg2')
        mod2 = pycore.create_module(pkg2, 'mod2')
        mod1.write('import pkg1.pkg2.mod2')

        mod1_scope = pycore.resource_to_pyobject(mod1).get_scope()
        init_dot_py = pkg2.get_child('__init__.py')
        found_pyname = self.assist.get_definition_location(mod1.read(),
                                                           mod1.read().index('pkg2') + 1)
        self.assertEquals(init_dot_py, found_pyname[0])

    def test_get_definition_location_unknown(self):
        code = 'a_func()\n'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((None, None), result)

    def test_get_definition_location_dot_spaces(self):
        code = 'class AClass(object):\n    ' + \
               '@staticmethod\n    def a_method():\n        pass\nAClass.\\\n     a_method()'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((None, 3), result)

    def test_get_definition_location_dot_line_break_inside_parens(self):
        code = 'class A(object):\n    def a_method(self):\n        pass\n' + \
               '(A.\na_method)'
        result = self.assist.get_definition_location(code, code.rindex('a_method') + 1)
        self.assertEquals((None, 2), result)

    def test_if_scopes_in_other_scopes_for_get_definition_location(self):
        code = 'def f(a_var):\n    pass\na_var = 10\nif True:\n    print a_var\n'
        result = self.assist.get_definition_location(code, len(code) - 3)
        self.assertEquals((None, 3), result)

    def test_code_assists_in_parens(self):
        code = 'def a_func(a_var):\n    pass\na_var = 10\na_func(a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'global', result)

    def test_simple_type_inferencing(self):
        code = 'class Sample(object):\n    def __init__(self, a_param):\n        pass\n' + \
               '    def a_method(self):\n        pass\n' + \
               'Sample("hey").a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_method', 'attribute', result)

    def test_proposals_sorter(self):
        self.assist.add_template('my_sample_template', '')
        code = 'def my_sample_function(self):\n' + \
               '    my_sample_var = 20\n' + \
               '    my_sample_'
        result = self.assist.assist(code, len(code))
        sorted_proposals = ProposalSorter(result).get_sorted_proposal_list()
        self.assertEquals('my_sample_var', sorted_proposals[0].name)
        self.assertEquals('my_sample_function', sorted_proposals[1].name)
        self.assertEquals('my_sample_template', sorted_proposals[2].name)

    def test_proposals_sorter_for_methods_and_attributes(self):
        self.assist.add_template('my_sample_template', '')
        code = 'class A(object):\n' + \
               '    def __init__(self):\n' + \
               '        self.my_a_var = 10\n' + \
               '    def my_b_func(self):\n' + \
               '        pass\n' + \
               '    def my_c_func(self):\n' + \
               '        pass\n' + \
               'a_var = A()\n' + \
               'a_var.my_'
        result = self.assist.assist(code, len(code))
        sorted_proposals = ProposalSorter(result).get_sorted_proposal_list()
        self.assertEquals('my_b_func', sorted_proposals[0].name)
        self.assertEquals('my_c_func', sorted_proposals[1].name)
        self.assertEquals('my_a_var', sorted_proposals[2].name)

    def test_proposals_sorter_for_global_methods_and_funcs(self):
        code = 'def my_b_func(self):\n' + \
               '    pass\n' + \
               'my_a_var = 10\n' + \
               'my_'
        result = self.assist.assist(code, len(code))
        sorted_proposals = ProposalSorter(result).get_sorted_proposal_list()
        self.assertEquals('my_b_func', sorted_proposals[0].name)
        self.assertEquals('my_a_var', sorted_proposals[1].name)

    def test_proposals_sorter_underlined_methods(self):
        self.assist.add_template('my_sample_template', '')
        code = 'class A(object):\n' + \
               '    def _my_func(self):\n' + \
               '        self.my_a_var = 10\n' + \
               '    def my_func(self):\n' + \
               '        pass\n' + \
               'a_var = A()\n' + \
               'a_var.'
        result = self.assist.assist(code, len(code))
        sorted_proposals = ProposalSorter(result).get_sorted_proposal_list()
        self.assertEquals('my_func', sorted_proposals[0].name)
        self.assertEquals('_my_func', sorted_proposals[1].name)

    def test_get_pydoc_for_functions(self):
        src = 'def a_func():\n    """a function"""\n' \
              '    a_var = 10\na_func()'
        self.assertTrue(self.assist.get_doc(src, len(src) - 4).endswith('a function'))
        self.assist.get_doc(src, len(src) - 4).index('a_func()')

    def test_get_pydoc_for_classes(self):
        src = 'class AClass(object):\n    pass\n'
        self.assist.get_doc(src, src.index('AClass') + 1).index('AClass')

    def test_get_pydoc_for_classes_with_init(self):
        src = 'class AClass(object):\n    def __init__(self):\n        pass\n'
        self.assist.get_doc(src, src.index('AClass') + 1).index('AClass')

    def test_get_pydoc_for_modules(self):
        pycore = self.project.get_pycore()
        mod = pycore.create_module(self.project.root, 'mod')
        mod.write('"""a module"""\n')
        src = 'import mod\nmod'
        self.assertEquals('a module', self.assist.get_doc(src, len(src) - 1))

    def test_get_pydoc_for_builtins(self):
        src = 'print(object)\n'
        self.assertTrue(self.assist.get_doc(src, src.index('obj')) is not None)

    def test_get_pydoc_for_methods_should_include_class_name(self):
        src = 'class AClass(object):\n    def a_method(self):\n'\
              '        """hey"""\n        pass\n'
        doc = self.assist.get_doc(src, src.index('a_method') + 1)
        doc.index('AClass.a_method')
        doc.index('hey')

    def test_get_pydoc_for_methods_should_include_methods_from_super_classes(self):
        src = 'class A(object):\n    def a_method(self):\n' \
              '        """hey1"""\n        pass\n' \
              'class B(A):\n    def a_method(self):\n' \
              '        """hey2"""\n        pass\n'
        doc = self.assist.get_doc(src, src.rindex('a_method') + 1)
        doc.index('A.a_method')
        doc.index('hey1')
        doc.index('B.a_method')
        doc.index('hey2')

    def test_get_pydoc_for_classes_should_name_super_classes(self):
        src = 'class A(object):\n    pass\n' \
              'class B(A):\n    pass\n'
        doc = self.assist.get_doc(src, src.rindex('B') + 1)
        doc.index('B(A)')

    def test_get_pydoc_for_builtin_functions(self):
        src = 's = "hey"\ns.replace\n'
        doc = self.assist.get_doc(src, src.rindex('replace') + 1)
        self.assertTrue(doc is not None)

    # TODO: should comment till the end of scope and not block
    def xxx_test_not_proposing_variables_defined_till_the_end_of_scope(self):
        code = 'if True:\n    a_v\na_var = 10\n'
        result = self.assist.assist(code, code.index('a_v') + 3)
        self.assert_completion_not_in_result('a_var', 'global', result)

    def test_completing_in_uncomplete_try_blocks(self):
        code = 'try:\n    a_var = 10\n    a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_in_uncomplete_try_blocks_in_functions(self):
        code = 'def a_func():\n    try:\n        a_var = 10\n        a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'local', result)

    def test_already_complete_try_blocks_with_finally(self):
        code = 'def a_func():\n    try:\n        a_var = 10\n        a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'local', result)

    def test_already_complete_try_blocks_with_finally2(self):
        code = 'try:\n    a_var = 10\n    a_\nfinally:\n    pass\n'
        result = self.assist.assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_already_complete_try_blocks_with_except(self):
        code = 'try:\n    a_var = 10\n    a_\nexcept Exception:\n    pass\n'
        result = self.assist.assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_already_complete_try_blocks_with_except2(self):
        code = 'a_var = 10\ntry:\n    another_var = a_\n    another_var = 10\n' \
               'except Exception:\n    pass\n'
        result = self.assist.assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_ifs_in_uncomplete_try_blocks(self):
        code = 'try:\n    if True:\n        a_var = 10\n    a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_ifs_in_uncomplete_try_blocks2(self):
        code = 'try:\n    if True:\n        a_var = 10\n        a_'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_excepts_in_uncomplete_try_blocks(self):
        code = 'try:\n    pass\nexcept Exc'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('Exception', 'builtin', result)

    def test_nested_blocks(self):
        code = 'a_var = 10\ntry:\n    try:\n        a_v'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_var', 'global', result)

    def test_proposing_function_keywords_when_calling(self):
        code = 'def f(p):\n    pass\nf(p'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_for_non_functions(self):
        code = 'f = 1\nf(p'
        result = self.assist.assist(code, len(code))

    def test_proposing_function_keywords_when_calling_extra_spaces(self):
        code = 'def f(p):\n    pass\nf( p'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_on_second_argument(self):
        code = 'def f(p1, p2):\n    pass\nf(1, p'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('p2=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_not_proposing_args(self):
        code = 'def f(p1, *args):\n    pass\nf(1, a'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('args=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_with_no_nothing_after_parens(self):
        code = 'def f(p):\n    pass\nf('
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_with_no_nothing_after_parens2(self):
        code = 'def f(p):\n    pass\ndef g():\n    h = f\n    f('
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_codeassists_before_opening_of_parens(self):
        code = 'def f(p):\n    pass\na_var = 1\nf(1)\n'
        result = self.assist.assist(code, code.rindex('f') + 1)
        self.assert_completion_not_in_result('a_var', 'global', result)


class CodeAssistInProjectsTest(unittest.TestCase):

    def setUp(self):
        super(CodeAssistInProjectsTest, self).setUp()
        self.project = testutils.sample_project()
        self.assist = PythonCodeAssist(self.project)
        self.pycore = self.project.get_pycore()
        samplemod = self.pycore.create_module(self.project.root, 'samplemod')
        samplemod.write("class SampleClass(object):\n    def sample_method():\n        pass" + \
                        "\n\ndef sample_func():\n    pass\nsample_var = 10\n" + \
                        "\ndef _underlined_func():\n    pass\n\n")
        package = self.pycore.create_package(self.project.root, 'package')
        nestedmod = self.pycore.create_module(package, 'nestedmod')

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
        testutils.remove_project(self.project)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        code = 'import samplemod\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('samplemod', 'global', result)

    def test_from_import_class(self):
        code = 'from samplemod import SampleClass\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'global', result)

    def test_from_import_function(self):
        code = 'from samplemod import sample_func\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_func', 'global', result)

    def test_from_import_variable(self):
        code = 'from samplemod import sample_var\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_var', 'global', result)

    def test_from_imports_inside_functions(self):
        code = 'def f():\n    from samplemod import SampleClass\n    Sample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'local', result)

    def test_from_import_only_imports_imported(self):
        code = 'from samplemod import sample_func\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('SampleClass', 'global', result)

    def test_from_import_star(self):
        code = 'from samplemod import *\nSample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'global', result)

    def test_from_import_star2(self):
        code = 'from samplemod import *\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_func', 'global', result)
        self.assert_completion_in_result('sample_var', 'global', result)

    def test_from_import_star_not_imporing_underlined(self):
        code = 'from samplemod import *\n_under'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('_underlined_func', 'global', result)

    def test_from_package_import_mod(self):
        code = 'from package import nestedmod\nnest'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('nestedmod', 'global', result)

    def test_from_package_import_star(self):
        code = 'from package import *\nnest'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('nestedmod', 'global', result)

    def test_completing_after_dot(self):
        code = 'class SampleClass(object):\n    def sample_method(self):\n        pass\nSampleClass.sam'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_method', 'attribute', result)

    def test_completing_after_multiple_dots(self):
        code = 'class Class1(object):\n    class Class2(object):\n        def sample_method(self):\n' + \
               '            pass\nClass1.Class2.sam'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_method', 'attribute', result)

    def test_completing_after_self_dot(self):
        code = 'class Sample(object):\n    def method1(self):\n        pass\n' + \
               '    def method2(self):\n        self.m'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('method1', 'attribute', result)

    def test_result_start_offset_for_dotted_completions(self):
        code = 'class Sample(object):\n    def method1(self):\n        pass\n' + \
               'Sample.me'
        result = self.assist.assist(code, len(code))
        self.assertEquals(len(code) - 2, result.start_offset)

    def test_backslash_after_dots(self):
        code = 'class Sample(object):\n    def a_method(self):\n        pass\n' + \
               'Sample.\\\n       a_m'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('a_method', 'attribute', result)

    def test_not_proposing_global_names_after_dot(self):
        code = 'class Sample(object):\n    def a_method(self):\n        pass\n' + \
               'Sample.'
        result = self.assist.assist(code, len(code))
        self.assert_completion_not_in_result('Sample', 'global', result)

    def test_assist_on_relative_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod1.write('def a_func():\n    pass\n')
        code = 'import mod1\nmod1.'
        result = self.assist.assist(code, len(code), mod2)
        self.assert_completion_in_result('a_func', 'attribute', result)

    def test_get_location_on_relative_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod1.write('def a_func():\n    pass\n')
        code = 'import mod1\nmod1.a_func\n'
        result = self.assist.get_definition_location(code, len(code) - 2, mod2)
        self.assertEquals((mod1, 1), result)

    def test_get_doc_on_relative_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod1.write('def a_func():\n    """hey"""\n    pass\n')
        code = 'import mod1\nmod1.a_func\n'
        result = self.assist.get_doc(code, len(code) - 2, mod2)
        self.assertTrue(result.endswith('hey'))

    def test_finding_occurrences(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('a_var = 1\n')
        result = self.assist.find_occurrences(mod, 1)
        self.assertEquals([(mod, 0)], result)

    def test_finding_occurrences_in_more_than_one_module(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod1.write('a_var = 1\n')
        mod2.write('import mod1\nmy_var = mod1.a_var')
        result = self.assist.find_occurrences(mod1, 1)
        self.assertEquals(2, len(result))
        self.assertTrue((mod1, 0) in result and (mod2, mod2.read().index('a_var')) in result)


class TemplateTest(unittest.TestCase):

    def test_template_get_variables(self):
        template = Template('Name = ${name}')
        self.assertEquals(['name'], template.variables())

    def test_template_get_variables_multiple_variables(self):
        template = Template('Name = ${name}\nAge = ${age}\n')
        self.assertEquals(['name', 'age'], template.variables())

    def test_substitution(self):
        template = Template('Name = ${name}\nAge = ${age}\n')
        self.assertEquals('Name = Ali\nAge = 20\n',
                          template.substitute({'name': 'Ali', 'age': '20'}))

    def test_underlined_variables(self):
        template = Template('Name = ${name_var}')
        self.assertEquals(['name_var'], template.variables())
        self.assertEquals('Name = Ali', template.substitute({'name_var': 'Ali'}))

    @testutils.assert_raises(KeyError)
    def test_unmapped_variable(self):
        template = Template('Name = ${name}')
        template.substitute({})

    def test_double_dollar_sign(self):
        template = Template('Name = $${name}')
        self.assertEquals([], template.variables())
        self.assertEquals('Name = ${name}', template.substitute({'name': 'Ali'}))

    def test_untemplate_dollar_signs(self):
        template = Template('$name = ${value}')
        self.assertEquals(['value'], template.variables())
        self.assertEquals('$name = Ali', template.substitute({'value': 'Ali'}))

    def test_template_get_variables_multiple_variables2(self):
        template = Template('Name = ${name}${age}\n')
        self.assertEquals(['name', 'age'], template.variables())

    def test_template_get_variables_start_of_the_string(self):
        template = Template('${name}\n')
        self.assertEquals(['name'], template.variables())

    def test_the_same_variable_many_times(self):
        template = Template("Today is ${today}, the day after ${today} is ${tomorrow}")
        self.assertEquals(['today', 'tomorrow'], template.variables())
        self.assertEquals("Today is 26th, the day after 26th is 27th",
                         template.substitute({'today': '26th', 'tomorrow': '27th'}))

    def test_cursor_in_templates(self):
        template = Template('My name is ${name}${cursor}.')
        self.assertEquals(['name'], template.variables())
        self.assertEquals('My name is Ali.', template.substitute({'name': 'Ali'}))

    def test_get_cursor_location(self):
        template = Template('My name is ${name}${cursor}.')
        self.assertEquals(14, template.get_cursor_location({'name': 'Ali'}))

    def test_get_cursor_location_with_no_cursor(self):
        template = Template('My name is ${name}.')
        self.assertEquals(15, template.get_cursor_location({'name': 'Ali'}))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(CodeAssistTest))
    result.addTests(unittest.makeSuite(CodeAssistInProjectsTest))
    result.addTests(unittest.makeSuite(TemplateTest))
    return result

if __name__ == '__main__':
    unittest.main()
