---
name: gpt-trigger
description: >
  GPT 触发（gpt-trigger）：Review Bus 循环的触发与运转入口（git-bus + Edge 单行
  唤醒 + 后台 waiter 自动唤醒）。凡用户说"gpt触发""触发GPT""唤醒GPT""通知GPT"
  "给GPT发wake/门铃""重启waiter""等GPT决策""这轮做完了/收尾发唤醒"，或项目
  采用"Web-GPT 当决策者、ZCode 当受约束执行器、GitHub 分支为唯一事实源"的协作
  模式、需要建立/运转完整执行轮循环时，一律使用本 skill：执行器完成一轮 →
  推送 git → 给 GPT 窗口发一行确定性唤醒 → 重启后台 waiter → STOP；GPT 把决策
  作为提交推上总线后，waiter 退出并经后台任务通知自动唤醒会话，会话从 git
  消费 authority 继续下一轮。绝不解析聊天内容、绝不往聊天框贴长文本载荷。
---

> 公开项目模板：项目路径、聊天ID及账户绑定须由安装者配置。历史示例和本技能不授予消息发送、定时任务、科学执行或硬件权限；依据当前用户请求与本地项目合同使用。


# GPT 触发（gpt-trigger）：git 总线 + 单行唤醒 + 自动唤醒会话

> 本 skill 与 `review-bus-loop` 内容同源（P12 继承的操作文档），名称 gpt-trigger
> 是"触发 GPT / 重启 waiter"场景的快捷入口；两份若需修订，保持同步或只保留一份。

## 0. 为什么是这个模式（对比"往聊天框写文字"）

| | 聊天框贴文本 | 本模式（git 总线） |
|---|---|---|
| 决策载荷 | 聊天文本，易截断/易被 UI 吃掉 | 文件提交，SHA256 绑定，可审计 |
| 双向确认 | 无 | 收据（receipt）+ exactly-once 台账 |
| 会话如何知道 GPT 说话了 | 人肉看聊天窗口 / 解析聊天 | `git fetch` 轮询，waiter 退出即唤醒 |
| GPT 如何知道执行器做完了 | 等人转述 | 一行确定性标记（marker）打进聊天，仅作"门铃" |
| 可靠性 | 依赖 UI 文案、窗口状态 | git 是事实源；聊天窗口关了都不影响决策传输 |

**核心原则：聊天只当门铃（一行确定性文本），载荷只走 git。**

## 1. 架构总览

```
        ZCode 执行器会话                        Web-GPT（决策者）
        ───────────────                        ─────────────────
   1. 完成一轮 → 证据/carrier 提交 → push
   2. Edge 发一行 REVIEW_READY（marker）──▶  GPT 看到门铃，读 git
   3. 重启后台 waiter → 会话 STOP
   4. waiter 每 60s git fetch 轮询分支 ◀──  GPT 编辑 GPT_DECISION.md 并 push
   5. 检测到新决策 commit → waiter exit 0
   6. ZCode 后台任务完成通知 == 自动唤醒会话
   7. 会话 fetch → 读 GPT_DECISION.md → 消费 → 执行 → 回到 1
```

参考实现（P12 项目，可直接复制后按 §6 改参数）：

| 组件 | P12 参考路径 | 作用 |
|---|---|---|
| Edge 唤醒发送器 | `D:\P12\P12_REVIEW_BUS\WORKER\p12_edge_wake.ps1` | 往**已绑定**的 Edge ChatGPT 标签页发一行文本并验证送达 |
| 绑定文件 | `D:\P12\.p12_runtime\edge_target.local.json` | 描述发往哪个窗口/会话（marker、reject_markers、URL、代数） |
| 唤醒请求/收据 | `D:\P12\.p12_runtime\WAKE_SEND_REQUEST.json` / `WAKE_SEND_RECEIPT.json` | 发送前写请求，发送后写收据（SUBMITTED_CONFIRMED） |
| 后台 waiter | `D:\P12\P12_REVIEW_BUS\bridge\p12_next_round_waiter.py` | 轮询 git 分支上的新决策提交；退出即触发会话唤醒 |
| 桥状态机 | `D:\P12\P12_REVIEW_BUS\bridge\p12_pcs_bridge.py` + `BRIDGE_STATE.json`/`COMMUNICATION_STATE.json`/`EVENT_LEDGER.jsonl` | exactly-once 消费、审计事件、发布状态 |
| 决策文件 | `P12_REVIEW_BUS/GPT_DECISION.md` | GPT 唯一的指令下发通道（commit 即指令） |

