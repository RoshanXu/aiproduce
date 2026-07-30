"""文本处理工具"""

import re
from pathlib import Path


def count_chinese_words(text: str) -> int:
    """统计中文文本字数（含标点）"""
    return len(text.replace("\n", "").replace(" ", ""))


def detect_chapter_boundaries(text: str) -> list[dict]:
    """自动检测章节边界

    支持常见小说章节格式:
    - 第X章/第X卷/第X节
    - Chapter X
    - 中文数字章节
    """
    patterns = [
        r"第[零一二三四五六七八九十百千万\d]+[章节卷部篇]",
        r"Chapter\s+\d+",
        r"(?:序章|楔子|尾声|番外)",
    ]

    combined = "|".join(f"({p})" for p in patterns)
    matches = list(re.finditer(combined, text, re.IGNORECASE))

    boundaries = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        boundaries.append({
            "title": m.group(),
            "start": start,
            "end": end,
            "text": text[start:end],
        })
    return boundaries


def split_text_by_words(text: str, max_words: int, overlap: int = 0) -> list[str]:
    """按字数拆分文本（仅用于兜底，优先使用语义拆分）

    Args:
        text: 输入文本
        max_words: 单块最大字数
        overlap: 块间重叠字数（保持语义连续性）
    """
    clean = text.replace("\n", "").replace(" ", "")
    blocks = []
    start = 0
    while start < len(clean):
        end = min(start + max_words, len(clean))
        blocks.append(clean[start:end])
        start = end - overlap
        if start >= len(clean):
            break
    return blocks


def load_novel(path: str | Path) -> str:
    """加载小说文件

    支持 .txt 和 .md 格式。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    return path.read_text(encoding="utf-8")


def format_script_preview(script: dict, max_lines: int = 20) -> str:
    """格式化剧本预览（CLI 用）"""
    lines = []
    lines.append(f"[{script.get('meta', {}).get('scene_id', '')}] "
                  f"{script.get('meta', {}).get('scene_location', '')} - "
                  f"{script.get('meta', {}).get('scene_time', '')}")
    lines.append("")
    body = script.get("body", [])
    for item in body[:max_lines]:
        if "▲" in str(item.get("prefix", "")):
            lines.append(f"▲ {item.get('content', '')}")
        else:
            char = item.get("character", "")
            content = item.get("content", "")
            lines.append(f"● {char}：{content}")
    if len(body) > max_lines:
        lines.append(f"... (共 {len(body)} 行)")
    return "\n".join(lines)
