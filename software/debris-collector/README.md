# 数据采集后台（树莓派）

只负责**拍照采集**，与训练工作台分开：不标注、不训练、不控制电机。在树莓派 VNC 的浏览器里操作，不需要 SSH 隧道或 Mac。照片按 用途/场景 分类存放在树莓派，拍完导出一个 ZIP，在 Mac 训练工作台“导入采集包”。

## 启动

相机画面默认取自正在运行的车子后台（`run.py`，127.0.0.1:8091），两者可同时运行：

```bash
cd ~/debris-collector && python3 collect.py
```

浏览器打开 http://127.0.0.1:8092/ 。照片存到 `~/metalsweep-dataset`（`--root` 可改）。

不开车子后台时，可让采集后台直接占用CSI相机（同一时间只能一个程序占用相机）：

```bash
python3 collect.py --picamera            # 画面倒置再加 --rotate180
```

## 页面操作

| 控件 | 作用 |
|---|---|
| Live camera | 实时预览（约每秒2张），只看不存 |
| Scene | 场景名称（字母/数字/_/-），换桌面、地点或光线才换名 |
| Split | train / val / test；同一场景只能属于一种用途，程序会拒绝跨用途 |
| No debris in this shot | 勾选表示这张是空桌面（约占20%） |
| Capture（Enter键） | 保存当前画面；完全相同的画面不会重复保存 |
| Undo last | 删除最后一张 |
| Progress | 各用途张数、首轮目标（30/10/10）、空图比例、场景数 |
| Scenes | 每个场景的用途与张数 |
| Download collection ZIP | 导出全部照片+manifest.json，保存到树莓派的下载文件夹 |

## 传到 Mac 并导入

在 Mac 终端复制（文件名按实际修改）：

```bash
scp pi@<树莓派IP>:~/Downloads/metalsweep_collection_*.zip ~/Downloads/
```

或直接复制整个采集文件夹：`scp -r pi@<树莓派IP>:~/metalsweep-dataset ~/Downloads/`。

Mac 训练工作台第1区“导入采集包”选择该ZIP；或命令行：

```bash
python workflow.py import-collection --source ~/Downloads/metalsweep_collection_XXXX.zip
```

导入保留场景与用途，照片为“未确认”，仍需在工作台逐张画框或确认无碎片后才会进入训练。重复导入同一包会自动跳过已有照片。

## 存储结构

```text
~/metalsweep-dataset/
  manifest.json                       # 每张：file, scene, split, empty, sha256, captured
  images/train/deskA_day/0001.jpg
  images/val/deskB_day/0001.jpg
```

仅用Python标准库（`--picamera`时需要系统自带的Picamera2）。测试：`python3 -m unittest test_collect`。
