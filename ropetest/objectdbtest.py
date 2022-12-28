import unittest

from rope.base.oi import memorydb, objectdb
from ropetest import testutils


def _do_for_all_dbs(function):
    def called(self):
        for db in self.dbs:
            function(self, db)

    return called


class _MockValidation:
    def is_value_valid(self, value):
        return value != -1

    def is_more_valid(self, new, old):
        return new != -1

    def is_file_valid(self, path):
        return path != "invalid"

    def is_scope_valid(self, path, key):
        return path != "invalid" and key != "invalid"


class _MockFileListObserver:

    log = ""

    def added(self, path):
        self.log += "added %s " % path

    def removed(self, path):
        self.log += "removed %s " % path


class ObjectDBTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        validation = _MockValidation()
        self.dbs = [objectdb.ObjectDB(memorydb.MemoryDB(self.project), validation)]

    def tearDown(self):
        for db in self.dbs:
            db.write()
        testutils.remove_project(self.project)
        super().tearDown()

    @_do_for_all_dbs
    def test_simple_per_name(self, db):
        db.add_pername("file", "key", "name", 1)
        self.assertEqual(1, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_simple_per_name_does_not_exist(self, db):
        self.assertEqual(None, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_simple_per_name_after_syncing(self, db):
        db.add_pername("file", "key", "name", 1)
        db.write()
        self.assertEqual(1, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_getting_returned(self, db):
        db.add_callinfo("file", "key", (1, 2), 3)
        self.assertEqual(3, db.get_returned("file", "key", (1, 2)))

    @_do_for_all_dbs
    def test_getting_returned_when_does_not_match(self, db):
        db.add_callinfo("file", "key", (1, 2), 3)
        self.assertEqual(None, db.get_returned("file", "key", (1, 1)))

    @_do_for_all_dbs
    def test_getting_call_info(self, db):
        db.add_callinfo("file", "key", (1, 2), 3)

        call_infos = list(db.get_callinfos("file", "key"))
        self.assertEqual(1, len(call_infos))
        self.assertEqual((1, 2), call_infos[0].get_parameters())
        self.assertEqual(3, call_infos[0].get_returned())

    @_do_for_all_dbs
    def test_invalid_per_name(self, db):
        db.add_pername("file", "key", "name", -1)
        self.assertEqual(None, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_overwriting_per_name(self, db):
        db.add_pername("file", "key", "name", 1)
        db.add_pername("file", "key", "name", 2)
        self.assertEqual(2, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_per_name(self, db):
        db.add_pername("file", "key", "name", 1)
        db.add_pername("file", "key", "name", -1)
        self.assertEqual(1, db.get_pername("file", "key", "name"))

    @_do_for_all_dbs
    def test_getting_invalid_returned(self, db):
        db.add_callinfo("file", "key", (1, 2), -1)
        self.assertEqual(None, db.get_returned("file", "key", (1, 2)))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_returned(self, db):
        db.add_callinfo("file", "key", (1, 2), 3)
        db.add_callinfo("file", "key", (1, 2), -1)
        self.assertEqual(3, db.get_returned("file", "key", (1, 2)))

    @_do_for_all_dbs
    def test_get_files(self, db):
        db.add_callinfo("file1", "key", (1, 2), 3)
        db.add_callinfo("file2", "key", (1, 2), 3)
        self.assertEqual({"file1", "file2"}, set(db.get_files()))

    @_do_for_all_dbs
    def test_validating_files(self, db):
        db.add_callinfo("invalid", "key", (1, 2), 3)
        db.validate_files()
        self.assertEqual(0, len(db.get_files()))

    @_do_for_all_dbs
    def test_validating_file_for_scopes(self, db):
        db.add_callinfo("file", "invalid", (1, 2), 3)
        db.validate_file("file")
        self.assertEqual(1, len(db.get_files()))
        self.assertEqual(0, len(list(db.get_callinfos("file", "invalid"))))

    @_do_for_all_dbs
    def test_validating_file_moved(self, db):
        db.add_callinfo("file", "key", (1, 2), 3)

        db.file_moved("file", "newfile")
        self.assertEqual(1, len(db.get_files()))
        self.assertEqual(1, len(list(db.get_callinfos("newfile", "key"))))

    @_do_for_all_dbs
    def test_using_file_list_observer(self, db):
        db.add_callinfo("invalid", "key", (1, 2), 3)
        observer = _MockFileListObserver()
        db.add_file_list_observer(observer)
        db.validate_files()
        self.assertEqual("removed invalid ", observer.log)

    @_do_for_all_dbs
    def test_legacy_serialization(self, db):
        import pickle

        db.add_callinfo("file", "key", (1, 2), 3)
        db.add_pername("file", "key", "name", 1)
        scope_info = db._get_scope_info("file", "key")

        pickled_data = b'\x80\x04\x95D\x00\x00\x00\x00\x00\x00\x00\x8c\x15rope.base.oi.memorydb\x94\x8c\tScopeInfo\x94\x93\x94)\x81\x94}\x94K\x01K\x02\x86\x94K\x03s}\x94\x8c\x04name\x94K\x01s\x86\x94b.'  # noqa

        assert pickle.loads(pickled_data).call_info == scope_info.call_info
        assert pickle.loads(pickled_data).per_name == scope_info.per_name

    @_do_for_all_dbs
    def test_new_pickle_serialization(self, db):
        import pickle

        db.add_callinfo("file", "key", (1, 2), 3)
        db.add_pername("file", "key", "name", 1)
        scope_info = db._get_scope_info("file", "key")

        serialized = pickle.dumps(scope_info)

        rehydrated_data = pickle.loads(serialized)
        assert rehydrated_data.call_info == scope_info.call_info
        assert rehydrated_data.per_name == scope_info.per_name

    @_do_for_all_dbs
    def test_new_json_serialization(self, db):
        import json

        from rope.base.oi.memorydb import ScopeInfo

        db.add_callinfo("file", "key", (1, 2), 3)
        db.add_pername("file", "key", "name", 1)
        scope_info = db._get_scope_info("file", "key")

        data = {"inside": [scope_info], "other": scope_info, "things": [1, 2, 3]}

        def object_hook(o):
            if o.get("$") == "ScopeInfo":
                new_o = ScopeInfo.__new__(ScopeInfo)
                new_o.__setstate__(o)
                return new_o
            return o

        serialized = json.dumps(data, default=lambda o: o.__getstate__())
        rehydrated_data = json.loads(serialized, object_hook=object_hook)

        rehydrated_scope_info = rehydrated_data["inside"][0]
        assert isinstance(rehydrated_scope_info, ScopeInfo)
        assert rehydrated_scope_info.call_info == scope_info.call_info
        assert rehydrated_scope_info.per_name == scope_info.per_name
