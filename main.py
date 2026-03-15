import re
import json
import time
import signal
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from config import config

client = OpenAI(api_key=config.api.key, base_url=config.api.base_url)

# ============================
# Step1: Markdown 按二级标题拆分
# ============================


def split_markdown_by_h2(text):
    """
    将 markdown 按 # 标题拆分
    """
    pattern = r"(# .+)"
    parts = re.split(pattern, text)

    sections = []
    current = ""

    for part in parts:
        if part.startswith("# "):
            if current:
                sections.append(current)
            current = part
        else:
            current += part

    if current:
        sections.append(current)

    return sections


# ============================
# Step2: 调用 LLM 翻译
# ============================


def translate_text(text, max_retries=3):

    prompt = f"""
Translate the following Markdown content into Chinese.

Requirements:
1. Keep all Markdown format unchanged
2. Keep formulas unchanged
3. Keep code blocks unchanged
4. Only translate natural language

Markdown:

{text}
"""

    for attempt in range(max_retries):
        print(
            "  [DEBUG] 调用 API (尝试 "
            + str(attempt + 1)
            + "/"
            + str(max_retries)
            + ")，模型："
            + config.api.model
        )

        try:
            response = client.chat.completions.create(
                model=config.api.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=120,
            )
            print("  [DEBUG] API 响应成功")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print("  [WARN] 尝试 " + str(attempt + 1) + " 失败：" + str(e))
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # 1s, 2s, 4s
                print("  [INFO] 等待 " + str(wait_time) + "s 后重试...")
                time.sleep(wait_time)
            else:
                print("  [ERROR] " + str(max_retries) + " 次尝试均失败")
                raise


# ============================
# Step3: 缓存机制（防止中断）
# ============================


def load_cache():
    if Path(config.files.cache).exists():
        return json.loads(Path(config.files.cache).read_text())
    return {}


def save_cache(cache):
    Path(config.files.cache).write_text(json.dumps(cache, ensure_ascii=False, indent=2))


# ============================
# Step4: 翻译任务
# ============================


# 用于在按 Ctrl+C 时平滑停止（便于中途修改模型后重新运行）
stop_event = threading.Event()


def translate_section(idx, section, cache, total_count):

    if stop_event.is_set():
        raise KeyboardInterrupt()

    if str(idx) in cache:
        print(f"[{idx+1}/{total_count}] ✓ 跳过 (缓存)")
        return cache[str(idx)]

    print(f"[{idx+1}/{total_count}] → 开始翻译...")

    try:
        translated = translate_text(section)
        cache[str(idx)] = translated
        save_cache(cache)
        print(f"[{idx+1}/{total_count}] ✓ 翻译完成，已保存缓存")
    except Exception as e:
        print(f"[{idx+1}/{total_count}] ✗ 翻译失败：{e}")
        raise

    time.sleep(0.5)

    return translated


# ============================
# Step5: 主流程
# ============================


def _handle_sigint(signum, frame):
    """SIGINT handler: 标记停止并在下一次安全检查时退出。"""
    print(
        "\n[INFO] 收到中断信号，将在当前正在翻译的章节完成后停止。可修改模型后重新运行。"
    )
    stop_event.set()


def main():

    # 设置 Ctrl+C（SIGINT）处理器，方便暂停/停止并保持缓存
    signal.signal(signal.SIGINT, _handle_sigint)

    input_path = Path(config.files.input)
    # 自动生成输出路径：file/output + 输入相对路径 + 文件名_CN.扩展名
    relative_path = input_path.relative_to("file/input")
    output_path = (
        Path("file/output")
        / relative_path.parent
        / (input_path.stem + "_CN" + input_path.suffix)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在

    text = input_path.read_text(encoding="utf-8")

    sections = split_markdown_by_h2(text)
    total_count = len(sections)

    print("=" * 50)
    print("输入文件：" + str(input_path))
    print("输出文件：" + str(output_path))
    print("模型：" + config.api.model)
    print("并发数：" + str(config.translation.max_workers))
    print("=" * 50)
    print("共 " + str(total_count) + " 个章节")

    cache = load_cache()
    cached_count = len(cache)
    print("缓存命中：" + str(cached_count) + "/" + str(total_count))
    print("=" * 50)

    results = [None] * len(sections)
    completed = 0

    with ThreadPoolExecutor(config.translation.max_workers) as executor:

        futures = {
            executor.submit(translate_section, i, sec, cache, total_count): i
            for i, sec in enumerate(sections)
        }

        try:
            for future in as_completed(futures):
                idx = futures[future]
                result = future.result()
                results[idx] = result
                completed += 1
                print("[进度] " + str(completed) + "/" + str(total_count))

                # 如果已请求停止，提前结束
                if stop_event.is_set():
                    print("[INFO] 已请求停止，正在退出。")
                    break
        except KeyboardInterrupt:
            print("[INFO] 用户中断，正在停止并保存当前进度...")
        finally:
            # 如果用户按 Ctrl+C，会通过 stop_event 在 translate_section 内触发，并且这里也可能被捕获。
            executor.shutdown(wait=False, cancel_futures=True)

    # 如果在中途停止，results 里可能存在 None，剔除后再写入
    final_text = "\n".join([r for r in results if r is not None])

    output_path.write_text(final_text, encoding="utf-8")

    # 删除缓存文件（每次运行到最终结果后清理）
    cache_path = Path(config.files.cache)
    if cache_path.exists():
        cache_path.unlink()
        print(f"已删除缓存：{cache_path}")

    print("=" * 50)
    print("done!")


# ============================

if __name__ == "__main__":
    main()
