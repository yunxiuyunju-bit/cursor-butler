# 光标管家 🖱️

Windows 一键换鼠标光标工具。为明日方舟主题光标包设计，但支持任何标准的 `.cur` / `.ani` 光标包。

![python](https://img.shields.io/badge/python-3.8%2B-blue) ![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)

## 功能

- **主题库**：自动扫描主题文件夹，一键应用 / 双击即换，当前方案带 ✓ 标记
- **实时预览**：像素级渲染光标第一帧（正常选择 + 链接 / 文本 / 忙 / 不可用）
- **大小调节**：32~256px 直写系统基准（`CursorBaseSize`），附系统精确模式入口
- **拖拽安装**：把主题压缩包**或已解压的主题文件夹**拖进窗口即自动安装——自动解压、解析 `.inf` 槽位映射或按中英文文件名识别（含 GBK 文件名修复），并自动跳过教程 / 预览图之类的杂物
- **宽松识别**：不要求凑齐 17 个槽位，有几个识别几个，只有单个光标的主题也能收录
- **无损放大**：`.ani` 最近邻整数倍放大（2x / 3x），逐帧处理并同步缩放热点坐标
- **开机自启**：勾选即写入注册表 Run 键

## 安装

### 方式一：下载安装包（推荐）

到 [Releases](../../releases) 下载 `CursorButler-v1.1.3-setup.exe`，双击一路下一步即可。装完会打开主题库文件夹，把你下载的主题丢进 `安装包` 子目录，重开程序就会自动识别。

安装到 `%LOCALAPPDATA%\Programs\光标管家`，**不需要管理员权限**。

### 方式二：绿色版

下载 `CursorButler-v1.1.3-portable.exe` 放到任意文件夹，旁边建一个 `光标主题` 文件夹放主题即可，卸载就是删文件夹。

### 方式三：从源码运行

```bash
pip install pillow tkinterdnd2
python cursor_app.py
```

## 主题库放哪？

程序按以下顺序自动查找主题库，用第一个"确实含有主题"的目录：

1. 环境变量 `CURSOR_LIB` 指定的目录
2. 程序目录下的 `光标主题\`
3. 程序目录本身
4. 程序上级目录下的 `光标主题\` 及上级目录本身
5. `%USERPROFILE%\光标主题`

主题可以这样放：

1. `.zip` 主题包 **拖进窗口** 或放进主题库的 `安装包\` 文件夹，下次启动自动安装
2. 已解压的主题文件夹直接放进主题库根目录，应用内点"刷新"
3. 在列表中双击主题或点"应用主题"即可生效

槽位识别支持三种方式（按优先级）：`.inf` 安装脚本的方案定义 → 中英文常见命名（`正常选择` / `normal` / `PRTS - normal 正常选择` 这类带前缀的也能识别）→ 文件名启发式。

## 从源码构建 exe

```bash
pip install pyinstaller pillow tkinterdnd2
pyinstaller --onefile --windowed --name 光标管家 --icon app.ico ^
  --collect-all tkinterdnd2 --hidden-import tkinterdnd2 cursor_app.py

# 再编译安装包（需先装 Inno Setup 6）
ISCC.exe installer.iss
```

## 已知的坑（本工具的由来）

- Windows 11 部分 Insider 版本上 `SystemParametersInfo(SPI_SETCURSORS)` 返回失败，改用 `SetSystemCursor` 逐槽位替换才能即时生效
- 高缩放屏（125%/150%）下必须开 Per-Monitor DPI 感知，否则界面被位图拉伸发虚
- 系统设置页的"指针样式"选择器会把自定义方案整体重置为 Windows 默认——调整大小请只用"大小"滑块
- PIL 生成的 PNG 帧 `.cur` 它自己的 CUR 读取器读不了，预览时走 type-1 ICO 重包装回退

## 免责声明

本仓库**不包含任何光标主题素材**，安装包也不附带。主题包的版权归原作者所有，请在支持原作者的前提下获取使用（比如给发资源的 UP 主一键三连）。

## License

MIT
