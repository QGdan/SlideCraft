# 场景蓝图构建与图片适配

实际命令（绑定项目内执行）：

```powershell
.\.venv\Scripts\python.exe -m ppt_workflow blueprint-build --input examples/campus-blueprint.json --out runs/new-scene-build --node D:/node/node.exe
```

这是独立原生编译路径，不走旧unified-v3的8–20页/两类别限制。请求版本blueprint-request/1，每页用layout、fields、source_refs、notes及该布局需要的asset_id/chart/items。参考examples里的完整请求，不猜字段。超出文字或实际版式图表容量会拒绝，不能缩小字体凑页。

输出candidate.pptx、deck-spec.json、design-system.json和blueprint-build.json。needs_review/退出码2是构建后待审核；release_allowed始终false。命令不创建六阶段审批，不替代资料研究或模板选型。

0.2图片元素可指定image_fit:cover/contain。cover保留比例并裁切，image_focus:{x:0..1,y:0..1}选择裁切焦点；contain等比居中，图框可以留白。没有image_fit的旧输入保留原行为。必须登记图片、尺寸、来源与SHA256，禁止把整页截图冒充原生文字或原生图表。

封面背景可以按主题复用，不能把同一张插画机械铺满所有页。内部像素不是可编辑PPT对象；“可替换图片”和“原生可编辑图表”分别说明。使用真实人物或品牌原图时，不生成替代品。

指定五种布局已在前序样页及本轮对照中渲染；任意导入模板、复杂图片重建、WPS/Figma往返未因此获得认证。批准件中的来源、事实和主张仍须原样继承。
