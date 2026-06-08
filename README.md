# CommandSender - 跨平台命令行发送工具

一个简洁的命令行批量发送工具，支持 **Windows** 和 **Linux (Ubuntu 22.04)** 系统。
可以将预设的命令快速发送到指定的终端窗口（如 PowerShell、CMD、Bash、Zsh 等）。

## 系统支持

| 平台 | 状态 | 窗口管理方案 |
|------|------|-------------|
| Windows 10/11 | 支持 | Windows API (user32.dll) |
| Ubuntu 22.04 | 支持 | xdotool |

## 界面说明

```
┌─────────────────────────────────────────────────┐
│ 最近文件: [▼ 选择文件    ] [新建] [打开] [保存] │
├─────────────────────────────────────────────────┤
│                                                 │
│           命令内容区域                          │
│      （用鼠标拖拽选择要发送的内容）            │
│                                                 │
├─────────────────────────────────────────────────┤
│  目标窗口    │  发送                            │
│  [选择目标窗口] │  [发送选中内容]               │
│   PowerShell │  [发送全部]                      │
└─────────────────────────────────────────────────┘
```

## 使用方法

### 1. 准备命令文件

创建文本文件（.txt），每行一条命令：

```txt
# 这是注释行，发送时会自动跳过
Get-Process
Get-Service
ipconfig
ping 8.8.8.8
```

### 2. 加载命令

- 点击 **"新建"** 创建新文件
- 点击 **"打开"** 加载本地已有的命令文件
- 从 **"最近文件"** 下拉列表快速选择

### 3. 编辑命令

在命令内容区域直接编辑：
- 修改命令内容
- 添加新命令（每行一条）
- 使用 `#` 或 `//` 开头添加注释

编辑完成后点击 **"保存"** 按钮保存到文件。

### 4. 选择目标窗口

1. 点击 **"选择目标窗口"** 按钮
2. 光标变为十字准星（或跟随系统提示）
3. 点击目标窗口（如终端窗口）
4. 目标窗口会显示红色高亮边框表示选中

### 5. 发送命令

两种发送方式：

- **发送选中内容**：先用鼠标拖拽选中文本，然后点击发送
- **发送全部**：点击发送全部内容

发送时自动跳过注释行（以 `#` 或 `//` 开头）。

## 安装指南

### Windows

直接下载 `CommandSender.exe`，双击运行。

首次运行可能需要管理员权限（用于窗口控制）。

### Ubuntu 22.04

#### 方法一：使用安装包

```bash
# 下载并解压
tar xzf CommandSender-2.0.0-ubuntu22.04.tar.gz
cd CommandSender-2.0.0-ubuntu22.04

# 安装
./install.sh
```

#### 方法二：从源码运行

```bash
# 安装依赖
sudo apt install python3-tk xdotool
pip3 install pyautogui pyperclip

# 运行
python3 command_sender.py
```

### 系统依赖（Linux）

应用依赖以下系统包：
- `python3-tk` - Python Tkinter GUI 库
- `xdotool` - X11 窗口自动化工具（用于窗口选择与激活）

```bash
sudo apt install python3-tk xdotool
```

## 文件说明

- `command_sender.py` - 主程序源代码
- `window_manager.py` - 平台抽象层（Windows/Linux 窗口管理）
- `commands/` - 命令文件存储目录
- `app_config.json` - 配置文件（自动生成）

## 打包/编译

### Windows

```batch
build.bat
```

### Ubuntu 22.04

```bash
# 仅编译
bash build.sh

# 编译并打包
bash package_ubuntu.sh
```

输出文件：
- `dist/CommandSender` (Linux 可执行文件)
- `dist/CommandSender-2.0.0-ubuntu22.04.tar.gz` (安装包)

## 注意事项

- 程序会自动创建 `commands/` 目录存放示例命令文件
- 发送命令时会激活目标窗口并粘贴内容
- 支持各类终端：PowerShell、CMD、Git Bash、Bash、Zsh 等
- 注释行（`#`、`//` 开头）在发送时自动跳过

## 许可证

MIT License
