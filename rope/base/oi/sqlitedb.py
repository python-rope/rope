import cPickle as pickle
import UserDict
import sqlite3
import threading

from rope.base.oi import objectdb


class SqliteDB(objectdb.FileDict):

    def __init__(self, project):
        self.project = project
        self.all_connections = []
        self.main_thread = threading.currentThread()
        self._connection = None
        self._cursor = None
        if not self._get_db_file().exists():
            self.create_tables()
        self.files_table = Table(self, 'files')
        self.scopes_table = Table(self, 'scopes')
        self.callinfos_table = Table(self, 'callinfos')
        self.pernames_table = Table(self, 'pernames')
        self.files = FilesTable(self)

    def _get_cursor(self):
        if self._connection is None:
            db = self._get_db_file()
            self._connection = sqlite3.connect(db.real_path)
            self._cursor = self._connection.cursor()
        return self._cursor

    def execute(self, command, args=[]):
        if self.main_thread == threading.currentThread():
            result = list(self.cursor.execute(command, args).fetchall())
            self._connection.commit()
            return result
        else:
            db = self._get_db_file()
            connection = sqlite3.connect(db.real_path)
            cursor = connection.cursor()
            result = list(cursor.execute(command, args))
            connection.commit()
            cursor.close()
            connection.close()
            return result

    def _get_db_file(self):
        return self.project.get_file(self.project.ropefolder.path +
                                     '/objectdb.sqlite3')

    cursor = property(_get_cursor)

    def create_tables(self):
        files_table = 'CREATE TABLE files(' \
                      'file_id INTEGER NOT NULL,' \
                      'path VARCHAR(255),' \
                      'PRIMARY KEY (file_id))'

        scopes_table = 'CREATE TABLE scopes(' \
                       'scope_id INTEGER NOT NULL,' \
                       'file_id INTEGER,' \
                       'key VARCHAR(255),' \
                       'PRIMARY KEY (scope_id),' \
                       'FOREIGN KEY (file_id) REFERENCES files (file_id))'

        callinfo_table = 'CREATE TABLE callinfos(' \
                         'scope_id INTEGER,' \
                         'args BLOB,' \
                         'returned BLOB,' \
                         'FOREIGN KEY (scope_id) REFERENCES scopes (scope_id))'

        pername_table = 'CREATE TABLE pernames(' \
                        'scope_id INTEGER,' \
                        'name VARCHAR(255),' \
                        'value BLOB,' \
                        'FOREIGN KEY (scope_id) REFERENCES scopes (scope_id))'
        self.execute(files_table)
        self.execute(scopes_table)
        self.execute(callinfo_table)
        self.execute(pername_table)

    def sync(self):
        if self._connection is not None:
            self._connection.commit()
            self._cursor.close()
            self._connection.close()
            self._cursor = None
            self._connection = None


class FilesTable(objectdb.FileDict):

    def __init__(self, db):
        self.db = db
        self.table = db.files_table

    def keys(self):
        return [item[0] for item in self.table.select('path')]

    def __getitem__(self, path):
        file_id = self.table.select('file_id', path=path)[0][0]
        return _FileInfo(self.db, file_id)

    def create(self, path):
        self.table.insert(path=path)

    def __contains__(self, path):
        return self.table.contains(path=path)

    def rename(self, path, newpath):
        self.table.update({'path': newpath}, path=path)

    def __delitem__(self, path):
        file_id = self.table.select('file_id', path=path)[0][0]
        keys = self.db.scopes_table.select('key', file_id=file_id)
        file_info = _FileInfo(self.db, file_id)
        for key in keys:
            del file_info[key[0]]
        self.table.delete(path=path)


class _FileInfo(objectdb.FileInfo):

    def __init__(self, db, file_id):
        self.db = db
        self.file_id = file_id
        self.table = db.scopes_table

    def create_scope(self, key):
        self.table.insert(file_id=self.file_id, key=key)

    def keys(self):
        return [item[0] for item in self.table.select(
                'key', file_id=self.file_id)]

    def __contains__(self, key):
        return self.table.contains(file_id=self.file_id, key=key)

    def __getitem__(self, key):
        scope_id = self.table.select(
            'scope_id', file_id=self.file_id, key=key)[0][0]
        return _ScopeInfo(self.db, scope_id)

    def __delitem__(self, key):
        scope_id = self.table.select('scope_id', key=key)[0][0]
        self.db.callinfos_table.delete(scope_id=scope_id)
        self.db.pernames_table.delete(scope_id=scope_id)
        self.table.delete(key=key)


class _ScopeInfo(objectdb.ScopeInfo):

    def __init__(self, db, scope_id):
        self.db = db
        self.scope_id = scope_id
        self.callinfo = db.callinfos_table
        self.pername = db.pernames_table

    def get_per_name(self, name):
        result = self.pername.select('value', scope_id=self.scope_id,
                                     name=name)
        if result:
            return pickle.loads(str(result[0][0]))
        return None

    def save_per_name(self, name, value):
        value = buffer(pickle.dumps(value))
        self.pername.update({'value': value},
                            scope_id=self.scope_id, name=name)

    def get_returned(self, parameters):
        parameters = buffer(pickle.dumps(parameters))
        result = self.callinfo.select('returned', scope_id=self.scope_id,
                                      args=parameters)
        if result:
            return pickle.loads(str(result[0][0]))
        return None

    def get_call_infos(self):
        result = self.callinfo.select('args, returned', scope_id=self.scope_id)
        for args, returned in result:
            yield objectdb.CallInfo(pickle.loads(str(args)),
                                    pickle.loads(str(returned)))

    def add_call(self, parameters, returned):
        parameters = buffer(pickle.dumps(parameters))
        returned = buffer(pickle.dumps(returned))
        self.callinfo.update({'returned': returned},
                             args=parameters, scope_id=self.scope_id)


class Table(object):

    def __init__(self, db, name):
        self.db = db
        self.name = name

    def select(self, what='*', **kwds):
        where = self._get_where(kwds)
        command = 'SELECT %s FROM %s %s' % (what, self.name, where)
        return self.db.execute(command, kwds.values())

    def _get_where(self, kwds):
        conditions = []
        for key in kwds:
            conditions.append('%s = ?' % key)
        if conditions:
            return 'WHERE ' + ' AND '.join(conditions)
        return ''

    def contains(self, **kwds):
        return len(self.select(**kwds)) > 0

    def insert(self, **kwds):
        if self.contains(**kwds):
            self.delete(**kwds)
        names = []
        for name in kwds:
            names.append(name)
        values = []
        for value in kwds.values():
            values.append(value)
        command = 'INSERT INTO %s (%s) VALUES (%s)' % \
                  (self.name, ', '.join(names),
                   ', '.join(['?'] * len(values)))
        self.db.execute(command, values)

    def delete(self, **kwds):
        where = self._get_where(kwds)
        command = 'DELETE FROM %s %s' % (self.name, where)
        return self.db.execute(command, kwds.values())

    def update(self, sets, **kwds):
        if not self.contains(**kwds):
            new_kwds = dict(kwds)
            new_kwds.update(sets)
            self.insert(**new_kwds)
            return
        where = self._get_where(kwds)
        values = []
        commands = []
        for key, value in sets.items():
            commands.append('%s = ?' % key)
            values.append(value)
        values.extend(kwds.values())
        command = 'UPDATE %s SET %s %s' % (self.name,
                                           ', '.join(commands), where)
        return self.db.execute(command, values)
