"""Regression: an idle browser socket must not block another page request."""
import socket
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,build_opener,ProxyHandler
import unittest
from types import SimpleNamespace
from threading import Lock
import cv2
import numpy as np
from app import Handler

class HttpTests(unittest.TestCase):
    def test_training_photo_is_unannotated(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        frame=np.full((480,640,3),150,np.uint8)
        server.detector=SimpleNamespace(lock=Lock(),frame=lambda:frame.copy())
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        opener=build_opener(ProxyHandler({}))
        try:
            with opener.open('http://127.0.0.1:'+str(server.server_port)+'/raw.jpg',timeout=2) as r:
                self.assertEqual(r.headers.get_content_type(),'image/jpeg')
                photo=cv2.imdecode(np.frombuffer(r.read(),np.uint8),cv2.IMREAD_COLOR)
                self.assertEqual(photo.shape,frame.shape)
                self.assertLess(np.abs(photo.astype(float)-frame).max(),3)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_idle_socket_does_not_block_page(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        idle=socket.create_connection(server.server_address,timeout=2)
        opener=build_opener(ProxyHandler({}))
        try:
            address='http://127.0.0.1:'+str(server.server_port)
            with opener.open(address+'/',timeout=2) as r:
                self.assertIn(b'<canvas',r.read())
            with opener.open(address+'/health',timeout=2) as r:
                self.assertIn(b'true',r.read())
        finally:
            idle.close();server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=='__main__':unittest.main()
