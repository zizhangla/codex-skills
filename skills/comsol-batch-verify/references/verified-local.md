# 已验证范围与接口经验

2026-10-09，Windows，本机 COMSOL 6.4.0.293。Python `{USER_HOME}/.conda/envs/trellis_win/python.exe`；COMSOL `C:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64`。路径是该机配置，不保证其他机器相同。

真实证据：`{WAVEFRONT_PROJECT_ROOT}/reports/comsol_skill_validation_20261009/smoke_01/receipt.json`。一次 compile、一次 batch；compile 4.0 秒，batch 外层 11.782 秒；峰值作业提交内存 847327232 字节。面积 0.9999999999999978、u 积分 0.5000000000000505、平方误差积分 3.5483677469365234e-27。模型保存为 `smoke_ComsolSmoke.mph`。运行所用 Java SHA256 `b09ef6f4e2c004aa5ea3e77fd2f502d5914c68488b44ff4efab5777ce6c6ec23`。

本次验证几何、CoefficientFormPDE、网格、稳态求解、数值积分、stdout 和 COMSOL 原生保存。没有加载 P11 模型，没有验证 Wave Optics 模块、真实模式场/功率归一化、LiveLink、COMSOL 硬件实验或科研结论。之后增加的回执持久化和模型存在性门禁用已有原始日志/模型进行离线核验，不为它们重放求解。

P11 原始排障报告：`{WAVEFRONT_PROJECT_ROOT}/reports/p11_comsol_readonly_diagnosis_20261009/REPORT.md`。这些是具体历史实例：activate 1×12 表被当成键值对行；String shift 用 getDouble；求解完成后 Java FileOutputStream 被安全设置阻断；IOException 编译失败；网格自动构建违反冻结条件。后续代码已有部分修复，使用时核对当前源码，不把旧 bug 宣称为当前 bug。

## 官方依据（检索 2026-10-09）

- [Windows COMSOL 命令行](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_running.38.31.html)：可调用 batch/class、compile，指定核数、偏好和临时目录；输入输出路径必须明确，防止默认覆盖输入。
- [稳态 study API](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_api_solver.51.79.html)：Stationary study 类型。
- [安全性首选项](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_running.38.10.html)：Java 文件系统访问受安全配置限制；不要把扩大 All files 访问当默认修复。
- [COMSOL 6.4 MATLAB 兼容版本](https://cn.comsol.com/system-requirements/64/builder)：支持 R2025a/R2025b；安装文件存在并不证明许可或连接通过。
