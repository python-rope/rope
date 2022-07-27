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

    search_submodule_like = 'SELECT module, source FROM names WHERE module LIKE ("%." || ?)'
    search_module_like = "SELECT module, source FROM names WHERE module LIKE (?)"

    import_assist = "SELECT name, module, source FROM names WHERE name LIKE (? || '%')"


class Package:
    @classmethod
    def create_table(self, connection):
        packages_table = "(package TEXT, path TEXT)"
        connection.execute(f"CREATE TABLE IF NOT EXISTS packages{packages_table}")

    insert = "INSERT INTO packages(package, path) VALUES (?, ?)"
