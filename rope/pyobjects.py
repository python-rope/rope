import compiler

import rope.pyscopes
from rope.exceptions import ModuleNotFoundException, RopeException


class PyObject(object):

    def __init__(self, type_):
        if type_ is None:
            type_ = self
        self.type = type_
    
    def get_attributes(self):
        if self.type is self:
            return {}
        return self.type.get_attributes()

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
        self.attributes = None
        self.scope = None
        self.parent = parent

    def get_attributes(self):
        if self.attributes is None:
            self.attributes = {}
            self._update_attributes_from_ast(self.attributes)
        return self.attributes

    def get_scope(self):
        if self.scope == None:
            self.scope = self._create_scope()
        return self.scope
    
    def get_module(self):
        current_object = self
        while current_object.parent is not None:
            current_object = current_object.parent
        return current_object

    def _update_attributes_from_ast(self, attributes):
        pass

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
        self.returned_object = None

    def _update_attributes_from_ast(self, attributes):
        pass
    
    def _create_scope(self):
        return rope.pyscopes.FunctionScope(self.pycore, self)
    
    def _get_parameters(self):
        result = {}
        if len(self.parameters) > 0:
            if self.parent.get_type() == PyObject.get_base_type('Type') and \
               not self.decorators:
                result[self.parameters[0]] = PyName(PyObject(self.parent),
                                                    lineno=self.ast_node.lineno,
                                                    module=self.get_module())
            else:
                result[self.parameters[0]] = PyName(lineno=self.ast_node.lineno,
                                                    module=self.get_module())
        if len(self.parameters) > 1:
            for parameter in self.parameters[1:]:
                result[parameter] = PyName(lineno=self.ast_node.lineno,
                                           module=self.get_module())
        return result
    
    def _get_returned_object(self):
        if self.is_being_inferred:
            raise IsBeingInferredException('Circular assignments')
        if self.returned_object is None:
            self.is_being_inferred = True
            try:
                object_infer = self.pycore._get_object_infer()
                inferred_object = object_infer.infer_returned_object(self)
                self.returned_object = inferred_object
            finally:
                self.is_being_inferred = False
        if self.returned_object is None:
            self.returned_object = PyObject(PyObject.get_base_type('Unknown'))
        return self.returned_object


class PyClass(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyClass, self).__init__(PyObject.get_base_type('Type'),
                                      pycore, ast_node, parent)
        self.parent = parent

    def _update_attributes_from_ast(self, attributes):
        for base in self._get_bases():
            attributes.update(base.get_attributes())
        new_visitor = _ClassVisitor(self.pycore, self)
        for n in self.ast_node.getChildNodes():
            compiler.walk(n, new_visitor)
        attributes.update(new_visitor.names)

    def _get_bases(self):
        result = []
        for base_name in self.ast_node.bases:
            base = rope.codeanalyze.StatementEvaluator.\
                   get_statement_result(self.parent.get_scope(), base_name)
            if base:
                result.append(base)
        return result

    def _create_scope(self):
        return rope.pyscopes.ClassScope(self.pycore, self)


class _PyModule(PyDefinedObject):
    
    def __init__(self, pycore, ast_node, resource=None):
        super(_PyModule, self).__init__(PyObject.get_base_type('Module'),
                                        pycore, ast_node, None)
        self.dependant_modules = set()
        self.resource = resource

    def _add_dependant(self, pymodule):
        if pymodule.get_resource():
            self.dependant_modules.add(pymodule.get_resource())

    def get_resource(self):
        return self.resource
    

class PyModule(_PyModule):

    def __init__(self, pycore, source_code, resource=None):
        self.source_code = source_code
        ast_node = compiler.parse(source_code)
        super(PyModule, self).__init__(pycore, ast_node, resource)

    def _update_attributes_from_ast(self, attributes):
        visitor = _GlobalVisitor(self.pycore, self)
        compiler.walk(self.ast_node, visitor)
        attributes.update(visitor.names)

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

    def _update_attributes_from_ast(self, attributes):
        if self.resource is None:
            return
        for child in self.resource.get_children():
            if child.is_folder():
                child_pyobject = self.pycore.resource_to_pyobject(child)
                child_pyobject._add_dependant(self)
                attributes[child.get_name()] = PyName(child_pyobject, False, 1,
                                                      child_pyobject)
            elif child.get_name().endswith('.py') and \
                 child.get_name() != '__init__.py':
                child_pyobject = self.pycore.resource_to_pyobject(child)
                child_pyobject._add_dependant(self)
                name = child.get_name()[:-3]
                attributes[name] = PyName(child_pyobject, False, 1,
                                          child_pyobject)

    def _get_init_dot_py(self):
        if self.resource is not None and self.resource.has_child('__init__.py'):
            return self.resource.get_child('__init__.py')
        else:
            return None
    
    def get_module(self):
        init_dot_py = self._get_init_dot_py()
        return self.pycore.resource_to_pyobject(init_dot_py)


