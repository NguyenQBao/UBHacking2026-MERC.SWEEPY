# 来源、依赖与材料范围

本仓库整理本项目已有代码、参数化CAD源文件、STL、图纸及说明。没有替项目选择新的开源许可证；第三方库、图片和数据集遵循各自条款，不因本次整理被重新授权。

## 官方硬件图片与接线参考

hardware/wiring中Raspberry Pi 4B照片/40针引脚图来自Raspberry Pi官方，SunFounder模块照片来自SunFounder官方文档。接线表和图纸排版是项目连接方案；官方图片不是对该接线方案的认证。

- https://www.raspberrypi.com/products/raspberry-pi-4-model-b/
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- https://docs.sunfounder.com/projects/3in1-kit-v2/en/latest/components/component_l298n_module.html
- https://www.st.com/resource/en/datasheet/l298.pdf

先前用户上传的个人照片、网页截图、聊天附件没有纳入本仓库。docs/concept中的机器人概念图是设计示意，不是已装配实车证据。

## 软件与打印参考

- Ultralytics：https://docs.ultralytics.com/ ，训练依赖固定8.4.194；按其AGPL-3.0或商业许可使用。
- OpenCV：https://docs.opencv.org/ ，图像处理、平面单应性与标定原理。
- Picamera2：https://github.com/raspberrypi/picamera2
- GPIO Zero：https://gpiozero.readthedocs.io/en/stable/api_output.html
- Prusa：https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135
- Arducam OV5647模块参考：https://www.arducam.com/raspberry-pi-camera/

CAD依赖与版本见各目录requirements及源码；图纸排版使用ReportLab/PyMuPDF，部分绘图脚本依赖Mac字体，其他系统需指定可用中文字体。

## 数据集

仓库不包含第三方训练图像/标注副本、用户训练照片或权重。TACO转换报告会保留源标注哈希、类别和许可元数据，图片与数据集的条款需按来源核对；不要将仓库代码许可等同于全部照片许可。

- https://github.com/pedropro/TACO
- https://ai.bu.edu/zerowaste/
- https://github.com/garythung/trashnet

原始生成资料的相对位置与SHA256记录在source-files.json。整理时将机器本地路径改为仓库路径、私人局域网IP改为raspberrypi.local；运行服务仍需使用当前设备的真实地址或SSH隧道。
