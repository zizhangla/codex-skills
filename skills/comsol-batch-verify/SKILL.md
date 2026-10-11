---
name: comsol-batch-verify
description: 在 Windows 上通过 COMSOL Java/batch 建模、求解、导出并核验结果，或定位编译、属性类型、文件安全与假成功问题。用于 COMSOL 调用排障和独立工程烟雾测试；不授予研究计算或旧尝试重跑权限。
---

# COMSOL batch 调用与核验

优先使用本机 COMSOL 安装目录的 `bin/win64/comsolcompile.exe` 和 `comsolbatch.exe`。不因缺少 MCP、Python MPh 或 MATLAB 连接而改造可工作的 Java/batch 路径。先读项目 AGENTS、当前状态与适用执行合同；工程测试和科学结果分别记账。用户明确要求测试 COMSOL 时，可在独立目录执行下述解析解测试；它不加载研究项目资产。

## 最小真实链路

在 Windows 运行：

```powershell
& '<python.exe>' '<skill-dir>/scripts/smoke_test.py' --run-dir '<一个尚不存在的绝对目录>' --comsol-bin '<COMSOL安装目录>/bin/win64'
```

此脚本构建单位正方形，解 `-Δu=0`、全边界 `u=x/1[m]`，解析解相同。默认 2 个 COMSOL 计算核，Windows Job Object 作业提交内存上限 4 GiB，编译和 batch 各 180 秒；只终止自己创建的作业。它使用私有 prefs/tmp、显式输出路径与 batch 日志，不修改安装配置或全局安全设置。已有目录会拒绝执行；不自动重试。改变脚本、资源上限或算例时先说明范围，保留旧回执。

检查 `receipt.json`、原始日志与模型文件。必须同时满足：编译产生新 class、batch 无失败、唯一结构化结果和完成标记、全部值有限、面积与积分匹配解析值、误差非负且小于固定阈值、保存模型存在。COMSOL 可能在错误时仍返回 0，退出码不能替代这些检查。创建 Java 模型的输出 MPH 可能附加模型 tag；以本次独立目录内实际文件为准，不能假定只生成指定文件名。

首次运行前核查活动 COMSOL 和研究执行器，避免资源或许可证竞争；不要停止别人的进程。正式项目计算还须核查 owner、冻结身份、输入、预算、锁、网格行为和停止规则。该脚本的固定 caps 仅适用于此独立工程样例，不能覆盖项目 caps。

## 失败定位

- 先判断编译、建模、网格、求解、导出哪个阶段失败。编译日志中的 ERROR、缺失 class 或 IO 异常必须在 batch 前阻断。`ModelUtil.load` 需要声明/处理 IOException；不要把编译失败归为不收敛。
- COMSOL 属性按实际 `getValueType` 读取。`shift` 可为 String；含单位或变量的表达式不能盲目转 double。表属性先核验 shape，再解释键值；不要假定 activate 总是每行两个字段。
- 求解完成后导出被拒绝，应记导出失败。小结果用 Java stdout 输出结构化数据、外部程序校验并落盘；大数组应增加版本、shape/dtype/单位、长度、分块序号和 SHA256。不要全局关闭安全限制，也不要将合成传输测试当作真实场验证。
- 日志按实际编码解码，未知或破损编码留痕，不能靠忽略字符通过。OOM、超时、许可证占用与数值不收敛分别分类。
- 网格自动重建、物理接口切换或 source/model 改动可能改变研究合同。不能靠接口修复改变物理条件、阈值或追认已消费尝试。

本地结果门禁负控测试：`python <skill-dir>/scripts/test_validator.py`，不启动 COMSOL。

读取 [本机验证与官方依据](references/verified-local.md) 获取已验证范围和 P11 故障经验。未经验证的 Wave Optics、LiveLink/MATLAB、硬件与大型模型不要标为可用。此 Skill 可自动被选用，但调用范围来自用户任务和适用项目合同。
