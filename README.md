# LLM_StructTranslate

将 Markdown 文档按章节拆分后并发调用 LLM 进行**结构化翻译**的小工具：尽量保持 Markdown 结构、公式与代码块不变，仅翻译自然语言内容。

> 适用场景：论文/博客/文档的批量翻译；希望保留原始 Markdown 结构（标题、列表、代码块、公式等）。



## 功能特性

- **按一级标题 `# ` 拆分** Markdown（每个章节单独翻译，降低单次上下文长度压力）
- **并发翻译**：`ThreadPoolExecutor` 多线程提升速度（可配置并发数）
- **断点续跑缓存**：翻译完成的章节写入 `translate_cache.json`，中断后可继续
- **可中途停止**：运行时按 `Ctrl + C`，会在安全点停止（便于中途换模型/改配置后继续跑）
- **输出与缓存就地生成**：在输入文件所在目录生成 `*_CN.md` 与 `translate_cache.json`



## 目录结构（简要）

```
.
├─ main.py                      # 主程序
├─ test.py                      # 测试/实验脚本（如有）
├─ translate_cache.json         # 旧版缓存文件（可能存在）
├─ config/
│  ├─ __init__.py               # 配置加载逻辑（支持环境变量覆盖）
│  ├─ config.json               # 配置（建议仅保留占位符；真实 key 用环境变量）
│  └─ config.example.json       # 示例配置
└─ file/
   ├─ input/                    # 输入目录（可放多份资料）
   └─ output/                   # 历史输出目录（旧逻辑可能用到）
```

> 说明：目前 `main.py` 的输出路径逻辑为“**输入文件同目录输出**”，不再写到 `file/output`。



## 安装

### 1) 创建环境并安装依赖

项目主要依赖：

- Python 3.9+（建议）
- `openai`（兼容 OpenAI SDK 风格接口的服务也可用）

**方式 A：使用 requirements.txt（推荐）**

```bash
pip install -r requirements.txt
```

**方式 B：手动安装**

```bash
pip install openai
```



## 配置

配置文件默认在：`config/config.json`。

### 方式 A：环境变量（推荐，开源仓库最安全）

`config/__init__.py` 已支持使用环境变量覆盖配置：

- `API_KEY`
- `API_BASE_URL`
- `API_MODEL`

Windows (PowerShell)：

```powershell
$env:API_KEY = "your_real_api_key"
$env:API_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
$env:API_MODEL = "kimi-k2.5"
```

macOS/Linux：

```bash
export API_KEY="your_real_api_key"
export API_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export API_MODEL="kimi-k2.5"
```

> 这样你可以把 `config/config.json` 里的 key/base_url 保持为占位符，不用担心推送泄露。

### 方式 B：复制示例配置文件

```bash
cp config/config.example.json config/config.json
```

然后编辑 `config/config.json`。

> 注意：仓库的 `.gitignore` 已忽略 `config/config.json`，避免误提交。



## 使用方法

### 1) 设置输入文件路径

在 `config/config.json` 中设置：

```json
{
  "files": {
    "input": "file/input/xxx/auto/xxx.md"
  }
}
```

### 2) 运行

```bash
python main.py
```

运行时会打印：输入文件、输出文件、缓存文件、模型、并发数、章节数、缓存命中等信息。



## 输出与缓存规则（重要）

当前 `main.py` 的规则：

- **输出文件**：与输入文件同目录，文件名为 `原名_CN.md`
- **缓存文件**：与输入文件同目录，固定为 `translate_cache.json`

例如：

- 输入：`file/input/2409.15306v1/auto/2409.15306v1.md`
- 输出：`file/input/2409.15306v1/auto/2409.15306v1_CN.md`
- 缓存：`file/input/2409.15306v1/auto/translate_cache.json`

缓存会记录每个章节（按拆分序号）对应的翻译结果；再次运行时会自动跳过已有缓存的章节。

> 当前版本：**缓存文件会保留，不再在结束时删除**，以便断点续跑。



## 中途暂停/停止（换模型/改配置）

运行时按 **Ctrl + C**：

- 程序会设置停止标记 `stop_event`
- 尽量在安全点停止（不会再发起新的章节翻译）
- 已完成的章节会写入缓存

停止后你可以：

1. 修改 `API_MODEL`（或 `config/config.json` 的 model）
2. 重新运行 `python main.py`
3. 会从缓存继续未完成章节



## 可调参数

`config/config.json`：

- `translation.max_workers`：并发线程数（默认 5）
- `api.model`：模型名（也可用 `API_MODEL` 覆盖）

> 提醒：并发太高可能触发服务端限流（429），可适当降低并发或增加重试等待。



## 常见问题（FAQ）

### Q1：会不会“累计上下文”导致超过上下文长度？

不会。

该脚本每个章节都是一次独立请求：`messages=[{"role":"user", "content": prompt}]`，不携带历史对话，因此上下文限制只与“**该次请求的 prompt + 章节内容 + 模型回复**”有关。

### Q2：为什么有时候需要更细粒度拆分？

如果某个章节本身太长，单次请求可能仍会超过模型上下文长度。这时可以考虑：

- 进一步按二级/三级标题拆分
- 或按段落拆分

### Q3：OpenAI SDK 能连阿里/其他平台的接口吗？

可以，只要接口兼容 OpenAI Chat Completions 风格，并正确设置 `base_url` 与 `api_key`。



## 开发说明

- 配置加载逻辑在 `config/__init__.py`
- 主流程在 `main.py`
- 缓存写入频率：每翻译完一个章节会立即写入（避免中途退出丢进度）

