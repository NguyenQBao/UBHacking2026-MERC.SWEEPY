# 碎片采集、标注、累计训练工作台

第一版一个类别 `debris`，不区分真实材料。Mac 负责标注和训练；Pi 4B + OV5647 负责采集照片。本包不接电机、不自动驾驶，也不自动替你标注照片。

## 最快开始：先导入照片，也能完整使用

在 Mac 终端进入本文件所在的 `debris-training` 文件夹，执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-train.txt
python studio.py --camera-url http://raspberrypi.local:8000/raw.jpg
```

Mac 的 Chrome 或 Safari 打开 **http://127.0.0.1:8090/** 。必须保留这个终端；不要双击 `index.html`，也不用在 VNC 中打开网页。之后每次只需：

```bash
source .venv/bin/activate
python studio.py --camera-url http://raspberrypi.local:8000/raw.jpg
```

同目录的 `启动训练工作台.command` 是以上步骤的便捷入口；首次创建环境、安装训练依赖，后续直接启动。若 macOS 不允许双击，使用上面的终端命令即可，不需要改系统安全设置。

建议使用有可用 PyTorch 安装包的 Python 3.11 或更新版本。开发检查环境是 Apple Silicon / Python 3.14.7、Ultralytics 8.4.194、PyTorch 2.15.0、Pillow 13.0.0。其他系统需实际安装验证；如果 pip 提示没有匹配的 torch 包，换兼容的 Python 版本新建虚拟环境。不要在 Pi 的系统 Python 上安装整套训练依赖。

只想先采集/标注，可以仅安装 `requirements-label.txt`；训练时再在同一虚拟环境安装 `requirements-train.txt` 并重启工作台。

## 接上 Pi 相机（只需更新一次现有检测程序）

这个包另附更新的 `debris-detector-pi4`。新增 `/raw.jpg` 返回无框、无文字、无掩膜的原始视图，尺寸仍为640×480；保留原来的检测网页。只有JPEG编码，不做亮度增强或裁剪；若原程序使用 `--rotate180`，采集视图也会相应旋转。

1. 在 Pi 原来运行 `app.py` 的终端按 Ctrl+C 停止。
2. 在 Mac 终端，进入解压后同时包含两个文件夹的目录，上传更新的文件：

```bash
scp debris-detector-pi4/app.py pi@raspberrypi.local:~/debris-detector-pi4/app.py
```

3. 回到 Pi 终端启动：

```bash
cd ~/debris-detector-pi4
python3 app.py --host 0.0.0.0 --port 8000
```

4. 用 Mac 浏览器检查 http://raspberrypi.local:8000/raw.jpg ，应看到没有检测框的单张照片；然后在工作台点击“刷新Pi相机画面”或“拍一张原图”。IP变化时修改 `--camera-url`。

背景参考按钮会锁定相机曝光/白平衡。采集训练照片前，重新启动 Pi 程序并不要点击“拍空桌面参考”，让相机在正常使用的自动曝光下稳定后再拍。

不要同时开 `rpicam-hello` 或另一个独占CSI摄像头的程序。Mac 和 Pi 需要网络互通；校园网络隔离时可沿用SSH隧道，例如Mac另开终端运行：

```bash
ssh -N -L 8001:127.0.0.1:8000 pi@raspberrypi.local
```

这时启动工作台改用 `--camera-url http://127.0.0.1:8001/raw.jpg`。相机地址不可用不影响导入已有照片、标注或训练。

## 第一批50张如何分配

这是跑通流程的起点，不是保证精度的数据量。

| 用途 | 示例数量 | 操作 |
|---|---:|---|
| train 训练 | 30 | 场景名 `deskA_day`，用途选训练，拍30张 |
| val 验证 | 10 | 换独立场景，命名 `deskB_day`，用途选验证，拍10张 |
| test 测试 | 10 | 再换独立场景，命名 `deskC_evening`，用途选测试，拍10张 |

