# 喵伴 MIAO

一只叫 **miaomiao** 的 Python 桌面猫咪。用你提供的绿幕 MP4 做真实透明动画，配有一个可以收起的中文养成面板。

## 启动

**EXE 版**：直接双击 `dist/miaomiao.exe`。这是 Windows 64 位单文件程序，已包含 Python、Qt 和 27 段透明动画，可以只复制这一个 EXE 到其他文件夹或电脑运行。首次启动需要解压内部资源，可能会等待几秒。

Windows 下双击 **启动桌宠.bat**。当前电脑已经具备依赖，透明素材也已经处理好。

也可以在本目录执行：

```powershell
python -m pip install -r requirements.txt
python main.py
```

只显示桌面小猫：`python main.py --desktop-only`。

需要 Python 3.10 或更新版本。当前验证环境为 Windows、Python 3.12、PySide6 6.11。其他系统未实机验证。

## 怎么陪 miaomiao 玩

- **单击小猫**：摸摸头，增加心情和亲密度。
- **拖拽小猫**：挪到喜欢的桌面位置；会记住位置。
- **双击小猫**：打开养成面板。
- **右键小猫**：喂食、喝水、梳毛、睡觉、探索等快捷操作。
- **关闭面板**：继续在桌面陪伴，不会退出程序。
- **右下角托盘**：打开面板、找回猫咪、切换散步、保存并退出。
- **宠物档案**：修改名字、调整大小、关闭自由散步。

六项状态是饱食、水分、精力、心情、清洁和健康。喂食消耗背包中的猫粮，喝水、梳毛、猫砂盆和睡觉免费。睡觉时不能喂食或玩耍，点击「叫醒」恢复互动，睡满会自动醒来。

喵币可以通过每日签到、今日约定、桌面探索和「追追球」小游戏获得。小铺使用的是游戏币，不涉及真实支付。动作有短暂播放时间和冷却，避免连续点击重复扣道具或刷奖励。

等级每 100 成长提升一级，称号依次变为「初见的小伙伴」「默契的好朋友」「形影不离的家人」。当前成长通过等级、亲密度和称号体现；原素材只有这一套猫咪外形。

## 存档

- Python 源码版默认位置：`save_data/pet.json`。
- EXE 版默认位置：`%LOCALAPPDATA%\miaomiao\save_data\pet.json`，与单文件解压目录分开。移动、替换 EXE 不会删除进度。日志在 `%LOCALAPPDATA%\miaomiao\logs\miao.log`。
- 将源码版进度带到 EXE：先退出源码版，再把 `save_data/pet.json` 复制到上面的 EXE 存档位置；不要覆盖仍想保留的另一份进度。
- 每 30 秒自动保存，照顾、购买、领奖和退出时也会保存。
- 原子写入，意外损坏的存档会保留为 `.corrupt-时间戳.json` 备份。
- 同一存档有单实例锁，避免重复启动互相覆盖。
- 离线最多结算 8 小时，消耗为在线的 30%，离线不扣健康；不会因几天没打开就失去小猫。
- 自定义存档：`python main.py --save path/to/pet.json`。

## 素材与抠图

原始 MP4 和「首帧图及其含义」文件夹都保持原样。共 **27 段视频、19 个动作编号**。

```powershell
python tools/prepare_assets.py
# 更高清，编码耗时与文件大小会增加
python tools/prepare_assets.py --size 768 --fps 24
# 单独重做第 7 个动作，并更新现有清单中的该动作
python tools/prepare_assets.py --only 7
```

输出是带 Alpha 通道的动画 WebP（默认最长边 512、保留 24fps 时序），位于 `assets/animations/`。透明首帧在 `assets/posters/`，动作清单在 `assets/manifest.json`。标准 MP4 不适合作为这里的透明播放格式，因此运行时播放的是抠图后的 WebP。

处理包含柔和边缘、绿边去色、整段固定裁切。第 7 段视频中途绿幕几乎变黑，额外使用低亮度色度与边界连通区域判断。保留碗、猫砂盆和原有毛发细节。素材自带的姿态切换、身体比例变化或循环接缝可能仍可见；没有合成不存在的过渡动作。

**已确认的源文件问题**：`4循环.mp4` 与 `5循环.mp4` 的 SHA-256 完全一致，实际是同一个歪头动作。保留原先 04 / 05 两个含义，图鉴里有说明。01 的图像实际偏低坐姿，名称沿用原文件的「趴卧清醒」。

## 动作对应

| 编号 | 原图含义 | 游戏用途 |
| --- | --- | --- |
| 01 | 趴卧清醒 | 休息陪伴 |
| 02 | 蜷缩睡觉 | 睡觉恢复精力 |
| 03 | 坐姿仰望 | 饿了、渴了、期待照顾 |
| 04 | 侧坐注视 | 安静陪伴；源视频与 05 重复 |
| 05 | 歪头坐姿 | 好奇与陪伴 |
| 06 | 侧身行走 | 桌面散步 |
| 07 | 站立抬尾 | 站立与随机待机 |
| 08 | 正坐正视 | 默认陪伴 |
| 09 | 站立挥爪 | 签到打招呼 |
| 10 | 低头玩耍 | 追追球小游戏 |
| 11 | 伸懒腰 | 醒来、随机伸展 |
| 12 | 打哈欠 | 精力不足 |
| 13 | 舔爪 | 梳毛、健康补给 |
| 14 | 回头看 | 随机回望 |
| 15 | 翻身卖萌 | 抚摸互动 |
| 16 | 低身前行 | 桌面探索 |
| 17 | 喝水 | 水分恢复 |
| 18 | 吃饭 | 猫粮和小食 |
| 19 | 拉粑粑 | 猫砂盆 |

图鉴中可以预览全部 19 种动作，以及 27 个循环 / 非循环 / 第二版本片段。

## 开发与验证

重新打包 EXE：双击 `打包EXE.bat`，或运行：

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --workpath build/standalone miaomiao.spec
```

`miaomiao.spec` 只带运行时需要的 Qt 与处理后的素材；原始 MP4、个人存档、测试数据、OpenCV 和 NumPy 不进入 EXE。资源读取遵循 [PyInstaller 的打包路径规则](https://pyinstaller.org/en/stable/runtime-information.html)。

EXE 自检：`dist\miaomiao.exe --self-test artifacts\exe-check`。它使用隔离存档，检查所有 27 段内嵌动画、页面、照顾动作、小游戏和存档恢复，输出 `report.json` 及界面渲染后退出。

```powershell
python -m pip install pytest
python -m pytest tests -q
python tools/smoke_test.py
```

测试覆盖透明通道、暗绿幕片段、进食扣库存、冷却、离线结算、睡眠、商店、每日奖励、损坏存档备份，以及真实 Qt 组件的页面切换、小游戏命中、奖励、存档恢复和关闭面板继续陪伴。渲染图位于 `artifacts/ui_*.png`，透明素材总览为 `artifacts/transparent_contact_sheet.jpg`。

代码结构：`pet/model.py` 管理养成与存档，`pet/app.py` 协调桌面行为，`pet/animation.py` 共享单个流式动画解码器，`pet/panel.py` 是养成面板，`pet/widgets.py` 绘制桌面猫咪与小游戏，`tools/prepare_assets.py` 负责绿幕处理。

实现使用 [Qt 透明窗口](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html) 和 [Pillow 动画 WebP](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp)。
