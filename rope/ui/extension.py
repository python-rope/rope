class Action(object):
    """Extending rope commands
    
    Represents an action that can have keyboard short-cut and
    menu item.  The `do` method is called when the action was
    invoked
    """
    
    def get_name(self):
        pass
    
    def do(self, context):
        pass
    
    def get_menu(self):
        pass
    
    def get_default_key(self):
        pass
    
    def get_active_contexts(self):
        pass


class ActionContext(object):
    
    def __init__(self, core):
        self.core = core
    
    def get_core(self):
        return self.core
    
    def get_active_editor(self):
        return self.core.get_editor_manager().active_editor


class SimpleAction(object):
    
    def __init__(self, name, command, default_key, menu_address,
                 active_contexts=['all', 'none']):
        self.name = name
        self.command = command
        self.key = default_key
        self.menu = menu_address
        self.active_contexts = active_contexts
    
    def get_name(self):
        return self.name
    
    def do(self, context):
        self.command(context)
    
    def get_menu(self):
        return self.menu
    
    def get_default_key(self):
        return self.key
    
    def get_active_contexts(self):
        return self.active_contexts