同一拍摄场景的照片必须属于同一集合，程序会阻止同名场景跨集合。这里只是分配示例：不能仅改场景名称就把同一组连续画面伪装成独立数据。每个用途最好逐渐积累多个独立场景。程序能阻止完全相同图片重复加入，不能自动判断近似照片或同一真实场景。

各集合既要有碎片，也可有确认过的空桌面。约20%的空图可以作为起点，现场按误检补充。使用真实安装的相机角度和实际碎片尺寸；覆盖左/中/右、近/中/远、不同朝向、不同桌面和光照。手移开、车停稳再拍，避免大量几乎相同的帧。保存原图，不要导入VNC截图、带框预测图或掩膜。

## 每50张自己标注

1. 在“批次”选择第1批，可勾选“只看未确认”。
2. 按住鼠标拖动，在每个可辨认碎片周围画框；统一类别为 `debris`。框应紧贴物体，图中所有需要清扫的目标都要标。
3. 画错时“删除”“撤销最后一个框”或“清空框”，然后重画。
4. 点击“保存框并下一张”（也支持Ctrl/Cmd+S）。没有碎片时点击“确认无碎片并下一张”。
5. 标注保存到磁盘，可关闭后继续。仅画了框没点保存的修改不会持久化。

未确认图片不会进入训练；空框必须明确确认是负样本，避免漏标图片被当作背景。不会自动将模型预测当作人工标签。采满50张自动进入下一批；允许不足50张先调试，但训练/验证各至少有一张已确认的正样本，否则拒绝启动。这个下限只是防止空集，不代表样本足够。

## 训练下一轮：累计数据，不只用最新50张

在工作台点击“累计训练一轮”。默认30个epoch，batch=4，输入尺寸640，自动选CUDA→Apple MPS→CPU；MPS不兼容时报错可选择CPU重试。Mac端无需账号或云端上传，首轮要联网下载官方 `yolo11n.pt`。

每次训练会：

- 固定一份当时所有已确认标注的数据快照，原图和YOLO标签复制到独立目录；训练期间继续标注不会改变正在使用的数据。
- 首轮从官方预训练YOLO11n开始，后续从上一轮**成功完成**的 `best.pt` 开始新的微调；不使用旧数据上的 `resume=True`。
- 使用所有累计训练图片，并用验证集自动检查；测试集不参与训练和最佳权重选择。
- 输出独立的本轮模型、训练曲线、验证预测图和日志。失败或被中断的轮次不会成为下一轮默认起点。

第2批、第3批继续拍摄和标注即可，不要删除前一批。日常比较用自动验证结果；独立测试集留到里程碑再看，反复根据测试结果调参会使它失去独立评估意义。

任务在后台运行；网页刷新可以继续查看当前任务。不要同时用两个工作台进程编辑同一个workspace。关闭网页服务不会删除数据，但已启动的训练子进程可能继续；重开服务后不会自动重新连接旧任务状态，先检查 `workspace/logs`，避免重复启动。

## 测试并看漏检/误检

训练完成后，工作台“独立测试集评估”使用最新成功模型和已确认的test图片。输出 `metrics.json`、混淆矩阵和预测图；没有独立测试正样本会提示补拍。每次测试也保存所用图片/标签快照，可追溯。

- Precision低：误报偏多，应补拍容易误认的背景，并检查漏标。
- Recall低：漏检偏多，应补充漏掉的尺寸、距离、光照和物体形态。
- mAP50、mAP50-95用于比较检测框质量；少量测试图片的数字很不稳定。
- 同时逐张查看预测图。不能把一个很小测试集上的高分当作可靠性能。

命令行也能使用（先激活 `.venv`，在本目录执行）：

