import compiler

import rope.exceptions


class ModuleNotFoundException(rope.exceptions.RopeException):
    """Module not found exception"""


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self.module_map = {}

    def get_module(self, name):
        results = self.project.find_module(name)
        if not results:
            raise ModuleNotFoundException('Module %s not found' % name)
        result = results[0]
        return self._create(results[0])

    def get_string_module(self, module_content):
        ast = compiler.parse(module_content)
        return PyModule(self, ast)

    def get_string_scope(self, module_content):
        module = self.get_string_module(module_content)
        return GlobalScope(self, module)

    def _invalidate_resource_cache(self, resource):
        if resource in self.module_map:
            del self.module_map[resource]

    def _create(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self, resource)
        else:
            result =  self.get_string_module(resource.read())
        self.module_map[resource] = result
        resource.add_change_observer(self._invalidate_resource_cache)
        return result


class PyObject(object):

    def __init__(self, type_):
        if type_ is None:
            type_ = self
        self.type = type_
    
    def get_attributes(self):
        return {}

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

    def __init__(self, type_, pycore, ast_node):
        super(PyDefinedObject, self).__init__(type_)
        self.pycore = pycore
        self.ast_node = ast_node
        self.attributes = None

    def get_attributes(self):
        if self.attributes is None:
            self.attributes = self._get_attributes_from_ast()
        return self.attributes

    def _get_attributes_from_ast(self):
        pass

    def _get_ast(self):
        return self.ast_node


class PyFunction(PyDefinedObject):

    def __init__(self, pycore, ast_node):
        super(PyFunction, self).__init__(PyObject.get_base_type('Function'), pycore, ast_node)
        self.parameters = self.ast_node.argnames

    def _get_attributes_from_ast(self):
        return {}


class PyClass(PyDefinedObject):

    def __init__(self, pycore, ast_node):
        super(PyClass, self).__init__(PyObject.get_base_type('Type'), pycore, ast_node)

    def _get_attributes_from_ast(self):
        new_visitor = _ClassVisitor(self.pycore)
        for n in self.ast_node.getChildNodes():
            compiler.walk(n, new_visitor)
        return new_visitor.names


class PyModule(PyDefinedObject):

    def __init__(self, pycore, ast_node):
        super(PyModule, self).__init__(PyObject.get_base_type('Module'), pycore, ast_node)
        self.is_package = False

    def _get_attributes_from_ast(self):
        visitor = _GlobalVisitor(self.pycore)
        compiler.walk(self.ast_node, visitor)
        return visitor.names


class PyPackage(PyObject):

    def __init__(self, pycore, resource):
        super(PyPackage, self).__init__(PyObject.get_base_type('Module'))
        self.is_package = True
        self.resource = resource
        self.pycore = pycore
        self.attributes = None

    def get_attributes(self):
        if self.attributes is None:
            attributes = {}
            for child in self.resource.get_children():
                if child.is_folder():
                    attributes[child.get_name()] = PyName(self.pycore._create(child))
                elif child.get_name().endswith('.py') and child.get_name() != '__init__.py':
                    name = child.get_name()[:-3]
                    attributes[name] = PyName(self.pycore._create(child))
            self.attributes = attributes
        return self.attributes

class PyFilteredPackage(PyObject):

    def __init__(self):
        super(PyFilteredPackage, self).__init__(PyObject.get_base_type('Module'))
        self.is_package = True
        self.attributes = {}

    def get_attributes(self):
        return self.attributes

    def _add_attribute(self, name, pyname):
        self.attributes[name] = pyname


class PyName(object):

    def __init__(self, object_=None, is_defined_here=False):
        self.object = object_
        self.is_defined_here = is_defined_here

    def get_attributes(self):
        if self.object:
            return self.object.get_attributes()
        else:
            return PyObject.get_base_type('Unknown').get_attributes()
    
    def get_type(self):
        if self.object:
            return self.object.get_type()
        else:
            return PyObject.get_base_type('Unknown')

    def _has_block(self):
        return self.is_defined_here and isinstance(self.object, PyDefinedObject)
    
    def _get_ast(self):
        return self.object._get_ast()


