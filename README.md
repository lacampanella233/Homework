# Homework

*(防止自己忘了怎么用而写的README)*

此仓库包含了作者专业课的课后作业, 以homework.sty为模板. 结合Git Homework Manager应用, 可以方便地管理和提交作业.

---

## Git Homework Manager 使用指南

欢迎使用 **Git Homework Manager**! 这款工具旨在帮助我更高效地管理 GitHub 上的作业仓库. 

### 🚀 核心流程

#### 1. 配置与登录
- 点击顶部的 **Update Token**, 输入我的 GitHub Personal Access Token 并保存. 
- 确保我的学期信息（如 `2026 Spring`）已填写. 

#### 2. 开始新作业
- 在 **Create New Homework** 卡片中选择课程并确认作业编号. 
- 点击 **🚀 Create HW Branch**. 系统将自动: 
    - 创建并切换到新分支（格式: `课程名-HW编号`）. 
    - 在本地仓库创建对应文件夹. 
    - 自动生成包含我学期和作业信息的 LaTeX 模板. 
    - 自动在 VS Code 中打开该文件夹. 

#### 3. 同步与提交
- 完成作业后, 点击 **📤 Commit & Push** 将更改同步到 GitHub. 
- 确认无误后, 点击 **🔀 Merge to Main**. 系统将通过 GitHub API 自动将代码合并到 `main` 分支, 并清理过期的本地和远程作业分支. 



### 🛠 辅助工具

- **Files 树**: 
    - 点击文件夹旁边的 💻 图标可直接在 **VS Code** 中打开. 
    - 点击 ↗️ 图标可在 **文件资源管理器** 中打开. 
- **External Tools**: 
    - **Open in GitHub Desktop**: 在桌面客户端中管理仓库. 
    - **Open in GitHub WebPage**: 快速跳转到浏览器查看仓库. 



### ❓ 常见问题
- **无法推送？** 请确保我已配置好 SSH 密钥并拥有仓库权限. 
- **合并失败？** 检查是否存在未提交的更改, 或网络连接是否正常. 

---

## 关于 `homework.sty`

该宏包提供了“问题”、“解答”、“证明”、“注记”等环境, 以及一些常用的数学符号和命令. 

加载宏包时有一个可选参数, 用于指定作业的语言, 目前支持中文(zh)和英文(en), 默认为中文. 使用`\usepackage[en]{homework}`以加载英文版本的宏包, 使用`\usepackage[zh]{homework}`以加载中文版本的宏包.

导言区只需要设置3个参数: 课程名、学期、作业编号. 学生姓名为作者的名字. 可以分别设置每个参数:
```latex
\course{课程名}
\term{学期}
\homeworkcounter{作业编号}
```

或一次性设置所有参数:
```latex
\config{课程名}{学期}{作业编号}
```

`problem`与`lemma`环境支持一个可选参数, 用于指定问题或引理的标题. 该标题在问题或引理编号后显示. 

`enumerate` 和 `itemize` 列表的项间距和段间距已压缩为 0pt, 使排版更紧凑.

模板预定义了一些快捷命令, 方便数学写作: 
| 命令        | 含义               | 定义                 |
|-------------|--------------------|----------------------|
| `\R`        | 实数集              | `\mathbb{R}`      |
| `\C`        | 复数集              | `\mathbb{C}`      |
| `\N`        | 自然数集            | `\mathbb{N}`      |
| `\Z`        | 整数集              | `\mathbb{Z}`      |
| `\Q`        | 有理数集            | `\mathbb{Q}`      |
| `\F`        | 域                  | `\mathbb{F}`      |
| `\abs{...}` | 绝对值              | `\left\lvert ... \right\rvert` |
| `\i`        | 虚数单位            | `\mathrm{i}`      |
| `\e`        | 自然底数            | `\mathrm{e}`      |
| `\d`        | 微分符号 （直立）   | `\mathrm{d}`      |
| `\fl{...}`  | 向下取整            | `\left\lfloor ... \right\rfloor` |
| `\bo{...}`  | 粗体符号            | `\boldsymbol{...}` |
| `\transpose`  | 转置符号          | `^\mathrm{T}` |
| `\im`       | 线性映射的像空间    | `\operatorname{im}` |
| `\rank`     | 矩阵的秩            | `\operatorname{rank}` |
| `\sspan`    | 向量空间的生成子空间 | `\operatorname{span}` |
| `\inprod{...}{...}` | 内积符号 | `\left\langle ... , ... \right\rangle` |

注: 之所以使用`\sspan`而不是`\span`, 是因为`\span`在LaTeX中已经被定义为表格环境中的命令, 直接使用会导致冲突.


宏包会自动制作标题, 因此不需要使用`\maketitle`命令. 只需在文档导言区设置好上述3个参数.


