try:
    import unittest2 as unittest
except ImportError:
    import unittest


from rope.base.oi import objectdb, memorydb
from ropetest import testutils


def _do_for_all_dbs(function):
    def called(self):
        for db in self.dbs:
            function(self, db)
    return called


class _MockValidation(object):

    def is_value_valid(self, value):
        return value != -1

    def is_more_valid(self, new, old):
        return new != -1

    def is_file_valid(self, path):
        return path != 'invalid'

    def is_scope_valid(self, path, key):
        return path != 'invalid' and key != 'invalid'


class _MockFileListObserver(object):

    log = ''

    def added(self, path):
        self.log += 'added %s ' % path

    def removed(self, path):
        self.log += 'removed %s ' % path


class ObjectDBTest(unittest.TestCase):

    def setUp(self):
        super(ObjectDBTest, self).setUp()
        self.project = testutils.sample_project()
        validation = _MockValidation()
        self.dbs = [
            objectdb.ObjectDB(memorydb.MemoryDB(self.project), validation)]

    def tearDown(self):
        for db in self.dbs:
            db.write()
        testutils.remove_project(self.project)
        super(ObjectDBTest, self).tearDown()

    @_do_for_all_dbs
    def test_simple_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        self.assertEqual(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_simple_per_name_does_not_exist(self, db):
        self.assertEquals(None, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_simple_per_name_after_syncing(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.write()
        self.assertEquals(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_getting_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        self.assertEquals(3, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_getting_returned_when_does_not_match(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        self.assertEquals(None, db.get_returned('file', 'key', (1, 1)))

    @_do_for_all_dbs
    def test_getting_call_info(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)

        call_infos = list(db.get_callinfos('file', 'key'))
        self.assertEquals(1, len(call_infos))
        self.assertEquals((1, 2), call_infos[0].get_parameters())
        self.assertEquals(3, call_infos[0].get_returned())

    @_do_for_all_dbs
    def test_invalid_per_name(self, db):
        db.add_pername('file', 'key', 'name', -1)
        self.assertEquals(None, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_overwriting_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.add_pername('file', 'key', 'name', 2)
        self.assertEquals(2, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.add_pername('file', 'key', 'name', -1)
        self.assertEquals(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_getting_invalid_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), -1)
        self.assertEquals(None, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        db.add_callinfo('file', 'key', (1, 2), -1)
        self.assertEquals(3, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_get_files(self, db):
        db.add_callinfo('file1', 'key', (1, 2), 3)
        db.add_callinfo('file2', 'key', (1, 2), 3)
        self.assertEquals(set(['file1', 'file2']), set(db.get_files()))

    @_do_for_all_dbs
    def test_validating_files(self, db):
        db.add_callinfo('invalid', 'key', (1, 2), 3)
        db.validate_files()
        self.assertEquals(0, len(db.get_files()))

    @_do_for_all_dbs
    def test_validating_file_for_scopes(self, db):
        db.add_callinfo('file', 'invalid', (1, 2), 3)
        db.validate_file('file')
        self.assertEquals(1, len(db.get_files()))
        self.assertEquals(0, len(list(db.get_callinfos('file', 'invalid'))))

    @_do_for_all_dbs
    def test_validating_file_moved(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)

        db.file_moved('file', 'newfile')
        self.assertEquals(1, len(db.get_files()))
        self.assertEquals(1, len(list(db.get_callinfos('newfile', 'key'))))

    @_do_for_all_dbs
    def test_using_file_list_observer(self, db):
        db.add_callinfo('invalid', 'key', (1, 2), 3)
        observer = _MockFileListObserver()
        db.add_file_list_observer(observer)
        db.validate_files()
        self.assertEquals('removed invalid ', observer.log)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectDBTest))
    return result


if __name__ == '__main__':
    unittest.main()
