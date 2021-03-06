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

    def page(self, max):
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

            if len(page) == max:
                break

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
        with self.connection.cursor() as cursor:
            cursor.tables()

            tables = []
            for (catalog, schema, table, kind, _) in cursor:
                if kind.lower() == target_kind.lower():
                    tables.append({
                        'catalog': catalog or '',
                        'schema': schema or '',
                        'table': table
                    })

        return tables

    def tables(self):
        """
        RPC method; returns all tables
        """
        print('tables()')
        return self._table_like('table')

    def views(self):
        """
        RPC method; returns all views
        """
        print('views()')
        return self._table_like('view')

    def columns(self, catalog, schema, table):
        """
        RPC method; returns columns from one or more tables
        """
        print('columns({}, {}, {})'.format(catalog, schema, table))
        with self.connection.cursor() as cursor:
            catalog = catalog or None
            schema = schema or None
            cursor.columns(table, catalog, schema, None)

            return [
                {
                    'catalog': row[0] or '',
                    'schema': row[1] or '',
                    'table': row[2],
                    'column': row[3],
                    'datatype': row[5]
                }
                for row in cursor
            ]

    def execute(self, sql):
        """
        RPC method; executes a query and configures the paging context for
        result-based functions
        """
        print('execute({})'.format(sql))
        if self.page_context is not None:
            print('- Called with active query')
            raise ValueError('Cannot have active query when calling execute()')

        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.page_context = PagingContext(cursor)
        return True

    def metadata(self):
        """
        RPC method: returns the columns available on the current result set
        """
        print('metadata()')
        if self.page_context is None:
            print('- Called without active query')
            raise ValueError('Must have active query before calling metadata()')

        metadata = self.page_context.metadata()
        return [
            {'column': column, 'datatype': type_name}
            for (column, type_name) in metadata
        ]

    def count(self):
        """
        RPC method: returns the update count on the current result set
        """
        print('count()')
        if self.page_context is None:
            print('- Called without active query')
            raise ValueError('Must have active query before calling metadata()')

        return self.page_context.count()

    def page(self, max):
        """
        RPC method: returns a page of data from the current result set
        """
        print('page({})'.format(max))
        if self.page_context is None:
            print('- Called without active query')
            raise ValueError('Must have active query before calling page()')

        if max <= 0:
            print('- Invalid page size')
            raise ValueError('Page size must be a positive integer')

        return self.page_context.page(max)

    def finish(self):
        """
        RPC method: closes the current result set
        """
        print('finish()')
        if self.page_context is None:
            print('- Called without active query')
            raise ValueError('Must have active query before calling finish()')

        self.page_context.finish()
        self.page_context = None
        return True

    def quit(self):
        """
        RPC method: terminates the server
        """
        print('quit()')
        if self.page_context is not None:
            print('- Called with active query')
            raise ValueError('Cannot have active query when calling quit()')

        self.connection.close()
        self.shutdown_fn()
        return True
