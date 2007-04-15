import compiler.consts

import rope.base.evaluate
import rope.base.pyscopes
from rope.base import pynames
from rope.base.exceptions import RopeError, AttributeNotFoundError


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

    def __eq__(self, obj):
        """Check the equality of two `PyObject`\s

        Currently it is assumed that two instances(The direct instances
        of `PyObject` are equal if their types are equal.  For every
        other object like defineds or builtins we assume objects are
        reference objects.

        """
        if self.__class__ != obj.__class__:
            return False
        if type(self) == PyObject:
            if self != self.type:
                self.type == obj.type
            else:
                return self.type is obj.type
        return self is obj

    def __hash__(self):
        """See docs for `__eq__()` method"""
        if type(self) == PyObject and self != self.type:
            return hash(self.type) + 1
        else:
            return super(PyObject, self).__hash__()

    _types = None
    _unknown = None

    @staticmethod
    def _get_base_type(name):
        if PyObject._types is None:
            PyObject._types = {}
            base_type = PyObject(None)
            PyObject._types['Type'] = base_type
            PyObject._types['Module'] = PyObject(base_type)
            PyObject._types['Function'] = PyObject(base_type)
            PyObject._types['Unknown'] = PyObject(base_type)
        return PyObject._types[name]


def get_base_type(name):
    """Return the base type with name `name`.

    The base types are 'Type', 'Function', 'Module' and 'Unknown'.  It
    was used to check the type of a `PyObject` but currently its use
    is discouraged.  Use classes defined in this module instead.
    For example instead of
    ``pyobject.get_type() == get_base_type('Function')`` use
    ``isinstance(pyobject, AbstractFunction)``.

    You can use `AbstractClass` for classs, `AbstractFunction` for
    functions, and `AbstractModule` for modules.  You can also use
    `PyFunction` and `PyClass` for testing if an object is
    defined somewhere and rope can access its source.  These classes
    provide more methods.

    """
    return PyObject._get_base_type(name)


def get_unknown():
    """Return a pyobject whose type is unknown

    Note that two unknown objects are equal.  So for example you can
    write::

      if pyname.get_object() == get_unknown():
          print 'Object of pyname is not known'

    Rope could have used `None` for indicating unknown objects but
    we had to check that in many places.  So actually this method
    returns a null object.

    """
    if PyObject._unknown is None:
        PyObject._unknown = PyObject(get_base_type('Unknown'))
    return PyObject._unknown


class AbstractClass(PyObject):

    def __init__(self):
        super(AbstractClass, self).__init__(get_base_type('Type'))

    def get_name(self):
        pass

    def get_doc(self):
        pass

    def get_superclasses(self):
        return []


class AbstractFunction(PyObject):

    def __init__(self):
        super(AbstractFunction, self).__init__(get_base_type('Function'))

    def get_name(self):
        pass

    def get_doc(self):
        pass

    def get_param_names(self, special_args=True):
        return []

    def get_returned_object(self, args):
        return get_unknown()


class AbstractModule(PyObject):

    def __init__(self, doc=None):
        super(AbstractModule, self).__init__(get_base_type('Module'))

    def get_doc(self):
        pass

    def get_resource(self):
        pass


class PyDefinedObject(object):
    """Python defined names that rope can access their sources"""

    def __init__(self, pycore, ast_node, parent):
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

    def get_doc(self):
        return self.get_ast().doc

    def _create_structural_attributes(self):
        return {}

    def _create_concluded_attributes(self):
        return {}

    def get_ast(self):
        return self.ast_node

    def _create_scope(self):
        pass


class PyFunction(PyDefinedObject, AbstractFunction):

    def __init__(self, pycore, ast_node, parent):
        AbstractFunction.__init__(self)
        PyDefinedObject.__init__(self, pycore, ast_node, parent)
        self.parameters = self.ast_node.argnames
        self.decorators = self.ast_node.decorators
        self.parameter_pyobjects = pynames._Inferred(
            self._infer_parameters, self.get_module()._get_concluded_data())
        self.returned = pynames._Inferred(self._infer_returned)
        self.parameter_pynames = None

    def _create_structural_attributes(self):
        return {}

    def _create_concluded_attributes(self):
        return {}

    def _create_scope(self):
        return rope.base.pyscopes.FunctionScope(self.pycore, self)

    def _infer_parameters(self):
        object_infer = self.pycore._get_object_infer()
        pyobjects = object_infer.infer_parameter_objects(self)
        self._handle_special_args(pyobjects)
        return pyobjects

    def _infer_returned(self, args=None):
        object_infer = self.pycore._get_object_infer()
        return object_infer.infer_returned_object(self, args)

    def _handle_special_args(self, pyobjects):
        if len(pyobjects) < len(self.parameters):
            if self.get_ast().flags & compiler.consts.CO_VARARGS:
                pyobjects.append(rope.base.builtins.get_list())
            if self.get_ast().flags & compiler.consts.CO_VARKEYWORDS:
                pyobjects.append(rope.base.builtins.get_dict())

    def _set_parameter_pyobjects(self, pyobjects):
        self._handle_special_args(pyobjects)
        self.parameter_pyobjects.set(pyobjects)

    def get_parameters(self):
        if self.parameter_pynames is None:
            result = {}
            for index, name in enumerate(self.parameters):
                result[name] = pynames.ParameterName(self, index)
            self.parameter_pynames = result
        return self.parameter_pynames

    def get_parameter(self, index):
        if index < len(self.parameter_pyobjects.get()):
            return self.parameter_pyobjects.get()[index]

    def get_returned_object(self, args):
        return self.returned.get(args)

    def get_name(self):
        return self.get_ast().name

    def get_param_names(self, special_args=True):
        result = list(self.parameters)
        if not special_args:
            node = self.get_ast()
            if node.flags & compiler.consts.CO_VARKEYWORDS:
                del result[-1]
            if node.flags & compiler.consts.CO_VARARGS:
                del result[-1]
        return result