## 2. 唤醒发送器（执行器 → GPT）的行为规范

`p12_edge_wake.ps1` 的每一行为都是硬约束，复制或改写时必须保留：

1. **绑定验证（fail-closed）**：枚举所有系统 Edge 顶层窗口，标题含绑定
   `conversation_title_marker` 的必须**恰好一个**；命中 `reject_markers`
   （兄弟项目的 marker）直接拒绝；每次发送前实时重验，不做缓存。
2. **composer 定位**：唯一可见的、矩形有限的"询问 ChatGPT"输入框；不唯一即失败。
3. **输入**：UIA `ValuePattern.SetValue`（后台安全，不抢焦点）→ 粘贴后回读比对。
4. **提交**：语义查找可见"发送"按钮用 `InvokePattern`；解析不到时，**至多一次**
   先 `SetForegroundWindow` 绑定窗口再发真实 Enter——绝不向未验证目标发 Enter。
5. **送达验证**：只有当输入框已清空 **且** 确切的 marker（`result_id=` 的值）出现在
   最新 USER 气泡的转录里，才输出 `SUBMITTED_CONFIRMED`。
6. **不确定即不重发**：输入有副作用但验证不确定 → `DELIVERY_OUTCOME_UNCERTAIN`，
   写收据退出，禁止自动重发（人工介入后才能重试）。
7. `-TestIdentity` 开关：纯只读身份探测（无焦点、无输入、无提交），换绑会话时先用它。

调用方式（执行器每轮结束时）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <WORKER>/p12_edge_wake.ps1 `
  -RequestPath "<runtime>/WAKE_SEND_REQUEST.json" `
  -BindingPath  "<runtime>/<project>_target.local.json" `
  -ResultPath   "<runtime>/WAKE_SEND_RECEIPT.json"
```

**铁律：发送前必须重写 `WAKE_SEND_REQUEST.json` 并核对 `round` 字段** —
陈旧请求文件曾把上一轮的唤醒发给 GPT（P12 真实事故，已写入收据归档）。

请求/收据 JSON 契约：

```json
// WAKE_SEND_REQUEST.json
{ "wake_key": "<round>|<carrier_sha>|<reviewed_sha>|<result_id>|<packet_sha>",
  "round": "P1xR_020",
  "result_id": "P1xR_020_..._RESULT_ID",
  "carrier_commit": "<git sha>",
  "packet_sha": "<canonical sha>",
  "wake_text": "DIFFUSION1X_REVIEW_READY round=... carrier_commit=... result_id=... packet_sha=.... Read <org>/<repo> branch <bus-branch> and complete the governed review. GitHub is source of truth." }

// WAKE_SEND_RECEIPT.json（发送器写出）
{ "state": "SUBMITTED_CONFIRMED", "marker": "<result_id>",
  "transcript_marker_found": true, "composer_empty": true,
  "identity": { "window_title": "...", "hwnd": ..., "binding_generation": 5 },
  "wake_key": "...", "at": "..." }
```

`wake_key` 是 exactly-once 键：轮次 + carrier + packet 的完整元组，归档进
`P12_REVIEW_BUS/receipts/` 作为推送证据的一部分。

## 3. 绑定文件规格（换会话/换地址时更新）

```json
{ "project_id": "DIFFUSION1X",
  "browser": "msedge",
  "binding_generation": 6,                    // 每次换会话 +1
  "conversation_title_marker": "P1xA0",        // 窗口标题里的唯一标记
  "composer_name_hint": "询问 ChatGPT",
  "reject_markers": ["P12A0", "P13", "P10"],   // 兄弟项目 marker，防串线
  "bound_hwnd_at_creation": 7475260,
  "conversation_url": "https://chatgpt.com/g/.../c/<conversation-id>",
  "note": "换绑历史……" }
```

