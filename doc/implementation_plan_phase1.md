# 实现计划 - 阶段 1：基础框架 + 静态页面

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

搭建前后端项目骨架，实现响应式布局和虚拟人头像展示，为后续功能开发奠定基础。

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 1.1 | 创建前端 React 项目 | 搭建 | - |
| 1.2 | 创建后端 FastAPI 项目 | 搭建 | - |
| 1.3 | 实现响应式布局组件 | 前端 | ✓ |
| 1.4 | 实现虚拟人头像区域 | 前端 | ✓ |
| 1.5 | 实现文字展示区域 | 前端 | ✓ |
| 1.6 | 实现情感状态管理 | 前端 | ✓ |
| 1.7 | 后端健康检查接口 | 后端 | ✓ |

---

## 2. 详细任务说明

### 2.1 创建前端 React 项目

**目录：** `frontend/`

**执行命令：**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**依赖安装：**
```bash
npm install
# 暂不安装额外依赖，使用 React 内置状态管理
```

**目录结构初始化：**
```
frontend/src/
├── components/
│   ├── AvatarArea/
│   ├── TextArea/
│   └── Layout/
├── hooks/
├── services/
├── types/
├── utils/
└── styles/
```

---

### 2.2 创建后端 FastAPI 项目

**目录：** `backend/`

**目录结构初始化：**
```
backend/
├── main.py
├── api/
│   └── __init__.py
├── services/
│   └── __init__.py
├── models/
│   └── __init__.py
├── utils/
│   └── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── requirements.txt
└── .env.example
```

**requirements.txt：**
```
fastapi>=0.109.0
uvicorn>=0.27.0
python-dotenv>=1.0.0
httpx>=0.26.0
websockets>=12.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

**启动验证：**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

### 2.3 实现响应式布局组件

**文件：** `frontend/src/components/Layout/`

**功能：**
- 检测屏幕宽度，区分手机/电脑
- 手机：上下布局（各占 50%）
- 电脑：左右布局

**断点定义：**
```typescript
const MOBILE_BREAKPOINT = 768; // px（业界默认值，可调整）
```

**说明：** 断点用于判断设备类型，不影响布局占比：
- 屏幕宽度 < 768px → 手机布局（上下各占 **50%**）
- 屏幕宽度 >= 768px → 电脑布局（左右各占 **50%**）

**组件结构：**
```typescript
// Layout.tsx
interface LayoutProps {
  avatarArea: React.ReactNode;
  textArea: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ avatarArea, textArea }) => {
  const isMobile = useMediaQuery(MOBILE_BREAKPOINT);

  return isMobile
    ? <MobileLayout ... />
    : <DesktopLayout ... />;
};
```

**样式要求：**
- 全屏布局，无滚动条
- 手机：`flex-direction: column`，各占 `50vh`
- 电脑：`flex-direction: row`，各占 `50vw`

---

### 2.4 实现虚拟人头像区域

**文件：** `frontend/src/components/AvatarArea/`

**功能：**
- 展示虚拟人头像图片
- 根据情感状态切换头像
- 耳朵图标定位（右上角）
- 图片等比缩放占满区域

**Props 定义：**
```typescript
type EmotionType = 'default' | 'empathy' | 'comfort' | 'happy';

interface AvatarAreaProps {
  emotion: EmotionType;
  showEarIndicator: boolean;
  isEarBlinking: boolean;
}
```

**头像映射：**
```typescript
const AVATAR_MAP: Record<EmotionType, string> = {
  default: '/assets/avatars/default.png',   // 默认陪伴
  empathy: '/assets/avatars/empathy.png',   // 共情倾听
  comfort: '/assets/avatars/comfort.png',   // 安慰支持
  happy: '/assets/avatars/happy.png',       // 轻松愉悦
};
```

**耳朵图标组件：**
```typescript
// EarIndicator.tsx
interface EarIndicatorProps {
  isBlinking: boolean;
}

// 使用 emoji 👂
// CSS 动画实现闪动效果
```

---

### 2.5 实现文字展示区域

**文件：** `frontend/src/components/TextArea/`

**功能：**
- 展示当前说话内容（用户或 AI）
- 流式文字追加显示
- 自动滚动到底部
- 错误提示展示

**Props 定义：**
```typescript
type Speaker = 'user' | 'assistant';

