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

    def insert_into(self):
        columns = ", ".join(self.columns)
        placeholders = ", ".join(["?"] * len(self.columns))
        return f"INSERT INTO {self.query}({columns}) VALUES ({placeholders})"


    def drop_table(self):
        return f"DROP TABLE {self.query}"



def table(cls):
    cls.insert_into = cls.get_all.insert_into()
    cls.drop_table = cls.get_all.drop_table()
    return cls


@table
class Name:
    table_name = "names"
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

    get_all = Query(table_name, columns)

    search_submodule_like = get_all.where('module LIKE ("%." || ?)')
    search_module_like = get_all.where("module LIKE (?)")

    import_assist = get_all.where("name LIKE (? || '%')")

    search_by_name_like = get_all.where("name LIKE (?)")

    delete_by_module_name = "DELETE FROM names WHERE module = ?"


@table
class Package:
    table_name = "packages"
    columns = [
        "package",
        "path",
    ]

    @classmethod
    def create_table(self, connection):
        packages_table = "(package TEXT, path TEXT)"
        connection.execute(f"CREATE TABLE IF NOT EXISTS packages{packages_table}")

    get_all = Query(table_name, columns)

    delete_by_package_name = "DELETE FROM names WHERE package = ?"
