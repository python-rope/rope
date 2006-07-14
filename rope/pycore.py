import compiler
import os
import subprocess
import sys

import rope.exceptions
from rope.exceptions import RopeException


class ModuleNotFoundException(rope.exceptions.RopeException):
    """Module not found exception"""


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self.module_map = {}

    def get_module(self, name):
        results = self.find_module(name)
        if not results:
            raise ModuleNotFoundException('Module %s not found' % name)
        result = results[0]
        return self._create(results[0])

    def get_string_module(self, module_content):
        ast = compiler.parse(module_content)
        return PyModule(self, ast)

    def get_string_scope(self, module_content):
        return self.get_string_module(module_content).get_scope()

    def _invalidate_resource_cache(self, resource):
        if resource in self.module_map:
            del self.module_map[resource]
            resource.remove_change_observer(self._invalidate_resource_cache)

    def _create(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self, resource)
        else:
            ast = compiler.parse(resource.read())
            result = PyModule(self, ast, resource=resource)
        self.module_map[resource] = result
        resource.add_change_observer(self._invalidate_resource_cache)
        return result

    def create_module(self, src_folder, new_module):
        packages = new_module.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        return parent.create_file(packages[-1] + '.py')

    def create_package(self, src_folder, new_package):
        packages = new_package.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        created_package = parent.create_folder(packages[-1])
        created_package.create_file('__init__.py')
        return created_package

    def _find_module_in_source_folder(self, source_folder, module_name):
        module = source_folder
        packages = module_name.split('.')
        for pkg in packages[:-1]:
            if  module.is_folder() and module.has_child(pkg):
                module = module.get_child(pkg)
            else:
                return None
        if not module.is_folder():
            return None

        if module.has_child(packages[-1]) and \
           module.get_child(packages[-1]).is_folder():
            return module.get_child(packages[-1])
        elif module.has_child(packages[-1] + '.py') and \
             not module.get_child(packages[-1] + '.py').is_folder():
            return module.get_child(packages[-1] + '.py')
        return None

    def _get_python_path_folders(self):
        result = []
        for src in sys.path:
            try:
                src_folder = self.project.get_out_of_project_resource(src)
                result.append(src_folder)
            except rope.exceptions.RopeException:
                pass
        return result
    
    def find_module(self, module_name):
        result = []
        for src in self.get_source_folders():
            module = self._find_module_in_source_folder(src, module_name)
            if module is not None:
                result.append(module)
        if result:
            return result
        for src in self._get_python_path_folders():
            module = self._find_module_in_source_folder(src, module_name)
            if module is not None:
                result.append(module)
        return result

    def get_source_folders(self):
        return self._find_source_folders(self.project.get_root_folder())

    def _is_package(self, folder):
        init_dot_py = folder.get_path() + '/__init__.py'
        try:
            init_dot_py_file = self.project.get_resource(init_dot_py)
            if not init_dot_py_file.is_folder():
                return True
        except RopeException:
            pass
        return False

    def _find_source_folders(self, folder):
        for resource in folder.get_folders():
            if self._is_package(resource):
                return [folder]
        result = []
        for resource in folder.get_files():
            if resource.get_name().endswith('.py'):
                result.append(folder)
        for resource in folder.get_folders():
            result.extend(self._find_source_folders(resource))
        return result


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

    def _update_attributes_from_ast(self, attributes):
        pass
    
    def _create_scope(self):
        return FunctionScope(self.pycore, self)
    
    def _get_resource(self):
        module = self.get_module()
        if module is not None:
            return module.get_resource()
        else:
            return None


    def _get_parameters(self):
        result = {}
        if len(self.parameters) > 0:
            if self.parent.get_type() == PyObject.get_base_type('Type') and \
               not self.decorators:
                result[self.parameters[0]] = PyName(PyObject(self.parent),
                                                    lineno=self.ast_node.lineno,
                                                    module=self._get_resource())
            else:
                result[self.parameters[0]] = PyName(lineno=self.ast_node.lineno,
                                                    module=self._get_resource())
        if len(self.parameters) > 1:
            for parameter in self.parameters[1:]:
                result[parameter] = PyName(lineno=self.ast_node.lineno,
                                           module=self._get_resource())
        return result


