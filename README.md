# LogiBox V3.4.0

**Logistics Analytics Platform / 物流工程分析平台**

LogiBox V3.4.0 is a PySide6 desktop analytics workspace for logistics engineering, inventory analysis and warehouse decision support.

## Core modules

- 工作台 / Dashboard
- 数据中心 / CSV / XLSX / XLS 导入、预览、质量检查、导出
- EOQ 经济订货批量
- ABC 库存价值分类
- XYZ 需求稳定性分析
- ABC × XYZ 交叉矩阵 / 差异化库存策略
- 安全库存 / ROP
- 报告中心 / Word 分析报告
- 关于 LogiBox

## V3.4.0 highlights

- 新增 ABC × XYZ 交叉矩阵模块，3×3 矩阵输出 9 类库存的差异化补货与监控策略
- 矩阵 SKU 数量热力图与各单元金额占比柱状图
- 单元策略建议表：单元、优先级、金额占比、定位、管理策略
- 矩阵结果导出 Excel（SKU明细 + 单元策略双工作表）或 CSV
- 界面全面中文化：导航、工作台、窗口标题、状态栏、关于页面
- 中文字体优先，避免缺字方框；图表中文标题与坐标轴正常显示
- CSV 导入自动识别 UTF-8 / GBK(GB18030) / Big5 编码，中文版 Excel 导出的 CSV 不再乱码
- 日志文件固定 UTF-8，控制台输出编码容错
- 工作台页面跳转改为按 key 路由，新增模块不再导致入口错位
- Word 报告新增交叉矩阵章节，版本号统一读取 core.config
- 修复表格左上角与滚动区域右上角样式未覆盖导致的白色方块

## V3.3 highlights

- 科技感深色工作台界面
- 统一侧边导航与页面路由
- DataStore 共享数据与分析状态
- 动态 Dashboard 数据概览
- ABC + XYZ 双维库存分析能力
- 结果 Excel / CSV 导出
- Word 分析报告生成
- 示例库存数据一键加载
- 保留 V2.x 现有模块与 MetricCard 接口兼容性

## V3.3.1 Core Refactor

- core/config.py、core/page_registry.py、core/theme.py、core/logging_config.py 统一基础设施
- 全局异常捕获：未处理错误会提示并写入 logs/logibox.log
- ChartCanvas 重写为可复用图表组件

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
git checkout -b V3.4-dev
git add .
git commit -m "Release LogiBox V3.4.0 Matrix Edition"
git push -u origin V3.4-dev
```

Release tag:

```powershell
git tag v3.4.0
git push origin v3.4.0
```
