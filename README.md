# Homework

*(防止自己忘了怎么用而写的README)*

此仓库包含了作者专业课的课后作业, 以homework.sty为模板.

---

## AI 使用声明

此仓库仅在以下操作中不加声明地使用 AI:
 - Git 相关操作: 拉取, 提交, 创建和合并分支等;
 - 新建课程或作业;
 - 录入作业题目;
 - 解决 `LaTeX` 上的技术困难, 如使用 `TikZ` 绘制示意图等;
 - 只读地检查作业 (如果没有被列为禁止动作).

若在其他场景使用了 AI, 则会明确指出.


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

模板预定义了一些快捷命令, 方便数学写作.

### 数集

| 命令 | 含义 | 定义 |
|------|------|------|
| `\R` | 实数集 | `\mathbb{R}` |
| `\C` | 复数集 | `\mathbb{C}` |
| `\N` | 自然数集 | `\mathbb{N}` |
| `\Z` | 整数集 | `\mathbb{Z}` |
| `\Q` | 有理数集 | `\mathbb{Q}` |
| `\F` | 域 | `\mathbb{F}` |

### 定界符与线性代数记号

| 命令 | 含义 | 定义 |
|------|------|------|
| `\abs{...}` | 绝对值 | `\left\lvert ... \right\rvert` |
| `\fl{...}` | 向下取整 | `\left\lfloor ... \right\rfloor` |
| `\bo{...}` | 粗体符号 | `\boldsymbol{...}` |
| `\transpose` | 转置符号 | `^\mathrm{T}` |
| `\inprod{...}{...}` | 内积符号 | `\left\langle ... , ... \right\rangle` |
| `\bracket{...}` | 尖括号 | `\left\langle ... \right\rangle` |
| `\bra{...}` | 量子力学中的左矢 | `\left\langle ... \right|` |
| `\ket{...}` | 量子力学中的右矢 | `\left| ... \right\rangle` |

### 数学常数与微分符号

| 命令 | 含义 | 定义 |
|------|------|------|
| `\i` | 虚数单位 | `\mathrm{i}` |
| `\e` | 自然底数 | `\mathrm{e}` |
| `\d` | 微分符号（直立） | `\,\mathrm{d}` |

### 映射与代数算子

| 命令 | 含义 | 定义 |
|------|------|------|
| `\Hom` | 态射集 | `\operatorname{Hom}` |
| `\Obj` | 范畴的对象 | `\operatorname{Obj}` |
| `\Aut` | 自同构群 | `\operatorname{Aut}` |
| `\Inn` | 内自同构群 | `\operatorname{Inn}` |
| `\Isom` | 同构集 | `\operatorname{Isom}` |
| `\End` | 自同态环 | `\operatorname{End}` |
| `\ord` | 元素的阶 | `\operatorname{ord}` |
| `\id` | 恒等态射 | `\operatorname{id}` |
| `\im` | 线性映射的像空间 | `\operatorname{im}` |
| `\rank` | 矩阵的秩 | `\operatorname{rank}` |
| `\sspan` | 向量空间的生成子空间 | `\operatorname{span}` |
| `\diag` | 对角矩阵 | `\operatorname{diag}` |

注: 之所以使用`\sspan`而不是`\span`, 是因为`\span`在LaTeX中已经被定义为表格环境中的命令, 直接使用会导致冲突.


宏包会自动制作标题, 因此不需要使用`\maketitle`命令. 只需在文档导言区设置好上述3个参数.


