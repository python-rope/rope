import imp
import os
import sys
import traceback
import unittest
import xmlrpclib


class TestResultProxy(unittest.TestResult):

    def __init__(self, port, count):
        super(TestResultProxy, self).__init__()
        self.remote = xmlrpclib.Server(('http://localhost:' + port))
        self.remote.set_test_count(count)

    def startTest(self, test):
        super(TestResultProxy, self).startTest(test)
        self.remote.start_test(str(test))

    def addSuccess(self, test):
        super(TestResultProxy, self).addSuccess(test)
        self.remote.add_success(str(test))

    def addError(self, test, err):
        super(TestResultProxy, self).addError(test, err)
        self.remote.add_error(str(test), self._exc_info_to_string(err, test))

    def addFailure(self, test, err):
        super(TestResultProxy, self).addFailure(test, err)
        self.remote.add_failure(str(test), self._exc_info_to_string(err, test))

    def stopTest(self, test):
        super(TestResultProxy, self).stopTest(test)
        self.remote.stop_test(str(test))

    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        # Skip test runner traceback levels
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next
        if exctype is test.failureException:
            # Skip assert*() traceback levels
            length = self._count_relevant_tb_levels(tb)
            return ''.join(traceback.format_exception(exctype, value, tb, length))
        return ''.join(traceback.format_exception(exctype, value, tb))


if __name__ == '__main__':
    port = sys.argv[1]
    test_file = sys.argv[2]
    module_name = ' ' + os.path.splitext(os.path.basename(test_file))[0]
    test_module = imp.load_module(module_name, open(test_file), test_file,
                                  ('.py', 'r', imp.PY_SOURCE))
    tests = unittest.defaultTestLoader.loadTestsFromModule(test_module)
    result = TestResultProxy(port, tests.countTestCases())
    tests(result)
