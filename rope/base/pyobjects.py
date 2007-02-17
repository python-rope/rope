import compiler

import rope.base.evaluate
import rope.base.pyscopes
from rope.base import pynames
from rope.base.exceptions import RopeError, AttributeNotFoundError
from rope.base.pynames import *


class PyObject(object):

    def __init__(self, type_):
        if type_ is None:
            type_ = self
        self.type = type_

    def get_attributes(self):
        if self.type is self:
            return {}
        return self.type.get_attributes()

    def get_attribute(self, name):
        if name not in self.get_attributes():
            raise AttributeNotFoundError('Attribute %s not found' % name)
        return self.get_attributes()[name]

    def get_type(self):
        return self.type

    @staticmethod
    def _get_base_type(name):
        if not hasattr(PyObject, 'types'):
            PyObject.types = {}
            base_type = PyObject(None)
            PyObject.types['Type'] = base_type
            PyObject.types['Module'] = PyObject(base_type)
            PyObject.types['Function'] = PyObject(base_type)
            PyObject.types['Unknown'] = PyObject(base_type)
        return PyObject.types[name]


def get_base_type(name):
    return PyObject._get_base_type(name)


class PyDefinedObject(PyObject):

    def __init__(self, type_, pycore, ast_node, parent):
        super(PyDefinedObject, self).__init__(type_)
        self.pycore = pycore
        self.ast_node = ast_node
        self.scope = None
        self.parent = parent
        self.structural_attributes = None
        self.concluded_attributes = self.get_module()._get_concluded_data()
        self.attributes = self.get_module()._get_concluded_data()

    def _get_structural_attributes(self):
        if self.structural_attributes is None:
            self.structural_attributes = self._create_structural_attributes()
        return self.structural_attributes

    def _get_concluded_attributes(self):
        if self.concluded_attributes.get() is None:
            self._get_structural_attributes()
            self.concluded_attributes.set(self._create_concluded_attributes())
        return self.concluded_attributes.get()

    def get_attributes(self):
        if self.attributes.get() is None:
            result = dict(self._get_concluded_attributes())
            result.update(self._get_structural_attributes())
            self.attributes.set(result)
        return self.attributes.get()

    def get_attribute(self, name):
        if name in self._get_structural_attributes():
            return self._get_structural_attributes()[name]
        if name in self._get_concluded_attributes():
            return self._get_concluded_attributes()[name]
        raise AttributeNotFoundError('Attribute %s not found' % name)

    def get_scope(self):
        if self.scope is None:
            self.scope = self._create_scope()
        return self.scope

    def get_module(self):
        current_object = self
        while current_object.parent is not None:
            current_object = current_object.parent
        return current_object

    def _create_structural_attributes(self):
        return {}

    def _create_concluded_attributes(self):
        return {}

    def _get_ast(self):
        return self.ast_node

    def _create_scope(self):
        pass


class PyFunction(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyFunction, self).__init__(get_base_type('Function'),
                                         pycore, ast_node, parent)
        self.parameters = self.ast_node.argnames
        self.decorators = self.ast_node.decorators
        self.is_being_inferred = False
        self.are_args_being_inferred = False
        self.parameter_pyobjects = self.get_module()._get_concluded_data()
        self.parameter_pynames = self.get_module()._get_concluded_data()

    def _create_structural_attributes(self):
        return {}

    def _create_concluded_attributes(self):
        return {}

    def _create_scope(self):
        return rope.base.pyscopes.FunctionScope(self.pycore, self)

    def _get_parameter_pyobjects(self):
        if self.are_args_being_inferred:
            raise IsBeingInferredError('Circular assignments')
        if len(self.parameters) == 0:
            return {}
        self.are_args_being_inferred = True
        try:
            object_infer = self.pycore._get_object_infer()
            pyobjects = object_infer.infer_parameter_objects(self)
        finally:
            self.are_args_being_inferred = False
        return pyobjects

    def get_parameters(self):
        if self.parameter_pynames.get() is None:
            result = {}
            for index, name in enumerate(self.parameters):
                result[name] = ParameterName(self, index)
            self.parameter_pynames.set(result)
        return self.parameter_pynames.get()

    def get_parameter(self, index):
        if not self.parameter_pyobjects.get():
            self.parameter_pyobjects.set(self._get_parameter_pyobjects())
        return self.parameter_pyobjects.get()[index]

    def get_returned_object(self, args=None):
        if self.is_being_inferred:
            raise IsBeingInferredError('Circular assignments')
        self.is_being_inferred = True
        try:
            object_infer = self.pycore._get_object_infer()
            inferred_object = object_infer.infer_returned_object(self, args)
            result = inferred_object
        finally:
            self.is_being_inferred = False
        if result is None:
            return PyObject(get_base_type('Unknown'))
        return result


