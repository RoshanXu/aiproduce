"""Gradio Web UI — 三阶段人工审核 + 设计感界面

Usage:
    python -m src.web.app
    aiproduce web
"""

import json
import os
import sys
from pathlib import Path

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
            yield "❌ 请上传小说文件", "", "", "", "", "", "", "", ""
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
        yield log, "⏳ 等待中...", "⏳ 等待中...", "⏳ 等待中...", "", "", "", "", ""

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

            log += f"\n✅ **阶段 1 完成！**\n\n"
            log += f"| 节点 | 产出 |\n|------|------|\n"
            log += f"| N02 解构 | {n02.get('chunk_count',0)} 语义块, {n02.get('chapter_count',0)} 章节 |\n"
            log += f"| N03 人物 | {n03c.get('total_characters',0)} 个角色 |\n"
            log += f"| N03 场景 | {len(n03w.get('core_scenes',[]))} 个 |\n"
            log += f"| N03 事件 | {len(n03t.get('main_timeline',[]))} 个 |\n"
            log += f"\n📂 项目ID: `{self.project_id}`\n"
            log += f"\n👉 **请切换到「人物资产」「世界观」「时间线」Tab 审核结果**\n"
            log += f"👉 审核通过后点击下方「审核资产库，继续策划」按钮\n"

            char_text = self._load_chars()
            world_text = self._load_world()
            timeline_text = self._load_timeline()

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段1失败: {e}\n```\n{traceback.format_exc()}\n```"
            char_text = world_text = timeline_text = ""

        yield log, char_text, world_text, timeline_text, "", "", "", "", ""

    # ─── 阶段 2: N04 → N07 ──────────────────────

    def phase2_planning(self, progress=gr.Progress()):
        """阶段2: 改编策划 + 分集大纲"""
        if self.phase < 1:
            yield "❌ 请先完成阶段1", "", "", "", "", "", "", "", ""
            return

        progress(0.1, desc="生成改编策划总纲...")
        log = "## 阶段 2/3：改编策划 + 分集大纲\n\n"
        log += "⏳ 正在生成改编策划总纲和分集大纲...\n"
        yield log, self._load_chars(), self._load_world(), self._load_timeline(), "⏳ 等待中...", "", "", "", ""

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

            plan_text = self._load_plan()
            outline_text = self._load_outline()

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段2失败: {e}\n```\n{traceback.format_exc()}\n```"
            plan_text = outline_text = ""

        yield log, self._load_chars(), self._load_world(), self._load_timeline(), plan_text, outline_text, "", "", ""

    # ─── 阶段 3: N09 → N14 ──────────────────────

    def phase3_script(self, progress=gr.Progress()):
        """阶段3: 场次拆分 + 剧本 + 三重校验"""
        if self.phase < 2:
            yield "❌ 请先完成阶段1和阶段2", "", "", "", "", "", "", "", ""
            return

        progress(0.1, desc="生成剧本...")
        log = "## 阶段 3/3：剧本生成 + 三重校验\n\n"
        log += "⏳ 正在拆分场次、生成剧本、执行校验...\n"
        yield log, self._load_chars(), self._load_world(), self._load_timeline(), self._load_plan(), self._load_outline(), "⏳ 生成中...", "", ""

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

            script_text = self._load_scripts()
            validation_text = self._load_reports()

        except Exception as e:
            import traceback
            log += f"\n❌ 阶段3失败: {e}\n```\n{traceback.format_exc()}\n```"
            script_text = validation_text = ""

        yield (log, self._load_chars(), self._load_world(), self._load_timeline(),
               self._load_plan(), self._load_outline(), script_text, validation_text, "")

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
            char_output = gr.Textbox(label="人物资产库", lines=25, max_lines=40,
                                     placeholder="阶段1完成后自动加载...")

        with gr.Tab("🌍 世界观"):
            world_output = gr.Textbox(label="世界观设定", lines=25, max_lines=40,
                                      placeholder="阶段1完成后自动加载...")

        with gr.Tab("⏱️ 时间线"):
            timeline_output = gr.Textbox(label="时间线与伏笔", lines=25, max_lines=40,
                                         placeholder="阶段1完成后自动加载...")

        with gr.Tab("📋 策划大纲"):
            with gr.Row():
                with gr.Column():
                    plan_output = gr.Textbox(label="改编策划总纲", lines=25, max_lines=40,
                                             placeholder="阶段2完成后自动加载...")
                with gr.Column():
                    outline_output = gr.Textbox(label="分集大纲", lines=25, max_lines=40,
                                                placeholder="阶段2完成后自动加载...")

        with gr.Tab("📝 剧本预览"):
            script_output = gr.Textbox(label="生成剧本", lines=30, max_lines=50,
                                       placeholder="阶段3完成后自动加载...")

        with gr.Tab("✅ 校验报告"):
            report_output = gr.Textbox(label="校验报告", lines=20, max_lines=40,
                                       placeholder="阶段3完成后自动加载...")

        # ── 底部 ──────────────────────────────
        gr.HTML('<div class="footer">AIproduce v0.1.0 · AI 多智能体协作 · 人工审核关键节点</div>')

        # ── 事件绑定 ──────────────────────────

        all_outputs = [log_output, char_output, world_output, timeline_output,
                       plan_output, outline_output, script_output, report_output, btn_phase2, btn_phase3]

        # 阶段1: 开始 → 资产库
        def on_phase1(*args):
            for out in web.phase1_init(*args):
                # out has 9 elements but we need 10 (btn_phase2, btn_phase3)
                yield (*out, gr.update(visible=web.phase >= 1), gr.update(visible=web.phase >= 2))
        btn_phase1.click(
            fn=on_phase1,
            inputs=[project_name, novel_file, adaptation_format, target_episodes, episode_duration],
            outputs=[log_output, char_output, world_output, timeline_output,
                     plan_output, outline_output, script_output, report_output,
                     btn_phase2, btn_phase3],
        )

        # 阶段2: 审核资产 → 策划大纲
        def on_phase2():
            for out in web.phase2_planning():
                yield (*out, gr.update(visible=web.phase >= 1), gr.update(visible=web.phase >= 2))
        btn_phase2.click(
            fn=on_phase2,
            inputs=[],
            outputs=[log_output, char_output, world_output, timeline_output,
                     plan_output, outline_output, script_output, report_output,
                     btn_phase2, btn_phase3],
        )

        # 阶段3: 审核大纲 → 剧本
        def on_phase3():
            for out in web.phase3_script():
                yield (*out, gr.update(visible=web.phase >= 1), gr.update(visible=web.phase >= 2))
        btn_phase3.click(
            fn=on_phase3,
            inputs=[],
            outputs=[log_output, char_output, world_output, timeline_output,
                     plan_output, outline_output, script_output, report_output,
                     btn_phase2, btn_phase3],
        )

    return app


def main():
    if not HAS_GRADIO:
        print("请先安装 Gradio: pip install gradio")
        sys.exit(1)
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)


if __name__ == "__main__":
    main()