class _AttributeListFinder(object):

    def __init__(self):
        self.name_list = []
        
    def visitName(self, node):
        self.name_list.append(node.name)
    
    def visitGetattr(self, node):
        compiler.walk(node.expr, self)
        self.name_list.append(node.attrname)

    @staticmethod
    def get_attribute_list(node):
        finder = _AttributeListFinder()
        compiler.walk(node, finder)
        return finder.name_list        

    @staticmethod
    def get_pyname_from_scope(attribute_list, scope):
        pyobject = scope.lookup(attribute_list[0])
        if pyobject != None and len(attribute_list) > 1:
            for name in attribute_list[1:]:
                if name in pyobject.get_attributes():
                    pyobject = pyobject.get_attributes()[name]
                else:
                    pyobject = None
                    break
        return pyobject
    
    @staticmethod
    def get_attribute(node, scope):
        finder = _AttributeListFinder()
        compiler.walk(node, finder)
        return _AttributeListFinder.get_pyname_from_scope(finder.name_list, scope)


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
            base = _AttributeListFinder.get_attribute(base_name,
                                                      self.parent.get_scope())
            if base:
                result.append(base)
        return result

    def _create_scope(self):
        return ClassScope(self.pycore, self)


class PyModule(PyDefinedObject):

    def __init__(self, pycore, ast_node, resource=None):
        super(PyModule, self).__init__(PyObject.get_base_type('Module'),
                                       pycore, ast_node, None)
        self.resource = resource
        self.is_package = False

    def _update_attributes_from_ast(self, attributes):
        visitor = _GlobalVisitor(self.pycore, self)
        compiler.walk(self.ast_node, visitor)
        attributes.update(visitor.names)

    def _create_scope(self):
        return GlobalScope(self.pycore, self)

    def get_resource(self):
        return self.resource

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
                elif child.get_name().endswith('.py') and \
                     child.get_name() != '__init__.py':
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

    def __init__(self, object_=None, is_defined_here=False, lineno=None, module=None):
        self.object = object_
        if self.object is None:
            self.object = PyObject(PyObject.get_base_type('Unknown'))
        self.is_defined_here = is_defined_here
        self.lineno = lineno
        self.module = module
        if self.has_block():
            self.lineno = self._get_ast().lineno

    def update_object(self, object_=None, is_defined_here=False, lineno=None, module=None):
        self.__init__(object_, is_defined_here, self.lineno, module=module)

    def get_attributes(self):
        return self.object.get_attributes()

    def get_object(self):
        return self.object
        
    def get_type(self):
        return self.object.get_type()

    def get_definition_location(self):
        """Returns a (module, lineno) tuple"""
        return (self.module, self.lineno)

    def has_block(self):
        return self.is_defined_here and isinstance(self.object,
                                                   PyDefinedObject)
    
    def _get_ast(self):
        return self.object._get_ast()


class Scope(object):

    def __init__(self, pycore, pyobject, parent_scope):
        self.pycore = pycore
        self.pyobject = pyobject
        self.parent = parent_scope
        self.scopes = None
    
    def get_names(self):
        """Returns the names defined in this scope"""
        return self.pyobject.get_attributes()

    def get_scopes(self):
        """Returns the subscopes of this scope.
        
        The returned scopes should be sorted by the order they appear
        """
        if self.scopes == None:
            self.scopes = self._create_scopes()
        return self.scopes

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in
                         self.pyobject.get_attributes().values()
                         if pyname.has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_lineno(self):
        return self.pyobject._get_ast().lineno

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
    
    def __init__(self, pycore, pyobject):
        super(FunctionScope, self).__init__(pycore, pyobject,
                                            pyobject.parent.get_scope())
        self.names = None
    
    def _get_names(self):
        if self.names == None:
            new_visitor = _FunctionVisitor(self.pycore, self.pyobject)
            for n in self.pyobject._get_ast().getChildNodes():
                compiler.walk(n, new_visitor)
            self.names = self.pyobject._get_parameters()
            self.names.update(new_visitor.names)
        return self.names
    
    def get_names(self):
        return self._get_names()

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in self._get_names().values()
                         if pyname.has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_kind(self):
        return 'Function'


class ClassScope(Scope):

    def __init__(self, pycore, pyobject):
        super(ClassScope, self).__init__(pycore, pyobject,
                                         pyobject.parent.get_scope())
    
    def get_names(self):
        return {}

    def get_kind(self):
        return 'Class'


