import difflib


class Change(object):

    def do(self):
        pass

    def undo(self):
        pass

    def get_description(self):
        return str(self)


class ChangeSet(Change):

    def __init__(self):
        self.changes = []

    def do(self):
        try:
            done = []
            for change in self.changes:
                change.do()
                done.append(change)
        except Exception:
            for change in done:
                change.undo()
            raise

    def undo(self):
        try:
            done = []
            for change in reversed(self.changes):
                change.undo()
                done.append(change)
        except Exception:
            for change in done:
                change.do()
            raise

    def add_change(self, change):
        self.changes.append(change)


class ChangeContents(Change):

    def __init__(self, resource, new_content):
        self.resource = resource
        self.new_content = new_content
        self.old_content = None

    def do(self):
        self.old_content = self.resource.read()
        self.resource.write(self.new_content)

    def undo(self):
        self.resource.write(self.old_content)

    def __str__(self):
        return 'Change <%s>' % self.resource.get_path()

    def get_description(self):
        differ = difflib.Differ()
        result = list(differ.compare(self.resource.read().splitlines(True),
                                     self.new_content.splitlines(True)))
        return ''.join(result)


class MoveResource(Change):

    def __init__(self, resource, new_location):
        self.project = resource.project
        self.new_location = new_location
        self.old_location = resource.get_path()

    def do(self):
        resource = self.project.get_resource(self.old_location)
        resource.move(self.new_location)

    def undo(self):
        resource = self.project.get_resource(self.new_location)
        resource.move(self.old_location)

    def __str__(self):
        return 'Move <%s>' % self.old_location

    def get_description(self):
        return 'Move <%s> to <%s>' % (self.old_location, self.new_location)


class CreateFolder(Change):

    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self.new_folder = None

    def do(self):
        self.new_folder = self.parent.create_folder(self.name)

    def undo(self):
        self.new_folder.remove()

    def __str__(self):
        return 'Create Folder <%s>' % (self.parent.get_path() + '/' + self.name)

