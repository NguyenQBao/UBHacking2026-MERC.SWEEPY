# 运行流程

以下相对路径均从仓库根目录执行。Pi用户名示例为pi、地址示例为raspberrypi.local，请用自己的实际地址。私有仓库克隆须使用有权限的GitHub账户。每个前台服务单独用一个终端；只有一个程序可以占用CSI摄像头。

## 1. Pi摄像头与模拟控制

从Mac将software/metalsweep-control目录传到Pi：

```bash
scp -r software/metalsweep-control pi@raspberrypi.local:~/
```

Pi终端（先停止旧app.py/rpicam-hello）：

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy python3-gpiozero python3-lgpio python3-venv
cd ~/metalsweep-control
python3 run.py --hsv 0,220,220
```

这是红色测试物模式，不是通用碎片识别；默认模拟，无GPIO输出。不要在尚未核验驱动/电压时添加--hardware。

Mac另一个终端建立隧道：

```bash
ssh -N -L 8091:127.0.0.1:8091 pi@raspberrypi.local
```

Mac打开 http://127.0.0.1:8091/ 。无框原图位于 http://127.0.0.1:8091/raw.jpg 。隧道终端保持运行。

## 2. Mac训练工作台

从仓库根目录，在Mac新终端执行：

```bash
cd software/debris-training
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-train.txt
python studio.py --camera-url http://127.0.0.1:8091/raw.jpg
```

打开 http://127.0.0.1:8090/ 。只采集/标注可先安装requirements-label.txt，训练前再安装完整依赖。旧说明中的8000端口属于独立诊断app.py；本页统一用8091隧道连接控制程序的原图。

默认workspace在software/debris-training/workspace，已被.gitignore排除。首次下载官方预训练权重需要联网。默认训练30轮、batch4、imgsz640、自动选择CUDA/MPS/CPU。训练期间可以继续标注，当前轮的数据快照不会改变。

## 3. 现场数据与公开标注

先按[data说明](DATA.md)采集实际纸团/瓶盖。COCO格式转换：

```bash
python import_coco.py --annotations /path/to/TACO/data/annotations.json --list-categories
python import_coco.py --annotations /path/to/TACO/data/annotations.json --images /path/to/TACO/data --out ./workspace_coco --category-ids 7,8,33 --limit 200
python studio.py --root ./workspace_coco
```

以上路径是待替换示例，不是包内数据。新工作区默认预填框、等待人工确认；公开图只作为train，现场数据提供独立val/test。已有工作区合并等细节见[COCO导入说明](../software/debris-training/README_COCO标注转换.md)。

## 4. 标定与真实控制

测距、实测车速、轮子方向和刷子驱动逐项验证后，再修改config.json对应的确认项。现有标定工具用6个手动点，未实现自动棋盘格/ArUco。详细指令和接线条件见[联动说明](../software/metalsweep-control/README_先按顺序测试.md)。

CCM6N原旋钮调速；默认软件配合额外继电器做开/关，不能把电位器线直接接Pi。没有继电器且刷子接口未核验时，先使用--wheels-only。

训练模型必须含debris类别。PT或NCNN推理性能需要在实际Pi4B测试；NCNN导出输入尺寸与运行时imgsz保持一致。当前训练默认640、控制程序默认320，部署前请先在同一验证集比较，再统一导出和推理配置。