class PyClass(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyClass, self).__init__(get_base_type('Type'),
                                      pycore, ast_node, parent)
        self.parent = parent
        self._superclasses = None

    def get_superclasses(self):
        if self._superclasses is None:
            self._superclasses = self._get_bases()
        return self._superclasses

    def _create_structural_attributes(self):
        new_visitor = _ClassVisitor(self.pycore, self)
        for n in self.ast_node.getChildNodes():
            compiler.walk(n, new_visitor)
        return new_visitor.names

    def _create_concluded_attributes(self):
        result = {}
        for base in reversed(self.get_superclasses()):
            result.update(base.get_attributes())
        return result

    def _get_bases(self):
        result = []
        for base_name in self.ast_node.bases:
            base = rope.base.evaluate.get_statement_result(
                self.parent.get_scope(), base_name)
            if base is not None and \
               base.get_object().get_type() == get_base_type('Type'):
                result.append(base.get_object())
        return result

    def _create_scope(self):
        return rope.base.pyscopes.ClassScope(self.pycore, self)


class _ConcludedData(object):

    def __init__(self):
        self.data_ = None

    def set(self, data):
        self.data_ = data

    def get(self):
        return self.data_

    data = property(get, set)

    def _invalidate(self):
        self.data = None

    def __str__(self):
        return '<' + str(self.data) + '>'


class _PyModule(PyDefinedObject):

    def __init__(self, pycore, ast_node, resource):
        self.dependant_modules = set()
        self.resource = resource
        self.concluded_data = []
        super(_PyModule, self).__init__(get_base_type('Module'),
                                        pycore, ast_node, None)

    def _get_concluded_data(self):
        new_data = _ConcludedData()
        self.concluded_data.append(new_data)
        return new_data

    def _add_dependant(self, pymodule):
        if pymodule.get_resource():
            self.dependant_modules.add(pymodule)

    def _invalidate_concluded_data(self):
        dependant_modules = set(self.dependant_modules)
        self.dependant_modules.clear()
        for data in self.concluded_data:
            data._invalidate()
        for module in dependant_modules:
            module._invalidate_concluded_data()

    def get_resource(self):
        return self.resource


class PyModule(_PyModule):

    def __init__(self, pycore, source_code, resource=None):
        if isinstance(source_code, unicode):
            source_code = source_code.encode('utf-8')
        self.source_code = source_code
        self._lines = None
        ast_node = compiler.parse(source_code.rstrip(' \t'))
        self.star_imports = []
        super(PyModule, self).__init__(pycore, ast_node, resource)

    def _get_lines(self):
        if self._lines is None:
            self._lines = rope.base.codeanalyze.SourceLinesAdapter(self.source_code)
        return self._lines

    lines = property(_get_lines, doc="return a `SourceLinesAdapter`")

    def _create_concluded_attributes(self):
        result = {}
        for star_import in self.star_imports:
            result.update(star_import.get_names())
        return result

    def _create_structural_attributes(self):
        visitor = _GlobalVisitor(self.pycore, self)
        compiler.walk(self.ast_node, visitor)
        return visitor.names

    def _create_scope(self):
        return rope.base.pyscopes.GlobalScope(self.pycore, self)