换绑流程：用户给出新会话地址 → 打开该 Edge 标签页 → 窗口标题应含项目专属
marker（如 `P12A0`）→ 先跑 `-TestIdentity` 拿 `IDENTITY_OK` → 更新绑定文件
（binding_generation +1，记录 URL 与 hwnd）→ 再正式发。

## 3.1 当前激活绑定：HOLOGUIDE3D P1–P9 统一循环（2026-10-03 起生效）

同一 GPT 项目（`g-p-6a4f5893b4648191890ffa055c47c2f9`）下的**另一个会话**是
P1–P9 Review Leader 窗口；P12 的绑定（§3 示例，marker `P12A1`）不变，两者互为
reject marker。通信机制与本 skill 完全一致，只有绑定对象不同：

| 参数 | 值 |
|---|---|
| project_id | `HOLOGUIDE3D`（统一窗口覆盖 P1–P9 串行循环） |
| conversation_title_marker | `P1-9RV0` |
| conversation_url | `https://chatgpt.com/g/g-p-6a4f5893b4648191890ffa055c47c2f9-ji-yu-kuo-san-mo-xing-de-3dgao-si-chang-zhong-jian/c/{CONFIGURE_LOCAL_ID}` |
| composer_name_hint | `询问 ChatGPT` |
| reject_markers | `["P12A1", "P12A0", "P11", "P13", "P10-3", "Leader2", "九旋牙"]` |
| wake marker 格式 | `HOLOBRIDGE_REVIEW_READY round=<RLxx> carrier_commit=<sha> reviewed_commit=<sha> result_id=<..._COMPLETE> packet_sha=<sha>. Read zizhangla/HoloGuide3D-Review leader-review-bus LEADER_BUS/REPORTS and complete the P1-P9 Review Leader governed review. GitHub is source of truth.` |
| 绑定文件（LOCAL-ONLY） | `D:\.review_leader\hologuide3d_p1p9_target.local.json` |
| runtime 目录（LOCAL-ONLY） | `D:\.review_leader\`（binding/wake_receipts/cwd_receipts） |
| 发送器（与 P12 成品同一脚本） | `D:\.review_leader\WORKER\review_bus_edge_wake.ps1`（p12_edge_wake.ps1 原样副本，仅路径不同） |
| 中央分支 / 报告目录 | `leader-review-bus` / `LEADER_BUS/REPORTS/` |
| 决策入口 | `LEADER_BUS/REVIEW_LEADER_STATE.json`（active_task）+ `LEADER_BUS/TASKS/` |

本循环特有字段：`reviewed_commit`（任务签发时的 leader HEAD）。

**通道规则（用户指令 2026-10-03，最终形态）：Edge 是本循环唯一正式投递通道。**
与 P12 完全相同的机制与纪律：发送前重写 `WAKE_SEND_REQUEST.json` 并核对
`round` → 发送器 fail-closed 身份核验（唯一 `P1-9RV0` Edge 窗口，reject
markers 生效）→ UIA 填入 wake_text 并回读比对 → 语义"发送"按钮 →
`SUBMITTED_CONFIRMED` 收据（composer 清空 + marker 入转录）→ 归档
`D:\.review_leader\wake_receipts\`。**禁止用 ZCode 内置浏览器（IAB）发送
任何 wake**；IAB 只允许只读查看页面。不确定即不重发；一次会话一次 wake。

**绑定状态（LIVE）**：2026-10-03T09:58 CST `IDENTITY_OK`（窗口
"P1-9RV0 - 个人 - Microsoft Edge"，hwnd 8129200，binding_generation 1），
此后两次 `SUBMITTED_CONFIRMED`（semantic_send_invoke）：
① `RL002_P06_R065_AUTHORITY_ACK_BINDING_VERIFIED`（通道验证门铃）；
② `RL002_P06_R065_BRIDGE_AND_DUPLICATE_INCIDENT_REPORTED`（RL002 桥报告 +
   双执行事件，桥报告 @ leader-review-bus `20a42a9fe`）。
收据归档于 `D:\.review_leader\wake_receipts\`。历史备注：RL001 的 wake 曾在
绑定建立前经 IAB 送达一次（2026-10-03 早间）——该通道自此停用，仅作历史记录。
注意：原生 P6 会话有自己的 notifier（`p6_webgpt_notifier.v2`），其轮次唤醒
（如 R065 terminal 的 wake）由它按自己的 exactly-once 台账投递，与本绑定的
wake 身份互不重复。

## 4. 后台 waiter（GPT → 执行器的唤醒机制）

这是本模式的"闹钟"：**waiter 在 ZCode 里以后台任务运行；它 exit 0 时，
后台任务完成通知会自动唤醒这个会话**，会话接着消费新决策。会话 STOP 之后
不需要人看任何窗口。

`p12_next_round_waiter.py`（约 200 行）触发条件（全部满足才退出 0，否则继续等）：

1. `git fetch`（走代理）后，`origin/<bus-branch>` 上决策文件
   （`-- GPT_DECISION.md` 路径过滤）的最新提交 **≠** 桥里已消费的
   `decision_commit`；
2. 其 commit subject 里的轮次号（正则 `P1xR_(\d+)`）**大于**桥记录的上一轮；
3. 桥状态是 `WAITING_FOR_GPT`（上一轮已发布完毕）且无活跃执行锁；
4. fetch 失败/状态含糊 → **继续等**（绝不伪造触发）。

输出一行机器可读标记供会话解析：

```
RUN_NEXT_ROUND decision_commit=<sha> round=21 subject=P1xR_021 authority: ...
```

安全超时 `--max-seconds`（默认 6h）到点以 `WAITER_TIMEOUT` 退出（**不触发**），
由会话重启 waiter —— GPT 有时半小时不出手，有时几分钟，绝不因超时误触发。

通用化最小模板（新项目可直接内嵌）：

```python
# waiter.py — 每 interval 秒 fetch 一次；触发条件见上；exit 0 = 唤醒会话
import json, re, subprocess, time
from pathlib import Path
REPO   = Path(__file__).resolve().parents[1]      # 按项目调整
BRANCH = "p1x-review-bus"
DECISION = "P1X_REVIEW_BUS/GPT_DECISION.md"
STATE   = Path(".../bridge/COMMUNICATION_STATE.json")   # 桥状态
INTERVAL, MAX_S = 60, 21600

