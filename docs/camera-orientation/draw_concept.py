"""Camera mount concept; diagram is not to scale and is not a fabrication drawing."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle, Circle, Polygon, Arc

P = Path(__file__).resolve().parent
font = FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams['svg.fonttype'] = 'path'
fig, ax = plt.subplots(figsize=(13, 8), dpi=160)
fig.patch.set_facecolor('#f4f6f2')
ax.set(xlim=(0, 1200), ylim=(760, 0))
ax.axis('off')

def text(x, y, content, size=12, color='#183a42', **kwargs):
    ax.text(x, y, content, fontproperties=font, fontsize=size, color=color, **kwargs)

def arrow(x1, y1, x2, y2, color='#2a6a91'):
    ax.annotate('', (x2, y2), (x1, y1), arrowprops=dict(arrowstyle='<->', color=color, lw=1.5))

def lead(x, y, target, content, size=11):
    text(x, y, content, size)
    ax.annotate('', target, (x+10, y+8), arrowprops=dict(arrowstyle='-', color='#687d80'))

text(30, 40, '摄像头怎么朝向', 24)
text(30, 72, '侧视示意 · 车头是橙色滚刷这一端 · 非等比例安装图，角度需要用实时画面调整', 12)
ax.plot([100, 1100], [535, 535], color='#758c83', lw=2)
text(1010, 561, '桌面', 11)
ax.add_patch(Rectangle((165, 315), 310, 12, facecolor='#c6ded9', edgecolor='#739d96'))
for x in (220, 410):
    ax.add_patch(Circle((x, 470), 65, facecolor='#343e43'))
    ax.add_patch(Circle((x, 470), 24, facecolor='#e5b83c'))
ax.add_patch(Rectangle((480, 350), 178, 160, facecolor='#293b42'))
ax.add_patch(Polygon([(480, 510), (658, 510), (717, 531), (480, 531)], facecolor='#465b61'))
text(508, 431, '集尘盒', 12, color='white')
ax.add_patch(Circle((730, 503), 32, facecolor='#ef9129', edgecolor='#b96215', lw=2))
text(687, 579, '滚刷前缘', 11)
ax.plot([762, 762], [535, 640], color='#c59256', lw=1, ls='--')
ax.plot([440, 440], [315, 640], color='#92aaa1', lw=1, ls='--')
# Round-hole clamp; dimensions of existing hole and provisional plate thickness are retained.
ax.add_patch(Rectangle((410, 303), 60, 12, facecolor='#176f61'))
ax.add_patch(Rectangle((413, 328), 54, 9, facecolor='#176f61'))
ax.plot([440, 440], [301, 341], color='#b4bec0', lw=4)
# Adjustable mast and an optional forward extension.
ax.add_patch(Rectangle((433, 174), 20, 130, facecolor='#176f61'))
ax.add_patch(Rectangle((439, 202), 6, 58, facecolor='#f4f6f2'))
for y in (213, 249):
    ax.add_patch(Circle((442, y), 5, facecolor='#becbcb', edgecolor='#314f51'))
ax.add_patch(Polygon([(433, 302), (408, 302), (433, 263)], facecolor='#2f9987'))
ax.add_patch(Rectangle((444, 166), 142, 15, facecolor='#176f61'))
ax.add_patch(Circle((590, 177), 9, facecolor='#c4cecd', edgecolor='#176f61', lw=3))
ax.add_patch(Rectangle((591, 169), 30, 36, angle=-35, facecolor='#25946f', edgecolor='#12513f'))
ax.add_patch(Circle((623, 187), 9, facecolor='#192e34'))
# Field-of-view envelope is illustrative, not the lens's measured FOV.
ax.add_patch(Polygon([(623, 187), (762, 535), (1110, 535)], facecolor='#7dc4b2', alpha=.2))
ax.plot([623, 1010], [187, 535], color='#378f76', ls='--', lw=1.5)
ax.plot([623, 850], [187, 187], color='#94a6a0', ls=':', lw=1)
ax.add_patch(Arc((623,187),210,210,theta1=0,theta2=42,color='#b9792f',lw=1.8))
text(743, 239, '向下约 35–45° 起步', 11, color='#95601f')
ax.add_patch(Polygon([(995, 530), (1013, 521), (1030, 533)], facecolor='#dc7c56'))
text(853, 568, '刷前可见工作区', 12)
lead(40, 133, (442, 233), '② 高度调节：两颗螺栓锁紧')
lead(480, 120, (590, 177), '③ 俯仰轴：调好后锁住')
lead(810, 154, (623, 187), '④ 25 × 25 mm 相机托架')
lead(795, 288, (525, 173), '横臂按遮挡情况决定是否前伸')
lead(34, 374, (428, 312), '① 利用原来的前方圆孔固定\n高度与横臂长度待试装后确定')
ax.annotate('', (1050,610), (820,610), arrowprops=dict(arrowstyle='->', color='#176f61', lw=2))
text(835, 645, '车头 / 前进方向', 12)
text(35, 680, '看实时画面调好，再锁紧支架', 13)
text(35, 714, '下沿：尽量看见滚刷前缘附近    中间：刷前桌面与碎片    左右：覆盖滚刷工作宽度', 12)
text(35, 747, '绿色区域仅表示希望看到的工作区，不代表摄像头实测视场；集尘盒遮挡时提高或前移镜头。', 11, color='#647a79')
fig.tight_layout(pad=.6)
fig.savefig(P / 'camera_mount_concept.png', facecolor=fig.get_facecolor())
fig.savefig(P / 'camera_mount_concept.svg', facecolor=fig.get_facecolor())
print(P / 'camera_mount_concept.png')