class PyName(object):

    def __init__(self, object_=None, is_defined_here=False, lineno=None, module=None):
        self.object = object_
        self.is_defined_here = is_defined_here
        self.lineno = lineno
        self.module = module
        self.is_being_inferred = False
        self.assigned_asts = []

    def get_attributes(self):
        return self.get_object().get_attributes()

    def get_object(self):
        if self.is_being_inferred:
            raise IsBeingInferredException('Circular assignments')
        if self.object is None and self.module is not None:
            self.is_being_inferred = True
            try:
                object_infer = self.module.pycore._get_object_infer()
                inferred_object = object_infer.infer_object(self)
                self.object = inferred_object
            finally:
                self.is_being_inferred = False
        if self.object is None:
            self.object = PyObject(PyObject.get_base_type('Unknown'))
        return self.object
    
    def get_type(self):
        return self.get_object().get_type()

    def get_definition_location(self):
        """Returns a (module, lineno) tuple"""
        lineno = self._get_lineno()
        return (self.module, lineno)

    def has_block(self):
        return self.is_defined_here and isinstance(self.get_object(),
                                                   PyDefinedObject)
    
    def _get_ast(self):
        return self.get_object()._get_ast()
    
    def _get_lineno(self):
        if self.has_block():
            self.lineno = self._get_ast().lineno
        if self.lineno == None and self.assigned_asts:
            self.lineno = self.assigned_asts[0].lineno
        return self.lineno


class _AssignVisitor(object):

    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor
        self.assigned_ast = None
    
    def visitAssign(self, node):
        self.assigned_ast = node.expr
        for child_node in node.nodes:
            compiler.walk(child_node, self)

    def visitAssName(self, node):
        if node.name not in self.scope_visitor.names:
            self.scope_visitor.names[node.name] = PyName(module=self.scope_visitor.get_module())
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
        self.names[node.name] = PyName(PyClass(self.pycore,
                                               node, self.owner_object), True,
                                       module=self.get_module())

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = PyName(pyobject, True, module=self.get_module())

    def visitAssign(self, node):
        compiler.walk(node, _AssignVisitor(self))

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            try:
                module = self.pycore.get_module(name)
                module._add_dependant(self.owner_object.get_module())
                lineno = 1
            except ModuleNotFoundException:
                self.names[imported] = PyName()
                return
            if alias is None and '.' in imported:
                tokens = imported.split('.')
                toplevel_module = self._get_module_with_packages(name)
                self.names[tokens[0]] = PyName(toplevel_module, False, 
                                               module=toplevel_module.get_module(),
                                               lineno=lineno)
            else:
                self.names[imported] = PyName(module, False, 
                                              module=module.get_module(), lineno=lineno)

    def _get_module_with_packages(self, module_name):
        module_list = self.pycore._find_module_resource_list(module_name)
        if module_list is None:
            return None
        return self.pycore.resource_to_pyobject(module_list[0])

    def visitFrom(self, node):
        try:
            module = self.pycore.get_module(node.modname)
            module._add_dependant(self.owner_object.get_module())
        except ModuleNotFoundException:
            module = None

        if node.names[0][0] == '*':
            if module is None or isinstance(module, PyPackage):
                return
            for name, pyname in module.get_attributes().iteritems():
                if not name.startswith('_'):
                    self.names[name] = PyName(pyname.get_object(), False, module=pyname.module,
                                              lineno=pyname.get_definition_location()[1])
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                if module is not None and module.get_attributes().has_key(name):
                    imported_pyname = module.get_attributes()[name]
                    imported_object = imported_pyname.get_object()
                    pyname_module, lineno = imported_pyname.get_definition_location()
                    self.names[imported] = PyName(imported_object, False, module=pyname_module,
                                                  lineno=lineno)
                else:
                    self.names[imported] = PyName()


class _GlobalVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_GlobalVisitor, self).__init__(pycore, owner_object)
    

class _ClassVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_ClassVisitor, self).__init__(pycore, owner_object)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = PyName(pyobject, True, module=self.get_module())
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor(self)
            compiler.walk(node, new_visitor)

    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore, node,
                                               self.owner_object),
                                       True, module=self.get_module())


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_FunctionVisitor, self).__init__(pycore, owner_object)
        self.returned_asts = []
    
    def visitReturn(self, node):
        self.returned_asts.append(node.value)


class _ClassInitVisitor(_AssignVisitor):

    def __init__(self, scope_visitor):
        super(_ClassInitVisitor, self).__init__(scope_visitor)
    
    def visitAssAttr(self, node):
        if isinstance(node.expr, compiler.ast.Name) and node.expr.name == 'self':
            self.scope_visitor.names[node.attrname] = PyName(lineno=node.lineno, 
                                                             module=self.scope_visitor.get_module())
            self.scope_visitor.names[node.attrname].assigned_asts.append(self.assigned_ast)
    
    def visitAssName(self, node):
        pass


class IsBeingInferredException(RopeException):
    pass

