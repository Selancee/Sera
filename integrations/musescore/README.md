# Sera MuseScore Studio Bridge v0.3.1

这是 Sera 的本地 MuseScore 桥接插件。它只负责把当前宿主上下文交给 Sera Agent Console，并在审核完成后打开新的 MusicXML 修订；不会启动外部浏览器，也不会覆盖源乐谱。

## 为什么不再使用 `writeScore()`

已在真实的 MuseScore Studio 4.5.2（build 251141402）中确认：插件能够加载，但调用 QML `writeScore()` 时日志输出 `PluginAPI::writeScore | Not implemented!!`。因此先前的“自动导出临时 MusicXML”失败不是等待时间、目录权限或 Sera 后端问题，而是该 MuseScore 版本的插件 API 没有实现这项能力。

当前桥接改用已验证的本地方案：

1. 用户先在 MuseScore 按 `Ctrl+S` 保存当前乐谱。
2. 插件让用户选择当前打开的已保存文件。
3. Sera 后端调用本机 MuseScore CLI，把 `.mscz`、`.mscx` 或 `.mxl` 转为临时 MusicXML；`.musicxml` 和 `.xml` 则直接读取。
4. 插件同时传输 MuseScore 的 measure/tick/staff 选区上下文，Sera 桌面窗口自动置前。
5. 用户在 Agent Console 中生成、校验并应用修改后，插件可让 MuseScore 打开最新 MusicXML 修订；它作为新乐谱打开，源文件保持不变。

MuseScore 官方文档也将命令行转换列为支持的批处理能力；桥接不再依赖 4.5.2 中不可用的 QML 导入/导出方法。

## 现在如何使用

1. 启动 `D:\Sera\dist_desktop\release\win-unpacked\Sera.exe`，等待 Agent Console 出现。
2. 在 MuseScore 打开乐谱并按 `Ctrl+S`。每次发送前都要保存，否则 4.5.2 的插件无法看到尚未落盘的修改。
3. 选择要编辑的小节或谱表；没有选区时，Sera 默认从第 1 小节开始聚焦。
4. 打开 `Plugins -> Sera Score Bridge`。
5. 点击 `Choose saved score`，选择当前 MuseScore 中已保存的 `.mscz`、`.mscx`、`.mxl`、`.musicxml` 或 `.xml` 文件。
6. 点击 `Send saved score / selection to Sera`。成功后 Sera 会自动置前，并显示已连接的宿主和选区。
7. 在 Sera 对话框输入修改要求，审查验证报告，再点击应用并生成宿主修订。
8. 回到插件，点击 `Refresh and open applied revision`。MuseScore 会打开一个新的修订乐谱，不覆盖原文件。Bridge 不显示草稿提案；只有在 Sera 中点击“应用并生成宿主修订”后，修订号才会从 0 增加。

## 安装或更新插件

在 `D:\Sera` 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_musescore_bridge.ps1 -UpdateExisting
```

脚本会把插件安装到当前用户的 `Documents\MuseScore4\Plugins\SeraBridge`。更新已有插件时会先创建带时间戳的备份。然后重启 MuseScore，在插件管理器中启用 `Sera Score Bridge`。

默认本地 API 为 `http://127.0.0.1:8000`。如果端口被其他程序占用，Sera Desktop 会明确显示启动失败，不会静默换端口。

## 已验证与尚未实现

已在 MuseScore Studio 4.5.2 中实际验证：

- 插件加载与界面显示；
- 选择已保存乐谱；
- 由 MuseScore CLI 转换并创建 Sera 会话；
- MuseScore 选区上下文传入 Sera；
- Sera 桌面窗口自动置前并显示已连接到 MuseScore Studio；
- 宿主原有连桁记谱在局部移调的保护范围比较和 MusicXML 导出中保持不变；
- 不打开外部浏览器，不改写源文件。

当前限制：

- 必须先保存乐谱；未保存的内存修改无法传给 Sera。
- 输出以新乐谱打开，不会原位修改当前标签页。
- MuseScore 单步 Undo、原位事务和复杂宿主元素 ID 映射尚未实现。
- Sibelius ManuScript 桥接尚未实现。
- 本次真实联调完成了 MuseScore 到 Sera 的输入闭环；“打开最新修订”的 API 和进程调用已有自动测试，但本次没有在真实宿主中完成输出方向的可见验收。

## 官方参考

- [MuseScore Plugin API `writeScore` / `readScore`](https://musescore.github.io/MuseScore_PluginAPI_Docs/plugins/html/class_ms_1_1_plugin_a_p_i_1_1_plugin_a_p_i.html)
- [MuseScore command-line usage](https://handbook.musescore.org/appendix/command-line-usage)

## v0.3.1 修订导出安全说明

Sera 不再把精简的 `ScoreDocument` 重新生成为整份 MusicXML。修订导出会以宿主原始 MusicXML 为底稿，只修改目标 XML 节点，因此会保留 MuseScore 写入的页面尺寸、系统布局、分页、谱表间距、隐式休止符以及未修改区域的记谱信息。

当前源文件保真路径支持以下局部修改：

- 音高与移调；
- 演奏法；
- 力度（按实际变化位置写入一次 direction，不再给每个音符添加 `mf`）；
- 标题与作曲者。

插入、删除、改变时值、拍号等会重构乐谱结构的操作目前会被明确拒绝，不会退回到整谱重建。后续只有在对应的宿主保真补丁实现和测试完成后才会逐项开放。

升级后必须重启 Sera 和 MuseScore，并从原始宿主文件重新发送，创建一个新会话。旧版本已经生成的 `*_r0001.musicxml` 修订不会被自动修复，请不要继续使用。
