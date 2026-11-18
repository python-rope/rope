import sys
import unittest
from textwrap import dedent, indent

from rope.base import builtins, pyobjects
from rope.base.oi.type_hinting import evaluate, utils
from rope.contrib.codeassist import code_assist
from ropetest import testutils


class AbstractHintingTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _assist(self, code, offset=None, resource=None, **kwds):
        if offset is None:
            offset = len(code)
        return code_assist(self.project, code, offset, resource, **kwds)

    def assert_completion_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                return
        self.fail(
            "completion <%s> in scope %r not proposed, available names: %r"
            % (name, scope, [(i.name, i.scope) for i in result])
        )

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail("completion <%s> was proposed" % name)

    def run(self, result=None):
        if self.__class__.__name__.startswith("Abstract"):
            return
        super().run(result)


class UnionAlternativeHintingTest(AbstractHintingTest):
    def test_unresolved_alternative_keeps_the_complete_union_unresolved(self):
        resource = testutils.create_module(self.project, "union_hint")
        resource.write("import types\nclass Known:\n    marker = 1\n")
        module = self.project.get_pymodule(resource)
        for hint in ("Known | types.Missing", "types.Missing | Known", "Known or types.Missing"):
            with self.subTest(hint=hint):
                self.assertIsNone(evaluate.evaluate(hint, module))

    def test_resolved_none_type_remains_a_native_union_alternative(self):
        resource = testutils.create_module(self.project, "union_hint")
        resource.write("import types\nclass Known:\n    marker = 1\n")
        module = self.project.get_pymodule(resource)
        none_type = utils.resolve_type("types.NoneType", module)
        self.assertIsNotNone(none_type)
        self.assertTrue(builtins._is_runtime_class(none_type, type(None)))
        result = evaluate.evaluate("Known | types.NoneType", module)
        self.assertIs(result.alternatives[1], none_type)
        self.assertIn("marker", result.get_attributes())


