Title
Webview 版重构：Agent 精简 + SQL 参数化 + Tray 最小化

Summary

以 Webview 链路为主：Tray 优先启动，窗口按需打开。
Agent 只负责增量扫描入库；统计/导出迁移到 Webview 进程完成。
Tray 通过 tray_stats.json 显示数据，菜单最小化且用制表符对齐。
Scope

不改动 PyQt 代码，仅参考其逻辑。
重点改动 Webview 链路、Agent 简化、SQL 参数化、Tray 菜单与数据流。
Architecture Changes

入口切换为 Tray 优先

修改 __main__.py 以启动新的 Tray 主入口（建议复用/替代 main_tray.py）。
统一 Mac/Windows 的 Tray 实现，按平台选择 rumps 或 pystray。
新增“统计工作进程”

新增 stats_worker.py。
stats worker 常驻，按 settings.json 中 refresh_interval 轮询 DB，计算 Today/Month 数据与阈值百分比并写入 tray_stats.json。
stats worker 退出由 Tray 进程统一管理。
数据职责迁移

Agent 只做“读取 message 目录并更新 DB”。
Webview 进程负责：统计、分组、导出、展示、阈值百分比计算。
Agent 精简

IPC 命令收敛

保留 status、refresh、shutdown。
删除或不再暴露 stats/stats_range/export 等统计接口。
更新 uds_server.py 去除统计依赖。
锁文件可靠性

在 __main__.py 和 uds_server.py 使用 PID 校验而非仅 mtime。
复用标准库实现跨平台 PID 存活检查，不引入新依赖。
增量扫描精度

使用 st_mtime_ns 或纳秒级整数存储到 files.mtime，不再截断秒。
读取时识别老值（秒级）并自动换算，避免误判。
SQL 参数化与 DB 读取层

新建只读 DB 查询模块

新增 db_read.py。
所有 SQL 统一使用参数化 ?，禁止 f-string 拼接条件。
实现：
aggregate(scope)
aggregate_range(start_ts, end_ts)
by_provider(scope)
by_model(scope)
export_csv(scope|range)
Dedup 规则：包含 provider_id/model_id 在分组键。
保持 API 返回形状不变

get_stats 仍返回 total_input_tokens / total_output_tokens / total_cost / request_count / providers / trend / distribution 以避免 JS 大改。
成本计算使用 Settings.calculate_cost(...)，位置由 agent 转移到 webview backend。
Webview API 调整

api.py

get_stats/get_stats_by_provider/get_stats_by_model/export_csv 改为调用 db_read。
refresh/get_agent_status 保持调用 AgentBridge（只用于触发 scan 与健康检查）。
bridge.py

移除统计相关方法，仅保留 status/refresh/shutdown。
Tray 最小化与对齐

菜单内容

Today 标题 + 2~3 行统计
Month 标题 + 2~3 行统计
操作项仅保留：Open Main Window、Quit
阈值行仅在 thresholds.enabled 为 true 时显示。
制表符对齐

行内字段使用 \t 分隔，格式示例：
In:\t{input}\tReq:\t{requests}
Out:\t{output}\tCost:\t{cost}
Token:\t{token_pct}%\tCost:\t{cost_pct}%
数据更新

Tray 周期读取 tray_stats.json 并更新菜单项。
找不到文件或解析失败时显示 -- 占位。
Tray-Stats 文件协议

文件路径：tray_stats.json
JSON 示例结构：
today: input/output/reasoning/requests/cost/token_pct/cost_pct
month: 同上
thresholds_enabled: bool
display: 可选预渲染行文本（含制表符）
Process Lifecycle

Tray 启动时确保 Agent 在线，否则拉起 Agent。
Tray 启动 stats worker 进程并记录 PID。
Tray 退出时：
发送 Agent shutdown
终止 stats worker
清理 PID 文件
Public API / Interface Changes

Agent IPC 命令集减少为：status, refresh, shutdown。
新增 Webview 内部模块 db_read 与独立 stats_worker。
新增 tray_stats.json 文件协议（供 Tray 读取）。
Test Cases and Scenarios

Agent 单实例锁：已有进程时不再启动第二个。
mtime 精度：同秒内更新文件不丢数据。
SQL 参数化：range 查询传入恶意字符串不影响 SQL。
Tray stats 文件缺失/损坏时的降级显示。
Tray 菜单渲染与阈值行显示逻辑一致。
Tray 退出后 Agent/worker 正常停止。
Assumptions and Defaults

“前端处理”解释为：统计与导出从 Agent 移到 Webview 进程完成。
去重规则按你的回复：包含 provider_id/model_id 参与分组。
Tray 需要在窗口未打开时仍实时显示统计，因此采用常驻 stats worker。
刷新周期默认使用 settings.refresh_interval，缺省 300s。