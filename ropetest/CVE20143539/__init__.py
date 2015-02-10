import os.path
import subprocess
try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestCVE20143539(unittest.TestCase):
    def test_case(self):
        cur_dir = os.path.dirname(__file__)
        script_name = os.path.join(cur_dir, 'run_reproducer.sh')
        pid = subprocess.Popen([script_name], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=cur_dir)
        pid.communicate()
        self.assertEquals(pid.returncode, 0)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(TestCVE20143539))
    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        unittest.main()
    else:
        runner = unittest.TextTestRunner()
        res = runner.run(suite())
        sys.exit(not res.wasSuccessful())
