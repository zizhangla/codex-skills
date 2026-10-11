# Codex Skills — zizhangla 的技能合集

**104 个本地技能**，覆盖科研选题、查新、理论与证明、实验、审计、论文与图表、专利、项目治理、通用辅助及预装技能。包含被技能引用的 shared-references 共享参考。完整列表见 [CATALOG.md](CATALOG.md)，机器可读目录见 [catalog.json](catalog.json)。

## 在 Codex 中安装全部技能

复制以下指令到Codex：

```text
从 https://github.com/zizhangla/codex-skills 克隆 v1.0.1 版本，检查 scripts/install.py 和 checksums.json，然后执行 python scripts/install.py --all。保留并跳过我的已有技能，不覆盖 .system 预装技能；按实际要使用的技能配置依赖和工具连接，不批量运行实验或录入凭据。安装后告诉我新增与跳过的技能数量。
```

在终端中也可直接执行（需要Git和Python 3.10+）：

```text
git clone --branch v1.0.1 https://github.com/zizhangla/codex-skills.git
cd codex-skills
python scripts/install.py --all
```

安装到`CODEX_HOME/skills`，未设置时使用`~/.codex/skills`。安装器会核验源文件校验和，跳过已有目录，并安装共享参考，不修改用户现有技能。安装后在下一轮对话调用相应技能。

## 按需安装

```text
python scripts/install.py --skills cns nature-research fudan-fulltext
```

也可使用Codex预装安装器：

```text
使用 $skill-installer 从 https://github.com/zizhangla/codex-skills/tree/v1.0.1/skills/cns 安装 cns。检查其共享参考与关联技能依赖。
```

有相邻共享文件依赖时，优先使用本仓库安装脚本。`--dry-run`只预览安装计划，`--dest <目录>`指定独立安装目录。

## 适用范围

- 技能安装是加载指引和辅助代码，不代表全部运行时、API、模型或付费服务已配置。
- 使用哪个技能，再按该技能说明安装依赖、配置自己的密钥或连接。复旦下载需要使用者自己的学校账号；凭据仅在本机录入。
- 项目专用技能以模板发布，路径及聊天ID须由使用者配置。历史示例不授予消息发送、定时任务、训练、科学执行或硬件操作权限。
- 公共副本移除了维护者个人路径、聊天ID与固定项目绑定；维护者本地原始技能未修改。公开包不含论文、项目数据、账号、浏览器会话或第三方二进制运行库。
- 官方插件提供的技能和专用工具需安装相应插件；见 [PLUGIN_SKILLS.md](PLUGIN_SKILLS.md)。该清单与本地技能一起覆盖当前技能目录，插件不通过复制提示词获得其连接权限。

## 校验与来源

源文件清单及SHA256见 [checksums.json](checksums.json)。发布时检查全部本地技能YAML入口和Python语法，并做全新目录的安装测试；这属于打包校验，不等于104个技能的所有外部服务与科学流程均已端到端验证。

复旦机构登录／CARSI工作流已在两篇订阅论文上核验PDF；独立的[复旦技能仓库](https://github.com/zizhangla/fudan-fulltext-skill)保留其发布说明。

保留原文件的许可证与来源说明。上游及授权说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本合集不是OpenAI或相关期刊的官方认证项目。
