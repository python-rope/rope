import unittest
import Tkinter

from rope.ui.statusbar import StatusBarManager, StatusBarException

class StatusBarTest(unittest.TestCase):

    def setUp(self):
        super(StatusBarTest, self).setUp()
        if not hasattr(StatusBarTest, '_frame'):
            StatusBarTest._frame = Tkinter.Frame()
        self.manager = StatusBarManager(StatusBarTest._frame)

    def tearDown(self):
        super(StatusBarTest, self).tearDown()

    def test_status_bar_manager(self):
        status = self.manager.create_status('sample')
        status.set_text('sample status')
        self.assertEquals('sample status', status.get_text())
        self.assertEquals('sample status', self.manager.get_status('sample').get_text())

    def test_status_bar_manager_multiple_status(self):
        status1 = self.manager.create_status('sample1')
        status2 = self.manager.create_status('sample2')
        status1.set_text('1. sample status')
        status2.set_text('2. sample status')
        self.assertEquals('1. sample status', status1.get_text())
        self.assertEquals('2. sample status', status2.get_text())

    def test_status_removing(self):
        status = self.manager.create_status('sample')
        self.assertEquals(status, self.manager.get_status('sample'))
        status.remove()
        self.assertNotEquals(status, self.manager.create_status('sample'))

    def test_getting_a_nonexistent_status(self):
        try:
            status = self.manager.get_status('nonexistent')
            self.fail('should have raised exception')
        except StatusBarException:
            pass

    def test_creating_a_status_while_it_exists(self):
        self.manager.create_status('sample')
        try:
            status = self.manager.create_status('sample')
            self.fail('should have raised exception')
        except StatusBarException:
            pass


if __name__ == '__main__':
    unittest.main()
