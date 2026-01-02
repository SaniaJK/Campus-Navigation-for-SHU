<div align="center">
  <h1>🗺️ SHU 校园智能导航系统</h1>
  <p>
    <b>基于 OpenStreetMap 数据与 Flask 框架的校园路径规划与漫游系统</b>
  </p>
  
  <p>
    <a href="#-项目简介">项目简介</a> •
    <a href="#-核心功能">核心功能</a> •
    <a href="#-技术栈">技术栈</a> •
    <a href="#-快速开始">快速开始</a> •
    <a href="#-项目结构">项目结构</a> •
    <a href="#-算法实现">算法实现</a>
  </p>

  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Framework-Flask-green?style=flat-square&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Frontend-Leaflet.js-orange?style=flat-square&logo=leaflet" alt="Leaflet">
  <img src="https://img.shields.io/badge/Data-OpenStreetMap-purple?style=flat-square&logo=openstreetmap" alt="OSM">
</div>

---

## 📖 项目简介

**SHU Campus Navigation** 是一个前后端分离的 Web 校园导航应用。与传统地图软件不同，本项目完全基于 **OpenStreetMap (OSM)** 原始数据进行解析，构建了自定义的校园拓扑路网。

系统不仅支持基础的点对点最短路径规划，还针对校园场景实现了**多点漫游（TSP近似解）**，并引入了**时间维度的交通潮汐模拟**（如上课高峰期骑行拥堵判定），为师生提供更加智能、贴合实际的出行建议。

![系统运行截图](screenshots/demo_main.png)


## ✨ 核心功能

* **📍 精准点对点导航**：支持“步行”与“骑行”双模式，基于路网拓扑计算最短路径。
* **🔄 多点智能漫游**：想去取快递、再去食堂、最后去教学楼？系统自动规划不走回头路的最优访问顺序。
* **🚦 动态交通模拟**：内置上课时间表，自动检测出发时间。若处于上课前 20 分钟高峰期，智能调整骑行耗时（模拟拥堵倍率 x1.25）。
* **🔍 智能 POI 搜索**：支持下拉模糊搜索校园内主要建筑（教学楼、宿舍、食堂等）。
* **🗺️ 交互式地图**：基于 Leaflet 引擎，支持高亮显示建筑物轮廓、当前位置定位。
* **🚀 一键自动化启动**：提供 `startup.py` 脚本，自动检测环境、安装依赖、启动后端并打开浏览器。

## 🛠 技术栈

### Backend (后端)
- **Python 3**: 核心编程语言。
- **Flask**: 轻量级 Web 框架，提供 RESTful API。
- **xml.dom.minidom**: 解析 OSM XML 地图数据。
- **Bisect**: 使用二分查找维护稀疏图邻接表的有序性，优化查询效率。

### Frontend (前端)
- **HTML5 / CSS3**: 页面布局与样式。
- **JavaScript (ES6)**: 交互逻辑开发。
- **Leaflet.js**: 开源交互式地图库。
- **jQuery & Select2**: DOM 操作与增强型搜索框。

### Data (数据)
- **OpenStreetMap (OSM)**: 原始地理信息数据源。

## 🚀 快速开始

### 环境要求
- Python 3.8 或更高版本
- Git

### 安装与运行

1.  **克隆项目**
    ```bash
    git clone [https://github.com/你的用户名/SHU-Smart-Campus-Navigation.git](https://github.com/你的用户名/SHU-Smart-Campus-Navigation.git)
    cd SHU-Smart-Campus-Navigation
    ```

2.  **一键启动 (推荐)**
    直接运行根目录下的启动脚本，它会自动安装依赖 (`flask`, `requests`, `lxml`) 并启动服务。
    ```bash
    python backend/startup.py
    ```
    *程序启动后将自动打开默认浏览器访问系统。*

3.  **手动启动 (备选)**
    ```bash
    # 1. 安装依赖
    pip install -r backend/requirements.txt
    
    # 2. 启动 Flask
    python backend/app.py
    
    # 3. 浏览器访问 [http://127.0.0.1:5000](http://127.0.0.1:5000)
    ```

## 📂 项目结构

```text
SHU-Smart-Campus-Navigation/
├── backend/
│   ├── app.py              # Flask 后端入口，API 定义
│   ├── parser.py           # 核心模块：OSM 解析、建图、Dijkstra 算法
│   ├── startup.py          # 自动化启动脚本
│   ├── requirements.txt    # Python 依赖列表
│   └── map_test.osm        # 校园地图原始数据
├── frontend/
│   ├── index.html          # 主页面
│   ├── app.js              # 前端交互逻辑
│   └── style.css           # 页面样式
└── README.md               # 项目说明文档
