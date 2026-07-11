# 配置说明：DeepSeek API Key

本工具调用 DeepSeek 的 `deepseek-chat` 模型做面试官。你需要一个 API Key（学生有免费额度，个人项目完全够用）。

## 1. 获取 Key

1. 打开 https://platform.deepseek.com/
2. 用手机号注册 / 登录
3. 左侧菜单「API Keys」→「创建 API Key」
4. 复制生成的 `sk-xxxx...`（只显示一次，妥善保存）

## 2. 配置方式（任选其一）

### 方式 A：设置环境变量（推荐，避免把 Key 写进代码）

在运行前设置环境变量 `DEEPSEEK_API_KEY`：

```bash
# Linux / macOS
export DEEPSEEK_API_KEY="sk-你的key"
python skill/scripts/interview_server.py

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-你的key"
python skill/scripts/interview_server.py
```

`interview_server.py` 已支持从环境变量读取；若未设置，启动时会给出明确提示。

### 方式 B：直接改代码

打开 `skill/scripts/interview_server.py`，找到顶部：

```python
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
```

把空字符串替换为你的 Key（注意保留引号）：

```python
API_KEY = "sk-你的key"
```

> ⚠️ 若把代码提交到公开仓库（如 GitHub），**务必用方式 A 或提交前清空 Key**，不要把真实 Key 推上去。

## 3. 其它可调参数

| 参数 | 位置 | 说明 |
|---|---|---|
| `PORT` | 文件顶部 | 服务端口，默认 `8824`，被占用可改 |
| `MODEL` | 文件顶部 | 默认 `deepseek-chat`，可换其它 DeepSeek 模型 |
| `temperature` | `call_deepseek()` | 默认 `0.6`，越高越发散 |

## 4. 验证配置成功

启动后，浏览器打开 `http://localhost:8824`，填岗位 + 简历点「诊断简历，开始面试」。若能正常返回面试官提问，说明 Key 生效；若报「调用失败」，检查 Key 是否正确、网络是否可达 DeepSeek。
