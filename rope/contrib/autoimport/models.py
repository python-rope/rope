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


class Package:
    @classmethod
    def create_table(self, connection):
        packages_table = "(package TEXT, path TEXT)"
        connection.execute(f"CREATE TABLE IF NOT EXISTS packages{packages_table}")