interface TextAreaProps {
  text: string;
  speaker: Speaker;
  isStreaming: boolean;
  error?: {
    message: string;
    onRetry: () => void;
  };
}
```

**样式要求：**
- 无背景，仅文字
- 文字居中或左对齐（根据设计）
- 错误时显示红色文字 + 重试按钮

---

### 2.6 实现情感状态管理

**文件：** `frontend/src/hooks/useEmotion.ts`

**功能：**
- 管理当前情感状态
- 提供状态切换方法
- 情感值映射

**接口定义：**
```typescript
type EmotionType = 'default' | 'empathy' | 'comfort' | 'happy';

// 服务端返回的中文情感值映射
const EMOTION_MAP: Record<string, EmotionType> = {
  '默认陪伴': 'default',
  '共情倾听': 'empathy',
  '安慰支持': 'comfort',
  '轻松愉悦': 'happy',
};

interface UseEmotionReturn {
  emotion: EmotionType;
  setEmotion: (emotion: EmotionType) => void;
  setEmotionFromServer: (serverEmotion: string) => void;
}
```

---

### 2.7 后端健康检查接口

**文件：** `backend/main.py`

**功能：**
- 提供 `/health` 接口验证服务运行状态
- 提供 `/api/config` 接口（预留）

**实现：**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mapijing API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/config")
async def get_config():
    return {"emotion_types": ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]}
```

---

## 3. 测试计划

### 3.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| Layout 组件 | 响应式布局切换 | `Layout.test.tsx` |
| AvatarArea 组件 | 头像切换、耳朵图标显示 | `AvatarArea.test.tsx` |
| TextArea 组件 | 文字渲染、错误显示 | `TextArea.test.tsx` |
| useEmotion Hook | 状态管理、映射转换 | `useEmotion.test.ts` |
| 健康检查接口 | 返回值验证 | `test_main.py` |

**前端测试框架：**
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

**后端测试框架：**
```bash
pip install pytest pytest-asyncio httpx
```

### 3.2 手工测试

| 测试项 | 验证内容 |
|--------|----------|
| 响应式布局 | 浏览器窗口缩放，验证手机/电脑布局切换 |
| 头像展示 | 四种头像正确显示，无变形 |
| 耳朵图标 | 位置正确（头像右上角），闪动动画正常 |
| 错误提示 | 红色文字显示，重试按钮可点击 |

---

## 4. 交付物

完成本阶段后，应具备：

- [ ] 前端项目可运行（`npm run dev`）
- [ ] 后端项目可运行（`uvicorn main:app --reload`）
- [ ] 响应式布局正常（手机/电脑）
- [ ] 头像可根据状态切换
- [ ] 耳朵图标可显示/闪动
- [ ] 文字区域可展示文字
- [ ] 错误提示可展示
- [ ] 单元测试全部通过
- [ ] 健康检查接口返回正常

---

## 5. 头像资源

头像图片已就绪：

| 文件 | 情感状态 | 路径 |
|------|----------|------|
| `default.png` | 默认陪伴 | `frontend/public/assets/avatars/default.png` |
| `empathy.png` | 共情倾听 | `frontend/public/assets/avatars/empathy.png` |
| `comfort.png` | 安慰支持 | `frontend/public/assets/avatars/comfort.png` |
| `happy.png` | 轻松愉悦 | `frontend/public/assets/avatars/happy.png` |

**状态：** ✅ 已完成

---

## 6. 预计产出文件

```
Mapijing/
├── frontend/
│   ├── public/
│   │   └── assets/avatars/       # 头像图片
│   ├── src/
│   │   ├── App.tsx               # 主应用
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Layout.css
│   │   │   │   └── Layout.test.tsx
│   │   │   ├── AvatarArea/
│   │   │   │   ├── AvatarArea.tsx
│   │   │   │   ├── AvatarArea.css
│   │   │   │   ├── EarIndicator.tsx
│   │   │   │   └── AvatarArea.test.tsx
│   │   │   └── TextArea/
│   │   │       ├── TextArea.tsx
│   │   │       ├── TextArea.css
│   │   │       ├── ErrorDisplay.tsx
│   │   │       └── TextArea.test.tsx
│   │   ├── hooks/
│   │   │   ├── useEmotion.ts
│   │   │   └── useEmotion.test.ts
│   │   ├── types/
│   │   │   └── emotion.ts
│   │   └── styles/
│   │       └── global.css
│   ├── package.json
│   ├── vite.config.ts
│   └── vitest.config.ts
│
└── backend/
    ├── main.py
    ├── tests/
    │   └── test_main.py
    ├── requirements.txt
    └── .env.example
```