class SourceAnnotationHintingTest(AbstractHintingTest):
    def test_unresolved_annotation_is_the_unknown_sentinel(self):
        resource = testutils.create_module(self.project, 'unresolved_annotation')
        resource.write("def choose(value: Missing) -> Missing:\n    return value\n")
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(pyobjects.get_unknown(), function.get_parameters()['value'].get_object())
        self.assertIs(pyobjects.get_unknown(), function.get_returned_object(None))

    def test_sequence_invalid_arity_is_not_a_guessed_element_contract(self):
        code = (
            "from collections.abc import Sequence\n"
            "def choose(items: Sequence[str, int]):\n    return items[0]\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual('real', namespace['choose'](['real']))
        resource = testutils.create_module(self.project, 'invalid_sequence_arity')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertEqual(pyobjects.get_unknown(), function.get_parameters()['items'].get_object())

    def test_mutable_sequence_is_not_claimed_as_read_only_sequence(self):
        code = (
            "from typing import MutableSequence\n"
            "def choose(items: MutableSequence[str]):\n    items.append('real')\n"
        )
        namespace = {}
        exec(code, namespace)
        values = []
        namespace['choose'](values)
        self.assertEqual(['real'], values)
        resource = testutils.create_module(self.project, 'mutable_sequence')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertEqual(pyobjects.get_unknown(), function.get_parameters()['items'].get_object())

    def test_sequence_tuple_annotation_preserves_element_positions(self):
        for origin in ('collections.abc', 'typing'):
            with self.subTest(origin=origin):
                code = (
                    f"from {origin} import Sequence\n"
                    "class Row:\n"
                    "    @property\n    def label(self) -> str:\n        return 'real'\n"
                    "def choose(items: Sequence[tuple[str, Row]]):\n"
                    "    for _, row in items:\n        return row.label\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertEqual('real', namespace['choose']([('key', namespace['Row']())]))
                resource = testutils.create_module(self.project, 'sequence_' + origin.replace('.', '_'))
                resource.write(code)
                function = self.project.get_pymodule(resource)['choose'].get_object()
                returned = function.get_returned_object(None)
                self.assertIsNotNone(returned)
                self.assertIs(builtins.get_str_type(), returned.get_type())

    def test_sequence_slicing_preserves_read_only_element_contract(self):
        code = (
            "from collections.abc import Sequence\n"
            "class Row:\n"
            "    @property\n    def label(self) -> str:\n        return 'real'\n"
            "def choose(items: Sequence[Row]):\n    return items[:1][0].label\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual('real', namespace['choose']([namespace['Row']()]))
        resource = testutils.create_module(self.project, 'sequence_slice')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        parameter = function.get_parameters()['items'].get_object()
        self.assertIn('__getitem__', parameter)
        self.assertNotIn('append', parameter)
        self.assertNotIn('__setitem__', parameter)
        returned = function.get_returned_object(None)
        self.assertIsNotNone(returned)
        self.assertIs(builtins.get_str_type(), returned.get_type())

    def test_fixed_tuple_annotation_does_not_collapse_to_first_element(self):
        code = "def choose(items: tuple[str, int]):\n    return items[1]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose'](('key', 7)))
        resource = testutils.create_module(self.project, 'tuple_positions')
        resource.write(code)
        returned = self.project.get_pymodule(resource)['choose'].get_object().get_returned_object(None)
        self.assertIs(builtins.builtins['int'].get_object(), returned.get_type())

    def test_local_sequence_keeps_its_actual_iteration_contract(self):
        code = (
            "class Sequence:\n"
            "    @classmethod\n    def __class_getitem__(cls, item):\n        return cls\n"
            "    def __iter__(self):\n        return iter([7])\n"
            "def choose(items: Sequence[str]):\n    return next(iter(items))\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose'](namespace['Sequence']()))
        resource = testutils.create_module(self.project, 'local_sequence')
        resource.write(code)
        returned = self.project.get_pymodule(resource)['choose'].get_object().get_returned_object(None)
        self.assertIs(builtins.builtins['int'].get_object(), returned.get_type())

    def test_class_annotation_uses_lexical_sequence_binding(self):
        for declaration, annotation in (
            ("Sequence = Local", "Sequence[str]"),
            ("class types:\n        Sequence = Local", "types.Sequence[str]"),
        ):
            with self.subTest(annotation=annotation):
                code = (
                    "from typing import Sequence\n"
                    "import typing as types\n"
                    "class Local:\n"
                    "    @classmethod\n    def __class_getitem__(cls, item):\n        return cls\n"
                    "    def __getitem__(self, key):\n        return 7\n"
                    "class Owner:\n"
                    f"    {declaration}\n"
                    f"    def choose(self, items: {annotation}):\n        return items[0]\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertEqual(7, namespace['Owner']().choose(namespace['Local']()))
                resource = testutils.create_module(self.project, 'lexical_sequence_' + annotation.replace('.', '_').replace('[', '_').replace(']', ''))
                resource.write(code)
                module = self.project.get_pymodule(resource)
                function = module['Owner'].get_object()['choose'].get_object()
                parameter = function.get_parameters()['items'].get_object()
                self.assertIs(module['Local'].get_object(), parameter.get_type())
                self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_fixed_tuple_dynamic_index_does_not_invent_first_type(self):
        code = "def choose(items: tuple[str, int], index: int):\n    return items[index]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose'](('key', 7), 1))
        resource = testutils.create_module(self.project, 'tuple_dynamic_index')
        resource.write(code)
        returned = self.project.get_pymodule(resource)['choose'].get_object().get_returned_object(None)
        self.assertEqual(pyobjects.get_unknown(), returned)

    def test_fixed_tuple_explicit_getitem_does_not_invent_first_type(self):
        code = "def choose(items: tuple[str, int], index: int):\n    return items.__getitem__(index)\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose'](('key', 7), 1))
        resource = testutils.create_module(self.project, 'tuple_explicit_getitem')
        resource.write(code)
        returned = self.project.get_pymodule(resource)['choose'].get_object().get_returned_object(None)
        self.assertEqual(pyobjects.get_unknown(), returned)

    def test_fixed_tuple_slices_preserve_positions_or_remain_unknown(self):
        cases = (("[1:][0]", 7, 'int'), ("[::-1][0]", 7, 'int'), ("[:1][0]", 'key', 'str'), ("[index:][0]", 7, None))
        for number, (expression, expected, inferred) in enumerate(cases):
            with self.subTest(expression=expression):
                code = f"def choose(items: tuple[str, int], index: int):\n    return items{expression}\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(expected, namespace['choose'](('key', 7), 1))
                resource = testutils.create_module(self.project, 'tuple_slice_' + str(number))
                resource.write(code)
                returned = self.project.get_pymodule(resource)['choose'].get_object().get_returned_object(None)
                if inferred is None:
                    self.assertEqual(pyobjects.get_unknown(), returned)
                else:
                    self.assertIs(builtins.builtins[inferred].get_object(), returned.get_type())

    def test_eager_annotation_preserves_declaration_epoch(self):
        for number, code in enumerate((
            "Type = int\ndef choose(value: Type):\n    return value\nType = str\n",
            "Other = int\nType = Other\ndef choose(value: Type):\n    return value\nOther = str\n",
            "class Owner:\n    Type = int\n    def choose(self, value: Type):\n        return value\n    Type = str\n",
        )):
            with self.subTest(number=number):
                namespace = {}
                exec(code, namespace)
                function = namespace['choose'] if 'choose' in namespace else namespace['Owner'].choose
                # Eager before 3.14; PEP 649 evaluates after the module ran.
                actual = function.__annotations__['value']
                self.assertIs(int if sys.version_info < (3, 14) or number == 1 else str, actual)
                expected = {int: builtins.builtins['int'].get_object(), str: builtins.get_str_type()}[actual]
                resource = testutils.create_module(self.project, 'eager_annotation_' + str(number))
                resource.write(code)
                module = self.project.get_pymodule(resource)
                function = module['choose'].get_object() if 'choose' in module else module['Owner'].get_object()['choose'].get_object()
                self.assertIs(expected, function.get_parameters()['value'].get_object().get_type())

    def test_postponed_annotation_keeps_late_binding(self):
        code = "from __future__ import annotations\nType = int\ndef choose(value: Type):\n    return value\nType = str\n"
        namespace = {}
        exec(code, namespace)
        import typing
        self.assertIs(str, typing.get_type_hints(namespace['choose'], namespace)['value'])
        resource = testutils.create_module(self.project, 'postponed_annotation')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(builtins.get_str_type(), function.get_parameters()['value'].get_object().get_type())

    def test_string_annotation_keeps_late_binding(self):
        code = "Type = int\ndef choose(value: 'Type'):\n    return value\nType = str\n"
        namespace = {}
        exec(code, namespace)
        import typing
        self.assertIs(str, typing.get_type_hints(namespace['choose'], namespace)['value'])
        resource = testutils.create_module(self.project, 'string_annotation')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(builtins.get_str_type(), function.get_parameters()['value'].get_object().get_type())

    def test_shadowed_annotated_is_not_unwrapped_as_stdlib(self):
        code = (
            "from typing import Annotated\n"
            "class Local:\n"
            "    @classmethod\n    def __class_getitem__(cls, item):\n        return cls\n"
            "class Owner:\n    Annotated = Local\n"
            "    def choose(self, value: Annotated[str, 'label']):\n        return value\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertIs(namespace['Local'], namespace['Owner'].choose.__annotations__['value'])
        resource = testutils.create_module(self.project, 'shadowed_annotated')
        resource.write(code)
        module = self.project.get_pymodule(resource)
        function = module['Owner'].get_object()['choose'].get_object()
        self.assertIs(module['Local'].get_object(), function.get_parameters()['value'].get_object().get_type())

    def test_typing_wrappers_do_not_become_function_parameter_types(self):
        for number, (hint, expected) in enumerate((('Annotated[str, "label"]', 'str'), ('Optional[str]', None))):
            with self.subTest(hint=hint):
                code = f"from typing import Annotated, Optional\ndef choose(value: {hint}):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual('real', namespace['choose']('real'))
                resource = testutils.create_module(self.project, 'typing_wrapper_' + str(number))
                resource.write(code)
                function = self.project.get_pymodule(resource)['choose'].get_object()
                parameter = function.get_parameters()['value'].get_object()
                if expected:
                    self.assertIs(builtins.get_str_type(), parameter.get_type())
                else:
                    self.assertFalse(isinstance(parameter, pyobjects.AbstractFunction))
                    self.assertFalse(isinstance(parameter.get_type(), pyobjects.AbstractFunction))
                    if parameter != pyobjects.get_unknown():
                        self.assertIsInstance(parameter.get_type(), evaluate.UnionType)

    def test_nested_forward_references_use_late_module_epoch(self):
        import typing
        for number, hint in enumerate(("list['Type']", "Optional['Type']", "Choice['Type']")):
            with self.subTest(hint=hint):
                code = (
                    "from typing import Optional\nType = int\nChoice = list\n"
                    f"def choose(value: {hint}):\n    return value\n"
                    "Type = str\nChoice = tuple\n"
                )
                namespace = {}
                exec(code, namespace)
                actual = typing.get_type_hints(namespace['choose'], namespace)['value']
                if sys.version_info >= (3, 11) or number == 1:
                    # get_type_hints resolves strings nested in builtin
                    # generics since 3.11; 3.10 leaves list['Type'] as is.
                    self.assertIn(str, typing.get_args(actual))
                self.assertEqual(['real'], namespace['choose'](['real']))
                resource = testutils.create_module(self.project, 'nested_forward_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                if number == 1:
                    self.assertIsInstance(parameter.get_type(), evaluate.UnionType)
                    self.assertIs(builtins.get_str_type(), parameter.get_type().alternatives[0])
                else:
                    # `Choice` itself is read eagerly before 3.14 (list) and
                    # after the module ran under PEP 649 (tuple).
                    container = {list: builtins.List, tuple: builtins.Tuple}[typing.get_origin(actual)]
                    self.assertIsInstance(parameter.get_type(), container)
                    element = parameter.get_type().get_holding_objects()[0]
                    self.assertIs(builtins.get_str_type(), element.get_type())

    def test_class_nested_forward_reference_uses_function_globals(self):
        import typing
        code = (
            "Type = int\nclass Owner:\n    Type = bytes\n"
            "    def choose(self, value: list['Type']):\n        return value\n"
            "    Type = tuple\nType = str\n"
        )
        namespace = {}
        exec(code, namespace)
        hint = typing.get_type_hints(namespace['Owner'].choose, namespace)['value']
        # get_type_hints resolves strings nested in builtin generics since 3.11.
        self.assertEqual(list[str] if sys.version_info >= (3, 11) else list['Type'], hint)
        resource = testutils.create_module(self.project, 'class_nested_forward')
        resource.write(code)
        function = self.project.get_pymodule(resource)['Owner'].get_object()['choose'].get_object()
        parameter = function.get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), builtins.List)
        self.assertIs(builtins.get_str_type(), parameter.get_type().holding.get_type())

    def test_annotated_metadata_never_becomes_type_syntax(self):
        import typing
        for number, hint in enumerate((
            "Annotated[int, 'label] | str']",
            "Annotated[int, ('metadata', 'Optional[str]')]",
            '\"Annotated[int, \'label] | str\']\"',
        )):
            with self.subTest(hint=hint):
                code = f"from typing import Annotated\ndef choose(value: {hint}):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertIs(int, typing.get_type_hints(namespace['choose'], namespace)['value'])
                self.assertEqual(7, namespace['choose'](7))
                resource = testutils.create_module(self.project, 'annotated_metadata_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertIs(builtins.builtins['int'].get_object(), parameter.get_type())

    def test_custom_class_subscription_uses_native_dispatch(self):
        code = (
            "class Local:\n    @classmethod\n    def __class_getitem__(cls, key):\n        return int\n"
            "def choose(value: Local[str]):\n    return value\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertIs(int, namespace['choose'].__annotations__['value'])
        resource = testutils.create_module(self.project, 'custom_class_subscription')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertIs(builtins.builtins['int'].get_object(), parameter.get_type())

    def test_metaclass_subscription_uses_native_dispatch(self):
        code = (
            "class Meta(type):\n    def __getitem__(cls, key):\n        return int\n"
            "class Local(metaclass=Meta): pass\n"
            "def choose(value: Local[str]):\n    return value\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertIs(int, namespace['choose'].__annotations__['value'])
        resource = testutils.create_module(self.project, 'metaclass_subscription')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertIs(builtins.builtins['int'].get_object(), parameter.get_type())

    def test_metaclass_union_overrides_do_not_become_native_unions(self):
        for number, (method, expression) in enumerate((('__or__', 'Local | str'), ('__ror__', 'str | Local'))):
            with self.subTest(method=method):
                code = (
                    f"class Parent(type):\n    def {method}(cls, other):\n        return int\n"
                    "class Meta(Parent): pass\nclass Local(metaclass=Meta): pass\n"
                    f"def choose(value: {expression}):\n    return value\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertIs(int, namespace['choose'].__annotations__['value'])
                resource = testutils.create_module(self.project, 'custom_class_union_' + str(number))
                resource.write(code)
                module = self.project.get_pymodule(resource)
                parameter = module['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)
                self.assertIsNone(evaluate.evaluate(expression, module))

    def test_inherited_native_union_operators_keep_metaclass_support(self):
        code = (
            "class Meta(type): pass\nclass Local(metaclass=Meta): pass\n"
            "def choose(value: Local | str):\n    return value\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace['Local'], str), namespace['choose'].__annotations__['value'].__args__)
        resource = testutils.create_module(self.project, 'native_metaclass_union')
        resource.write(code)
        module = self.project.get_pymodule(resource)
        parameter = module['choose'].get_object().get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), evaluate.UnionType)
        self.assertIs(module['Local'].get_object(), parameter.get_type().alternatives[0])

    def test_instance_alias_union_is_not_a_type_union(self):
        for number, (method, expression) in enumerate((('__or__', 'Alias | str'), ('__ror__', 'str | Alias'))):
            with self.subTest(method=method):
                code = (
                    f"class Form:\n    def {method}(self, other):\n        return int\n"
                    "Alias = Form()\n"
                    f"def choose(value: {expression}):\n    return value\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertIs(int, namespace['choose'].__annotations__['value'])
                resource = testutils.create_module(self.project, 'instance_alias_union_' + str(number))
                resource.write(code)
                module = self.project.get_pymodule(resource)
                parameter = module['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)
                self.assertIsNone(evaluate.evaluate(expression, module))

    def test_native_parameterized_alias_union_preserves_element_type(self):
        import typing
        code = "def choose(value: list[str] | None):\n    return value\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual((list[str], type(None)), typing.get_args(namespace['choose'].__annotations__['value']))
        self.assertEqual(['real'], namespace['choose'](['real']))
        resource = testutils.create_module(self.project, 'native_parameterized_union')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), evaluate.UnionType)
        sequence = parameter.get_type().alternatives[0]
        if not isinstance(sequence, pyobjects.AbstractClass):
            sequence = sequence.get_type()
        self.assertIsInstance(sequence, builtins.List)
        self.assertIs(builtins.get_str_type(), sequence.holding.get_type())
        self.assertTrue(builtins._is_runtime_class(parameter.get_type().alternatives[1], type(None)))

    def test_named_generic_alias_materializes_native_parameter(self):
        for number, declaration in enumerate(("Rows = list[str]", "Rows = list[str]\nOther = Rows\nRows = Other")):
            with self.subTest(declaration=declaration):
                code = declaration + "\ndef choose(value: Rows):\n    return value[0].strip()\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual('real', namespace['choose']([' real ']))
                self.assertEqual((str,), namespace['choose'].__annotations__['value'].__args__)
                resource = testutils.create_module(self.project, 'named_generic_alias_' + str(number))
                resource.write(code)
                function = self.project.get_pymodule(resource)['choose'].get_object()
                parameter = function.get_parameters()['value'].get_object()
                self.assertNotIsInstance(parameter, builtins.GenericAlias)
                self.assertIsInstance(parameter.get_type(), builtins.List)
                self.assertIs(builtins.get_str_type(), parameter.get_type().holding.get_type())
                self.assertIs(builtins.get_str_type(), function.get_returned_object(None).get_type())

    def test_qualified_generic_alias_materializes_native_parameter(self):
        import subprocess
        import sys
        source = testutils.create_module(self.project, 'row_types')
        source.write("Rows = list[str]\n")
        resource = testutils.create_module(self.project, 'qualified_generic_alias')
        resource.write("import row_types as t\ndef choose(value: t.Rows):\n    return value[0].strip()\n")
        execution = subprocess.run(
            [sys.executable, '-c', "from qualified_generic_alias import choose; assert choose([' real ']) == 'real'; assert choose.__annotations__['value'] == list[str]"],
            cwd=self.project.address, capture_output=True, text=True,
        )
        self.assertEqual(0, execution.returncode, execution.stderr)
        self.assertEqual('', execution.stderr)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        parameter = function.get_parameters()['value'].get_object()
        self.assertNotIsInstance(parameter, builtins.GenericAlias)
        self.assertIsInstance(parameter.get_type(), builtins.List)
        self.assertIs(builtins.get_str_type(), parameter.get_type().holding.get_type())
        self.assertIs(builtins.get_str_type(), function.get_returned_object(None).get_type())

    def test_nested_generic_alias_preserves_native_holdings(self):
        code = "Rows = list[tuple[str, int]]\ndef choose(value: Rows):\n    return value[0][1]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose']([('key', 7)]))
        resource = testutils.create_module(self.project, 'nested_generic_alias')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        parameter = function.get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), builtins.List)
        pair = parameter.get_type().holding
        self.assertNotIsInstance(pair, builtins.GenericAlias)
        self.assertIsInstance(pair.get_type(), builtins.Tuple)
        self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_named_generic_union_alias_preserves_none_alternative(self):
        import typing
        code = "Rows = list[str]\nMaybe = Rows | None\ndef choose(value: Maybe):\n    return value\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual((list[str], type(None)), typing.get_args(namespace['choose'].__annotations__['value']))
        self.assertIsNone(namespace['choose'](None))
        self.assertEqual(['real'], namespace['choose'](['real']))
        resource = testutils.create_module(self.project, 'named_generic_union_alias')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), evaluate.UnionType)
        sequence, none_type = parameter.get_type().alternatives
        self.assertIsInstance(sequence, builtins.List)
        self.assertIs(builtins.get_str_type(), sequence.holding.get_type())
        self.assertTrue(builtins._is_runtime_class(none_type, type(None)))

    def test_generic_alias_with_unproven_argument_remains_unknown(self):
        code = "Rows = list['Missing']\ndef choose(value: Rows):\n    return value\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(['real'], namespace['choose'](['real']))
        resource = testutils.create_module(self.project, 'unproven_generic_alias')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertEqual(pyobjects.get_unknown(), parameter)
        self.assertNotIsInstance(parameter, builtins.GenericAlias)

    def test_mutable_type_choices_do_not_invent_selected_alias(self):
        cases = (
            ("Choices = [list[str], list[int]]", "Choices[1]"),
            ("Choices = [list[str]]\nChoices[0] = list[int]", "Choices[0]"),
            ("Choices = [list[str]]\nChoices[0] = list[int]", "Choices.pop()"),
            ("Choices = [list[str]]\nChoices[0] = list[int]", "next(iter(Choices))"),
            ("Choices = []\nChoices.append(list[str])\nChoices[0] = list[int]", "Choices[0]"),
        )
        for number, (declaration, selection) in enumerate(cases):
            with self.subTest(selection=selection, declaration=declaration):
                code = declaration + f"\nRows = {selection}\ndef choose(value: Rows):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
                self.assertEqual([7], namespace['choose']([7]))
                resource = testutils.create_module(self.project, 'mutable_type_choices_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_mutable_class_choices_do_not_invent_selected_type(self):
        code = "Choices = [str, int]\nSelected = Choices[1]\ndef choose(value: Selected):\n    return value\n"
        namespace = {}
        exec(code, namespace)
        self.assertIs(int, namespace['choose'].__annotations__['value'])
        self.assertEqual(7, namespace['choose'](7))
        resource = testutils.create_module(self.project, 'mutable_class_choices')
        resource.write(code)
        parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
        self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_immutable_type_choices_keep_exact_tuple_position(self):
        code = "Choices = (list[str], list[int])\nRows = Choices[1]\ndef choose(value: Rows):\n    return value[0]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
        self.assertEqual(7, namespace['choose']([7]))
        resource = testutils.create_module(self.project, 'immutable_type_choices')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        parameter = function.get_parameters()['value'].get_object()
        self.assertIsInstance(parameter.get_type(), builtins.List)
        self.assertIs(builtins.builtins['int'].get_object(), parameter.get_type().holding.get_type())
        self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_transitive_mutable_alias_paths_remain_unknown(self):
        cases = (
            ("Choices = [(list[str],), (list[int],)]", "Choices[1][0]"),
            ("Choices = [(list[str],)]\nChoices[0] = (list[int],)", "Choices[0][0]"),
            ("Choices = {'rows': list[str]}\nChoices['rows'] = list[int]", "Choices['rows']"),
            ("Choices = ({'rows': list[str]},)\nChoices[0]['rows'] = list[int]", "Choices[0]['rows']"),
            ("Choices = {'rows': (list[str],)}\nChoices['rows'] = (list[int],)", "Choices['rows'][0]"),
            ("Choices = [{'rows': (list[str],)}]\nChoices[0]['rows'] = (list[int],)", "Choices[0]['rows'][0]"),
            ("Choices = set(((list[str],),))\nChoices.remove((list[str],))\nChoices.add((list[int],))", "Choices.pop()[0]"),
        )
        for number, (declaration, selection) in enumerate(cases):
            with self.subTest(selection=selection, declaration=declaration):
                code = declaration + f"\nRows = {selection}\ndef choose(value: Rows):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
                self.assertEqual([7], namespace['choose']([7]))
                resource = testutils.create_module(self.project, 'transitive_mutable_alias_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_nested_immutable_alias_paths_keep_exact_positions(self):
        code = "Choices = ((list[str],), (list[int],))\nRows = Choices[1][0]\ndef choose(value: Rows):\n    return value[0]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
        self.assertEqual(7, namespace['choose']([7]))
        resource = testutils.create_module(self.project, 'nested_immutable_alias')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_mutable_instance_alias_fields_do_not_select_first_instance(self):
        classes = (
            "class Text:\n    Rows = list[str]\nclass Number:\n    Rows = list[int]\n",
            "class Text:\n    @property\n    def Rows(self):\n        return list[str]\nclass Number:\n    @property\n    def Rows(self):\n        return list[int]\n",
            "class TextBase:\n    Rows = list[str]\nclass Text(TextBase): pass\nclass NumberBase:\n    Rows = list[int]\nclass Number(NumberBase): pass\n",
            "class Text:\n    def __init__(self):\n        self.Rows = list[str]\nclass Number:\n    def __init__(self):\n        self.Rows = list[int]\n",
        )
        for number, declarations in enumerate(classes):
            with self.subTest(number=number):
                code = declarations + "Choices = [Text(), Number()]\nRows = Choices[1].Rows\ndef choose(value: Rows):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
                self.assertEqual([7], namespace['choose']([7]))
                resource = testutils.create_module(self.project, 'mutable_instance_alias_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_type_alias_iterator_position_is_not_assumed(self):
        cases = (
            "Choices = iter((list[str], list[int]))\nnext(Choices)\nRows = next(Choices)\n",
            "def choices():\n    yield list[str]\n    yield list[int]\nChoices = choices()\nnext(Choices)\nRows = next(Choices)\n",
            "class Text:\n    Rows = list[str]\nclass Number:\n    Rows = list[int]\nChoices = iter((Text(), Number()))\nnext(Choices)\nRows = next(Choices).Rows\n",
        )
        for number, declarations in enumerate(cases):
            with self.subTest(number=number):
                code = declarations + "def choose(value: Rows):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
                self.assertEqual([7], namespace['choose']([7]))
                resource = testutils.create_module(self.project, 'iterator_alias_position_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_immutable_instance_selection_preserves_exact_field(self):
        code = (
            "class Text:\n    Rows = list[str]\nclass Number:\n    Rows = list[int]\n"
            "Choices = ((Text(),), (Number(),))\nRows = Choices[1][0].Rows\n"
            "def choose(value: Rows):\n    return value[0]\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
        self.assertEqual(7, namespace['choose']([7]))
        resource = testutils.create_module(self.project, 'immutable_instance_alias')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_sampled_receiver_methods_do_not_restore_type_certainty(self):
        declarations = (
            "class Text:\n    def Rows(self):\n        return list[str]\n    def child(self):\n        return self\n"
            "class Number:\n    def Rows(self):\n        return list[int]\n    def child(self):\n        return self\n"
            "def identity(value):\n    return value\n"
        )
        cases = (
            "Choices = [Text(), Number()]\nRows = Choices[1].Rows()",
            "Choices = [Text(), Number()]\nmethod = Choices[1].Rows\nRows = method()",
            "Choices = [Text(), Number()]\nRows = Choices[1].child().Rows()",
            "Choices = [Text(), Number()]\nRows = identity(Choices[1]).Rows()",
            "Choices = [(Text(),), (Number(),)]\nRows = Choices[1][0].Rows()",
            "Choices = iter((Text(), Number()))\nnext(Choices)\nRows = next(Choices).Rows()",
        )
        for number, selection in enumerate(cases):
            with self.subTest(number=number):
                code = declarations + selection + "\ndef choose(value: Rows):\n    return value\n"
                namespace = {}
                exec(code, namespace)
                self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
                self.assertEqual([7], namespace['choose']([7]))
                resource = testutils.create_module(self.project, 'sampled_receiver_method_' + str(number))
                resource.write(code)
                parameter = self.project.get_pymodule(resource)['choose'].get_object().get_parameters()['value'].get_object()
                self.assertEqual(pyobjects.get_unknown(), parameter)

    def test_exact_tuple_receiver_method_preserves_type_alias(self):
        code = (
            "class Text:\n    def Rows(self):\n        return list[str]\n"
            "class Number:\n    def Rows(self):\n        return list[int]\n"
            "Choices = (Text(), Number())\nRows = Choices[1].Rows()\n"
            "def choose(value: Rows):\n    return value[0]\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(list[int], namespace['choose'].__annotations__['value'])
        self.assertEqual(7, namespace['choose']([7]))
        resource = testutils.create_module(self.project, 'exact_receiver_method')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertIs(builtins.builtins['int'].get_object(), function.get_returned_object(None).get_type())

    def test_annotated_parameters_preserve_native_string_methods(self):
        code = (
            "def clean(script: str, /, *, ending: str):\n"
            "    return script.strip().rstrip(ending)\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual("value", namespace['clean'](' value; ', ending=';'))
        resource = testutils.create_module(self.project, 'annotations')
        resource.write(code)
        function = self.project.get_pymodule(resource)['clean'].get_object()
        for name in ('script', 'ending'):
            with self.subTest(name=name):
                parameter = function.get_parameters()[name].get_object()
                self.assertIs(builtins.get_str_type(), parameter.get_type())
                self.assertIn('rstrip', parameter)

    def test_forward_return_annotation_uses_declared_class(self):
        code = "class Label: pass\ndef choose(value) -> 'Label':\n    return value\n"
        namespace = {}
        exec(code, namespace)
        self.assertIsInstance(namespace['choose'](namespace['Label']()), namespace['Label'])
        resource = testutils.create_module(self.project, 'annotations')
        resource.write(code)
        module = self.project.get_pymodule(resource)
        returned = module['choose'].get_object().get_returned_object(None)
        self.assertIs(module['Label'].get_object(), returned.get_type())

    def test_unresolved_source_annotation_does_not_adopt_docstring_type(self):
        code = (
            "def choose(value: 'Missing'):\n"
            "    '''\n    :type value: str\n    '''\n"
            "    return value\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['choose'](7))
        resource = testutils.create_module(self.project, 'annotations')
        resource.write(code)
        function = self.project.get_pymodule(resource)['choose'].get_object()
        self.assertEqual(pyobjects.get_unknown(), function.get_parameters()['value'].get_object())


class DocstringParamHintingTest(AbstractHintingTest):
    def test_hint_param(self):
        code = dedent('''\
            class Sample(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""
                    a_arg.is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_param(self):
        code = dedent('''\
            class ISample(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Sample(ISample):
                def a_method(self, a_arg):
                    a_arg.is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_param_on_a_hierarchy_python_refuses(self):
        code = dedent('''\
            class Base(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Left(Base):
                pass


            class Sample(Base, Left):
                def a_method(self, a_arg):
                    a_arg.is_''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_param_follows_the_method_resolution_order(self):
        code = dedent('''\
            class Base(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Left(Base):
                pass


            class Right(Base):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Event"""


            class Sample(Left, Right):
                def a_method(self, a_arg):
                    a_arg.is_''')
        result = self._assist(code)
        self.assert_completion_in_result("is_set", "attribute", result)
        self.assert_completion_not_in_result("is_alive", "attribute", result)


    def test_hint_param_follows_the_method_resolution_order(self):
        code = dedent('''\
            class Base(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Left(Base):
                pass


            class Right(Base):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Event"""


            class Sample(Left, Right):
                def a_method(self, a_arg):
                    a_arg.is_''')
        result = self._assist(code)
        self.assert_completion_in_result("is_set", "attribute", result)
        self.assert_completion_not_in_result("is_alive", "attribute", result)


    def test_hint_param_on_a_hierarchy_python_refuses(self):
        code = dedent('''\
            class Base(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Left(Base):
                pass


            class Sample(Base, Left):
                def a_method(self, a_arg):
                    a_arg.is_''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

class DocstringReturnHintingTest(AbstractHintingTest):
    def test_hierarchical_hint_rtype(self):
        code = dedent('''\
            class ISample(object):
                def b_method(self):
                    """:rtype: threading.Thread"""


            class Sample(ISample):
                def b_method(self):
                    pass
                def a_method(self):
                    self.b_method().is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)


def fix_indents(hint):
    return indent(hint, " " * 12).strip()


class AbstractAssignmentHintingTest(AbstractHintingTest):
    def _make_class_hint(self, type_str):
        raise NotImplementedError

    def _make_constructor_hint(self, type_str):
        raise NotImplementedError

    def test_hint_attr(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_attr(self):
        code = dedent(f"""\
            class ISample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}


            class Sample(ISample):
                a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_defined_by_constructor(self):
        code = dedent(f"""\
            class Sample(object):
                def __init__(self, arg):
                    {fix_indents(self._make_constructor_hint("threading.Thread"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_redefined_by_constructor(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}
                def __init__(self):
                    self.a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_attr_redefined_by_constructor(self):
        code = dedent(f"""\
            class ISample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}


            class Sample(ISample):
                def __init__(self):
                    self.a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_for_pre_defined_type(self):
        code = dedent(f"""\
            class Other(object):
                def is_alive(self):
                    pass


            class Sample(object):
                {fix_indents(self._make_class_hint("Other"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_for_post_defined_type(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("Other"))}
                def a_method(self):
                    self.a_attr.is_a""")
        offset = len(code)
        # Note: the leading blank lines are required.
        code += dedent("""\


            class Other(object):
                def is_alive(self):
                    pass
        """)
        result = self._assist(code, offset)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_list(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("list[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_tuple(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("tuple[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_set(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("set[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_iterable(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("collections.Iterable[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_iterator(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("collections.Iterator[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_dict_key(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("dict[str, threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr.keys():
                        i.sta""")
        result = self._assist(code)
        self.assert_completion_in_result("startswith", "builtin", result)

    def test_hint_parametrized_dict_value(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("dict[str, threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_nested_tuple_list(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("tuple[list[threading.Thread]]"))}
                def a_method(self):
                    for j in self.a_attr:
                        for i in j:
                            i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_or(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("str | threading.Thread"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_assignment_hints_ignore_names_that_are_not_assigned(self):
        from rope.base import libutils
        from rope.base.oi.type_hinting import utils
        from rope.base.oi.type_hinting.providers.pep0484_type_comments import (
            AssignmentProvider,
        )

        pymodule = libutils.get_string_module(self.project, "def a_func():\n    pass\n")
        defined_name = pymodule["a_func"]
        self.assertIsNone(AssignmentProvider(None)(defined_name))
        self.assertIsNone(utils.get_class_with_attr_name(defined_name))

    def test_hint_or_keeps_first_alternative_attributes(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("str | threading.Thread"))}
                def a_method(self):
                    self.a_attr.upp""")
        result = self._assist(code)
        self.assert_completion_in_result("upper", "builtin", result)

    def test_hint_nonexistent(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("sdfdsf.asdfasdf.sdfasdf.Dffg"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assertEqual(result, [])

    def test_hint_invalid_syntax(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("sdf | & # &*"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assertEqual(result, [])


class DocstringNoneAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f'''\
            """:type a_attr: {type_str}"""
            a_attr = None
        ''')
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f'''\
            """:type arg: {type_str}"""
            self.a_attr = arg
        ''')
        return indent(hint, " " * 8)


class DocstringNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f'''\
            """:type a_attr: {type_str}"""
            a_attr = NotImplemented
        ''')
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f'''\
            """:type arg: {type_str}"""
            self.a_attr = arg
        ''')
        return indent(hint, " " * 8)


class PEP0484CommentNoneAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f"""\
            a_attr = None  # type: {type_str}
        """)
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f"""\
            self.a_attr = None  # type: {type_str}
        """)
        return indent(hint, " " * 8)


class PEP0484CommentNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f"""\
            a_attr = NotImplemented  # type: {type_str}
        """)
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f"""\
            self.a_attr = NotImplemented  # type: {type_str}
        """)
        return indent(hint, " " * 8)


class EvaluateTest(unittest.TestCase):
    def test_parser(self):
        tests = [
            ("Foo", "(name Foo)"),
            ("mod1.Foo", "(name mod1.Foo)"),
            ("mod1.mod2.Foo", "(name mod1.mod2.Foo)"),
            ("Foo[Bar]", "('[' (name Foo) [(name Bar)])"),
            (
                "Foo[Bar1, Bar2, Bar3]",
                "('[' (name Foo) [(name Bar1), (name Bar2), (name Bar3)])",
            ),
            ("Foo[Bar[Baz]]", "('[' (name Foo) [('[' (name Bar) [(name Baz)])])"),
            (
                "Foo[Bar1[Baz1], Bar2[Baz2]]",
                "('[' (name Foo) [('[' (name Bar1) [(name Baz1)]), ('[' (name Bar2) [(name Baz2)])])",
            ),
            ("mod1.mod2.Foo[Bar]", "('[' (name mod1.mod2.Foo) [(name Bar)])"),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar]",
                "('[' (name mod1.mod2.Foo) [(name mod1.mod2.Bar)])",
            ),
            (
                "mod1.mod2.Foo[Bar1, Bar2, Bar3]",
                "('[' (name mod1.mod2.Foo) [(name Bar1), (name Bar2), (name Bar3)])",
            ),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar[mod1.mod2.Baz]]",
                "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar) [(name mod1.mod2.Baz)])])",
            ),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
                "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])",
            ),
            ("(Foo, Bar) -> Baz", "('(' [(name Foo), (name Bar)] (name Baz))"),
            (
                "(mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]], mod1.mod2.Bar[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]) -> mod1.mod2.Baz[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
                "('(' [('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]), ('[' (name mod1.mod2.Bar) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])] ('[' (name mod1.mod2.Baz) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]))",
            ),
            (
                "(Foo, Bar) -> Baz | Foo[Bar[Baz]]",
                "('|' ('(' [(name Foo), (name Bar)] (name Baz)) ('[' (name Foo) [('[' (name Bar) [(name Baz)])]))",
            ),
            (
                "Foo[Bar[Baz | (Foo, Bar) -> Baz]]",
                "('[' (name Foo) [('[' (name Bar) [('|' (name Baz) ('(' [(name Foo), (name Bar)] (name Baz)))])])",
            ),
        ]

        for t, expected in tests:
            result = repr(evaluate.compile(t))
            self.assertEqual(expected, result)


class RegressionHintingTest(AbstractHintingTest):
    def test_hierarchical_hint_for_mutable_attr_type(self):
        """Test for #157, AttributeError: 'PyObject' object has no attribute 'get_doc'"""
        code = dedent("""\
            class SuperClass(object):
                def __init__(self):
                    self.foo = None


            class SubClass(SuperClass):
                def __init__(self):
                    super(SubClass, self).__init__()
                    self.bar = 3


                def foo(self):
                    return self.bar""")
        result = self._assist(code)
        self.assert_completion_in_result("bar", "attribute", result)
