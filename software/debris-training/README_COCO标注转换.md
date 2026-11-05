# TACO / COCO 标注转换与导入

本工具将已下载的COCO检测框转换为统一类别 `debris`，并导入**新的训练工作区**。原图片和已有标注不会被覆盖。不需要先装Ultralytics；已有Pillow依赖即可。它不下载数据、不训练，也不为未标注图片生成标签。

## 转换规则

COCO：`bbox=[x,y,w,h]`，x/y是左上角像素坐标。

YOLO每个物体一行：`类别编号 中心X/图宽 中心Y/图高 框宽/图宽 框高/图高`。

例如图像640×480、COCO框 `[100,120,80,60]`：

```text
0 0.21875000 0.31250000 0.12500000 0.12500000
```

原类别ID不一定连续，也不一定从0开始。工具按原始ID筛选，再把选中的全部类别映射到 `0: debris`。此操作是重新定义检测目标，不是教模型区分金属/塑料。只有与实际清扫目标相符的类别才应该合并。

## 1. 准备数据

从 https://github.com/pedropro/TACO 获取官方标注和对应图片。常见结构如下；工具按JSON里 images[].file_name 查找图片：

```text
TACO/
  data/
    annotations.json
    batch_1/000000.jpg
    batch_2/...
```

因此上述结构的 `--images` 应指定 `TACO/data`，不是整个TACO目录，也不是batch_1。必须用与JSON尺寸一致的原图，不能换成网页缩略图或另一版缩放图。下载是否成功需要在本机核对；本工具没有替你下载真实数据。

在Mac终端进入工具所在目录，激活之前训练用的环境：

```bash
cd software/debris-training
source .venv/bin/activate
```

如果还没有环境，先运行 `python3 -m venv .venv`，激活后 `python -m pip install -r requirements-label.txt`。

## 2. 先列出类别

下面以数据放在Mac的Downloads为例；按实际下载位置替换路径：

```bash
python import_coco.py \
  --annotations "$HOME/Downloads/TACO/data/annotations.json" \
  --list-categories
```

终端输出“原类别ID＋名称”。按输出选择瓶盖、包装碎片等与实物相符的类别。不要照其他版本的数据集猜编号。

## 3. 转换并创建新工作区

以下命令默认导入所有类别，最多200张，**只加入train**：

```bash
python import_coco.py \
  --annotations "$HOME/Downloads/TACO/data/annotations.json" \
  --images "$HOME/Downloads/TACO/data" \
  --out ./workspace_coco \
  --limit 200
```

如果已经选好类别，额外加 `--category-ids "原ID1,原ID2"`，把占位文字换成上一步真实的整数ID。每次输出路径必须不存在；重复运行请换新名字。

如果要保留已有现场数据一起训练，先停止原标注工作台，再给上面的命令额外加：

```text
--base-workspace ./workspace
```

它把原工作区的images和manifest复制到新工作区，再添加公开数据；原数据仍保留。只复制照片/标注，不复制旧训练模型、日志、快照。若想继续旧权重，可在workflow.py训练时显式传旧best.pt的路径。

公开图片默认只作为训练数据。验证/测试请使用独立现场照片。精确重复图片会跳过（包括已在原验证/测试集里的图片）；近似照片、同一片段仍需要人工检查。

## 4. 在网页检查已有框

```bash
python studio.py --root ./workspace_coco
```

打开 http://127.0.0.1:8090/ 。公开标注的矩形框已经预填，不用重新画；检查后点击“保存框并下一张”。默认保持未确认状态，所以还没有复核的图片不会进入现有workflow.py训练快照。

如果已核对来源标注、类别映射和图片方向/尺寸，并希望直接接受源标签，可在创建新工作区时额外加 `--accept-labels`。该选项仅表示你接受已有标签，不表示标注必然准确。建议仍抽查不同类别和图片至少一批。

之后把现场照片采集/标注到这个新工作区，按场景划分训练、验证、测试，再运行训练。只有公开train数据时，现有训练程序会因缺少已确认的val正样本而拒绝开始，这是正常的数据划分检查。

## 输出与检查

- `images/`：工作台使用的标准化JPEG。
- `manifest.json`：图片、预填像素框、人工确认状态；工作台的标注主记录。
- `yolo_labels/train/*.txt`：本次公开数据的YOLO标签副本，文件名对应images里的新编号。
- `coco_import_report.json`：来源、源标注哈希、类别映射、原图片ID与新编号、跳过数量、许可元数据。

`yolo_labels`是转换时的副本，后续网页改框不会同步修改它。实际训练使用manifest生成的不可变快照，包含标准的images/train与labels/train目录及data.yaml。

程序拒绝不匹配的图片尺寸、EXIF旋转、非法路径、损坏/过小的框；部分越界框裁到图像边界，裁后小于2像素则中止。选中类别含crowd/ignore标注的整张图会跳过，避免把未处理目标当背景。类别筛选后没有目标的图默认跳过；仅加 `--include-empty` 才接收原JSON中完全无标注的图，仍须人工确认它是否真空图。

整个新工作区在转换成功后才发布；失败时不留下半成品工作区。真实数据里尚未标出的目标无法靠格式转换发现。

工具只支持**带bbox的COCO JSON**。纯语义分割色彩图、没有检测框的分类数据（例如原始TrashNet）不能直接使用。ZeroWaste需先确认下载版本提供的具体标注结构，不能仅把文件改名为COCO。

本地测试：`python -m unittest -v test_import_coco.py`。

格式参考：https://docs.ultralytics.com/datasets/detect/