class PyClass(PyDefinedObject, AbstractClass):

    def __init__(self, pycore, ast_node, parent):
        AbstractClass.__init__(self)
        PyDefinedObject.__init__(self, pycore, ast_node, parent)
        self.parent = parent
        self._superclasses = None

    def get_superclasses(self):
        if self._superclasses is None:
            self._superclasses = self._get_bases()
        return self._superclasses

    def get_name(self):
        return self.get_ast().name

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


class _PyModule(PyDefinedObject, AbstractModule):

    def __init__(self, pycore, ast_node, resource):
        self.dependant_modules = set()
        self.resource = resource
        self.concluded_data = []
        AbstractModule.__init__(self)
        PyDefinedObject.__init__(self, pycore, ast_node, None)

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
                resource.get_child('__init__.py')).get_ast()
        else:
            ast_node = compiler.parse('\n')
        super(PyPackage, self).__init__(pycore, ast_node, resource)

    def _create_structural_attributes(self):
        result = {}
        if self.resource is None:
            return result
        for name, resource in self._get_child_resources().items():
            result[name] = pynames.ImportedModule(self, resource=resource)
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
        if not isinstance(old_pyname, pynames.AssignedName):
            self.scope_visitor.names[name] = pynames.AssignedName(
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

    def _add_node(self, node):
        new_levels = []
        if self.levels is not None:
            new_levels = list(self.levels)
            new_levels.append(self.index)
        self.index += 1
        self._added(node, new_levels)

    def _added(self, node, levels):
        if hasattr(node, 'name'):
            self.names.append((node.name, levels))

    def visitAssName(self, node):
        self._add_node(node)

    def visitName(self, node):
        self._add_node(node)

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
        self._add_node(node)

    def visitSubscript(self, node):
        self._add_node(node)

    def visitSlice(self, node):
        self._add_node(node)

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
        self.names[node.name] = pynames.DefinedName(
            PyClass(self.pycore, node, self.owner_object))

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = pynames.DefinedName(pyobject)

    def visitAssign(self, node):
        compiler.walk(node, _AssignVisitor(self))

    def _assign_evaluated_object(self, assigned_vars, assigned,
                                 evaluation, lineno):
        names = _NodeNameCollector.get_assigned_names(assigned_vars)
        for name, levels in names:
            assignment = pynames._Assigned(assigned, levels)
            self.names[name] = pynames.EvaluatedName(
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
                self.names[alias] = pynames.ImportedModule(self.get_module(),
                                                   module_name)
            else:
                self.names[first_package] = pynames.ImportedModule(self.get_module(),
                                                           first_package)

    def visitFrom(self, node):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        imported_module = pynames.ImportedModule(self.get_module(),
                                                 node.modname, level)
        if node.names[0][0] == '*':
            self.owner_object.star_imports.append(
                pynames.StarImport(imported_module))
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                self.names[imported] = pynames.ImportedName(imported_module,
                                                            name)

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
        self.names[node.name] = pynames.DefinedName(pyobject)
        if len(node.argnames) > 0:
            new_visitor = _ClassInitVisitor(self, node.argnames[0])
            for child in node.getChildNodes():
                compiler.walk(child, new_visitor)

    def visitClass(self, node):
        self.names[node.name] = pynames.DefinedName(
            PyClass(self.pycore, node, self.owner_object))


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_FunctionVisitor, self).__init__(pycore, owner_object)
        self.returned_asts = []
        self.generator = False

    def visitReturn(self, node):
        self.returned_asts.append(node.value)

    def visitYield(self, node):
        self.returned_asts.append(node.value)
        self.generator = True


class _ClassInitVisitor(_AssignVisitor):

    def __init__(self, scope_visitor, self_name):
        super(_ClassInitVisitor, self).__init__(scope_visitor)
        self.self_name = self_name

    def visitAssAttr(self, node):
        if isinstance(node.expr, compiler.ast.Name) and \
           node.expr.name == self.self_name:
            if node.attrname not in self.scope_visitor.names:
                self.scope_visitor.names[node.attrname] = pynames.AssignedName(
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
