import unittest
import imp
import sys
import xmlrpclib

class TestResultProxy(unittest.TestResult):
    
    def __init__(self, port, count):
        super(TestResultProxy, self).__init__()
        self.remote = xmlrpclib.Server(('http://localhost:' + port))
        self.remote.set_test_count(count)
    
    def startTest(self, test):
        super(TestResultProxy, self).startTest(test)
        self.remote.start_test(test.id())

    def addSuccess(self, test):
        super(TestResultProxy, self).addSuccess(test)
        self.remote.add_success(test.id())

    def addError(self, test, err):
        super(TestResultProxy, self).addError(test, err)
        self.remote.add_error(test.id(), str(err))

    def addFailure(self, test, err):
        super(TestResultProxy, self).addFailure(test, err)
        self.remote.add_failure(test.id(), str(err))
    
    def stopTest(self, test):
        super(TestResultProxy, self).stopTest(test)
        self.remote.stop_test(test.id())

if __name__ == '__main__':
    port = sys.argv[1]
    test_file = sys.argv[2]
    test_module = imp.load_module('test file', open(test_file), test_file,
                                  ('.py', 'r', imp.PY_SOURCE))
    tests = unittest.defaultTestLoader.loadTestsFromModule(test_module)
    result = TestResultProxy(port, tests.countTestCases())
    tests(result)
