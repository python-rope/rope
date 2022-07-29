from unittest import TestCase

from rope.contrib.autoimport import models


class QueryTest(TestCase):
    def test_select_non_existent_column(self):
        with self.assertRaisesRegex(ValueError, """Unknown column names passed: {['"]doesnotexist['"]}"""):
            models.Name.objects.select('doesnotexist')._query


class NameModelTest(TestCase):
    def test_name_objects(self):
        self.assertEqual(
            models.Name.objects.select_star()._query,
            "SELECT * FROM names",
        )

    def test_query_strings(self):
        with self.subTest("objects"):
            self.assertEqual(
                models.Name.objects.select_star()._query,
                'SELECT * FROM names',
            )

        with self.subTest("search_submodule_like"):
            self.assertEqual(
                models.Name.search_submodule_like.select_star()._query,
                'SELECT * FROM names WHERE module LIKE ("%." || ?)',
            )

        with self.subTest("search_module_like"):
            self.assertEqual(
                models.Name.search_module_like.select_star()._query,
                'SELECT * FROM names WHERE module LIKE (?)',
            )

        with self.subTest("import_assist"):
            self.assertEqual(
                models.Name.import_assist.select_star()._query,
                "SELECT * FROM names WHERE name LIKE (? || '%')",
            )

        with self.subTest("search_by_name_like"):
            self.assertEqual(
                models.Name.search_by_name_like.select_star()._query,
                'SELECT * FROM names WHERE name LIKE (?)',
            )

        with self.subTest("delete_by_module_name"):
            self.assertEqual(
                models.Name.delete_by_module_name._query,
                'DELETE FROM names WHERE module = ?',
            )


class PackageModelTest(TestCase):
    def test_query_strings(self):
        with self.subTest("objects"):
            self.assertEqual(
                models.Package.objects.select_star()._query,
                'SELECT * FROM packages',
            )

        with self.subTest("delete_by_package_name"):
            self.assertEqual(
                models.Package.delete_by_package_name._query,
                'DELETE FROM packages WHERE package = ?',
            )
