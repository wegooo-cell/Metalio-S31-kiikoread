# kiikoread · Metalio S31

为 **Metalio E-INK4 Plus / 无名4.7** 专门适配的 kiikoread 阅读固件，源码公开。本仓库面向 **ESP32-S31、V1.5、34Pin E0470A14-AF** 设备，是独立适配项目，并非 Metalio 官方固件。

[English](README.md) · [日本語](README.ja-JP.md) · [官网刷机](https://kiikoread.com/?device=metalio#flash-action) · [Pico 项目](https://github.com/wegooo-cell/read-pico-reader)

## 当前正式版：rc104

- [官网在线刷机与版本选择](https://kiikoread.com/?device=metalio&version=rc104#flash-action)
- [rc104 固件、TF/USB 包和 SHA-256](https://github.com/wegooo-cell/read-pico-reader/releases/tag/metalio-s31-v0.3.3-rc104)
- [版本日志](docs/CHANGELOG.md) · [板型与构建说明](docs/BOARDS.md)

正式二进制继续在统一发布仓库归档，本仓库维护 Metalio S31 源码；本仓库历史 Release 中带 test 的版本为早期预览版。Metalio 与 Pico 的芯片、供电、波形和分区分别适配，固件不能跨机型刷写。

### TXT自动目录

TXT会识别中文章节编号、Chapter、序言/番外等标题；有统一长分隔线的文本优先使用该结构，纯数字目录则结合连续编号保守判断。兼容标题前空格和长章名，不把短横线场景分隔或普通括号对白直接当成章节。

目录只保存紧凑的原文件定位，按需分配1KiB页，最多16384项、128KiB；标题最多缓存8条，正文沿用原有按段读取，不载入整本书。资源不足或候选过多时回退原分段目录，保留原有文件与分段限制。首次需流式扫描原文件，之后校验并复用索引缓存；缓存写入失败仍可阅读。

新增目录定位到旧阅读分段内部，不重排已有进度与书签编号，也不改写TXT。规则两机共用，编码支持仍按各板原实现；Pico/S31均支持UTF‑8、GBK，S31继续支持UTF‑16。

### 英文断行

TXT/EPUB横排优先保留完整英文单词，兼容撇号、重音字母和已有连字符。正文完整行的小空隙通过词间空格适度对齐，不拉散单词内部字距，段末行保持自然宽度。整词换行会留下至少行宽20%且三个字高的空白时，六字母以上的纯拉丁词可补显示用连字符；断点前至少三字母、后至少两字母，并至少消除一半留白。超长词和极窄行仍保留安全拆分；这是按宽度处理，并非词典音节断字。Pico/S31两机同步，不改原文、进度或书签的原文字节位置，重新排版后页数可能变化。竖排规则不变。

## 功能

- 设置 → 书架样式新增「液态玻璃书架」：每页九本，不透明封面、薄玻璃挡条和细层板；保留原样式及各机型原刷新策略，不增加补刷，选择随重启和配置备份保存。
- 首页、书架、文件管理与系统设置；支持 EPUB、TXT 和书内图片。
- 导入 TTF/OTF 系统及阅读字体，列表最多128款，支持字号、字重和抗锯齿设置。
- S31 冷暖前光、低亮度调节、按键振动、AI 键快捷菜单及 BLE 翻页器。
- Wi-Fi、热点和 USB 传书，官网 USB 刷机与联网 OTA；OTA 优先 GitHub Pages，官网备用。
- 阅读票根、壁纸、书架拼贴和透明书封锁屏，支持密码验证与阅读上下文恢复。
- rc103 的“关机睡眠”仅提供默认“浅睡10分钟后进入深睡”和“彻底断电”，移除单独锁屏省电设置。具体续航与深睡唤醒效果仍需实机验证。

## 安装与升级

使用电脑 Chrome 或 Edge 打开[官网](https://kiikoread.com/?device=metalio#flash-action)，选择 **Metalio EINK 4 Plus**。

**首次安装必须先恢复 Metalio 官方固件，并从官方固件进入 BOOT。** 已有兼容 kiikoread 基础包可直接更新。网页默认保留机内设置，可选择是否清除数据；TF 卡文件保留，不做刷前备份。

TF 升级使用 Release 中的 `Metalio-S31-update.bin`，在设备“系统升级”中选择 TF 卡升级。应用 Bin 只用于兼容的 S31 双槽基础包，不能直接写到 `0x0`；完整初装请用官网或对应 USB 包。

## 构建

共享 `main/` 阅读器和 UI，S31 驱动及分区由 `boards/metalio47/` 选择。使用匹配 ESP32-S31 的 SDK、工具链及锁定组件，完整参数见 [docs/BOARDS.md](docs/BOARDS.md)。当前 rc104 的配置示例：

```sh
python3 tools/build_firmware.py --board metalio47 \
  --idf-metalio47 /path/to/metalio-esp-idf \
  --python /path/to/python --tools /path/to/espressif-tools \
  --managed-metalio47 /path/to/locked-managed-components \
  --output build/metalio47 \
  --s31-pie --s31-text-ripple --s31-reader-panel37 --s31-fast-reader-panels --s31-shelf37
```

保留原厂 GC48 / GL48 / DU20 数据和本板供电顺序；构建后核对芯片、项目、版本、分区及校验值。各模式的实验短波形、失败回退和验证限制见板型文档。

## 许可与贡献

许可按 [LICENSE](LICENSE)、[第三方声明](THIRD_PARTY_NOTICES.md)及各文件标识分别适用，与 Pico 的现有许可范围一致：已授予的 Apache-2.0 等权利保留；明确标注个人学习许可的新增原创内容按该许可适用，商用需相应权利人许可。

问题反馈与贡献请使用本仓库的 Issues 和 Pull Requests，并注明 S31 固件版本、板型与复现步骤。参考硬件及原厂实现：[CloudZao/Metalio-E-INK4-Plus](https://github.com/CloudZao/Metalio-E-INK4-Plus)。
