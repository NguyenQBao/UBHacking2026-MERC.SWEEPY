# 摄像头插槽支架（camera-slot-mount）

[camera-slot-mount.stl](camera-slot-mount.stl)：摄像头电路板从上方插入的托槽，下部方形套筒套在主柱子（[camera-holder-vertical.stl](../cad-v8/camera-holder-vertical.stl)，10×10mm，Ø4mm孔间距10mm）顶端，用两根M3螺丝/Ø4销穿过套筒孔与柱子前两个孔固定。由[generate.py](generate.py)生成，可改参数重新生成。

| 项目 | 默认值 | 说明 |
|---|---|---|
| 电路板 | 25×24mm，插槽厚2.0mm | 常见OV5647板尺寸；插槽按板厚1.6mm+0.4mm间隙；Hiwonder实物**尚未测量**，打印前请用尺量宽、高、厚 |
| 板后空间 | 6mm | 容纳背面排线座/4针插座 |
| 前唇 | 每边压住2mm | 中间开窗给镜头，顶端开口用于插入 |
| 排线口 | 宽18mm | 从托槽底部穿出，经颈部背面引出 |
| 俯角 | 30° | 镜头向前下方；改TILT_DEG |
| 套筒 | 内孔10.4mm，深22mm | 孔中心距柱顶5mm、15mm，与柱子孔对齐 |
| 外形 | 约30.4×25.6×57.6mm | 套筒开口朝下平放打印，无需支撑 |

重新生成：

```bash
pip install manifold3d numpy
python generate.py
```

如果相机装反（排线朝上），把config.json中`rotate180`改为true即可，不必改模型。
