# 整理后检查 · 2026-11-05

本次检查在独立导出目录内进行，原outputs资料保留。测试环境为Mac临时Python 3.14环境，使用Pillow、NumPy和OpenCV-headless；没有连接实际Pi、摄像头、GPIO、继电器或电机。

| 软件目录 | 命令 | 结果 |
|---|---|---|
| software/debris-training | python -m unittest -v test_workflow.py test_import_coco.py | 15 tests，OK |
| software/metalsweep-control | python -m unittest -v test_control.py test_http.py | 17 tests，OK |
| software/debris-detector-pi4 | python -m unittest -v test_app.py test_http.py | 10 tests，OK |

合计42项检查通过，覆盖合成数据标注/转换/快照、独立数据划分、HTTP边界、平面投影、轮刷状态机、独立动作时限、停止取消后续动作和完整离线收集流程。

另检查：Python源码语法、Markdown相对链接、导出目录文件大小、个人机器路径/私人IP/凭据模式扫描、文件SHA256清单。训练启动器改为默认读取8091 SSH隧道的原图，也支持CAMERA_URL覆盖地址；已检查zsh语法。

STL与图纸来自此前生成资料，二进制文件保持原样，网格检查记录随模型保留；本次没有重新切片/打印或开展实物测量。首次整理不重新训练模型、不下载TACO图片、不包含用户现场采集照片/权重。

复现软件检查可在临时环境安装：

```bash
python -m pip install 'Pillow>=10,<14' 'numpy>=1.26,<3' 'opencv-python-headless>=4.10,<6'
```

分别进入表中目录运行测试（不需要安装Ultralytics来执行这些模拟检查）。主机需允许本机回环HTTP绑定。文件与文档检查在仓库根目录执行：`python tools/check_repository.py`。

这些结果证明代码在整理后的路径下仍可运行，不能推导现场识别率、运动精度、停机安全等级或进盒成功率。