class PyPackage(_PyModule):

    def __init__(self, pycore, resource=None):
        self.resource = resource
        if resource is not None and resource.has_child('__init__.py'):
            ast_node = pycore.resource_to_pyobject(
                resource.get_child('__init__.py'))._get_ast()
        else:
            ast_node = compiler.parse('\n')
        super(PyPackage, self).__init__(pycore, ast_node, resource)

    def _create_structural_attributes(self):
        result = {}
        if self.resource is None:
            return result
        for name, resource in self._get_child_resources().items():
            result[name] = ImportedModule(self, resource=resource)
        return result

    def _create_concluded_attributes(self):
        result = {}
        init_dot_py = self._get_init_dot_py()
        if init_dot_py:
            init_object = self.pycore.resource_to_pyobject(init_dot_py)
            result.update(init_object.get_attributes())
            init_object._add_dependant(self)
        return result

    def _get_child_resources(self):
        result = {}
        for child in self.resource.get_children():
            if child.is_folder():
                result[child.name] = child
            elif child.name.endswith('.py') and \
                 child.name != '__init__.py':
                name = child.name[:-3]
                result[name] = child
        return result

    def _get_init_dot_py(self):
        if self.resource is not None and self.resource.has_child('__init__.py'):
            return self.resource.get_child('__init__.py')
        else:
            return None

    def _create_scope(self):
        return self.get_module().get_scope()

    def get_module(self):
        init_dot_py = self._get_init_dot_py()
        if init_dot_py:
            return self.pycore.resource_to_pyobject(init_dot_py)


class _AssignVisitor(object):

    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor
        self.assigned_ast = None

    def visitAssign(self, node):
        self.assigned_ast = node.expr
        for child_node in node.nodes:
            compiler.walk(child_node, self)

    def _assigned(self, name, assignment=None):
        old_pyname = self.scope_visitor.names.get(name, None)
        if old_pyname is None or not isinstance(old_pyname, AssignedName):
            self.scope_visitor.names[name] = AssignedName(
                module=self.scope_visitor.get_module())
        if assignment is not None:
            self.scope_visitor.names[name].assignments.append(assignment)

    def visitAssName(self, node):
        assignment = None
        if self.assigned_ast is not None:
            assignment = pynames._Assigned(self.assigned_ast)
        self._assigned(node.name, assignment)

    def visitAssTuple(self, node):
        names = _NodeNameCollector.get_assigned_names(node)
        for name, levels in names:
            assignment = None
            if self.assigned_ast is not None:
                assignment = pynames._Assigned(self.assigned_ast, levels)
            self._assigned(name, assignment)

    def visitAssAttr(self, node):
        pass

    def visitSubscript(self, node):
        pass

    def visitSlice(self, node):
        pass


class _NodeNameCollector(object):

    def __init__(self, levels=None):
        self.names = []
        self.levels = levels
        self.index = 0

    def _add_name(self, name):
        new_levels = []
        if self.levels is not None:
            new_levels = list(self.levels)
            new_levels.append(self.index)
        self.index += 1
        if name is not None:
            self.names.append((name, new_levels))

    def visitAssName(self, node):
        self._add_name(node.name)

    def visitName(self, node):
        self._add_name(node.name)

    def visitTuple(self, node):
        new_levels = []
        if self.levels is not None:
            new_levels = list(self.levels)
            new_levels.append(self.index)
        self.index += 1
        visitor = _NodeNameCollector(new_levels)
        for child in node.getChildNodes():
            compiler.walk(child, visitor)
        self.names.extend(visitor.names)

    def visitAssTuple(self, node):
        self.visitTuple(node)

    def visitAssAttr(self, node):
        self._add_name(None)

    def visitSubscript(self, node):
        self._add_name(None)

    def visitSlice(self, node):
        self._add_name(None)

    @staticmethod
    def get_assigned_names(node):
        visitor = _NodeNameCollector()
        compiler.walk(node, visitor)
        return visitor.names


