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
| 外形 | 约30.4×25.4×57.6mm | 推荐侧躺打印（见下），直立打印贴床面积小、头重易晃 |

重新生成：

```bash
pip install manifold3d numpy
python generate.py
```

如果相机装反（排线朝上），把config.json中`rotate180`改为true即可，不必改模型。

## 多厚度试打（PrusaSlicer）

[camera-slot-mount-variants.3mf](camera-slot-mount-variants.3mf)：一盘4件，插槽厚1.2 / 1.6 / 2.0 / 2.4mm（单件STL在[variants](variants)），每件**侧躺**（托槽侧壁贴床，高30.4mm，贴床面积约为直立的2.4倍，层纹顺着颈部方向更结实），已设置“自动**树形（organic）**支撑、仅从热床生成”（只托起悬空的套筒），4件沿Y排成一列、间距12mm，互不重叠。3MF只含模型和逐件设置，不含打印机配置，打开后沿用PrusaSlicer当前所选的打印机/耗材/打印预设（按Prusa CORE One 250×220热床居中排列）。

```bash
python generate.py --slot 1.2 --out variants/camera-slot-mount-slot1.2mm.stl   # 其余厚度同理
python make_plate.py
```

试插后选最合适的一件，其余回收。
