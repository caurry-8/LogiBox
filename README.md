# LogiBox V3.2

**Logistics Analytics Platform / 物流工程分析平台**

LogiBox V3.2 is a PySide6 desktop analytics workspace for logistics engineering, inventory analysis and warehouse decision support.

## Core modules

- 工作台 / Dashboard
- 数据中心 / CSV / XLSX / XLS 导入、预览、质量检查、导出
- EOQ 经济订货批量
- ABC 库存价值分类
- XYZ 需求稳定性分析
- 安全库存 / ROP
- 报告中心 / Word 分析报告
- 关于 LogiBox

## V3.2 highlights

- 科技感深色工作台界面
- 统一侧边导航与页面路由
- DataStore 共享数据与分析状态
- 动态 Dashboard 数据概览
- ABC + XYZ 双维库存分析能力
- 结果 Excel / CSV 导出
- Word 分析报告生成
- 示例库存数据一键加载
- 保留 V2.x 现有模块与 MetricCard 接口兼容性

## Run

```powershell
python main.py
```

## Install dependencies

```powershell
pip install -r requirements.txt
```

## Suggested Git workflow

```powershell
git checkout -b V3.2-dev
git add .
git commit -m "Release LogiBox V3.2"
git push -u origin V3.2-dev
```

Release tag:

```powershell
git tag v3.0.0
git push origin v3.0.0
```
