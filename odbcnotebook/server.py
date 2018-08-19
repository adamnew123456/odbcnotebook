from http.server import HTTPServer
import ssl
import sys
import types

import pyodbc

from odbcnotebook import jsonrpc, odbc

USAGE = 'odbcnotebook [-p PORT] [-c CONNECTION_STRING] [-s KEY CERT PASSWORD]'

def wrap_ssl(runconfig, sock):
    """
    Wraps a socket in an SSL context, if SSL is enabled.
    """
    if runconfig.ssl:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(runconfig.certificate, runconfig.key, password=runconfig.keypassword)
        return context.wrap_socket(sock, server_side=True)
    else:
        return sock

def parse_args():
    """
    Parses command-line arguments and returns a run configuration
    """
    runconfig = types.SimpleNamespace()
    runconfig.ssl = False
    runconfig.port = None
    runconfig.connection_string = None

    i = 1
    try:
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == '-s':
                if runconfig.ssl:
                    raise ValueError

                runconfig.ssl = True
                runconfig.certificate = sys.argv[i + 1]
                runconfig.key = sys.argv[i + 2]
                runconfig.keypassword = sys.argv[i + 3]
                i += 4
            elif arg == '-p':
                if runconfig.port is not None:
                    raise ValueError

                runconfig.port = int(sys.argv[i + 1])
                if runconfig.port <= 0 or runconfig.port > 65536:
                    raise ValueError

                i += 2
            elif arg == '-c':
                if runconfig.connection_string is not None:
                    raise ValueError

                runconfig.connection_string = sys.argv[i + 1]
                i += 2
            else:
                raise ValueError

        if runconfig.connection_string is None:
            raise ValueError
    except (IndexError, ValueError):
        print(USAGE)
        sys.exit(1)

    if runconfig.port is None:
        runconfig.port = 1995

    return runconfig

def run_server(runconfig):
    """
    Processes RPC requests until the server is closed
    """
    try:
        connection = pyodbc.connect(runconfig.connection_string)
    except pyodbc.Error as err:
        print('Failed to open ODBC conncetion:', err)
        return

    odbc_inst = odbc.RPC(connection)
    handler_class = jsonrpc.make_json_handler(odbc_inst)
    server = HTTPServer(('localhost', runconfig.port), handler_class)

    def shutdown():
        # Since HTTPServer.shutdown blocks until the server shuts down, the
        # only way to call it is from a thread that isn't running that HTTPServer
        import threading
        threading.Thread(target=server.shutdown).start()

    odbc_inst.set_shutdown(shutdown)

    server.socket = wrap_ssl(runconfig, server.socket)
    server.serve_forever()

def main():
    """
    Entry point
    """
    run_server(parse_args())
