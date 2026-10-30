# MathorCup 2026 大数据挑战赛 A 题参考文献与引用说明

**整理日期：2026 年 10 月 24 日**

本文按 Q1 感官评分补全、Q2 关键化合物归因、Q3
风格生成与多目标优化整理。期刊论文按"作者，论文名，期刊名，卷期号：页码/文章编号，出版年"著录；网上资源按"作者/机构，资源标题，网址，访问日期"著录。电子期刊若使用文章编号而非连续页码，则保留文章编号。

## 一、参考文献目录

\[1\] Michiel Schreurs, Supinya Piampongsant, Miguel Roncoroni, Lloyd
Cool, Beatriz Herrera-Malaver, Christophe Vanderaa, Florian A.
Theßeling, Łukasz Kreft, Alexander Botzki, Philippe Malcorps, Luk
Daenen, Tom Wenseleers, Kevin J. Verstrepen，Predicting and improving
complex beer flavor through machine learning，*Nature
Communications*，15(1)：2368，2024。DOI：https://doi.org/10.1038/s41467-024-46346-0。

\[2\] Yu-Tang Wang, Zhao-Xia Yang, Zan-Hao Piao, Xiao-Juan Xu, Jun-Hong
Yu, Ying-Hua Zhang，Prediction of flavor and retention index for
compounds in beer depending on molecular structure using a machine
learning method，*RSC
Advances*，11：36942--36950，2021。DOI：https://doi.org/10.1039/D1RA06551C。

\[3\] Corina Maria Șutea, Elena Mudura, Carmen Rodica Pop, Liana Claudia
Salanță, Anca Corina Fărcaș, Petruț Cristian Balaș, Emese Gal,
Elisabeta-Irina Geană, Haifeng Zhao, Teodora Emilia Coldea，Beer Aroma
Compounds: Key Odorants, Off-Flavour Compounds and Improvement
Proposals，*Foods*，14(24)：4287，2025。DOI：https://doi.org/10.3390/foods14244287。

\[4\] Xingjie Wang, Stephanie Frank, Martin Steinhaus，Molecular
Insights into the Aroma Difference between Beer and Wine: A
Meta-Analysis-Based Sensory Study Using Concentration Leveling
Tests，*Journal of Agricultural and Food
Chemistry*，72(40)：22250--22257，2024。DOI：https://doi.org/10.1021/acs.jafc.4c06838。

\[5\] Shuya Zhang, Xiaoping Hou, Yuxiang Zhao, Kecheng Sun, Zirui Yin,
Jiahui Ding, Danni Sun, Jianghua Li, Xinrui Zhao, Yang He，Progress on
the formation, quantification, and elimination of off-flavor compounds
in non-distilled alcoholic beverages，*Journal of the Science of Food
and
Agriculture*，106(8)：4496--4506，2026。DOI：https://doi.org/10.1002/jsfa.70310。

\[6\] Zixuan Liu, Jianqiang Du, Jigen Luo, Yang Yuan, Qiang Huang, Jia
He，A stable feature selection method based on majority voting and SHAP
for high-dimensional metabolomics data，*Computer Methods and Programs
in
Biomedicine*，274：109170，2026。DOI：https://doi.org/10.1016/j.cmpb.2025.109170。

\[7\] Kaisa Miettinen，*Nonlinear Multiobjective
Optimization*，Boston：Kluwer Academic Publishers，1999。

\[8\] Kihyuk Sohn, Honglak Lee, Xinchen Yan，Learning Structured Output
Representation using Deep Conditional Generative Models，*Advances in
Neural Information Processing Systems 28 (NeurIPS
2015)*：3483--3491，2015。网址：https://papers.nips.cc/paper_files/paper/2015/hash/8d55a249e6baa5c06772297520da2051-Abstract.html。

\[9\] Gurobi Optimization, LLC，Multiple Objectives，Gurobi Optimizer
Reference
Manual，https://docs.gurobi.com/projects/optimizer/en/current/features/multiobjective.html，访问时间：2026
年 10 月 25 日。

\[10\] Gurobi Optimization, LLC，Gurobi Optimizer Reference
Manual，https://doc.gurobi.com/projects/optimizer/en/current/，访问时间：2026
年 10 月 25 日。

