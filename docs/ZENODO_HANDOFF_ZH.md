# GitHub—Zenodo 人工归档交接

本项目仓库位置是 https://github.com/williamjay1/project37-wte-ccs-heat-service ，
本次尚未创建正式 release，也没有 DOI。生成 DOI 和账户授权
由真实作者本人操作。不要将自动化测试通过写成工厂验证或录用保证。

## 发布前

1. 确定 GitHub 仓库位置、所有参与者姓名及应署名的贡献、单位和可选 ORCID；
   不从用户名推断论文作者，不使用示例人物。审阅代码许可和逐项数据来源。
2. 在仓库根目录运行 README 的检查、全流程复现和结果比较。运行目录必须是
   一个不存在的新目录；本机工作仍存 D 盘，原始 F/E 盘文件不修改。
3. 填写 `publication_metadata.json`。第一版计划 `1.0.0`，并不是已有 release。
   DOI 保持 null；核验真实署名和许可后才能设置人工发布审阅完成。
4. 执行 `python tools/prepare_citation.py --metadata publication_metadata.json`。
   它只在真实字段完整时生成 CITATION.cff，缺失时明确失败。填写元数据并生成
   CFF 后运行 `python tools/update_manifest.py` 和完整性检查；更新哈希并不
   等于已经科学验证，代码/数据修改仍须重新计算比较。不同时创建
   `.zenodo.json`，因为两者共存时 Zenodo 优先读取后者而不是 CFF。
5. 上传代码、可发布的六项输入、数值参考结果、图表和说明到选定仓库。
   **不要直接上传历史整个工作目录或旧研究包**：不含私信、审稿沟通、
   账号凭据、绝对原始路径、受保护报告、字体或未获授权的厂级材料。

## 导入并获取 DOI（你亲自操作）

1. 进入 https://zenodo.org ，登录你控制的账号，并按界面授权关联 GitHub。
2. GitHub 自动归档使用公开仓库；若采用私人仓库，则不要假定 GitHub 集成
   可以直接读取它，应按 Zenodo 手动上传路线和实际访问设置处理。
3. 进入 https://zenodo.org/account/settings/github/ ，Sync now 后启用该仓库。
4. **先启用，再创建 GitHub release**，固定实际测试的提交，标签例如 v1.0.0。
   README/声明/日期应与实际发布一致；不要创建空标签来假装归档已经完成。
5. 核验 Zenodo 的归档文件、真实作者、标题、版本、逐项混合许可和相关标识。
   未明确可统一重许可的输入不能被软件 MIT 默认许可覆盖。
6. 区分该版本的 version DOI 与指向整系列的 concept DOI。论文复现应引用
   与具体代码、数据和结果对应的 version DOI，附 GitHub URL 和 release 标签。
7. 将 DOI 与公开仓库链接反馈给本项目，再更新 CFF、论文的数据/代码声明和
   参考文献。只更新引用元数据不声称现有 release 字节改变；有代码/数据变更
   应重新测试并用新版本归档，不覆盖旧版本。

DOI 是持久标识与归档记录，不代表数据质量、创新性、同行评议或期刊录用。
不编造 DOI、作者审核、基金、利益冲突、机构审批或预注册。

## 官方核查入口（2026-10-05）

* https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content
* https://help.zenodo.org/docs/github/enable-repository/
* https://help.zenodo.org/docs/github/describe-software/
* https://help.zenodo.org/docs/github/describe-software/citation-file/
