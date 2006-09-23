import rope.codeanalyze
import rope.refactor.rename


class IntroduceFactoryRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore

    def introduce_factory(self, resource, offset, factory_name):
        pymodule = self.pycore.resource_to_pyobject(resource)
        module_scope = pymodule.get_scope()
        source_code = pymodule.source_code
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        
        class_scope = old_pyname.get_object().get_scope()
        
        new_function_name = old_name + '.' + factory_name
        for file_ in self.pycore.get_python_files():
            if file_ == resource:
                continue
            rename_in_module = rope.refactor.rename.RenameInModule(self.pycore, [old_pyname],
                                                                   old_name, new_function_name, True)
            changed_code = rename_in_module.get_changed_module(resource=file_)
            if changed_code is not None:
                file_.write(changed_code)
    
        rename_in_module = rope.refactor.rename.RenameInModule(self.pycore, [old_pyname],
                                                               old_name, new_function_name, True)
        source_code2 = rename_in_module.get_changed_module(pymodule=pymodule)
        if source_code2 is None:
            source_code2 = source_code
        lines = source_code2.splitlines(True)
        start = class_scope.get_end() - 1
        result = lines[:start]
        result.append('\n')
        result.append('    @staticmethod\n')
        result.append('    def %s(*args, **kws):\n' % factory_name)
        result.append('        return %s(*args, **kws)\n' % old_name)
        result.extend(lines[start:])
        resource.write(''.join(result))