\[11\] Tamar Gadrich, Francesca R. Pennecchi, Ilya Kuselman，Ordinal
Analysis of Variation of Sensory Responses in Combination with
Multinomial Ordered Logistic Regression vs. Chemical Composition: A Case
Study of the Quality of a Sausage from Different Producers，*Journal of
Food
Quality*，2022：4181460，2022。网址：https://onlinelibrary.wiley.com/doi/10.1155/2022/4181460。

------------------------------------------------------------------------

## 二、每篇文献对论文的具体价值

### \[1\] Predicting and improving complex beer flavor through machine learning

**对应：Q1、Q2、Q3；优先级最高。**

研究分析了啤酒化学属性与感官/消费者评价之间的关系，比较机器学习模型，并分析关键化合物与风味改良的可能性。

-   **Q1：**
    为用化学特征预测感官属性、比较线性模型与树模型提供直接的啤酒领域依据。
-   **Q2：**
    支持将预测性能和关键特征解释结合，而不是只报告相关系数或单次重要性排名。
-   **Q3：**
    为"预测风味---识别可调整化学属性---提出改良方案"的总体路线提供背景。
-   **注意：**
    本题数据与原文的数据、标签和实验设计不同，不能照搬原文模型排名或性能指标。

### \[2\] Prediction of flavor and retention index for compounds in beer depending on molecular structure using a machine learning method

**对应：Q2 为主。**

研究使用化合物分子结构描述符和机器学习，预测啤酒风味化合物的风味类别与色谱保留指数。

-   为机器学习分析化学结构与风味属性关系提供啤酒领域研究背景。
-   可与 \[1\] 配合引用：\[1\] 更关注整瓶啤酒的复杂风味，\[2\]
    更关注单个化合物的风味类别。
-   **注意：**
    单个化合物的风味类别预测不等于整瓶啤酒的多维感官评分预测。

### \[3\] Beer Aroma Compounds: Key Odorants, Off-Flavour Compounds and Improvement Proposals

**对应：Q2、Q3。**

综述啤酒关键气味物质与缺陷风味化合物，包括双乙酰、二甲基硫、乙醛等，并讨论其来源和改善措施。

-   为 Q2 筛选出的候选化合物补充风味化学解释。
-   为 Q3 设计缺陷风险指标、解释候选方案合理性提供背景。
-   **注意：**
    若要将某个数值作为硬阈值，应进一步核对原始研究、浓度单位、啤酒基质和检测条件。

### \[4\] Molecular Insights into the Aroma Difference between Beer and Wine

**对应：Q2、Q3。**

研究汇总啤酒和葡萄酒的气味物质浓度，并用浓度调整的感官测试研究两类饮品的香气差异。

-   支持把风味看作多种化合物共同作用的整体，而非某一种化合物的单独效应。
-   可为 Q3 的目标风格参考谱、整体组成偏差和感官验证提供背景。
-   **注意：** 原文比较啤酒与葡萄酒，不能直接代表本题所有啤酒风格。

### \[5\] Progress on the formation, quantification, and elimination of off-flavor compounds in non-distilled alcoholic beverages

**对应：Q3 为主，Q2 为辅。**

综述非蒸馏酒精饮品中缺陷风味化合物的形成、定量检测与控制。

-   帮助确定缺陷风险约束的候选变量。
-   支持讨论阈值、风险控制和优化结果的化学合理性。
-   **注意：**
    不同饮品与实验条件的阈值不能直接混用，约束参数必须与本题数据单位一致。

### \[6\] A stable feature selection method based on majority voting and SHAP for high-dimensional metabolomics data

**对应：Q2。**

研究将交叉验证、Bootstrap、多数投票和 SHAP
结合，用于提高高维、小样本代谢组学中特征筛选的稳定性。

可借鉴的流程： 1. 对训练数据进行多次 Bootstrap 重采样。 2.
每次重新训练模型并计算特征重要性。 3. 统计每个化合物进入 Top-k 的频率。
4. 比较不同模型的候选集合一致性。 5. 将稳定候选与啤酒风味化学文献核对。

**注意：**
原文并非啤酒风味研究；它支持稳定筛选的方法设计，不直接证明某种化合物的感官作用。

### \[7\] Nonlinear Multiobjective Optimization

**对应：Q3。**

多目标优化理论专著，可用于解释目标风格偏差、配方改动幅度和缺陷风险之间的冲突，以及
Pareto 最优和目标权衡等概念。

