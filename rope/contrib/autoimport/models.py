from typing import List


class Query:
    def __init__(self, query: str, columns: List[str]):
        self.query = query
        self.columns = columns

    def select(self, *columns):
        assert set(columns) <= set(self.columns)
        selected_columns = ", ".join(columns)
        return f"SELECT {selected_columns} FROM {self.query}"

    def select_star(self):
        return f"SELECT * FROM {self.query}"

    def where(self, where_clause):
        return Query(
            f"{self.query} WHERE {where_clause}",
            columns=self.columns,
        )


class Name:
    columns = [
        "name",
        "module",
        "package",
        "source",
        "type",
    ]

    @classmethod
    def create_table(self, connection):
        names_table = (
            "(name TEXT, module TEXT, package TEXT, source INTEGER, type INTEGER)"
        )
        connection.execute(f"CREATE TABLE IF NOT EXISTS names{names_table}")
        connection.execute("CREATE INDEX IF NOT EXISTS name ON names(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS module ON names(module)")
        connection.execute("CREATE INDEX IF NOT EXISTS package ON names(package)")

    get_all = Query("names", columns)
    insert = (
        "INSERT INTO names(name, module, package, source, type) VALUES (?, ?, ?, ?, ?)"
    )
    drop_table = "DROP TABLE names"

    search_submodule_like = get_all.where('module LIKE ("%." || ?)')
    search_module_like = get_all.where("module LIKE (?)")

    import_assist = get_all.where("name LIKE (? || '%')")

    search_by_name_like = get_all.where("name LIKE (?)")

    delete_by_module_name = "DELETE FROM names WHERE module = ?"


class Package:
    columns = [
        "package",
        "path",
    ]
    @classmethod
    def create_table(self, connection):
        packages_table = "(package TEXT, path TEXT)"
        connection.execute(f"CREATE TABLE IF NOT EXISTS packages{packages_table}")

    get_all = Query("packages", columns)
    insert = "INSERT INTO packages(package, path) VALUES (?, ?)"
    drop_table = "DROP TABLE packages"

    delete_by_package_name = "DELETE FROM names WHERE package = ?"
