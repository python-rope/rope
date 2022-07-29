from unittest import TestCase

from rope.contrib.autoimport import models


class NameModelTest(TestCase):
    def test_select_non_existent_column(self):
        with self.assertRaisesRegex(ValueError, """Unknown column names passed: {['"]doesnotexist['"]}"""):
            models.Name.objects.select('doesnotexist')._query

