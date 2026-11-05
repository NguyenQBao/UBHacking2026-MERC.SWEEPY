import unittest
import cv2
import numpy as np
from app import detect,settings,sample_color,DEFAULTS

class DetectorTests(unittest.TestCase):
    def setUp(self):self.bg=np.full((480,640,3),150,np.uint8);self.cfg=dict(DEFAULTS)
    def test_empty_and_reference_required(self):
        self.assertEqual(detect(self.bg,None,None,self.cfg)[2]['count'],0)
        self.assertEqual(detect(self.bg,self.bg,None,self.cfg)[2]['count'],0)
    def test_background_and_direction(self):
        f=self.bg.copy();cv2.rectangle(f,(430,220),(450,240),(10,10,10),-1)
        result=detect(f,self.bg,None,self.cfg)[2];self.assertEqual(result['count'],1)
        self.assertEqual(result['targets'][0]['direction'],'RIGHT')
        f=self.bg.copy();cv2.rectangle(f,(180,220),(200,240),(10,10,10),-1)
        self.assertEqual(detect(f,self.bg,None,self.cfg)[2]['targets'][0]['direction'],'LEFT')
    def test_area_and_roi(self):
        f=self.bg.copy();f[120:122,120:122]=0;self.assertEqual(detect(f,self.bg,None,self.cfg)[2]['count'],0)
        f=self.bg.copy();f[10:40,10:40]=0;self.assertEqual(detect(f,self.bg,None,self.cfg)[2]['count'],0)
        cfg=settings({'max_area':100},self.cfg);f[220:250,440:470]=0
        self.assertEqual(detect(f,self.bg,None,cfg)[2]['count'],0)
    def test_global_change_suppressed(self):
        r=detect(np.zeros_like(self.bg),self.bg,None,self.cfg)[2]
        self.assertEqual(r['count'],0);self.assertIn('变化过大',r['status'])
    def test_color_no_reference_and_red_wrap(self):
        cfg=settings({'mode':'color'},self.cfg)
        self.assertEqual(detect(self.bg,None,None,cfg)[2]['count'],0)
        hsv=np.zeros((480,640,3),np.uint8);hsv[:]=[80,20,150]
        hsv[220:241,430:441]=[179,240,220];hsv[220:241,441:452]=[0,240,220]
        f=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR);color=sample_color(f,441,230)
        self.assertTrue(color[0]>170 or color[0]<10)
        r=detect(f,None,color,cfg)[2];self.assertEqual(r['count'],1)
        self.assertEqual(r['targets'][0]['direction'],'RIGHT')
    def test_invalid_settings(self):
        for value in ({'threshold':0},{'min_area':float('nan')},{'roi':[0,0,700,300]},
                      {'mode':'unknown'},{'min_area':500,'max_area':10},{'threshold':True}):
            with self.assertRaises(ValueError):settings(value,self.cfg)
        with self.assertRaises(ValueError):sample_color(self.bg,-1,0)
        for value in ({'max_aspect':-1},{'min_fill_percent':101}):
            with self.assertRaises(ValueError):settings(value,self.cfg)

    def test_optional_shape_filters(self):
        f=self.bg.copy()
        cv2.rectangle(f,(100,220),(260,227),(0,0,0),-1)
        self.assertEqual(detect(f,self.bg,None,self.cfg)[2]['count'],1)
        cfg=settings({'max_aspect':8},self.cfg)
        self.assertEqual(detect(f,self.bg,None,cfg)[2]['count'],0)
        f=self.bg.copy()
        cv2.line(f,(430,220),(430,270),(0,0,0),5)
        cv2.line(f,(430,270),(480,270),(0,0,0),5)
        self.assertEqual(detect(f,self.bg,None,self.cfg)[2]['count'],1)
        cfg=settings({'min_fill_percent':50},self.cfg)
        self.assertEqual(detect(f,self.bg,None,cfg)[2]['count'],0)

    def test_paper_preset_keeps_compact_target(self):
        cfg=settings({'threshold':40,'min_area':150,'max_area':5000,
                      'max_aspect':8,'min_fill_percent':25},self.cfg)
        f=self.bg.copy();cv2.rectangle(f,(420,230),(445,255),(0,0,0),-1)
        self.assertEqual(detect(f,self.bg,None,cfg)[2]['count'],1)

if __name__=='__main__':unittest.main()
