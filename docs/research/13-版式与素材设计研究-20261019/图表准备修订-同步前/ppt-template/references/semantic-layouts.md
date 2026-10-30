# 语义版式与容量

quality-v1设计系统除font/colors/layouts外，增加semantic_layouts对象，键使用真实已登记的layout key，例如：

```json
{"semantic_layouts":{"chart_takeaway":{"carriers":["native_bar","native_line"],"max_body_characters":120,"max_chart_categories":6,"max_chart_series":3,"min_body_font_pt":18}}}
```

这些容量是该模板的设计决定，不是全项目统一阈值。先通过代表样页检验。content-plan每页的carrier应至少有一种版式能承载，compose实际选用的版式必须对应，并满足正文总字符、最小字号、图表类别数及系列数约束。

数据比较、时间趋势、关系解释、案例过程、行动安排可有不同构图。照片/插画与图表用途分开；无数据的页面不因没有chart而降低编辑性等级。不能用更多装饰框来证明信息设计变好。

真实模板复制可继续使用已验证WPS或项目既有automizer实验路线，但容量合同不能代替目标软件兼容性与编辑往返检查。新增任意模板适配器前，先明确支持对象、版本与回退边界。