class _ScopeVisitor(object):

    def __init__(self, pycore, owner_object):
        self.names = {}
        self.pycore = pycore
        self.owner_object = owner_object

    def get_module(self):
        if self.owner_object is not None:
            return self.owner_object.get_module()
        else:
            return None

    def visitClass(self, node):
        self.names[node.name] = DefinedName(PyClass(self.pycore,
                                                    node, self.owner_object))

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = DefinedName(pyobject)

    def visitAssign(self, node):
        compiler.walk(node, _AssignVisitor(self))

    def _assign_evaluated_object(self, assigned_vars, assigned,
                                 evaluation, lineno):
        names = _NodeNameCollector.get_assigned_names(assigned_vars)
        for name, levels in names:
            assignment = pynames._Assigned(assigned, levels)
            self.names[name] = EvaluatedName(
                assignment=assignment, module=self.get_module(),
                lineno=lineno, evaluation=evaluation)

    def visitFor(self, node):
        self._assign_evaluated_object(
            node.assign, node.list, '.__iter__().next()', node.lineno)
        compiler.walk(node.body, self)

    def visitWith(self, node):
        self._assign_evaluated_object(
            node.vars, node.expr, '.__enter__()', node.lineno)
        compiler.walk(node.body, self)

    def visitImport(self, node):
        for import_pair in node.names:
            module_name, alias = import_pair
            first_package = module_name.split('.')[0]
            if alias is not None:
                self.names[alias] = ImportedModule(self.get_module(),
                                                   module_name)
            else:
                self.names[first_package] = ImportedModule(self.get_module(),
                                                           first_package)

    def visitFrom(self, node):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        imported_module = ImportedModule(self.get_module(),
                                         node.modname, level)
        if node.names[0][0] == '*':
            self.owner_object.star_imports.append(StarImport(imported_module))
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                self.names[imported] = ImportedName(imported_module, name)

    def visitGlobal(self, node):
        module = self.get_module()
        for name in node.names:
            if module is not None:
                try:
                    pyname = module.get_attribute(name)
                except AttributeNotFoundError:
                    pyname = pynames.AssignedName(node.lineno)
            self.names[name] = pyname


class _GlobalVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_GlobalVisitor, self).__init__(pycore, owner_object)


class _ClassVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_ClassVisitor, self).__init__(pycore, owner_object)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = DefinedName(pyobject)
        if len(node.argnames) > 0:
            new_visitor = _ClassInitVisitor(self, node.argnames[0])
            for child in node.getChildNodes():
                compiler.walk(child, new_visitor)

    def visitClass(self, node):
        self.names[node.name] = DefinedName(PyClass(self.pycore, node,
                                                    self.owner_object))


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_FunctionVisitor, self).__init__(pycore, owner_object)
        self.returned_asts = []

    def visitReturn(self, node):
        self.returned_asts.append(node.value)


class _ClassInitVisitor(_AssignVisitor):

    def __init__(self, scope_visitor, self_name):
        super(_ClassInitVisitor, self).__init__(scope_visitor)
        self.self_name = self_name

    def visitAssAttr(self, node):
        if isinstance(node.expr, compiler.ast.Name) and node.expr.name == self.self_name:
            if node.attrname not in self.scope_visitor.names:
                self.scope_visitor.names[node.attrname] = AssignedName(
                    lineno=node.lineno, module=self.scope_visitor.get_module())
            self.scope_visitor.names[node.attrname].assignments.append(
                pynames._Assigned(self.assigned_ast))

    def visitAssTuple(self, node):
        for child in node.getChildNodes():
            compiler.walk(child, self)

    def visitAssName(self, node):
        pass

    def visitFunction(self, node):
        pass

    def visitClass(self, node):
        pass

    def visitFor(self, node):
        pass

    def visitWith(self, node):
        pass


class IsBeingInferredError(RopeError):
    pass

