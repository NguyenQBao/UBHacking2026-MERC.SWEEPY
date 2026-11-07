"""Fixed-plane measurement + learned detection or explicit coloured-test-object mode."""
import json
import math
from pathlib import Path
import cv2
import numpy as np
from control import Target


def fit_ground(points, size, rotate180=False):
    uv = np.array([p['uv'] for p in points], dtype=np.float64)
    xy = np.array([p['xy_mm'] for p in points], dtype=np.float64)
    if uv.shape != (len(points), 2) or xy.shape != uv.shape or len(points) < 6:
        raise ValueError('Need >=6 measured 2D correspondences')
    if not np.isfinite(uv).all() or not np.isfinite(xy).all():
        raise ValueError('Non-finite calibration')
    if len(np.unique(uv, axis=0)) != len(uv) or len(np.unique(xy, axis=0)) != len(xy):
        raise ValueError('Duplicate calibration points')
    if (uv < 0).any() or (uv >= np.asarray(size)).any():
        raise ValueError('Pixel outside image')
    if cv2.contourArea(cv2.convexHull(uv.astype('float32'))) < 100 or cv2.contourArea(cv2.convexHull(xy.astype('float32'))) < 100:
        raise ValueError('Calibration points must span a plane, not a line')
    H, _ = cv2.findHomography(uv, xy, method=0)
    if H is None or not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-12:
        raise ValueError('Degenerate homography')
    predicted = cv2.perspectiveTransform(uv.reshape(-1, 1, 2), H).reshape(-1, 2)
    error = float(np.linalg.norm(predicted-xy, axis=1).max())
    if error > 15:
        raise ValueError(f'Calibration residual {error:.1f} mm >15; check points')
    return dict(size=list(size), rotate180=rotate180, points=points, H=H.tolist(),
                max_fit_error_mm=error)


class Ground:
    def __init__(self, path, rotate180):
        data = json.loads(Path(path).read_text())
        # Recompute from correspondences, do not trust an arbitrary stored H.
        fit = fit_ground(data['points'], data['size'], data['rotate180'])
        if fit['size'] != [640, 480] or fit['rotate180'] != rotate180:
            raise ValueError('Calibration resolution/rotation differs from live camera')
        self.H = np.array(fit['H'])
        self.hull = cv2.convexHull(np.array([p['uv'] for p in data['points']], np.float32))

    def project(self, u, v):
        if not all(math.isfinite(x) for x in (u, v)) or cv2.pointPolygonTest(self.hull, (float(u), float(v)), False) < 0:
            return None
        p = self.H @ np.array([u, v, 1.])
        if abs(p[2]) < 1e-8:
            return None
        return tuple((p[:2]/p[2]).tolist())


class Vision:
    def __init__(self, cfg, model_path=None, hsv=None, ground=None):
        self.cfg, self.ground, self.hsv = cfg, ground, hsv
        self.model = None
        if model_path:
            path = Path(model_path)
            if not path.exists():
                raise ValueError('Model file/directory does not exist')
            from ultralytics import YOLO
            self.model = YOLO(str(path), task='detect')
            self.classes = [int(k) for k, v in self.model.names.items() if v == 'debris']
            if not self.classes:
                raise ValueError('Use your trained debris model; default COCO models have no debris class')

    def detect(self, frame):
        boxes = []
        if self.model:
            result = self.model.predict(frame, imgsz=self.cfg['imgsz'], conf=self.cfg['confidence'],
                                        classes=self.classes, device='cpu', verbose=False, max_det=30)[0]
            for box, score in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist()):
                boxes.append((box, score))
        else:
            # ponytail: this is colour matching for a test object, not general debris recognition.
            h, s, v = self.hsv
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            dh = abs(image[:, :, 0]-h)
            mask = ((np.minimum(dh, 180-dh) <= 10) & (abs(image[:, :, 1]-s) <= 70)
                    & (abs(image[:, :, 2]-v) <= 80)).astype('uint8')*255
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            if cv2.countNonZero(mask) < frame.shape[0]*frame.shape[1]*.25:
                for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                    if 60 <= cv2.contourArea(contour) <= 10000:
                        x, y, w, ht = cv2.boundingRect(contour)
                        boxes.append(([x, y, x+w, y+ht], 1.))  # 1 means matched, NOT learned confidence
        targets = []
        for box, score in boxes:
            if len(box) != 4 or not all(math.isfinite(v) for v in box):
                continue
            a, b, c, d = box
            if not 0 <= a < c <= 640 or not 0 <= b < d <= 480:
                continue
            xy = self.ground.project((a+c)/2, d) if self.ground else None
            targets.append(Target(tuple(box), float(score), xy))
        return targets