class Scope(object):

    def __init__(self, pycore, pyname, parent_scope):
        self.pycore = pycore
        self.pyname = pyname
        self.parent = parent_scope
    
    def get_names(self):
        """Returns the names defined in this scope"""
        return self.pyname.get_attributes()

    def get_scopes(self):
        """Returns the subscopes of this scope.
        
        The returned scopes should be sorted by the order they appear
        """
        block_objects = [pyname for pyname in self.pyname.get_attributes().values()
                         if pyname._has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = []
        for block in block_objects:
            if block.get_type() == PyObject.get_base_type('Function'):
                result.append(FunctionScope(self.pycore, block, self))
            elif block.get_type() == PyObject.get_base_type('Type'):
                result.append(ClassScope(self.pycore, block, self))
            else:
                result.append(GlobalScope(self.pycore, block))
        return result

    def get_lineno(self):
        return self.pyname._get_ast().lineno

    def get_kind(self):
        pass
    
    def lookup(self, name):
        if name in self.get_names():
            return self.get_names()[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


class GlobalScope(Scope):

    def __init__(self, pycore, module):
        super(GlobalScope, self).__init__(pycore, module, None)

    def get_lineno(self):
        return 1

    def get_kind(self):
        return 'Module'


class FunctionScope(Scope):
    
    def __init__(self, pycore, pyname, parent):
        super(FunctionScope, self).__init__(pycore, pyname, parent)
    
    def get_names(self):
        result = {}
        for name in self.pyname.object.parameters:
            result[name] = PyName()
        new_visitor = _FunctionVisitor(self.pycore)
        for n in self.pyname._get_ast().getChildNodes():
            compiler.walk(n, new_visitor)
        result.update(new_visitor.names)
        return result

    def get_scopes(self):
        new_visitor = _FunctionVisitor(self.pycore)
        for n in self.pyname._get_ast().getChildNodes():
            compiler.walk(n, new_visitor)
        return []

    def get_kind(self):
        return 'Function'


class ClassScope(Scope):

    def __init__(self, pycore, pyname, parent):
        super(ClassScope, self).__init__(pycore, pyname, parent)
    
    def get_names(self):
        return {}

    def get_kind(self):
        return 'Class'


class _ScopeVisitor(object):

    def __init__(self, pycore):
        self.names = {}
        self.pycore = pycore
    
    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore, node), True)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node)
        self.names[node.name] = PyName(pyobject, True)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            try:
                module = self.pycore.get_module(name)
            except ModuleNotFoundException:
                module = PyObject(PyObject.get_base_type('Module'))
            if alias is None and '.' in imported:
                tokens = imported.split('.')
                if tokens[0] in self.names and \
                   isinstance(self.names[tokens[0]].object, PyFilteredPackage):
                    pypkg = self.names[tokens[0]].object
                else:
                    pypkg = PyFilteredPackage()
                    self.names[tokens[0]] = PyName(pypkg)
                for token in tokens[1:-1]:
                    if token in pypkg.get_attributes() and \
                       isinstance(pypkg.get_attributes()[token].object, PyFilteredPackage):
                        newpkg = pypkg.get_attributes()[token].object
                    else:
                        newpkg = PyFilteredPackage()
                        pypkg._add_attribute(token, PyName(newpkg))
                    pypkg = newpkg
                pypkg._add_attribute(tokens[-1], PyName(module, False))
            else:
                self.names[imported] = PyName(module, False)

    def visitFrom(self, node):
        try:
            module = self.pycore.get_module(node.modname)
        except ModuleNotFoundException:
            module = PyFilteredPackage()

        if node.names[0][0] == '*':
            if module.is_package:
                return
            for name, pyname in module.get_attributes().iteritems():
                if not name.startswith('_'):
                    self.names[name] = PyName(pyname.object, False)
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                if module.get_attributes().has_key(name):
                    self.names[imported] = PyName(module.get_attributes()[name].object, False)
                else:
                    self.names[imported] = PyName()


class _GlobalVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_GlobalVisitor, self).__init__(pycore)
    

class _ClassVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_ClassVisitor, self).__init__(pycore)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node)
        self.names[node.name] = PyName(pyobject, True)
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor()
            compiler.walk(node, new_visitor)
            self.names.update(new_visitor.names)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore, node), True)


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_FunctionVisitor, self).__init__(pycore)


class _ClassInitVisitor(object):

    def __init__(self):
        self.names = {}
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.names[node.attrname] = PyName()

