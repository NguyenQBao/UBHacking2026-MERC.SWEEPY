# CAD V8

当前打印模型（2026-11-05更新），替代此前的 camera-mount-v7 与 brush-collector-v3（已移至 [archive](../../archive)）。

| 文件 | 部件（按文件名） | 外形尺寸 X×Y×Z (mm) |
|---|---|---|
| [camera-holder-vertical.stl](camera-holder-vertical.stl) | 摄像头支架·竖杆 | 10 × 100 × 10 |
| [camera-holder-horizontal.stl](camera-holder-horizontal.stl) | 摄像头支架·横杆 | 4.5 × 7 × 80 |
| [camera-holder-front.stl](camera-holder-front.stl) | 摄像头支架·前部件 | 30 × 42 × 30 |
| [shaft-main.stl](shaft-main.stl) | 滚刷主轴（带纵向槽，直连减速电机） | 29.7 × 145 × 30 |
| [cleaning-wheel.stl](cleaning-wheel.stl) | 清扫轮片（配合主轴，照片中未装） | 7.6 × 145 × 28.1 |
| [ramp-main.stl](ramp-main.stl) | 导料斜坡（收集盒前缘） | 67.5 × 149 × 31.1 |
| [metal-storage-main.stl](metal-storage-main.stl) | 收集盒（Metal storage，装在底盘前端下方） | 149 × 60 × 118 |

## 装配示意

![V8收集机构试装照片](assembly_photo.jpg)

大致布局（照片为桌面摆放示意，非最终固定状态）：

1. 收集盒装在亚克力底盘前端下方，开口朝前。
2. 斜坡接在收集盒前缘，向前下方斜伸到地面。
3. 滚刷主轴横放在斜坡前方，一端直连金属减速电机输出轴，转动把碎片扫上斜坡进盒。
4. 摄像头支架（竖杆+横杆+前部件）照片中未装，安装位置待定。

电机、轴承座/滚刷另一端支撑和固定螺丝不在STL内，按实物确认。

## 检查状态

- 7个文件均为二进制STL，文件长度与三角面数一致，网格封闭（无非流形边）。
- 收集盒、斜坡、滚刷主轴已打印并与底盘摆放比对；尚未完成固定、通电转动和实际收集测试。
- 无源码/参数文件；修改需回到原CAD工程。
