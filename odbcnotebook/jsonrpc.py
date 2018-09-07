"""
A basic implementation of JSON-RPC 2 based upon the request handlers in
http.server
"""
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPStatus
import json
import traceback

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
}

class RpcErrors(Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

RPC_ERROR_MESSAGES = {
    RpcErrors.PARSE_ERROR: 'Parse error',
    RpcErrors.INVALID_REQUEST: 'Invalid Request',
    RpcErrors.METHOD_NOT_FOUND: 'Method not found',
    RpcErrors.INVALID_PARAMS: 'Invalid params',
    RpcErrors.INTERNAL_ERROR: 'Internal Error',
}

def make_json_handler(rpc):
    """
    Builds a JSON-RPC request handler for the given RPC object
    """

    class JSONRPCHandler(BaseHTTPRequestHandler):
        """
        A request handler for http.server that speaks JSON-RPC.
        """
        def _validate_http_request(self):
            """
            Ensures that we understand the HTTP portion of the request.
            """
            if self.path != '/':
                print('Invalid request path:', self.path)
                self.send_error(HTTPStatus.NOT_FOUND, 'Request Must Have Path Of /')
                raise ValueError

            content_type = self.headers.get('Content-Type', None)
            if content_type != 'application/json':
                print('Invalid request Content-Type:', self.path)
                self.send_error(HTTPStatus.BAD_REQUEST, 'Content-Type Must Be application/json')
                raise ValueError

        def _validate_rpc_request(self, request):
            """
            Ensures that we understand the JSON-RPC portion of the request.
            """
            if request.get('jsonrpc', None) != '2.0':
                raise ValueError('Invalid jsonrpc: must be "2.0"')

            id = request.get('id', None)
            if not (id is None or isinstance(id, (str, int, float))):
                raise ValueError('Invalid id: must be null, string or number')

            method = request.get('method', None)
            if not isinstance(method, str):
                raise ValueError('Invalid method: must be string')

            params = request.get('params', [])
            if not isinstance(params, (dict, list)):
                raise ValueError('Invalid params: must be array or object')

        def _build_rpc_error(self, id, error, exception, keep_null_id=False):
            """
            Returns an error response that can be encoded to JSON.

            By default this respects the ID of the request, and returns None if the
            ID is also None. To override this behavior, set keep_null_id=True.
            """
            if id is None and not keep_null_id:
                return None

            message = RPC_ERROR_MESSAGES.get(error, str(exception))

            return {
                'jsonrpc': '2.0',
                'id': id,
                'error': {
                    'code': error.value,
                    'message': message,
                    'data': {
                        'stacktrace': str(exception) + '\n' + '\n'.join(traceback.format_tb(exception.__traceback__))
                    }
                }
            }

        def _build_rpc_result(self, id, result):
            """
            Returns a result response that can be encoded to JSON.
            """
            if id is None:
                return None

            return {
                'jsonrpc': '2.0',
                'id': id,
                'result': result
            }

        def _process_request(self, request):
            """
            Calls a single RPC function and returns the result.
            """
            try:
                self._validate_rpc_request(request)
            except ValueError as err:
                return self._build_rpc_error(None, RpcErrors.INVALID_REQUEST, err, keep_null_id=True)

            id = request.get('id', None)

            try:
                method = getattr(rpc, request['method'])
            except AttributeError as err:
                return self._build_rpc_error(id, RpcErrors.METHOD_NOT_FOUND, err)

            try:
                params = request.get('params', None)
                if params is None:
                    result = method()
                elif isinstance(params, list):
                    result = method(*params)
                elif isinstance(params, dict):
                    result = method(**params)

                return self._build_rpc_result(id, result)

            except TypeError as err:
                return self._build_rpc_error(id, RpcErrors.INVALID_PARAMS, err)
            except Exception as err:
                return self._build_rpc_error(id, RpcErrors.INTERNAL_ERROR, err)

        def _send_json(self, value):
            """
            Dumps the value to a JSON string, and sets the appropriate headers to
            return it
            """
            raw_value = json.dumps(value).encode('utf-8')

            self.send_response(200, 'OK')
            for header, value in CORS_HEADERS.items():
                self.send_header(header, value)

            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw_value)))
            self.end_headers()

            self.wfile.write(raw_value)

        def do_POST(self):
            """
            Parses and processes a single or batch JSON-RPC request.
            """
            try:
                self._validate_http_request()
            except ValueError:
                return

            content_length = int(self.headers.get('Content-Length', '0'))
            request_bytes = self.rfile.read(content_length)
            while len(request_bytes) < content_length:
                request_bytes += self.rfile.read(content_length - len(request_bytes))

            request_raw = request_bytes.decode('utf-8')
            try:
                request = json.loads(request_raw)
            except ValueError as err:
                error = self._build_rpc_error(None, RpcErrors.PARSE_ERROR, err, keep_null_id=True)
                self._send_json(error)
                return

            if isinstance(request, list):
                responses = [self._process_request(single) for single in request]
                response = [r for r in responses if r is not None]
            elif isinstance(request, dict):
                response = self._process_request(request)
            else:
                try:
                    raise ValueError
                except ValueError as err:
                    error = self._build_rpc_error(None, RpcErrors.INVALID_REQUEST, err)
                    self._send_json(error)
                    return

            if response is not None:
                self._send_json(response)
            else:
                self.send_response(200, 'OK')
                self.end_headers()

        def do_OPTIONS(self):
            """
            Sends back the headers necessary to support CORS
            """
            print('Processing CORS OPTIONS request')
            self.send_response(200, 'OK')
            for header, value in CORS_HEADERS.items():
                self.send_header(header, value)

            self.end_headers()

    return JSONRPCHandler
