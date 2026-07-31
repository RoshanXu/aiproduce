"""Gradio Web UI — 三阶段人工审核 + 设计感界面

Usage:
    python -m src.web.app
    aiproduce web
"""

import json
import os
import sys
from pathlib import Path

# 显式加载 .env（确保在 agent 导入前生效）
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

CUSTOM_CSS = """
.gradio-container { max-width: 1200px !important; }
.header-title { text-align: center; padding: 1.5rem 0 0.5rem; }
.header-title h1 {
    background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.5px;
}
.header-sub { text-align: center; color: #94a3b8; font-size: 0.95rem; margin-bottom: 1rem; }
.phase-steps { display: flex; justify-content: center; gap: 0; margin: 1rem 0; }
.phase-dot { width: 32px; height: 32px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
.phase-active { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; box-shadow: 0 0 12px rgba(99,102,241,0.4); }
.phase-done { background: #22c55e; color: #fff; }
.phase-pending { background: #334155; color: #64748b; border: 2px solid #475569; }
.phase-line { width: 48px; height: 2px; align-self: center; }
.phase-line-done { background: #22c55e; }
.phase-line-pending { background: #334155; }
.primary-btn { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; border: none !important; }
.success-btn { background: linear-gradient(135deg, #22c55e, #16a34a) !important; border: none !important; }
.review-btn { background: linear-gradient(135deg, #3b82f6, #2563eb) !important; border: none !important; }
.log-box textarea { font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    background: #0f172a !important; color: #e2e8f0 !important; font-size: 13px !important; }
.footer { text-align: center; color: #475569; font-size: 0.8rem; margin-top: 2rem; }
/* 卡片样式 */
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 14px 16px; transition: border-color 0.2s; }
.card:hover { border-color: #6366f1; box-shadow: 0 2px 8px rgba(99,102,241,0.1); }
.card-title { font-weight: 700; font-size: 1rem; color: #1e293b; margin-bottom: 8px; }
.card-row { display: flex; gap: 8px; margin: 4px 0; font-size: 0.9rem; color: #334155; }
.c-label { color: #6366f1; min-width: 56px; font-size: 0.8rem; font-weight: 600; }
.char-card { border-left: 3px solid #a78bfa; }
.world-card { border-left: 3px solid #22c55e; }
.time-card { border-left: 3px solid #f59e0b; }
.plan-card { border-left: 3px solid #3b82f6; }
.outline-card { border-left: 3px solid #ec4899; }
.script-card { border-left: 3px solid #8b5cf6; margin-bottom: 8px; }
.report-card { margin-bottom: 6px; }
.scene-body { margin: 8px 0; font-size: 0.95rem; line-height: 1.7; color: #334155; }
.scene-body p { margin: 2px 0; }
"""


