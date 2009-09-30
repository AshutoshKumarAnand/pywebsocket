#!/usr/bin/env python
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for dispatch module."""



import os
import unittest

import config  # This must be imported before mod_pywebsocket.
from mod_pywebsocket import dispatch

import mock


_TEST_HANDLERS_DIR = os.path.join(
        os.path.split(__file__)[0], 'testdata', 'handlers')

class DispatcherTest(unittest.TestCase):
    def test_converter(self):
        converter = dispatch._path_to_resource_converter('/a/b')
        self.assertEqual('/h', converter('/a/b/h_wsh.py'))
        self.assertEqual('/c/h', converter('/a/b/c/h_wsh.py'))
        self.assertEqual(None, converter('/a/b/h.py'))
        self.assertEqual(None, converter('a/b/h_wsh.py'))

        converter = dispatch._path_to_resource_converter('a/b')
        self.assertEqual('/h', converter('a/b/h_wsh.py'))

        converter = dispatch._path_to_resource_converter('/a/b///')
        self.assertEqual('/h', converter('/a/b/h_wsh.py'))
        self.assertEqual('/h', converter('/a/b/../b/h_wsh.py'))

        converter = dispatch._path_to_resource_converter('/a/../a/b/../b/')
        self.assertEqual('/h', converter('/a/b/h_wsh.py'))

        converter = dispatch._path_to_resource_converter(r'\a\b')
        self.assertEqual('/h', converter(r'\a\b\h_wsh.py'))
        self.assertEqual('/h', converter(r'/a/b/h_wsh.py'))

    def test_source_file_paths(self):
        paths = list(dispatch._source_file_paths(_TEST_HANDLERS_DIR))
        paths.sort()
        self.assertEqual(7, len(paths))
        expected_paths = [
                os.path.join(_TEST_HANDLERS_DIR, 'a_wsh.py'),
                os.path.join(_TEST_HANDLERS_DIR, 'b_wsh.py'),
                os.path.join(_TEST_HANDLERS_DIR, 'sub/c_wsh.py'),
                os.path.join(_TEST_HANDLERS_DIR, 'sub/e_wsh.py'),
                os.path.join(_TEST_HANDLERS_DIR, 'sub/f_wsh.py'),
                ]
        for expected, actual in zip(expected_paths, paths):
            self.assertEqual(expected, actual)

    def test_source(self):
        self.assertRaises(dispatch.DispatchError, dispatch._source, '')
        self.assertRaises(dispatch.DispatchError, dispatch._source, 'def')
        self.assertRaises(dispatch.DispatchError, dispatch._source, '1/0')
        self.failUnless(dispatch._source(
                'def web_socket_shake_hands(request):pass\n'
                'def web_socket_transfer_data(request):pass\n'))

    def test_source_warnings(self):
        dispatcher = dispatch.Dispatcher(_TEST_HANDLERS_DIR)
        warnings = dispatcher.source_warnings()
        warnings.sort()
        expected_warnings = [
                (os.path.join(_TEST_HANDLERS_DIR, 'b_wsh.py') + ': '
                 'web_socket_shake_hands is not defined.'),
                (os.path.join(_TEST_HANDLERS_DIR, 'sub', 'c_wsh.py') + ': '
                 'web_socket_shake_hands is not callable.'),
                (os.path.join(_TEST_HANDLERS_DIR, 'sub', 'g_wsh.py') + ': '
                 'web_socket_shake_hands is not defined.'),
                (os.path.join(_TEST_HANDLERS_DIR, 'sub', 'h_wsh.py') + ': '
                 'web_socket_transfer_data is not defined.'),
                ]
        self.assertEquals(4, len(warnings))
        for expected, actual in zip(expected_warnings, warnings):
            self.assertEquals(expected, actual)

    def test_shake_hand(self):
        dispatcher = dispatch.Dispatcher(_TEST_HANDLERS_DIR)
        request = mock.MockRequest()
        request.ws_resource = '/a'
        request.ws_origin = 'http://example.com'
        dispatcher.shake_hands(request)  # Must not raise exception.

        request.ws_origin = 'http://bad.example.com'
        self.assertRaises(dispatch.DispatchError,
                          dispatcher.shake_hands, request)

    def test_transfer_data(self):
        dispatcher = dispatch.Dispatcher(_TEST_HANDLERS_DIR)
        request = mock.MockRequest(connection=mock.MockConn(''))
        request.ws_resource = '/a'
        request.ws_protocol = 'p1'

        dispatcher.transfer_data(request)
        self.assertEqual('a_wsh.py is called for /a, p1',
                         request.connection.written_data())

        request = mock.MockRequest(connection=mock.MockConn(''))
        request.ws_resource = '/sub/e'
        request.ws_protocol = None
        dispatcher.transfer_data(request)
        self.assertEqual('sub/e_wsh.py is called for /sub/e, None',
                         request.connection.written_data())

    def test_transfer_data_no_handler(self):
        dispatcher = dispatch.Dispatcher(_TEST_HANDLERS_DIR)
        for resource in ['/b', '/sub/c', '/sub/d', '/does/not/exist']:
            request = mock.MockRequest(connection=mock.MockConn(''))
            request.ws_resource = resource
            request.ws_protocol = 'p2'
            try:
                dispatcher.transfer_data(request)
                self.fail()
            except dispatch.DispatchError, e:
                self.failUnless(str(e).find('No handler') != -1)
            except Exception:
                self.fail()

    def test_transfer_data_handler_exception(self):
        dispatcher = dispatch.Dispatcher(_TEST_HANDLERS_DIR)
        request = mock.MockRequest(connection=mock.MockConn(''))
        request.ws_resource = '/sub/f'
        request.ws_protocol = 'p3'
        try:
            dispatcher.transfer_data(request)
            self.fail()
        except dispatch.DispatchError, e:
            self.failUnless(str(e).find('Intentional') != -1)
        except Exception:
            self.fail()


if __name__ == '__main__':
    unittest.main()


# vi:sts=4 sw=4 et