class Name:
    @classmethod
    def create_table(self, connection):
        names_table = (
            "(name TEXT, module TEXT, package TEXT, source INTEGER, type INTEGER)"
        )
        connection.execute(f"CREATE TABLE IF NOT EXISTS names{names_table}")
        connection.execute("CREATE INDEX IF NOT EXISTS name ON names(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS module ON names(module)")
        connection.execute("CREATE INDEX IF NOT EXISTS package ON names(package)")

    insert = "INSERT INTO names(name, module, package, source, type) VALUES (?, ?, ?, ?, ?)"
    drop_table = "DROP TABLE names"

    search_submodule_like = 'SELECT module, source FROM names WHERE module LIKE ("%." || ?)'
    search_module_like = "SELECT module, source FROM names WHERE module LIKE (?)"

    import_assist = "SELECT name, module, source FROM names WHERE name LIKE (? || '%')"

    search_name_like = "SELECT name, module, source, type FROM names WHERE name LIKE (?)"

    get_modules = "SELECT module, source FROM names WHERE name LIKE (?)"

    get_all_names = "SELECT name FROM names"

    select_all = "SELECT * FROM names"

    delete_by_module_name = "DELETE FROM names WHERE module = ?"


class Package:
    @classmethod
    def create_table(self, connection):
        packages_table = "(package TEXT, path TEXT)"
        connection.execute(f"CREATE TABLE IF NOT EXISTS packages{packages_table}")

    insert = "INSERT INTO packages(package, path) VALUES (?, ?)"
    drop_table = "DROP TABLE packages"

    select_all = "SELECT * FROM packages"

    delete_by_package_name = "DELETE FROM names WHERE package = ?"
