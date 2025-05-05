soot-mash-demo/
├── client/                ← 🔸 可选前端：如果你想写个简单浏览器界面调用 mash API
│   ├── index.html
│   └── scripts/
│       └── main.js
│
├── server/                ← 🧠 核心后端代码
│   ├── main.py            ← ✅ FastAPI app 主入口（用 uvicorn 跑它）
│   ├── app.py             ← 实例化 FastAPI + 注册路由
│   ├── config.py          ← 存放 config（token、SOOT key等）
│   ├── mash/              ← mash 特有逻辑：prompt、组合逻辑、图像处理
│   │   ├── __init__.py
│   │   ├── routes.py      ← 路由（FastAPI Router）
│   │   ├── processor.py   ← mash核心处理逻辑
│   │   └── image_utils.py ← 图片处理逻辑（如果你有图像相关操作）
│   ├── soot/              ← 调用 SOOT API 的模块
│   │   ├── __init__.py
│   │   ├── connector.py   ← 调用 /spaces /upload 等接口
│   └── utils/
│       ├── __init__.py
│       └── helpers.py     ← 其他辅助函数
│
├── requirements.txt       ← pip install -r 用这个
├── README.md
├── .gitignore
└── venv/                  ← 虚拟环境（已加 gitignore）
