## CommandSender v2.0.0 - 跨平台版本

### 适配系统
- **Windows 10/11**
- **Ubuntu 22.04** (新增)

### 功能特性
- 命令行批量发送到指定终端窗口
- 支持剪贴板粘贴和键盘模拟两种发送方式
- 可视化窗口选择（十字准星 + 红色高亮边框）
- 命令文件管理（新建/打开/保存/最近文件）
- 自动跳过注释行（`#` `//` 开头）
- 跨平台窗口管理：Windows 使用原生 API，Linux 使用 xdotool

### 安装指南 (Ubuntu 22.04)

#### 系统依赖
```bash
sudo apt install xdotool python3-tk
```

#### 安装
```bash
tar xzf CommandSender-2.0.0-ubuntu22.04.tar.gz
cd CommandSender-2.0.0-ubuntu22.04
./install.sh
```

#### 运行
```bash
CommandSender
```

#### 卸载
```bash
cd CommandSender-2.0.0-ubuntu22.04 && ./uninstall.sh
```

#### 文件位置
- 可执行文件: `/usr/local/bin/CommandSender`
- 命令文件: `~/.config/commandsender/commands/`
- 配置文件: `~/.config/commandsender/app_config.json`

### 变更日志 (v2.0.1)
- **修复** pyautogui 在无 X11 环境下导入即崩溃的问题（改为延迟导入模式）
- **修复** `build.sh` 在 Ubuntu 24.04+ 上因 PEP 668 限制 pip 安装失败的问题

### 变更日志 (v2.0.0)
- **新增** `window_manager.py` 平台抽象层（Windows + Linux 双平台实现）
- **重构** 核心代码移除 Windows API 硬编码依赖
- **新增** Ubuntu 22.04 构建脚本 (`build.sh`) 和安装包生成脚本 (`package_ubuntu.sh`)
- **新增** `.desktop` 桌面集成文件
- **更新** README 添加 Linux 安装指南
- **新增** 安装包内附 `install.sh` 和 `uninstall.sh`

### 安装包信息
- **文件名**: `CommandSender-2.0.0-ubuntu22.04.tar.gz`
- **SHA256**: `221dc32205778edd3dab9d077a79ac412f6ef7b3fef74142fc111c1a567518d8`
- **大小**: 15 MB
