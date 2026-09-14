# AGENTS.md

本文件适用于整个 `D:\程昊一\Homework` 仓库。

## 仓库用途

这是个人课程作业仓库，使用根目录 `homework.sty` 生成 LaTeX 作业。仓库管理自动化由 `.agents/skills/homework-manager/` 提供；涉及创建课程、创建作业、同步、切换或完成作业时，优先使用该 Skill 的脚本，不要临时拼接一组等价的 Git 命令。

Skill 使用统一入口 `scripts/homework.ps1`：入口负责稳定参数、仓库初始化和白名单分派；公共逻辑位于 `scripts/Homework.Common.psm1`；每类任务的实现位于 `scripts/actions/<Action>.ps1`。Agent 应选择公开 Action，不直接执行内部动作脚本。

## AI 使用声明

- `README.md` 中的“AI 使用声明”是本仓库的适用规则。以下操作使用 AI 时可以不另行声明：Git 相关操作（包括拉取、提交、创建和合并分支等）、新建课程或作业、录入作业题目、只读地检查作业。
- 在上述范围以外使用 AI，必须明确指出 AI 的使用情况。不得把未列出的操作扩张解释为可以不加声明。
- “录入作业题目”仅指忠实录入题目，不包含解题、改写、纠错、补充内容或推导答案。
- “只读地检查作业”仅指读取、分析和报告，不授权修改题目、答案、证明、排版或其他仓库文件。

## 目录与命名

- 课程目录位于仓库根目录，当前形如 `Algebra-0`、`Analysis-0`、`Physics-0`。
- 每次作业位于 `<course>/<number>/`；主文件必须是 `<number>.tex`，并在创建时复制根目录当前版本的 `homework.sty`。
- 作业分支名为 `<course>-HW<number>`，例如 `Analysis-0-HW13`。
- `main` 是汇总分支，远程名为 `origin`；当前远程使用 SSH。
- 新作业编号取该课程所有纯数字目录名的最大值加一。不要硬编码“当前下一次”编号。
- 新作业默认沿用该课程最近一个数字作业目录中 `.tex` 文件的 `homework` 语言选项和 `\config` 课程显示名。当前约定是 Algebra/Analysis 使用中文，Physics 使用英文，但以仓库现状为准。

## 作业内容边界

- “管理作业”“新建作业”“提交”“切换”“完成作业”等请求只授权仓库管理，不授权编写、改写或纠正题目、答案和证明。
- 只有用户明确要求编辑某份作业内容时，才修改相应 `.tex`；保持其语言、数学记号和局部排版风格。
- 根目录 `homework.sty` 是新作业模板来源。不要批量替换旧作业目录中的历史副本，除非用户明确要求迁移。
- LaTeX 中间文件由根目录 `.gitignore` 统一忽略。数字作业主文件生成的同名 PDF（例如 `Analysis-0/13/13.pdf`）也不追踪；题目、绘图等作为源材料使用的其他 PDF 和图片仍应追踪。
- 不要使用 `git add -f` 绕过编译产物忽略规则。若新增了未覆盖的编译产物类型，先确认它不是输入资源，再扩充根目录 `.gitignore`。

## Git 安全规则

- 每次操作前运行 `git status --short --branch`，区分任务开始前已有的修改与本次修改。不得覆盖、清理、还原或顺带提交用户已有修改。
- 禁止使用 `git reset --hard`、`git checkout -- .`、`git clean` 或其他批量丢弃改动的命令。
- 不使用无范围的 `git add .`。新建课程只暂存对应 `.gitkeep`；新建作业和同步只暂存目标作业目录；文档或 Skill 修改只暂存用户明确指定的文件。
- 创建课程、创建作业、切换分支和合并前要求工作区干净。若不干净，停止并报告具体路径，不自行决定如何处理。
- 不制造空提交。没有待提交变更时，显式同步请求只执行 push。
- pull 使用 `--ff-only`。发生冲突或非快进时停止，不自动 rebase、强推或改写历史。
- 合并完成后，只有在 `main` 已成功推送时才清理作业分支；本地分支使用 `git branch -d`，禁止强制删除。清理失败是 warning，不得把已经成功的合并误报为失败。
- read-only/status 操作可以直接执行。修改文件或本地分支必须来自用户当前请求；push、合并和删除远程分支必须由用户明确要求该动作。
- 本仓库可能同时由 LaTeX 编辑器、Git 客户端和 Agent 使用。任何已有未提交状态均视为用户所有。

## Skill 使用

脚本入口：

```powershell
pwsh -NoProfile -File .agents/skills/homework-manager/scripts/homework.ps1 <Action> [parameters]
```

- `Status` 是只读操作。
- `NewCourse`、`NewHomework`、`Sync`、`Switch`、`Finish` 默认仅输出计划；确认与用户请求完全一致后才添加 `-Apply`。
- `Finish -Apply` 会推送当前作业分支、在本地合并到更新后的 `main`、推送 `main`，然后尝试清理远程和本地作业分支。必须特别核对预览中的分支名。
- `Open` 只在用户要求打开 VS Code、资源管理器、GitHub 网页或 GitHub Desktop 时使用。
- 脚本的 `-RepoPath` 仅用于隔离测试或显式指定另一个仓库；正常使用保持默认或明确传入 `D:\程昊一\Homework`。
- 新增任务类型时，同时更新入口的 `ValidateSet`、动作文件白名单、分派调用和 `SKILL.md`。公共 Git、路径和校验逻辑应放入 `Homework.Common.psm1`，不要复制到多个动作文件。

## LaTeX 验证

修改某个 `<number>.tex` 或其 `homework.sty` 后，从该作业目录运行：

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error <number>.tex
```

- 只编译与任务相关的文档；不要为了仓库管理操作重编译历史作业。
- 报告命令退出码和关键错误。生成的作业 PDF 与中间文件应保持未追踪、被忽略；生成 PDF 不等于数学内容正确。
- 若编译失败，保留源文件和日志供诊断，不删除用户产物。

## 完成前检查

- 再次运行 `git status --short --branch`，列出本次文件与操作前已有文件。
- 说明是否创建/切换了分支，是否 commit、push、merge 或删除了分支；未执行的操作不得表述为成功。
- 未经明确要求，不把 `AGENTS.md`、Skill 文件或作业内容一起提交到远程。
