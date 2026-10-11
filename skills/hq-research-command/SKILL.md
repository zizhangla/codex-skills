---
name: hq-research-command
description: 用户要求给xx发号令、司令部大指令或指定科研项目全面审查并发布Git指引时，核查方案、代码和结果，形成Nature目标的可证伪规划、证据评分及COMMAND_HQ正式方法令。适用于HoloGuide3D Review Bus；普通代码修复或单篇文献查询不触发。
---

# 司令部科研发号令

交付完成的审查、可证伪规划和已核验Git指令。用户“给xx发号令”授权指定项目只读审查、中央方法发布与仓库非authority入口；不授权新科学计算、保护读取、历史重跑、在途hot patch或给其它聊天发消息。

1. 遵守当前AGENTS，先context index verify，再解析HQ remote40位HEAD；校验CHARTER、CURRENT、REGISTER及project/global pointers的status/effective/hash/替代关系。项目映射见[project-map.json](references/project-map.json)，核对实际repo/ref/namespace，不猜root lookalike。
2. 固定native HEAD/authority、CURRENT_TASK、最新governed review/result carrier。`scripts/capture_sources.py`只抓明确批准的文本/源码并存tree/SHA，不自动跟随全部链接或下载protected数据。身份/来源冲突阻塞受影响动作。
3. 按[审查规程](references/audit-and-score.md)审方案、生产调用链、独立oracle、统计/结果，记录path/行号/commit及NOT_CHECKED，包含推导、最强反对理由和反例。旧切片不能指控新代码；不运行历史科学脚本来证明审查。
4. 核查一手文献methods/证明/限制并记录访问深度；摘要不能支持方法结论，未检出不说“首次”。内部x/10不是Nature官方量表或录用概率。
5. 每项目一个主假说、最强null、具体构造/推导、最小判别试验、公平baseline、null/reversal、endpoint/独立单位/资源账、成功/失败/不确定门槛和分阶段预算。新阈值标DRAFT，不覆盖native冻结门槛；条件上限必须写证据条件，不保证N。
6. 用[packet模板](assets/command-packet.json)，运行`scripts/validate_packet.py`。PASS仅完整性，不是科学资格或发布许可。另须按references/publication.md完成独立的PUBLICATION_READINESS：身份/现行HQ hash与替代闭包、native lookup是否实际可读及调和范围、source重新核验、未检查项、review裁决、发布路径白名单。all-missing/SUPERSEDED authority即使packet完整也阻塞科学方向采纳；只能发布清楚标BLOCKED的审查记录，不能签成已核实状态或执行权。若工作区许可，一个bounded independent reviewer覆盖Skill行为与全局审查/发布边界；遵守模型路由、最多一个delegate，不fork全历史。
7. 将实际核验记录写PUBLICATION_READINESS.json并运行scripts/check_publication_readiness.py；其通过仅为attestation记录齐备，不能代替真实查证。按[发布合同](references/publication.md)签发immutable正文，更新REGISTER/CURRENT/项目索引与显式替代；recheck source refs、CAS非force发布、回读remote bytes。Skill版本镜像HQ，记录中央发布/原生部署/聊天交付分别状态。

最终给actual commit、当前/条件上限评分表、瓶颈和直接落实链接。无新令则UNCHANGED，不制造实验或无限修复轮。Skill不创建scheduler。研究顺序：physical contract→bounds→prospective mechanism→matched baselines→legal construction→generalization→scale/optical transfer→justified claims。