def sh(*a): return subprocess.run(a, cwd=REPO, capture_output=True,
                                  text=True, timeout=120,
                                  env={**__import__('os').environ,
                                       **{"https_proxy": PROXY}})
def newest():
    r = sh("git", "log", f"origin/{BRANCH}", "-1", "--format=%H %s", "--", DECISION)
    return None if r.returncode else r.stdout.strip()

consumed = json.loads(STATE.read_text(encoding="utf-8")).get("decision_commit")
last_round = 0
t0 = time.time()
while time.time() - t0 < MAX_S:
    sh("git", "fetch", "origin", BRANCH)
    line = newest()
    if line:
        commit, subject = line.split(" ", 1)
        m = re.search(r"P1xR_(\d+)", subject)
        rnd = int(m.group(1)) if m else 0
        if commit != consumed and rnd > last_round:
            print(f"RUN_NEXT_ROUND decision_commit={commit} round={rnd} "
                  f"subject={subject}")
            raise SystemExit(0)          # ← 后台任务完成 == 会话唤醒
    time.sleep(INTERVAL)
print("WAITER_TIMEOUT")                  # 不触发，会话重启 waiter
raise SystemExit(3)
```

启动（执行器每轮收尾时）：

```bash
py -3.14 -u <bus>/bridge/p12_next_round_waiter.py   # ZCode 后台任务
```

## 5. 一轮的完整循环（会话内执行清单）

**A. 被唤醒（waiter exit 0）→ 消费**
1. 读 waiter 输出，`git fetch`，`git show <commit>:<GPT_DECISION.md>` 读全文；
2. 通过桥的 audited 命令消费 authority（exactly-once：
   `execution:<authority_blob_sha>` 台账；禁止 silent re-claim）；
3. durable CLAIM **先提交推送**，再做任何执行器工作。

**B. 执行轮内工作**（科学/工程内容按 GPT_DECISION 的冻结合约执行；
两个阶段时：资格测试全过 → FREEZE 提交 → 正式阶段一次执行，此后零改动）。

**C. 发布 → 唤醒 → 等待**
1. 证据文件写盘（确定性 UTF-8 LF、manifest 绑定 git index blob 字节）；
2. `git add` + carrier 提交（含 canonical REVIEW_PACKET，自哈希）→ `git push`；
3. 归档唤醒收据到 `receipts/`（若有新的），closeout 提交推送；
4. **重写 `WAKE_SEND_REQUEST.json`**（核对 round/result_id/carrier/packet）；
5. 跑 Edge 发送器 → 拿到 `SUBMITTED_CONFIRMED`
   （HOLOGUIDE3D P1–P9 循环同样只走 Edge 发送器；IAB 禁止发送，见 §3.1）；
6. **重启后台 waiter**（run_in_background）；
7. 向用户汇报一轮结果，**STOP 结束回合**——绝不在同回合自作主张开下一轮。
   （**2026-10-06 用户指令更新**：新权威到位即**直接开下一轮**，无需用户说
   "继续"；waiter 触发 + V3 账本未消费权威 = 开轮依据。每轮发布 carrier 后
   仍 STOP 一次；全部硬红线不变。）

若推送被拒（评审方往总线追加了文档）：**merge，绝不 rebase 已冻结证据提交**，
merge 后重验 carrier 内容字节，再走唤醒。

## 6. 新项目适配清单（P12 → P1x）

| 参数 | 在哪里改 |
|---|---|
| 项目 ID / 轮次命名（`DIFFUSION1X` / `P1xR_NNN`） | 发送器 wake_text、waiter 正则、桥常量 |
| 仓库 / 总线分支 | waiter 的 REPO/BRANCH；发送器 wake_text |
| 决策文件路径 | waiter 的 `git log -- <path>` |
| 总线根目录名（`P1X_REVIEW_BUS/`） | 全部脚本常量 |
| 窗口 marker / reject_markers / 会话 URL | `<project>_target.local.json` |
| runtime 目录 | `.p1x_runtime/`（与其它项目隔离） |
| 代理（如有） | waiter 的 PROXY_ENV、桥 fetch |

复制顺序建议：先复制 waiter + 写最小桥状态（哪怕只有一个
`decision_commit`/`round` 字段）跑通"被唤醒→读决策→写一行确认→STOP"；
再复制 Edge 发送器（它是 P10→P11→P12 三代验证过的成品，尽量原样用）；
最后按需加 exactly-once 台账与审计事件。

## 7. 红线（违反任何一条都会破坏整个模式）

0. **窗口操作红线（用户指令 2026-10-03）**：Edge 上只允许定位**自己项目
   marker 对应的那一个窗口**并给它发消息；**禁止**发到别的项目的窗口、
   **禁止刷新**、**禁止新建标签页**、**禁止乱点任何其他元素**。唯一允许的
   动作序列：定位自己窗口 → 定位该项目 GPT 的输入框 → 写入消息 → 点发送。
   发送器必须 fail-closed：身份不唯一/输入框不唯一/收不到送达确认，一律
   带原因退出，绝不 fallback 到其它窗口或其它交互方式。

1. 载荷只走 git；聊天里只发一行确定性 wake_text（含 result_id marker）。
2. 绝不解析 GPT 的聊天回复作为指令来源 —— 指令唯一来源是 `GPT_DECISION.md` 提交。
3. 收据不是 `SUBMITTED_CONFIRMED` 就不算送达；`DELIVERY_OUTCOME_UNCERTAIN`
   不得自动重发。
4. 每次发送前重写并核对请求 JSON（陈旧请求 = 给 GPT 发错轮次）。
5. waiter 只信 git；fetch 失败/含糊一律继续等。
6. 会话被唤醒后第一件事永远是 fetch + 读决策文件，而不是凭记忆继续干。
7. 一轮结束必须 STOP；waiter 是唯一的下一轮入口。
8. 兄弟项目共用一台机器：窗口绑定用 marker + reject_markers 隔离；
   runtime 目录、总线目录互不共享。


## 3.2 Channel fallback + script path discipline (2026-10-03, user directive)

- Edge wake script (review_bus_edge_wake.ps1) previously carried P12 DEFAULTS for
  `-RequestPath`/`-ResultPath`; overriding only `-BindingPath` once consumed another
  project's queued request and misdelivered it (INCIDENT 2026-10-03, P12R_034 into
  "P- review 1"). Defaults are now HOLOGUIDE3D paths - keep it that way; when
  adapting the script for any project, override EVERY default or fail closed.
- Edge window presence: `Get-Process msedge | MainWindowTitle` misses non-main
  Edge windows; the script's UIA enumeration is authoritative. If it still returns
  `edge_target_not_unique count=0` and the user confirms the window is open,
  fall back to the ZCode built-in browser (IAB) for that one send - and keep the
  IAB/browser session PERSISTENT (do not reload on window switches; reuse the
  live session across wake attempts).
- Wake idempotency unchanged: exactly one wake per result_id, verified by receipt;
  stale wakes overtaken by a leader adjudication are recorded OVERTAKEN, not sent.

## 3.3 P10 V3 单行道传输（HQ0022 R1 采纳，2026-10-06）

P10 的生产传输已收敛为 V3 单一状态机（SQLite WAL ledger = 唯一持久
authority/review 状态），生产入口全部在 `D:\P10\HoloGuide3D-Review\P10_AUTOMATION_V3\`：

| 组件 | 作用 |
|---|---|
| `transport_ledger.py` | V3 SQLite 状态机（RECEIVED→…→CONSUMED + DELIVERY_CLAIMED/WAITING/UNCERTAIN 生命周期；CAS claim；release/uncertain/严格 ACK API） |
| `github_authority_event.py` | GPT_DECISION push → 解析 CURRENT_TASK Active 轮次 → V3 记账 → 写 DISPATCH 信封 |
| `frontend_event_agent.pyw` | 事件驱动投递代理（mutex 单实例；结果分类器：PRE_SEND 可安全重试 / POST_INVOKE→DELIVERY_OUTCOME_UNCERTAIN 禁止盲重发） |
| `p10_perpetual_watchdog.pyw` | 常驻看门狗（V3-only 前向安全网；账本态驱动的 safe-refire；绝不触碰 claimed/uncertain） |
| `next_round_waiter.py` | 常驻 git-decision waiter（V3 身份；观察≠消费；心跳；mutex 单 owner；默认无限期） |
| `executor_transport_ack.py` | 规范执行器 ACK/CONSUME（round+commit+blob 逐字段绑定，错即零推进） |
| `uia_background_delivery.ps1` | 后台 UIA 投递（Edge 目标 = 精确 P10A<N> 代数最高唯一者，fail-closed；失败必须标注 phase=PRE_SEND/POST_INVOKE） |

**零闪（HQ0021）硬契约**：常驻代理一律 `pythonw`；每个 subprocess 携带
`CREATE_NO_WINDOW`（`creationflags=0x08000000`）；禁止用 `DETACHED_PROCESS`
启动会再孵化 console 子进程的父进程（每轮 poll 都会闪一个可见 console）。
动态验收标准：真实启动路径 ≥3 个 target-free 循环，`visible_console_events=0`。

**观察 ≠ 消费**：waiter/watchdog 对决策的"看到"只写观察账本
（WAKE_LEDGER.jsonl），消费只能由执行器经 `executor_transport_ack.py`
的严格身份绑定路径推进 V3 ledger（ authority_key 必须逐字抄自 ledger，
不得自行计算 —— T9 REARM1 D 裁决的真实教训）。
