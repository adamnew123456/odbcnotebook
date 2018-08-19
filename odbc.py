class PagingContext:
    """
    Wraps a cursor object, and provides convenience functions for retrieving
    metadata and rows
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.metadata_cache = [
            (info[0], info[1].__name__)
            for info in cursor.description
        ]

    def metadata(self):
        return self.metadata_cache

    def count(self):
        """
        Returns the cursor's update count
        """
        return self.cursor.rowcount

    def page(self):
        """
        Returns up to a page of data rows
        """
        columns = [name for (name, _) in self.metadata_cache]
        page = []
        for row in self.cursor:
            named_row = {}
            for (column, value) in zip(columns, row):
                named_row[column] = str(value)

            page.append(named_row)

        return page

    def finish(self):
        """
        Closes the underlying ODBC cursor
        """
        self.cursor.close()

class RPC:
    """
    The RPC functions that are exposed on the server
    """
    def __init__(self, connection):
        self.connection = connection
        self.page_context = None
        self.shutdown_fn = None

    def set_shutdown(self, fn):
        self.shutdown_fn = fn

    def _table_like(self, target_kind):
        """
        Retrieves either tables or views, depending upon what the target kind
        is ('TABLE' or 'VIEW')
        """
        cursor = self.connection.cursor()
        cursor.tables()

        tables = []
        for (catalog, schema, table, kind, _) in cursor:
            if kind.lower() == target_kind.lower():
                tables.append({
                    'catalog': catalog or '',
                    'schema': schema or '',
                    'table': table
                })

        cursor.close()
        return tables

    def tables(self):
        return self._table_like('table')

    def views(self):
        return self._table_like('view')

    def columns(self, catalog, schema, table):
        cursor = self.connection.cursor()
        cursor.columns(table, catalog, schema, None)

        return [
            {
                'catalog': row[0],
                'schema': row[1],
                'table': row[2],
                'column': row[3],
                'datatype': row[5]
            }
            for row in cursor
        ]

    def execute(self, sql):
        if self.page_context is not None:
            raise ValueError('Cannot have active query when calling execute()')

        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.page_context = PagingContext(cursor)
        return True

    def metadata(self):
        if self.page_context is None:
            raise ValueError('Must have active query before calling metadata()')

        metadata = self.page_context.metadata()
        return {
            'columnnames': [column for (column, _) in metadata],
            'columntypes': [type_name for (_, type_name) in metadata]
        }

    def count(self):
        if self.page_context is None:
            raise ValueError('Must have active query before calling metadata()')

        return self.page_context.count()

    def page(self):
        if self.page_context is None:
            raise ValueError('Must have active query before calling page()')

        return self.page_context.page()
    def finish(self):
        if self.page_context is None:
            raise ValueError('Must have active query before calling finish()')

        self.page_context.finish()
        self.page_context = None
        return True

    def quit(self):
        if self.page_context is not None:
            raise ValueError('Cannot have active query when calling quit()')

        self.connection.close()
        self.shutdown_fn()
        return True