class AIproduceWebUI:
    """三阶段审核 + 状态管理"""

    def __init__(self):
        self.project_id = None
        self.project_dir = None
        self.phase = 0  # 0=待开始, 1=资产库完成, 2=策划大纲完成, 3=全部完成
        self.current_novel_path = None
        self.current_params = {}

    # ─── 阶段 1: N01 → N03 ──────────────────────

    def phase1_init(self, project_name, novel_file, adaptation_format,
                    target_episodes, episode_duration, progress=gr.Progress()):
        """阶段1: 初始化 + 解构 + 资产库"""
        if novel_file is None:
            yield "❌ 请上传小说文件", "", "", "", "", "", "", "", gr.update(visible=False), gr.update(visible=False)
            return

        progress(0.1, desc="保存文件...")
        upload_dir = Path("workspace/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        novel_path = upload_dir / Path(novel_file.name).name
        novel_path.write_bytes(Path(novel_file.name).read_bytes())
        self.current_novel_path = str(novel_path)
        self.current_params = {
            "project_name": project_name,
            "adaptation_format": adaptation_format,
            "target_episodes": target_episodes,
            "episode_duration": episode_duration,
        }

        log = f"## 阶段 1/3：原著解构 + 资产库构建\n\n"
        log += f"📖 原著: {novel_path.name}\n"
        log += f"🎬 改编: {adaptation_format} | {target_episodes}集×{episode_duration}分钟\n"
        log += f"🤖 模型: {os.getenv('DEFAULT_MODEL', 'claude-sonnet-5')}\n\n"
        log += "⏳ 正在调用 DeepSeek 分析原著...\n"
        bs = gr.update(visible=False), gr.update(visible=False)
        yield log, "⏳ 等待中...", "⏳ 等待中...", "⏳ 等待中...", "", "", "", "", *bs

        try:
            from src.workflow.runner import WorkflowRunner
            runner = WorkflowRunner()
            result = runner.run_thin_slice(
                project_name=project_name,
                source_file_path=self.current_novel_path,
                adaptation_format=adaptation_format,
                target_episodes=target_episodes,
                episode_duration=episode_duration,
                model_name=os.getenv("DEFAULT_MODEL", "claude-sonnet-5"),
                stop_after="N03",
            )

            self.project_id = result["project_id"]
            self.project_dir = Path("workspace/projects") / self.project_id
            self.phase = 1

            results = result.get("results", {})
            n02 = results.get("N02", {})
            n03c = results.get("N03", {}).get("characters", {})
            n03w = results.get("N03", {}).get("world", {}).get("world", {})
            n03t = results.get("N03", {}).get("timeline", {}).get("timeline", {})
            # 保存到实例变量，后续阶段复用（卡片HTML格式）
            self._chars_json = self._cards_chars(n03c)
            self._world_json = self._cards_world(n03w)
            self._timeline_json = self._cards_timeline(n03t)

            log += f"\n✅ **阶段 1 完成！**\n\n"
            log += f"| 节点 | 产出 |\n|------|------|\n"
            log += f"| N02 解构 | {n02.get('chunk_count',0)} 语义块, {n02.get('chapter_count',0)} 章节 |\n"
            log += f"| N03 人物 | {n03c.get('total_characters',0)} 个角色 |\n"
            log += f"| N03 场景 | {len(n03w.get('core_scenes',[]))} 个 |\n"
            log += f"| N03 事件 | {len(n03t.get('main_timeline',[]))} 个 |\n"
            log += f"\n📂 项目ID: `{self.project_id}`\n"
            log += f"\n👉 **请切换到「人物资产」「世界观」「时间线」Tab 审核结果**\n"
            log += f"👉 审核通过后点击下方「审核资产库，继续策划」按钮\n"

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段1失败: {e}\n```\n{traceback.format_exc()}\n```"
            self._chars_json = self._world_json = self._timeline_json = ""

        btns = gr.update(visible=self.phase >= 1), gr.update(visible=self.phase >= 2)
        yield (log, getattr(self, '_chars_json', ''),
               getattr(self, '_world_json', ''),
               getattr(self, '_timeline_json', ''),
               "", "", "", "", *btns)

    # ─── 阶段 2: N04 → N07 ──────────────────────

    def phase2_planning(self, progress=gr.Progress()):
        """阶段2: 改编策划 + 分集大纲"""
        if self.phase < 1:
            yield "❌ 请先完成阶段1", "", "", "", "", "", "", "", gr.update(visible=False), gr.update(visible=False)
            return

        progress(0.1, desc="生成改编策划总纲...")
        log = "## 阶段 2/3：改编策划 + 分集大纲\n\n"
        log += "⏳ 正在生成改编策划总纲和分集大纲...\n"
        btns = gr.update(visible=self.phase >= 1), gr.update(visible=self.phase >= 2)
        yield log, getattr(self, '_chars_json', ''), getattr(self, '_world_json', ''), getattr(self, '_timeline_json', ''), "⏳ 等待中...", "", "", "", *btns

        try:
            from src.workflow.runner import WorkflowRunner
            runner = WorkflowRunner()
            result = runner.run_thin_slice(
                project_id=self.project_id,
                model_name=os.getenv("DEFAULT_MODEL", "claude-sonnet-5"),
                stop_after="N07",
            )

            self.phase = 2
            results = result.get("results", {})
            n04 = results.get("N04", {})
            n07 = results.get("N07", {})

            log += f"\n✅ **阶段 2 完成！**\n\n"
            bp = n04.get("blueprint", {})
            sell = bp.get("core_positioning", {}).get("one_line_sell", "")
            log += f"**策划定位**: {sell}\n\n"
            log += f"| 节点 | 产出 |\n|------|------|\n"
            log += f"| N04 策划 | 改编策划总纲 |\n"
            log += f"| N07 大纲 | {n07.get('total_episodes',0)} 集 |\n"
            log += f"\n👉 **请切换到「剧本预览」Tab 查看策划总纲**\n"
            log += f"👉 审核通过后点击下方「审核大纲，继续写剧本」按钮\n"

            self._plan_json = self._cards_plan(n04)
            self._outline_json = self._cards_outline(n07)

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段2失败: {e}\n```\n{traceback.format_exc()}\n```"
            self._plan_json = self._outline_json = ""

        btns = gr.update(visible=self.phase >= 1), gr.update(visible=self.phase >= 2)
        yield (log,
               getattr(self, '_chars_json', ''), getattr(self, '_world_json', ''), getattr(self, '_timeline_json', ''),
               getattr(self, '_plan_json', ''), getattr(self, '_outline_json', ''),
               "", "", *btns)

    # ─── 阶段 3: N09 → N14 ──────────────────────

    def phase3_script(self, progress=gr.Progress()):
        """阶段3: 场次拆分 + 剧本 + 三重校验"""
        if self.phase < 2:
            yield "❌ 请先完成阶段1和阶段2", "", "", "", "", "", "", "", gr.update(visible=False), gr.update(visible=False)
            return

        progress(0.1, desc="生成剧本...")
        log = "## 阶段 3/3：剧本生成 + 三重校验\n\n"
        log += "⏳ 正在拆分场次、生成剧本、执行校验...\n"
        btns = gr.update(visible=self.phase >= 1), gr.update(visible=self.phase >= 2)
        yield log, getattr(self, '_chars_json', ''), getattr(self, '_world_json', ''), getattr(self, '_timeline_json', ''), getattr(self, '_plan_json', ''), getattr(self, '_outline_json', ''), "⏳ 生成中...", "", *btns

        try:
            from src.workflow.runner import WorkflowRunner
            runner = WorkflowRunner()
            result = runner.run_thin_slice(
                project_id=self.project_id,
                model_name=os.getenv("DEFAULT_MODEL", "claude-sonnet-5"),
                stop_after="N14",
            )

            self.phase = 3
            results = result.get("results", {})
            n09 = results.get("N09", {})
            n11 = results.get("N11", [])
            n12 = results.get("N12", [])
            n13 = results.get("N13", [])
            n14 = results.get("N14", [])

            log += f"\n✅ **全部完成！**\n\n"
            log += f"| 节点 | 产出 |\n|------|------|\n"
            log += f"| N09 场次 | {n09.get('total_scenes',0)} 场 |\n"
            log += f"| N11 剧本 | {len(n11)} 场 |\n"
            log += f"| N12 人设校验 | {len(n12)} 份报告 |\n"
            log += f"| N13 时间线校验 | {len(n13)} 份报告 |\n"
            log += f"| N14 格式校验 | {len(n14)} 份报告 |\n"
            log += f"\n📂 项目ID: `{self.project_id}`\n"
            log += f"\n🎉 **全流程结束！切换到各 Tab 查看最终产出。**\n"

            # 格式化剧本为 HTML 卡片
            scripts_html = []
            for s in n11:
                meta = s.get("meta", {})
                sid = meta.get("scene_id", "?")
                loc = meta.get("scene_location", "?")
                scripts_html.append(f"<div class='card script-card'><div class='card-title'>📝 {sid} | 📍 {loc}</div>")
                desc = s.get("scene_description", {}).get("content", "")
                if desc: scripts_html.append(f"<p style='color:#64748b'>{desc[:300]}</p>")
                scripts_html.append("<div class='scene-body'>")
                for item in s.get("body", [])[:20]:
                    ch = item.get("character", "")
                    c = item.get("content", "")
                    prefix = item.get("prefix", "")
                    if ch:
                        scripts_html.append(f"<p><b style='color:#a78bfa'>{ch}</b>：{c}</p>")
                    elif prefix == "▲":
                        scripts_html.append(f"<p style='color:#64748b'>▲ {c}</p>")
                    else:
                        scripts_html.append(f"<p>{c}</p>")
                scripts_html.append("</div></div>")
            self._scripts_json = "".join(scripts_html)

            # 格式化校验报告为 HTML
            reports_html = []
            for r in (n12 + n13 + n14):
                v = r.get("verdict", "?")
                color = "#22c55e" if v == "PASS" else "#ef4444"
                reports_html.append(
                    f"<div class='card report-card' style='border-left:3px solid {color}'>"
                    f"<div class='card-title'>{r.get('scene_id','?')} — "
                    f"<span style='color:{color}'>{v}</span></div>")
                for b in r.get("blocking_issues", []):
                    reports_html.append(f"<p>❌ {b.get('detail',str(b))[:120]}</p>")
                for w in r.get("warning_issues", []):
                    reports_html.append(f"<p style='color:#f59e0b'>⚠️ {w.get('detail',str(w))[:120]}</p>")
                reports_html.append("</div>")
            self._reports_json = "".join(reports_html)

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段3失败: {e}\n```\n{traceback.format_exc()}\n```"
            self._scripts_json = self._reports_json = ""

        btns = gr.update(visible=self.phase >= 1), gr.update(visible=self.phase >= 2)
        yield (log,
               getattr(self, '_chars_json', ''), getattr(self, '_world_json', ''), getattr(self, '_timeline_json', ''),
               getattr(self, '_plan_json', ''), getattr(self, '_outline_json', ''),
               getattr(self, '_scripts_json', ''), getattr(self, '_reports_json', ''),
               *btns)

    # ─── 加载已有项目 ──────────────────────────

    def load_project(self, project_id):
        """通过项目ID加载历史数据"""
        if not project_id or not project_id.strip():
            return "", "", "", "", "", "", "", "", gr.update(visible=False), gr.update(visible=False)

        pid = project_id.strip()
        project_dir = Path("workspace/projects") / pid
        if not project_dir.exists():
            return (f"❌ 项目不存在: {pid}", "", "", "", "", "", "", "",
                    gr.update(visible=False), gr.update(visible=False))

        self.project_id = pid
        self.project_dir = project_dir
        self.phase = 3

        # 从 SQLite 读数据
        try:
            from src.db.engine import init_db, get_session
            from src.db.repository import (
                CharacterRepository, WorldRepository, TimelineRepository,
                ChunkRepository, SummaryRepository,
            )
            db_path = project_dir / "db.sqlite"
            if not db_path.exists():
                return (f"❌ 项目数据库不存在: {db_path}", "", "", "", "", "", "", "",
                        gr.update(visible=False), gr.update(visible=False))

            init_db(db_path)
            with get_session() as session:
                # 人物
                chars = CharacterRepository(session).list_by_project(pid)
                chars_data = [{
                    "name": c.name, "core_identity": c.core_identity,
                    "core_personality": c.core_personality, "speech_style": c.speech_style or "",
                    "asset": c.asset_json or {},
                } for c in chars]
                self._chars_json = self._cards_chars(chars_data)

                # 世界观
                world = WorldRepository(session).get_by_project(pid)
                self._world_json = self._cards_world(world.asset_json) if world and world.asset_json else ""

                # 时间线
                timeline = TimelineRepository(session).get_by_project(pid)
                self._timeline_json = self._cards_timeline(timeline.asset_json) if timeline and timeline.asset_json else ""

            # 策划大纲
            planning_dir = project_dir / "work" / "planning"
            self._plan_json = ""
            if planning_dir.exists():
                for f in sorted(planning_dir.glob("*.json")):
                    try:
                        self._plan_json = json.dumps(json.loads(f.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
                    except: pass

            outlines_dir = project_dir / "work" / "outlines"
            self._outline_json = ""
            if outlines_dir.exists():
                for f in sorted(outlines_dir.glob("*.json")):
                    try:
                        self._outline_json = json.dumps(json.loads(f.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
                    except: pass

            # 剧本及校验报告
            # 剧本及校验（HTML格式）
            scripts_parts = []
            drafts_dir = project_dir / "work" / "drafts"
            if drafts_dir.exists():
                for f in sorted(drafts_dir.glob("*.json")):
                    try:
                        d = json.loads(f.read_text(encoding="utf-8"))
                        meta = d.get("meta", {})
                        scripts_parts.append(
                            f"<div class='card script-card'><div class='card-title'>📝 {meta.get('scene_id','?')} | 📍 {meta.get('scene_location','?')}</div>")
                        desc = d.get("scene_description", {}).get("content", "")
                        if desc: scripts_parts.append(f"<p style='color:#64748b'>{desc[:300]}</p>")
                        for item in d.get("body", [])[:20]:
                            ch = item.get("character", "")
                            c = item.get("content", "")
                            if ch: scripts_parts.append(f"<p><b style='color:#a78bfa'>{ch}</b>：{c}</p>")
                            else: scripts_parts.append(f"<p style='color:#64748b'>▲ {c}</p>")
                        scripts_parts.append("</div>")
                    except: pass
            self._scripts_json = "".join(scripts_parts)

            reports_parts = []
            vdir = project_dir / "work" / "validation"
            if vdir.exists():
                for f in sorted(vdir.glob("*.json")):
                    try:
                        r = json.loads(f.read_text(encoding="utf-8"))
                        v = r.get("verdict", "?")
                        color = "#22c55e" if v == "PASS" else "#ef4444"
                        reports_parts.append(
                            f"<div class='card report-card' style='border-left:3px solid {color}'>"
                            f"<div class='card-title'>{r.get('scene_id','?')} — <span style='color:{color}'>{v}</span></div>")
                        for b in r.get("blocking_issues", []):
                            reports_parts.append(f"<p>❌ {b.get('detail',str(b))[:120]}</p>")
                        for w in r.get("warning_issues", []):
                            reports_parts.append(f"<p style='color:#f59e0b'>⚠️ {w.get('detail',str(w))[:120]}</p>")
                        reports_parts.append("</div>")
                    except: pass
            self._reports_json = "".join(reports_parts)

        except Exception as e:
            import traceback
            return (f"❌ 加载失败: {e}\n```\n{traceback.format_exc()}\n```",
                    "", "", "", "", "", "", "",
                    gr.update(visible=False), gr.update(visible=False))

        log = f"✅ 已加载项目: {pid}\n"
        log += f"   人物: {len(chars_data)} 个 | 工作目录: {project_dir}\n"
        return (log,
                self._chars_json, self._world_json, self._timeline_json,
                self._plan_json, self._outline_json,
                self._scripts_json, self._reports_json,
                gr.update(visible=True), gr.update(visible=True))

    def _format_scripts(self, project_dir):
        drafts = project_dir / "work" / "drafts"
        if not drafts.exists(): return ""
        parts = []
        for f in sorted(drafts.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                meta = d.get("meta", {})
                parts.append(f"## {meta.get('scene_id','?')} | {meta.get('scene_location','?')}\n\n")
                desc = d.get("scene_description", {}).get("content", "")
                if desc: parts.append(f"▲ {desc[:300]}\n\n")
                for item in d.get("body", [])[:20]:
                    ch = item.get("character", "")
                    c = item.get("content", "")
                    parts.append(f"{'**'+ch+'**：' if ch else ''}{c}\n\n")
                parts.append("\n---\n")
            except: pass
        return "".join(parts)

    def _format_reports(self, project_dir):
        vdir = project_dir / "work" / "validation"
        if not vdir.exists(): return ""
        parts = []
        for f in sorted(vdir.glob("*.json")):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
                parts.append(f"### {r.get('scene_id','?')} — {r.get('verdict','?')}\n")
                for b in r.get("blocking_issues", []):
                    parts.append(f"- ❌ {b.get('detail',str(b))[:100]}\n")
                for w in r.get("warning_issues", []):
                    parts.append(f"- ⚠️ {w.get('detail',str(w))[:100]}\n")
                parts.append("\n")
            except: pass
        return "".join(parts)

    # ─── 数据加载 ────────────────────────────────

    def _load_chars(self):
        return self._load_file("characters.json", "assets")

    def _load_world(self):
        return self._load_file("world_settings.json", "assets")

    def _load_timeline(self):
        return self._load_file("timeline.json", "assets")

    def _load_plan(self):
        if not self.project_dir:
            return ""
        for f in (self.project_dir / "work" / "planning").glob("*.json"):
            try:
                return json.dumps(json.loads(f.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
            except: pass
        return ""

    def _load_outline(self):
        if not self.project_dir:
            return ""
        outlines_dir = self.project_dir / "work" / "outlines"
        if outlines_dir.exists():
            files = sorted(outlines_dir.glob("*.json"))
            if files:
                try:
                    return json.dumps(json.loads(files[0].read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
                except: pass
        return ""

    def _load_scripts(self):
        if not self.project_dir:
            return ""
        drafts = self.project_dir / "work" / "drafts"
        if not drafts.exists():
            return ""
        parts = []
        for f in sorted(drafts.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                meta = d.get("meta", {})
                parts.append(f"## {meta.get('scene_id','?')} | {meta.get('scene_location','?')} | {meta.get('scene_time','?')}\n")
                desc = d.get("scene_description", {}).get("content", "")
                if desc:
                    parts.append(f"▲ {desc[:200]}\n\n")
                for item in d.get("body", [])[:20]:
                    ch = item.get("character", "")
                    prefix = item.get("prefix", "")
                    content = item.get("content", "")
                    line = f"**{ch}** {content}" if ch else f"{prefix} {content}"
                    parts.append(f"{line}\n\n")
                parts.append("\n---\n")
            except: pass
        return "".join(parts)

    def _load_reports(self):
        if not self.project_dir:
            return ""
        vdir = self.project_dir / "work" / "validation"
        if not vdir.exists():
            return ""
        parts = []
        for f in sorted(vdir.glob("*.json")):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
                parts.append(f"### {r.get('scene_id','?')} — {r.get('verdict','?')}\n")
                for b in r.get("blocking_issues", []):
                    parts.append(f"- ❌ {b.get('detail',str(b))[:100]}\n")
                for w in r.get("warning_issues", []):
                    parts.append(f"- ⚠️ {w.get('detail',str(w))[:100]}\n")
                parts.append("\n")
            except: pass
        return "".join(parts)

    # ─── HTML 卡片格式化 ────────────────────────

    def _cards_chars(self, data):
        """人物卡片 HTML"""
        if not data: return "<p style='color:#64748b'>暂无数据</p>"
        chars = data if isinstance(data, list) else data.get("characters", [])
        if not chars: return f"<p style='color:#64748b'>原始数据: {len(str(data))} 字符</p>"
        cards = []
        for c in chars:
            if isinstance(c, str): c = {"name": c}
            name = c.get("name", "?")
            identity = c.get("core_identity", c.get("identity", ""))
            personality = c.get("core_personality", c.get("personality", ""))
            speech = c.get("speech_style", "")
            goal = c.get("core_goal", c.get("goal", ""))
            asset = c.get("asset", {})
            if asset:
                identity = identity or asset.get("core_identity", "")
                personality = personality or asset.get("core_personality", "")
                speech = speech or asset.get("speech_style", "")
            fields = []
            if identity: fields.append(f"<span class='c-label'>身份</span><span>{identity}</span>")
            if personality: fields.append(f"<span class='c-label'>性格</span><span>{personality}</span>")
            if speech: fields.append(f"<span class='c-label'>语言</span><span>{speech}</span>")
            if goal: fields.append(f"<span class='c-label'>目标</span><span>{goal}</span>")
            if not fields:
                fields.append(f"<span>{c.get('core_identity', str(c)[:100])}</span>")
            cards.append(
                f"<div class='card char-card'><div class='card-title'>🎭 {name}</div>"
                + "".join(f"<div class='card-row'>{f}</div>" for f in fields)
                + "</div>")
        return f"<div class='card-grid'>{''.join(cards)}</div>"

    def _cards_world(self, data):
        """世界观卡片 HTML"""
        if not data: return "<p style='color:#64748b'>暂无数据</p>"
        basic = data.get("basic_settings", {})
        culture = data.get("culture_details", {})
        scenes = data.get("core_scenes", [])
        # 英文 key → 中文标签
        CN = {
            "era_background": "时代背景", "geography": "地理疆域", "core_factions": "核心势力",
            "social_hierarchy": "社会阶层", "universal_rules": "通用规则",
            "costume_rules": "服饰规制", "food_and_items": "饮食器物",
            "etiquette_and_titles": "礼仪称谓", "customs_and_institutions": "习俗制度",
        }
        cards = []
        # 基础设定
        items = []
        for k, v in basic.items():
            if v and v != "待补充":
                label = CN.get(k, k)
                if isinstance(v, list): v = "、".join(v)
                items.append(f"<div class='card-row'><span class='c-label'>{label}</span><span>{v}</span></div>")
        if items:
            cards.append("<div class='card world-card'><div class='card-title'>🌍 基础设定</div>"
                         + "".join(items) + "</div>")
        # 文化细节
        items = []
        for k, v in culture.items():
            if v and v != "待补充":
                label = CN.get(k, k)
                if isinstance(v, list): v = "、".join(v)
                items.append(f"<div class='card-row'><span class='c-label'>{label}</span><span>{v}</span></div>")
        if items:
            cards.append("<div class='card world-card'><div class='card-title'>📜 文化细节</div>"
                         + "".join(items) + "</div>")
        # 核心场景
        if scenes:
            s_items = []
            for s in scenes:
                if isinstance(s, dict):
                    s_items.append(f"<div class='card-row'><span class='c-label'>📍 {s.get('scene_name','?')}</span>"
                                   f"<span>{s.get('space_type','')} - {s.get('core_function','')}</span></div>")
                else:
                    s_items.append(f"<div class='card-row'>📍 {s}</div>")
            cards.append("<div class='card world-card'><div class='card-title'>🏠 核心场景</div>"
                         + "".join(s_items) + "</div>")
        if not cards:
            return f"<pre style='color:#64748b'>{json.dumps(data, ensure_ascii=False, indent=2)[:500]}</pre>"
        return f"<div class='card-grid'>{''.join(cards)}</div>"

    def _cards_timeline(self, data):
        """时间线卡片 HTML"""
        if not data: return "<p style='color:#64748b'>暂无数据</p>"
        events = data.get("main_timeline", data.get("events", []))
        foreshadows = data.get("foreshadow_table", [])
        cards = []
        for ev in (events or []):
            if isinstance(ev, str):
                cards.append(f"<div class='card time-card'><div class='card-title'>⏱️ {ev[:80]}</div></div>")
            elif isinstance(ev, dict):
                # 支持多种字段名
                t = ev.get("time_point", ev.get("time_label", ev.get("time", "?")))
                desc = ev.get("event_description", ev.get("description", ev.get("event", "")))
                conf = ev.get("time_confidence", "")
                loc = ev.get("location", "")
                chars = ev.get("involved_characters", ev.get("characters", []))
                if isinstance(chars, list): chars = "、".join(chars)
                cards.append(
                    f"<div class='card time-card'><div class='card-title'>⏱️ {t}"
                    + (f" <span style='font-size:0.75em;color:#64748b'>({conf})</span>" if conf else "")
                    + "</div>"
                    + (f"<div class='card-row'><span>{desc[:200]}</span></div>" if desc else "")
                    + (f"<div class='card-row'><span class='c-label'>地点</span><span>{loc}</span></div>" if loc else "")
                    + (f"<div class='card-row'><span class='c-label'>人物</span><span>{chars}</span></div>" if chars else "")
                    + "</div>")
        for fv in (foreshadows or []):
            if isinstance(fv, dict):
                status = fv.get("status", "")
                color = "#22c55e" if status == "resolved" else "#f59e0b" if status == "pending" else "#ef4444"
                cards.append(
                    f"<div class='card time-card' style='border-left:3px solid {color}'>"
                    f"<div class='card-title'>🔮 {fv.get('foreshadow_id','?')} "
                    f"<span style='color:{color};font-size:0.8em'>({status})</span></div>"
                    f"<div class='card-row'><span>{fv.get('plant_content', str(fv))[:200]}</span></div></div>")
        if not cards:
            return f"<pre style='color:#64748b;font-size:0.85em'>{json.dumps(data, ensure_ascii=False, indent=2)[:800]}</pre>"
        return f"<div class='card-grid'>{''.join(cards)}</div>"

    def _cards_plan(self, data):
        """策划总纲 HTML — 适配 LLM 产出的中文章节结构"""
        if not data: return "<p style='color:#64748b'>暂无数据</p>"
        bp = data.get("blueprint", data)
        root = bp.get("改编策划总纲", bp)
        parts = []
        for section_title, section_content in root.items():
            if not isinstance(section_content, dict): continue
            parts.append(f"<div class='card plan-card'><div class='card-title'>📌 {section_title}</div>")
            for k, v in section_content.items():
                if isinstance(v, list):
                    items_html = []
                    for item in v:
                        if isinstance(item, dict):
                            name = item.get("线名", item.get("角色", item.get("新角色", "")))
                            detail = item.get("内容", item.get("原因", item.get("功能", str(item))))
                            items_html.append(f"<li><b>{name}</b>：{detail}</li>")
                        else:
                            items_html.append(f"<li>{item}</li>")
                    parts.append(f"<div class='card-row'><span class='c-label'>{k}</span><ul style='margin:0;padding-left:16px'>{''.join(items_html)}</ul></div>")
                elif isinstance(v, dict):
                    sub_items = []
                    for sk, sv in v.items():
                        sub_items.append(f"<li><b>{sk}</b>：{sv}</li>")
                    parts.append(f"<div class='card-row'><span class='c-label'>{k}</span><ul style='margin:0;padding-left:16px'>{''.join(sub_items)}</ul></div>")
                else:
                    parts.append(f"<div class='card-row'><span class='c-label'>{k}</span><span>{v}</span></div>")
            parts.append("</div>")
        if not parts:
            return f"<pre style='color:#64748b;font-size:0.85em'>{json.dumps(bp, ensure_ascii=False, indent=2)[:1500]}</pre>"
        return "".join(parts)

    def _cards_outline(self, data):
        """分集大纲 HTML"""
        if not data: return "<p style='color:#64748b'>暂无数据</p>"
        episodes = data.get("episodes", data.get("outlines", []))
        if not episodes:
            return f"<pre style='color:#64748b'>{json.dumps(data, ensure_ascii=False, indent=2)[:500]}</pre>"
        cards = []
        for ep in episodes[:30]:
            if isinstance(ep, dict):
                cards.append(
                    f"<div class='card outline-card'><div class='card-title'>📺 {ep.get('episode_id','?')}</div>"
                    f"<div class='card-row'><span class='c-label'>冲突</span><span>{ep.get('core_conflict','?')[:100]}</span></div>"
                    f"<div class='card-row'><span class='c-label'>钩子</span><span>{ep.get('hook','?')[:100]}</span></div></div>")
        return f"<div class='card-grid'>{''.join(cards)}</div>" if cards else f"<pre>{str(episodes)[:1000]}</pre>"

    def _load_file(self, filename, subdir):
        if not self.project_dir:
            return ""
        path = self.project_dir / subdir / filename
        if path.exists():
            try:
                return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
            except: pass
        for alt in self.project_dir.rglob(filename):
            try:
                return json.dumps(json.loads(alt.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
            except: pass
        return ""


def create_ui() -> gr.Blocks:
    web = AIproduceWebUI()

    with gr.Blocks(title="AIproduce — 小说改剧本", css=CUSTOM_CSS,
                   theme=gr.themes.Ocean()) as app:

        # ── 标题 ──────────────────────────────
        gr.HTML("""
        <div class="header-title"><h1>🎬 AIproduce</h1></div>
        <div class="header-sub">小说 → 剧本 · AI 多智能体改编系统</div>
        """)

        # ── 运行 Tab ──────────────────────────
        with gr.Tab("🚀 运行控制"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 项目配置")
                    project_name = gr.Textbox(label="项目名称", value="我的改编项目")
                    novel_file = gr.File(label="上传小说 (.txt/.md)", file_types=[".txt", ".md"])
                    adaptation_format = gr.Dropdown(
                        label="改编形式", choices=["网剧", "短剧", "漫剧"], value="网剧")
                    with gr.Row():
                        target_episodes = gr.Slider(label="目标集数", minimum=1, maximum=100, value=24, step=1)
                        episode_duration = gr.Slider(label="单集时长(分钟)", minimum=1, maximum=120, value=45, step=5)

                    # 三阶段按钮
                    with gr.Group():
                        btn_phase1 = gr.Button("▶️ 阶段1：解构原著 + 构建资产库",
                                               variant="primary", size="lg", elem_classes="primary-btn")
                        btn_phase2 = gr.Button("🔍 审核资产库，继续策划 ➡️",
                                               variant="secondary", size="lg", elem_classes="review-btn",
                                               visible=False)
                        btn_phase3 = gr.Button("🔍 审核策划大纲，继续写剧本 ➡️",
                                               variant="secondary", size="lg", elem_classes="review-btn",
                                               visible=False)

                with gr.Column(scale=2):
                    gr.Markdown("### 📊 运行日志")
                    log_output = gr.Markdown(
                        value="👆 上传小说文件，配置参数，点击阶段1按钮开始",
                        elem_classes="log-box")

        # ── 结果 Tab ──────────────────────────
        with gr.Tab("👤 人物资产"):
            char_output = gr.HTML(label="人物资产库", value="<p style='color:#64748b'>阶段1完成后自动加载...</p>")

        with gr.Tab("🌍 世界观"):
            world_output = gr.HTML(label="世界观设定", value="<p style='color:#64748b'>阶段1完成后自动加载...</p>")

        with gr.Tab("⏱️ 时间线"):
            timeline_output = gr.HTML(label="时间线与伏笔", value="<p style='color:#64748b'>阶段1完成后自动加载...</p>")

        with gr.Tab("📋 策划大纲"):
            with gr.Row():
                with gr.Column():
                    plan_output = gr.HTML(label="改编策划总纲", value="<p style='color:#64748b'>阶段2完成后自动加载...</p>")
                with gr.Column():
                    outline_output = gr.HTML(label="分集大纲", value="<p style='color:#64748b'>阶段2完成后自动加载...</p>")

        with gr.Tab("📝 剧本预览"):
            script_output = gr.HTML(label="生成剧本", value="<p style='color:#64748b'>阶段3完成后自动加载...</p>")

        with gr.Tab("✅ 校验报告"):
            report_output = gr.HTML(label="校验报告", value="<p style='color:#64748b'>阶段3完成后自动加载...</p>")

        # ── 加载已有项目 ──────────────────────
        with gr.Row():
            with gr.Column(scale=3):
                project_id_input = gr.Textbox(
                    label="📂 加载已有项目（输入项目ID查看历史结果）",
                    placeholder="如 PROJ-20260730-1C5136")
            with gr.Column(scale=1):
                load_btn = gr.Button("📂 加载", variant="secondary")

        # ── 底部 ──────────────────────────────
        gr.HTML('<div class="footer">AIproduce v0.1.0 · AI 多智能体协作 · 人工审核关键节点</div>')

        # ── 事件绑定 ──────────────────────────

        outputs_10 = [log_output, char_output, world_output, timeline_output,
                      plan_output, outline_output, script_output, report_output,
                      btn_phase2, btn_phase3]

        btn_phase1.click(
            fn=web.phase1_init,
            inputs=[project_name, novel_file, adaptation_format, target_episodes, episode_duration],
            outputs=outputs_10)

        btn_phase2.click(fn=web.phase2_planning, outputs=outputs_10)

        btn_phase3.click(fn=web.phase3_script, outputs=outputs_10)

        load_btn.click(fn=web.load_project, inputs=[project_id_input], outputs=outputs_10)

    return app


def main():
    if not HAS_GRADIO:
        print("请先安装 Gradio: pip install gradio")
        sys.exit(1)
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)


if __name__ == "__main__":
    main()
