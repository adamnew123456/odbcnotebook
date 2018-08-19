# What is this?

This is an ODBC backend for the
[ADONotebook](https://github.com/adamnew123456/adonotebook) protocol, see that
project's page to learn more. This document only covers how to install and run
the ODBC server.

# Installing

Run `python3 setup.py install`

# Running

Run the `odbc-server` script. At minimum, it requires an ODBC connection string:

    odbc-server -c "DSN=My ODBC DSN"
    
Then, connect to it on port 1995 with a notebook client.

## Options

-  `-p port` Sets the port that the server listens on (default: 1995)
- `-s certificate-file key-file key-password` Enables SSL, and loads the private key from the given PEM files. If the key is not needed, pass a blank string for the `key-password` argument.
- `-c connection-string` Sets the connection string that pyodbc uses to connect to the data source.