**注意：** 这是通用优化理论，不是啤酒应用论文。实际 Gurobi
实现还应结合官方文档 \[9\]、\[10\]。

### \[8\] Learning Structured Output Representation using Deep Conditional Generative Models

**对应：Q3，条件生成方法背景。**

研究深度条件生成模型如何在给定条件下生成结构化输出。

-   可用于说明"给定目标风格条件，生成候选化学谱"的方法学思路。
-   **注意：** 原文不是啤酒化学组成研究，不能据此声称 CVAE
    已在本题有效。小样本下应先与相似样本/经验分布基线比较，并检查生成样本的新颖性和分布一致性。

### \[9\] Multiple Objectives（Gurobi 官方文档）

**对应：Q3。**

说明 Gurobi 多目标设置，包括加权组合和按优先级分层优化。

-   用于说明目标权重或优先级如何在求解器中实现。
-   关键限制：Gurobi
    的原生多目标功能要求各个目标均为线性表达式。若目标含平方偏差，需考虑单一凸二次目标、线性化或
    ε-约束等方案，而不能直接假设所有二次目标都可原样放入原生多目标接口。

### \[10\] Gurobi Optimizer Reference Manual

**对应：Q3。**

官方参考手册可用于确认变量、约束和目标函数类型，以及求解状态和结果查询方式。适合支撑软件实现细节，不应单独作为某种算法优越性的学术证据。

### \[11\] Ordinal Analysis of Variation of Sensory Responses ... A Case Study of the Quality of a Sausage

**对应：Q1，方法迁移参考。**

研究使用有序逻辑回归分析食品的有序感官响应与化学组成关系。

-   如果本题评分确实是 0--6 有序等级，可将有序回归作为对照模型。
-   可用于解释等级变量有顺序性，但不必然满足连续变量的等距假设。
-   **注意：** 研究对象是香肠而不是啤酒，只能支撑方法思路。

------------------------------------------------------------------------

## 三、正文引用写法示例

### Q1：感官评分补全

啤酒感官风味与化学组成之间存在复杂关系，已有研究使用多种机器学习模型预测啤酒风味，并分析对预测有贡献的化学属性\[1\]。考虑到本题评分变量的取值形式，本文首先核实评分是否为原始有序等级；若为有序等级，则将有序回归作为对照模型\[11\]，并通过交叉验证比较不同模型的预测表现。

### Q2：关键化合物筛选

已有研究将机器学习用于啤酒风味化合物的风味类别预测\[2\]，也将整瓶啤酒的化学属性与感官评价结合分析\[1\]。为降低单次特征排名对样本扰动的敏感性，本文采用重采样和特征稳定性分析，并参考高维代谢组学中的稳定特征筛选方法\[6\]。最终候选化合物再与啤酒关键气味物质和缺陷风味研究进行核对\[3\]。

### Q3：风格生成与约束优化

已有研究通过调整多种气味物质的浓度考察整体香气变化\[4\]。因此，本文将目标风格偏差、化学组成改动幅度与缺陷风险纳入候选方案评价，并参考多目标优化理论处理目标之间的权衡\[7\]。具体求解时，依据目标函数和约束的数学结构选择优化模型，并参考
Gurobi
官方文档实现目标设置与求解\[9--10\]。条件生成模型仅用于产生候选方案，其方法学背景参考条件生成模型研究\[8\]，生成结果仍需独立验证。

------------------------------------------------------------------------

## 四、提交前核验清单

-   [ ] 检查学校或竞赛是否规定 GB/T 7714
    等格式；如有要求，以正式要求为准。
-   [ ] 核对作者顺序、题名、期刊名、年份、卷期、页码/文章编号和 DOI。
-   [ ] 正文实际引用的文献才放入最终参考文献表。
-   [ ] 不把文献中的结果写成自己数据的实验结论。
-   [ ] 阈值、单位和感官等级定义等数值应回到原文或原始实验来源核实。
-   [ ] Q3 的生成模型、Gurobi 与多目标优化需结合本题数据结构验证可行性。

**范围说明：**
本文整理了当前讨论过的主要文献，并补充了条件生成与多目标优化基础来源；这不是穷尽式系统综述。正式提交前，应再次核对学校格式要求和每条书目信息。
