"""Click >=6 measured ground points on an unannotated camera snapshot (640x480, or 480x640 when rotated 90/270)."""
import argparse
import json
from pathlib import Path
import cv2
from vision import fit_ground, frame_size


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True)
    p.add_argument('--points', default='points.example.json')
    p.add_argument('--out', default='ground.json')
    p.add_argument('--rotate', type=int, choices=(0, 90, 180, 270), default=0,
                   help='Same value as config.json rotate; the snapshot is already rotated by run.py')
    p.add_argument('--rotate180', action='store_true', help='Old alias for --rotate 180')
    p.add_argument('--no-gui', action='store_true', help='All uv coordinates already entered in JSON')
    args = p.parse_args()
    rotate = 180 if args.rotate180 else args.rotate
    width, height = frame_size(rotate)
    frame = cv2.imread(args.image)
    if frame is None or frame.shape[:2] != (height, width):
        raise ValueError(f'Use unannotated /raw.jpg at {width}x{height} (rotate={rotate})')
    points = json.loads(Path(args.points).read_text())
    if not args.no_gui:
        for point in points:
            point['uv'] = None
        selected = []
        def click(event, u, v, flags, userdata):
            if event == cv2.EVENT_LBUTTONDOWN and len(selected) < len(points):
                selected.append([u, v])
        cv2.namedWindow('ground calibration')
        cv2.setMouseCallback('ground calibration', click)
        try:
            while len(selected) < len(points):
                view = frame.copy()
                for i, (u, v) in enumerate(selected):
                    cv2.circle(view, (u, v), 4, (0, 0, 255), -1)
                    cv2.putText(view, str(i+1), (u+5, v), 0, .6, (0, 0, 255), 1)
                msg = f'Click point {len(selected)+1}: XY mm={points[len(selected)]["xy_mm"]}; ESC cancel; U undo'
                cv2.putText(view, msg, (8, 20), 0, .45, (0, 100, 255), 1)
                cv2.imshow('ground calibration', view)
                key = cv2.waitKey(30) & 255
                if key == 27:
                    return
                if key == ord('u') and selected:
                    selected.pop()
            for point, uv in zip(points, selected):
                point['uv'] = uv
        finally:
            cv2.destroyAllWindows()
    data = fit_ground(points, (width, height), rotate)
    out = Path(args.out)
    if out.exists():
        raise ValueError('Output exists: choose another --out, preserve previous calibration')
    out.write_text(json.dumps(data, indent=2)+'\n')
    print(f'Saved {out}; fit residual={data["max_fit_error_mm"]:.2f}mm. Verify on independent ruler points.')


if __name__ == '__main__':
    main()