class _AssignVisitor(object):

    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor
        self.assigned_object = None
    
    def _search_in_dictionary_for_attribute_list(self, names, attribute_list):
        pyobject = names.get(attribute_list[0], None)
        if pyobject != None and len(attribute_list) > 1:
            for name in attribute_list[1:]:
                if name in pyobject.get_attributes():
                    pyobject = pyobject.get_attributes()[name].get_object()
                else:
                    pyobject = None
                    break
        return pyobject
        
    def visitAssign(self, node):
        type_ = None
        if isinstance(node.expr, compiler.ast.CallFunc):
            function_name = _AttributeListFinder.get_attribute_list(node.expr.node)
            function_object = self._search_in_dictionary_for_attribute_list(self.scope_visitor.names,
                                                                            function_name)
            if function_object is None and self.scope_visitor.owner_object.parent is not None:
                function_object = _AttributeListFinder.\
                                  get_pyname_from_scope(function_name,
                                                        self.scope_visitor.owner_object.parent.get_scope())
            if function_object is not None:
                if function_object.get_type() == PyObject.get_base_type('Type'):
                    type_ = function_object.get_object()
        self.assigned_object = PyObject(type_=type_)
        for child_node in node.nodes:
            compiler.walk(child_node, self)

    def visitAssName(self, node):
        if node.name in self.scope_visitor.names:
            self.scope_visitor.names[node.name].update_object(object_=self.assigned_object,
                                                              lineno=node.lineno, 
                                                              module=self.scope_visitor.get_resource())
        else:
            self.scope_visitor.names[node.name] = PyName(object_=self.assigned_object,
                                                         lineno=node.lineno,
                                                         module=self.scope_visitor.get_resource())


class _ScopeVisitor(object):

    def __init__(self, pycore, owner_object):
        self.names = {}
        self.pycore = pycore
        self.owner_object = owner_object

    def get_resource(self):
        if self.owner_object is not None:
            return self.owner_object.get_module().get_resource()
        else:
            return None
        
    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore,
                                               node, self.owner_object), True,
                                       module=self.get_resource())

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = PyName(pyobject, True, module=self.get_resource())

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
            except ModuleNotFoundException:
                module = PyObject(PyObject.get_base_type('Module'))
                module.is_package = False
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
                       isinstance(pypkg.get_attributes()[token].object,
                                  PyFilteredPackage):
                        newpkg = pypkg.get_attributes()[token].object
                    else:
                        newpkg = PyFilteredPackage()
                        pypkg._add_attribute(token, PyName(newpkg))
                    pypkg = newpkg
                pypkg._add_attribute(tokens[-1], PyName(module, False, module=module, lineno=1))
            else:
                self.names[imported] = PyName(module, False, module=module, lineno=1)

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
                    pyname_module = module
                    if pyname.module is not None:
                        pyname_module = pyname.module
                    self.names[name] = PyName(pyname.object, False, module=pyname_module,
                                              lineno=pyname.get_definition_location()[1])
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                if module.get_attributes().has_key(name):
                    imported_pyname = module.get_attributes()[name]
                    imported_object = imported_pyname.object
                    if isinstance(imported_object, PyPackage):
                        self.names[imported] = PyFilteredPackage()
                    else:
                        pyname_module = module
                        if imported_pyname.module is not None:
                            pyname_module = imported_pyname.module
                        self.names[imported] = PyName(imported_object, False, module=pyname_module,
                                                      lineno=imported_pyname.get_definition_location()[1])
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
        self.names[node.name] = PyName(pyobject, True, module=self.get_resource())
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor(self)
            compiler.walk(node, new_visitor)

    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore, node,
                                               self.owner_object), True, 
                                       module=self.get_resource())


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_FunctionVisitor, self).__init__(pycore, owner_object)


class _ClassInitVisitor(_AssignVisitor):

    def __init__(self, scope_visitor):
        super(_ClassInitVisitor, self).__init__(scope_visitor)
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.scope_visitor.names[node.attrname] = PyName(object_=self.assigned_object,
                                                             lineno=node.lineno, 
                                                             module=self.scope_visitor.get_resource())
    
    def visitAssName(self, node):
        pass


class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, file, stdin=None, stdout=None):
        self.file = file
        file_path = self.file._get_real_path()
        env = {}
        env.update(os.environ)
        source_folders = []
        for folder in file.get_project().get_pycore().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        self.process = subprocess.Popen(executable=sys.executable,
                                        args=(sys.executable, self.file.get_name()),
                                        cwd=os.path.split(file_path)[0], stdin=stdin,
                                        stdout=stdout, stderr=stdout, env=env)

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()

    def kill_process(self):
        """Stop the process. This does not work on windows."""
        os.kill(self.process.pid, 9)


