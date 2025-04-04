# 游戏导航网站

这是一个基于 Flask 的游戏导航网站，数据来源于飞书多维表格。

## 项目结构

```
gamenav/
├── README.md           # 项目说明文档
├── requirements.txt    # 项目依赖
├── config.py          # 配置文件
├── app.py             # 主应用
├── static/            # 静态文件
│   ├── css/          # CSS 样式文件
│   │   ├── base.css  # 基础样式
│   │   ├── index.css # 首页样式
│   │   └── detail.css # 详情页样式
│   └── js/           # JavaScript 文件
│       └── main.js   # 主要脚本
└── templates/         # HTML 模板
    ├── base.html     # 基础模板
    ├── index.html    # 首页
    └── detail.html   # 详情页
```

## 功能特点

1. 首页
- 分类导航：展示不同类型的游戏
- 游戏列表：展示游戏封面、名称、推荐短语和标签

2. 游戏详情页
- 游戏详情：展示游戏名称、推荐短语和标签
- 马上游戏：基于 IFrame 的内嵌游戏区域
- 游戏截图：多张轮播展示
- 游戏介绍：展示游戏玩法

## 技术栈

- 后端：Python Flask 3.0.0
- 前端：原生 HTML/CSS
- 数据源：飞书多维表格

## 开发计划

1. 项目初始化
- [x] 创建项目结构
- [x] 编写 README.md
- [ ] 创建 requirements.txt
- [ ] 配置 config.py

2. 后端开发
- [ ] 实现飞书多维表格数据获取
- [ ] 实现路由和视图函数
- [ ] 实现数据缓存机制

3. 前端开发
- [ ] 创建基础模板
- [ ] 实现首页布局和样式
- [ ] 实现详情页布局和样式
- [ ] 实现响应式设计

4. 测试和优化
- [ ] 测试所有功能
- [ ] 优化性能
- [ ] 完善错误处理

## 运行说明

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置飞书应用信息：
在 `config.py` 中填入您的飞书应用信息。

3. 运行应用：
```bash
python app.py
```

4. 访问网站：
打开浏览器访问 http://localhost:5000 