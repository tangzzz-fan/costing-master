# Excel 输出模板

本目录提供 Excel 兼容的 CSV 表头模板。用 Excel 打开 CSV、另存为 `.xlsx`，再按 `references/excel-output-guide.md` 组装工作簿。

## 模板清单

| 模板 | 对应工作流/参考 | 用途 |
|---|---|---|
| `boq-feature-check.csv` | `workflows/boq-missing-items-check.md` | 清单特征检查 |
| `bid-price-analysis.csv` | `workflows/pricing-and-bid-review.md` | 投标报价分析、不平衡报价线索 |
| `material-price-adjustment.csv` | `workflows/material-price-analysis.md` | 材料价差计算 |
| `progress-payment-audit.csv` | `workflows/progress-payment-audit.md` | 进度款审核汇总 |
| `settlement-deduction-register.csv` | `workflows/settlement-audit.md` | 审减/审增问题台账 |
| `cost-variance-analysis.csv` | `workflows/cost-management.md` | 成本偏差分析 |
| `evidence-index.csv` | `workflows/document-extraction-and-evidence.md` | 证据索引 |
| `comprehensive-unit-price.csv` | `workflows/pricing-and-bid-review.md` | 综合单价分析 |

## 使用步骤

1. 用 Excel 打开对应 CSV，检查表头和数据列。
2. 新建工作簿，按 `00_封面与版本`、`01_数据源与口径`、`02_原始数据`、`03_计算明细`、`04_汇总`、`05_问题台账`、`06_证据索引`、`07_需补资料`、`08_质检与审核` 建 sheet。
3. 把 CSV 导入对应 sheet；原始数据表不要合并单元格。
4. 添加公式：合价、偏差、调差、进度款、质保金、预付款扣回等。
5. 添加数据验证：判断等级统一为“确定/疑似/待补/人工确认”；状态统一为“待处理/处理中/已关闭”。
6. 冻结首行、开启筛选、设置金额/比例格式。
7. 在 `00_封面与版本` 记录项目、任务、版本、日期、适用标准、地方规则、编制/审核人。
8. 对外交付前导出 PDF/Word，完成人工审核和签认；Excel 保留为计算和跟踪底稿。

## 常用公式

```text
合价 = 工程量 × 综合单价
目标偏差 = 动态成本 - 目标成本
偏差比例 = 偏差金额 / 目标成本
材料调差 = 调差数量 × (施工期价 - 基准期价 × (1 + 风险幅度))
材料跌价调差 = 调差数量 × (施工期价 - 基准期价 × (1 - 风险幅度))
进度款 = 已完产值 × 支付比例 - 预付款扣回 - 甲供材扣回 - 质保金 - 其他扣款
质保金 = 本期应付款 × 质保金比例
```

## 注意

- CSV 使用 UTF-8 BOM，Excel 直接打开中文不乱码。
- 模板只提供表头；不要把模拟数据当作项目实际数据。
- 公式列不要手工覆盖；保留原始数据 sheet。
- 需要签章、签认或对外正式出具的文件，导出 PDF/Word 后按企业流程签认，不用 Excel 签名。
- 需要多 sheet、数据验证和公式时，建议在 Excel 中另存为 `.xlsx`，并按企业模板统一格式。