```bash
# 默认累计训练30轮，可调整epoch和设备
python workflow.py train --epochs 30 --device auto

# 单独重复验证，供调试；正式测试用 --split test
python workflow.py evaluate --split val
python workflow.py evaluate --split test

# 在未标注的新照片上画预测框（它不会修改人工标注）
python workflow.py predict --source /你的绝对路径/新照片文件夹

# 只导出当前标注为标准YOLO数据，不训练
python workflow.py prepare

# 需要从某个较早模型继续时，用它自己的完整路径
python workflow.py train --model /你的绝对路径/best.pt --epochs 20
```

## 导出给Pi

工作台“导出Pi用NCNN模型”把最新成功模型另存到 `workspace/deploy`，然后转换为NCNN；首次转换可能自动安装公开转换依赖。不要只复制 `.param` 或 `.bin` 中一个，应复制生成的整个 `best_ncnn_model` 目录及元数据。导出输入尺寸默认640；若为了Pi速度改成320，须在该尺寸重新验证小碎片漏检：

```bash
python workflow.py export --imgsz 320
```

本工具完成采集、标注、训练、离线预测/评估和模型导出；**现有Pi检测网页不会自动换成新模型**。之后还需接入模型推理，并在Pi上验证相机预处理、方向、帧率和实际精度。导出成功不等于已部署，更不等于可以安全自动行驶。

## 导出训练数据

工作台第4区有两个下载按钮（浏览器直接下载ZIP，不修改工作区）：

| 按钮 | 内容 | 用途 |
|---|---|---|
| 下载 YOLO 数据集 | 只含**已确认**标注；`images/{train,val,test}`、`labels/{train,val,test}`、`data.yaml`（`path: .`）、`provenance.json` | 在其他电脑、Colab、Ultralytics直接训练：解压后 `yolo detect train data=data.yaml` |
| 下载完整备份 | 全部照片（含未确认）+ `manifest.json` | 备份或换电脑继续标注：解压成一个文件夹，`python studio.py --root 该文件夹` |

命令行同样可用（输出默认放 `workspace/exports/`）：

```bash
python workflow.py export-dataset --format yolo
python workflow.py export-dataset --format backup --out ~/Desktop/metalsweep_backup.zip
```

导出时同样检查场景/重复图片跨集合和原图校验和，不合格会拒绝导出。

## 文件与备份

| 文件/文件夹 | 含义 |
|---|---|
| `workspace/images` | 导入/采集的无框JPEG照片 |
| `workspace/manifest.json` | 图片、场景、用途、批次、人工框和确认状态；标注的唯一主记录 |
| `workspace/snapshots/…` | 各轮实际使用的图片、YOLO txt、data.yaml、provenance.json |
| `workspace/runs/round_…/weights/best.pt` | 本轮最佳权重 |
| `workspace/runs/round_…/results.csv` | 本轮训练和验证指标 |
| `workspace/evaluations/…` | 独立评估和预测图 |
| `workspace/logs` | 通过网页启动任务的日志 |
| `workspace/deploy` | 导出给Pi的模型 |

每批标完请备份整个workspace，尤其是images和manifest.json。不要手工移动、缩放或覆盖里面的原图；校验和不符会拒绝导出。重标图片需要重新训练才会影响模型，旧快照保持不变。标注功能是单机本地服务，默认仅监听127.0.0.1。

## 开发验证与边界

```bash
python -m unittest -v test_workflow.py
```

覆盖50张分批边界、保存恢复、明确空图、过期修改、场景/重复图片泄漏、YOLO坐标转换、快照不变、累计导出、缺失集合、原图校验、成功模型选择，以及HTTP导入/标注。实际训练的开发冒烟测试使用合成图，只验证流程可运行，不能证明现场精度。实际OV5647采集与Pi部署仍需实机检查。

参考：[YOLO标注格式](https://docs.ultralytics.com/datasets/detect/)、[训练](https://docs.ultralytics.com/modes/train/)、[验证/测试](https://docs.ultralytics.com/modes/val/)、[NCNN导出](https://docs.ultralytics.com/integrations/ncnn/)。训练依赖Ultralytics适用其AGPL-3.0或商业授权；本包不包含预训练权重和第三方照片。
