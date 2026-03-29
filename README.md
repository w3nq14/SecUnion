# BlogLink Network Visualizer

一个用于发现和可视化博客友链关系网络的工具，支持递归查找、AI智能过滤、图形化展示友链关系。

## ✨ 功能特性

- 🕷️ **递归查找** - 支持1-3层深度的友链递归发现
- 🤖 **AI智能过滤** - 自动识别并过滤企业域名
- 📊 **可视化展示** - 交互式网络图展示友链关系
- 💾 **本地缓存** - 支持离线查看历史数据
- 🎯 **黑白名单** - 灵活的域名过滤机制
- 📋 **双视图模式** - 表格/图形视图自由切换

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 现代浏览器（Chrome/Firefox/Edge）

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 配置（可选）

如需启用AI检测功能，创建 `backend/.env` 文件：

```bash
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://api.linkapi.ai/v1
```

> 不配置AI功能不影响基本查找和可视化

### 启动服务

**方式一：一键启动（推荐）**

```bash
python start.py
```

**方式二：手动启动**

```bash
# 终端1 - 启动后端
cd backend
python run.py

# 终端2 - 启动前端
cd frontend
python -m http.server 3000
```

### 访问系统

- 🌐 前端界面: http://localhost:3000
- 🔌 后端API: http://localhost:8011

## 📖 使用指南

### 1. 开始查找

- 输入一个或多个博客URL（每行一个）
- 选择查找深度（1-3层）
- 点击"查找友链"按钮

### 2. 查看结果

- **表格视图** - 默认显示，列出所有博客信息
- **图形视图** - 点击"切换到图形视图"查看关系网络
- **交互操作** - 点击节点高亮其连接关系

### 3. 数据管理

- **查看缓存** - 加载历史数据
- **黑名单管理** - 过滤不需要的域名
- **全部友链** - 查看所有已发现的博客

## 📁 项目结构

```
SecUnion/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI主服务
│   ├── crawler.py       # 发现引擎
│   ├── parser.py        # 友链解析器
│   ├── ai_detector.py   # AI域名检测
│   ├── storage.py       # 数据存储层
│   ├── domain_filter.py # 域名过滤器
│   ├── graph_builder.py # 图结构构建
│   ├── url_normalizer.py# URL标准化
│   ├── run.py           # 启动脚本
│   └── requirements.txt # 依赖列表
├── frontend/            # 前端页面
│   ├── index.html      # 主页面
│   ├── graph.js        # 可视化逻辑
│   └── styles.css      # 样式文件
├── data/               # 数据目录
│   ├── blogs.json      # 博客缓存
│   └── domain_filter.json # 黑白名单
├── start.py            # 一键启动脚本
└── README.md           # 项目文档
```

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/crawl` | POST | 启动查找任务 |
| `/status/{job_id}` | GET | 查询任务状态 |
| `/cache` | GET | 获取缓存数据 |
| `/all_blogs` | GET | 获取所有博客 |
| `/blacklist` | POST | 添加黑名单 |
| `/stop/{job_id}` | POST | 停止查找任务 |

## 🛠️ 技术栈

**后端**
- FastAPI - 现代Web框架
- aiohttp - 异步HTTP客户端
- BeautifulSoup4 - HTML解析
- NetworkX - 图数据结构

**前端**
- Cytoscape.js - 网络图可视化
- 原生JavaScript - 无框架依赖

## ⚠️ 注意事项

1. 请遵守目标网站的 robots.txt 规则
2. 默认每个域名间隔1秒请求，避免服务器过载
3. AI检测功能需要API密钥，不配置则跳过
4. 数据存储在本地JSON文件，建议定期备份

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
