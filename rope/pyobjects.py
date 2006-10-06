import compiler

import rope.pyscopes
from rope.exceptions import (RopeException, AttributeNotFoundException)
from rope.pynames import *


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
            raise AttributeNotFoundException('Attribute %s not found' % name)
        return self.get_attributes()[name]

    def get_type(self):
        return self.type

    @staticmethod
    def get_base_type(name):
        if not hasattr(PyObject, 'types'):
            PyObject.types = {}
            base_type = PyObject(None)
            PyObject.types['Type'] = base_type
            PyObject.types['Module'] = PyObject(base_type)
            PyObject.types['Function'] = PyObject(base_type)
            PyObject.types['Unknown'] = PyObject(base_type)
        return PyObject.types[name]


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
        raise AttributeNotFoundException('Attribute %s not found' % name)
    
    def get_scope(self):
        if self.scope == None:
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
        super(PyFunction, self).__init__(PyObject.get_base_type('Function'),
                                         pycore, ast_node, parent)
        self.parameters = self.ast_node.argnames
        self.decorators = self.ast_node.decorators
        self.is_being_inferred = False
        self.are_args_being_inferred = False
        self.returned_object = self.get_module()._get_concluded_data()
        self.parameter_pyobjects = self.get_module()._get_concluded_data()
        self.parameter_pynames = self.get_module()._get_concluded_data()

    def _create_structural_attributes(self):
        return {}
    
    def _create_concluded_attributes(self):
        return {}

    def _create_scope(self):
        return rope.pyscopes.FunctionScope(self.pycore, self)
    
    def _get_parameter_pyobjects(self):
        if self.are_args_being_inferred:
            raise IsBeingInferredException('Circular assignments')
        if len(self.parameters) == 0:
            return {}
        self.are_args_being_inferred = True
        try:
            object_infer = self.pycore._get_object_infer()
            pyobjects = object_infer.infer_parameter_objects(self)
        finally:
            self.are_args_being_inferred = False
        
        if pyobjects is None:
            pyobjects = []
            if self.parent.get_type() == PyObject.get_base_type('Type') and \
               not self.decorators:
                pyobjects.append(PyObject(self.parent))
            else:
                pyobjects.append(PyObject(PyObject.get_base_type('Unknown')))
            for parameter in self.parameters[1:]:
                pyobjects.append(PyObject(PyObject.get_base_type('Unknown')))
        return pyobjects
    
    def get_parameters(self):
        if self.parameter_pynames.get() is None:
            result = {}
            for index, name in enumerate(self.parameters):
                result[name] = ParameterName(self, index)
            self.parameter_pynames.set(result)
        return self.parameter_pynames.get()
    
    def _get_parameter(self, index):
        if not self.parameter_pyobjects.get():
            self.parameter_pyobjects.set(self._get_parameter_pyobjects())
        return self.parameter_pyobjects.get()[index]
    
    def _get_returned_object(self):
        if self.is_being_inferred:
            raise IsBeingInferredException('Circular assignments')
        if self.returned_object.get() is None:
            self.is_being_inferred = True
            try:
                object_infer = self.pycore._get_object_infer()
                inferred_object = object_infer.infer_returned_object(self)
                self.returned_object.set(inferred_object)
            finally:
                self.is_being_inferred = False
        if self.returned_object.get() is None:
            self.returned_object.set(PyObject(PyObject.get_base_type('Unknown')))
        return self.returned_object.get()


class PyClass(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyClass, self).__init__(PyObject.get_base_type('Type'),
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
            base = rope.codeanalyze.StatementEvaluator.\
                   get_statement_result(self.parent.get_scope(), base_name)
            if base:
                result.append(base.get_object())
        return result

    def _create_scope(self):
        return rope.pyscopes.ClassScope(self.pycore, self)


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
        super(_PyModule, self).__init__(PyObject.get_base_type('Module'),
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
        self.source_code = source_code
        ast_node = compiler.parse(source_code.rstrip(' \t'))
        self.star_imports = []
        super(PyModule, self).__init__(pycore, ast_node, resource)
    
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
        return rope.pyscopes.GlobalScope(self.pycore, self)


class PyPackage(_PyModule):

    def __init__(self, pycore, resource=None):
        self.resource = resource
        if resource is not None and resource.has_child('__init__.py'):
            ast_node = compiler.parse(resource.get_child('__init__.py').read())
        else:
            ast_node = compiler.parse('\n')
        super(PyPackage, self).__init__(pycore, ast_node, resource)

    def _create_structural_attributes(self):
        result = {}
        if self.resource is None:
            return result
        for child in self.resource.get_children():
            if child.is_folder():
                result[child.get_name()] = ImportedModule(self, resource=child)
            elif child.get_name().endswith('.py') and \
                 child.get_name() != '__init__.py':
                name = child.get_name()[:-3]
                result[name] = ImportedModule(self, resource=child)
        init_dot_py = self._get_init_dot_py()
        if init_dot_py:
            init_object = self.pycore.resource_to_pyobject(init_dot_py)
            result.update(init_object.get_attributes())
            init_object._add_dependant(self)
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

    def visitAssName(self, node):
        old_pyname = self.scope_visitor.names.get(node.name, None)
        if old_pyname is None or not isinstance(old_pyname, AssignedName):
            self.scope_visitor.names[node.name] = AssignedName(
                module=self.scope_visitor.get_module())
        if self.assigned_ast:
            self.scope_visitor.names[node.name].assigned_asts.append(self.assigned_ast)


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
    
    def visitFor(self, node):
        self.visitAssign(node.assign)
        compiler.walk(node.body, self)
    
    def visitImport(self, node):
        for import_pair in node.names:
            module_name, alias = import_pair
            first_package = module_name.split('.')[0]
            if alias is not None:
                self.names[alias] = ImportedModule(self.get_module(), module_name)
            else:
                self.names[first_package] = ImportedModule(self.get_module(), first_package)

    def visitFrom(self, node):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        imported_module = ImportedModule(self.get_module(), node.modname, level)
        if node.names[0][0] == '*':
            self.owner_object.star_imports.append(StarImport(imported_module))
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                self.names[imported] = ImportedName(imported_module, name)


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
            compiler.walk(node, new_visitor)

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
            self.scope_visitor.names[node.attrname].assigned_asts.append(self.assigned_ast)
    
    def visitAssName(self, node):
        pass


class IsBeingInferredException(RopeException):
    pass

