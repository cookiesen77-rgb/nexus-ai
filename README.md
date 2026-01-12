# Nexus AI（开源版）

Nexus 是一个面向开发者的 **AI Agent 系统**：把「对话 + 工具调用 + 工作流」整合到一个可运行的后端与前端里，支持你快速搭建自己的 AI 助手/生产力工具。

### 获取 Key（最重要）

Nexus 默认通过 **OpenAI 兼容接口**调用模型。请先到 **NexusAPI** 获取并管理你的 Key：

- 官网：[`https://nexusapi.cn`](https://nexusapi.cn)

（建议先注册并创建一个 Key，再继续下面的快速开始）

---

## 你能用 Nexus 做什么

- **聊天对话**：多轮对话、上下文管理
- **工具调用**：文件读写、Shell、代码执行、Web 搜索、浏览器自动化等（按配置启用）
- **PPT 能力**：生成 PPT 文案与配图（后端提供接口，前端提供入口）
- **设计模块**：设计对话、图片生成、元素拆分、图片文字编辑等（开源版不依赖云端存储）
- **可配置模型**：通过 `.env` 一键切换 **模型 / Key / 请求地址**，无需改代码

---

## 快速开始（3 分钟跑起来）

### 1) 安装依赖

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) 配置 Key 与请求地址（必做）

```bash
cp env.template .env
```

编辑 `.env`，填写从 NexusAPI 获取的 Key：

```env
ALLAPI_KEY=YOUR_KEY_FROM_NEXUSAPI
ALLAPI_BASE_URL=https://nexusapi.cn/v1
```

> 你可以在 [`https://nexusapi.cn`](https://nexusapi.cn) 获取 Key。

### 3) 配置你想用的模型（可随时改）

同样在 `.env` 里修改：

```env
LLM_DEFAULT_MODEL=grok-4.1
LLM_THINKING_MODEL=grok-4.1
LLM_VISION_MODEL=grok-4.1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
```

### 4) 启动后端

```bash
./scripts/start.sh
```

默认地址：`http://127.0.0.1:8000`

### 5) （可选）启动前端

```bash
cd frontend
npm ci
npm run dev
```

---

## 一键更换「模型 / Key / 请求地址」（推荐做法）

你只需要修改 `.env`，无需改代码：

- **换 Key**：改 `ALLAPI_KEY`
- **换请求地址**：改 `ALLAPI_BASE_URL`（默认 `https://nexusapi.cn/v1`）
- **换模型**：改 `LLM_DEFAULT_MODEL` / `LLM_THINKING_MODEL` / `LLM_VISION_MODEL`

---

## 开源安全说明

- 请勿在仓库中提交 `.env`
- 请勿把任何 Key 写进代码或文档
- 本仓库已移除与云端后台相关的实现（如 Supabase/管理后台），默认只使用环境变量配置

---

## NexusAPI

获取 Key、管理 Key、查看接口信息：[`https://nexusapi.cn`](https://nexusapi.cn)
