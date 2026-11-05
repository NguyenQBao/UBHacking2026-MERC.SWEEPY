"""Synthetic validation. No camera or motors needed."""
import unittest
import numpy as np
import cv2
from debris_demo import make_calibration,ground_point,detect

class DemoTests(unittest.TestCase):
    def setUp(self):
        self.cal=make_calibration([[100,400],[500,400],[500,100],[100,100]],200,300,100)
        self.bg=np.full((480,640,3),180,np.uint8)
    def test_known_range_and_signs(self):
        q=ground_point(self.cal,300,250)
        self.assertAlmostEqual(q['x_right_mm'],0)
        self.assertAlmostEqual(q['y_forward_mm'],250)
        self.assertAlmostEqual(q['ground_range_mm'],250)
        self.assertGreater(ground_point(self.cal,450,250)['bearing_right_deg'],0)
        self.assertLess(ground_point(self.cal,150,250)['bearing_right_deg'],0)
        self.assertIsNone(ground_point(self.cal,600,250))
    def test_debris_right_and_empty(self):
        frame=self.bg.copy();cv2.rectangle(frame,(440,240),(460,260),(20,20,20),-1)
        _,r=detect(frame,self.bg,self.cal)
        self.assertEqual(len(r['targets']),1)
        self.assertEqual(r['targets'][0]['direction'],'右')
        self.assertAlmostEqual(r['targets'][0]['measurement']['y_forward_mm'],250,delta=1)
        self.assertEqual(detect(self.bg,self.bg,self.cal)[1]['targets'],[])
        self.assertEqual(detect(frame,None,self.cal)[1]['targets'],[])
    def test_reject_scene_change_and_extrapolation(self):
        self.assertEqual(detect(np.zeros_like(self.bg),self.bg,self.cal)[1]['targets'],[])
        frame=self.bg.copy();cv2.rectangle(frame,(550,240),(570,260),(20,20,20),-1)
        self.assertEqual(detect(frame,self.bg,self.cal)[1]['targets'],[])
    def test_bad_calibration(self):
        for points in ([[0,0]]*4,[[100,400],[500,100],[500,400],[100,100]],[[100,100],[500,100],[500,400],[100,400]]):
            with self.assertRaises(ValueError):make_calibration(points,200,300,100)
        with self.assertRaises(ValueError):make_calibration(self.cal['polygon'],float('nan'),300,100)

if __name__=='__main__':unittest.main()
