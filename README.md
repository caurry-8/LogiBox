# LogiBox V2.2

物流工程效率工具箱。

## 本版本重点升级

- 修复 ABC 统计卡片 `parentWidget()` 生命周期问题
- 新增共享 DataStore 数据架构
- 数据中心支持 Excel / CSV 导入、预览、导出
- ABC 支持直接分析数值字段
- ABC 支持“年需求量 × 单价 = 年消耗金额”
- ABC 支持自定义 A / B 阈值
- ABC 增加 A/B/C 统计卡片
- ABC 增加金额贡献饼图与 SKU 数量柱状图
- 修复 Matplotlib 中文显示方框问题
- 表格改为更大的自适应区域，支持 QSplitter 拖动调整
- 百分比结果统一格式化为两位小数百分比
- 首页 Dashboard 增加数据行数、字段数、当前文件状态
- 统一深色主题

## 启动

```powershell
python main.py
```

## 测试流程

1. 进入“数据中心”导入 `data/sample_inventory.csv`
2. 进入“ABC 库存分类”
3. 选择“年需求量 × 单价 = 年消耗金额”
4. 选择年需求量与单价
5. 点击“开始 ABC 分类”
6. 查看统计卡片、饼图、柱状图和分类结果表
7. 导出分类结果

## Git

```powershell
git add .
git commit -m "V2.2 ABC专业分析与界面优化"
git push
```
