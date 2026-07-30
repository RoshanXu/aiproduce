"""Gradio Web UI — 简易前端界面

提供：
1. 上传小说 → 自动运行 Thin Slice 链路
2. 查看解构结果（人物/世界观/时间线）
3. 预览生成剧本

Usage:
    python -m src.web.app
    # 或
    aiproduce web
"""

import json
import sys
from pathlib import Path

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False


class AIproduceWebUI:
    """AIproduce Gradio Web 界面"""

    def __init__(self):
        self.current_project_id = None
        self.current_project_dir = None

    # ─── 项目操作 ────────────────────────────────

    def init_and_run(self, project_name: str, novel_file, adaptation_format: str,
                     target_episodes: int, episode_duration: int, progress=gr.Progress()):
        """上传小说 → 初始化项目 → 运行 Thin Slice"""
        if novel_file is None:
            yield "❌ 请上传小说文件", "", "", "", ""
            return

        # 保存上传的文件
        progress(0.1, desc="保存上传文件...")
        upload_dir = Path("workspace/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        novel_path = upload_dir / Path(novel_file.name).name
        novel_path.write_bytes(Path(novel_file.name).read_bytes())

        # 初始化项目
        progress(0.2, desc="初始化项目...")
        from src.agents.scheduler import SchedulerAgent

        agent = SchedulerAgent()
        result = agent.execute(
            action="init",
            project_name=project_name,
            source_file_path=str(novel_path),
            adaptation_format=adaptation_format,
            target_episodes=target_episodes,
            episode_duration_min=episode_duration,
        )

        self.current_project_id = result["project_id"]
        self.current_project_dir = Path("workspace/projects") / self.current_project_id

        log_text = f"✅ 项目初始化完成\n"
        log_text += f"   项目ID: {self.current_project_id}\n"
        log_text += f"   项目名: {project_name}\n"
        log_text += f"   工作目录: {self.current_project_dir}\n"
        yield log_text, "", "", "", ""

        # 运行 Thin Slice
        progress(0.3, desc="运行 Thin Slice 链路...")
        yield log_text + "\n🔄 开始运行 Thin Slice 链路...\n", "", "", "", ""

        try:
            from src.workflow.runner import WorkflowRunner
            runner = WorkflowRunner()
            result = runner.run_thin_slice(self.current_project_id)

            log_text += "\n✅ Thin Slice 执行完成!\n"
            for key, value in result.items():
                if isinstance(value, (int, float, str)):
                    log_text += f"   {key}: {value}\n"

            # 生成验证报告
            report = runner._generate_validation_report(result)
            log_text += f"\n📊 验证报告:\n"
            for h in report.get("hypotheses", []):
                status = "✅" if h.get("status") == "PASS" else "❌"
                log_text += f"   {status} {h.get('id')}: {h.get('description', '')[:60]}\n"

        except Exception as e:
            log_text += f"\n❌ 执行失败: {e}\n"
            import traceback
            log_text += traceback.format_exc()

        yield log_text, "", "", "", ""

        # 加载结果
        progress(0.9, desc="加载结果...")
        char_text, world_text, timeline_text = self.load_assets()
        script_text = self.load_scripts()

        yield log_text, char_text, world_text, timeline_text, script_text

    # ─── 数据加载 ────────────────────────────────

    def load_assets(self):
        """加载资产库结果"""
        if not self.current_project_dir:
            return "请先运行项目", "请先运行项目", "请先运行项目"

        char_text = self._load_asset_file("characters.json")
        world_text = self._load_asset_file("world_settings.json")
        timeline_text = self._load_asset_file("timeline.json")
        return char_text, world_text, timeline_text

    def _load_asset_file(self, filename: str) -> str:
        """加载单个资产文件"""
        asset_path = self.current_project_dir / "assets" / filename
        if asset_path.exists():
            try:
                data = json.loads(asset_path.read_text(encoding="utf-8"))
                return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                pass

        # 也检查 work 目录
        for alt_path in self.current_project_dir.rglob(filename):
            try:
                data = json.loads(alt_path.read_text(encoding="utf-8"))
                return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return f"（尚未生成: {filename}）"

    def load_scripts(self):
        """加载剧本预览"""
        if not self.current_project_dir:
            return "请先运行项目"

        drafts_dir = self.current_project_dir / "work" / "drafts"
        if not drafts_dir.exists():
            return "（尚未生成剧本）"

        scripts = []
        for scene_file in sorted(drafts_dir.glob("*.json")):
            try:
                data = json.loads(scene_file.read_text(encoding="utf-8"))
                scripts.append(data)
            except Exception:
                continue

        if not scripts:
            return "（无剧本文件）"

        # 格式化为可读文本
        output = []
        for script in scripts[:10]:  # 最多显示10场
            meta = script.get("meta", {})
            output.append(f"{'='*60}")
            output.append(f"场次: {meta.get('scene_id', '?')}")
            output.append(f"地点: {meta.get('scene_location', '?')}")
            output.append(f"时间: {meta.get('scene_time', '?')}")
            output.append(f"人物: {meta.get('characters_in_scene', '?')}")
            output.append(f"{'='*60}")

            scene_desc = script.get("scene_description", {})
            if scene_desc.get("content"):
                output.append(f"\n【场景】\n{scene_desc['content'][:200]}")

            body = script.get("body", [])
            if body:
                output.append(f"\n【正文】(共{len(body)}条)")
                for item in body[:15]:  # 每场最多15条
                    prefix = item.get("prefix", "")
                    character = item.get("character", "")
                    content = item.get("content", "")
                    if character:
                        output.append(f"  {prefix} {character}: {content[:100]}")
                    else:
                        output.append(f"  {prefix} {content[:100]}")

            transition = script.get("transition", {})
            if transition.get("transition_type"):
                output.append(f"\n【转场】★ {transition['transition_type']}")

            output.append("")

        return "\n".join(output)

    def load_validation_reports(self):
        """加载校验报告"""
        if not self.current_project_dir:
            return "请先运行项目"

        validation_dir = self.current_project_dir / "work" / "validation"
        if not validation_dir.exists():
            return "（无校验报告）"

        reports = []
        for report_file in sorted(validation_dir.glob("*.json")):
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
                reports.append(data)
            except Exception:
                continue

        if not reports:
            return "（无校验报告）"

        output = []
        for r in reports:
            output.append(f"{'─'*50}")
            output.append(f"场景: {r.get('scene_id', '?')}")
            output.append(f"判定: {r.get('verdict', '?')}")
            blocking = r.get("blocking_issues", [])
            warnings = r.get("warning_issues", [])
            output.append(f"阻塞: {len(blocking)} | 警告: {len(warnings)}")

            for b in blocking[:3]:
                output.append(f"  ❌ {b.get('detail', str(b))[:80]}")
            for w in warnings[:3]:
                output.append(f"  ⚠️ {w.get('detail', str(w))[:80]}")

        return "\n".join(output)

    def refresh_all(self):
        """刷新所有 Tab"""
        char, world, timeline = self.load_assets()
        scripts = self.load_scripts()
        reports = self.load_validation_reports()
        return char, world, timeline, scripts, reports


def create_ui() -> gr.Blocks:
    """创建 Gradio UI"""
    web = AIproduceWebUI()

    with gr.Blocks(title="AIproduce - 小说改剧本") as app:
        gr.Markdown("""
        # 🎬 AIproduce — 小说改剧本智能体系统
        上传小说 → 自动运行 Thin Slice 链路 → 查看解构结果与剧本预览
        """)

        with gr.Tab("🚀 运行"):
            with gr.Row():
                with gr.Column(scale=1):
                    project_name = gr.Textbox(
                        label="项目名称", value="我的改编项目",
                        placeholder="输入项目名称"
                    )
                    novel_file = gr.File(
                        label="上传小说文件 (.txt/.md)",
                        file_types=[".txt", ".md", ".text"]
                    )
                    adaptation_format = gr.Dropdown(
                        label="改编形式",
                        choices=["网剧", "短剧", "漫剧"],
                        value="网剧"
                    )
                    with gr.Row():
                        target_episodes = gr.Slider(
                            label="目标集数", minimum=1, maximum=100,
                            value=24, step=1
                        )
                        episode_duration = gr.Slider(
                            label="单集时长（分钟）", minimum=1, maximum=120,
                            value=45, step=5
                        )
                    run_btn = gr.Button("▶️ 开始运行", variant="primary", size="lg")

                with gr.Column(scale=2):
                    log_output = gr.Textbox(
                        label="运行日志", lines=20, max_lines=30,
                        placeholder="点击「开始运行」启动 Thin Slice 链路..."
                    )

            run_btn.click(
                fn=web.init_and_run,
                inputs=[project_name, novel_file, adaptation_format,
                        target_episodes, episode_duration],
                outputs=[log_output, gr.Textbox(), gr.Textbox(),
                         gr.Textbox(), gr.Textbox()],
            )

        with gr.Tab("👤 人物资产"):
            with gr.Row():
                char_output = gr.Textbox(
                    label="人物资产库", lines=25, max_lines=40,
                    placeholder="运行项目后自动加载..."
                )

        with gr.Tab("🌍 世界观"):
            world_output = gr.Textbox(
                label="世界观设定", lines=25, max_lines=40,
                placeholder="运行项目后自动加载..."
            )

        with gr.Tab("⏱️ 时间线"):
            timeline_output = gr.Textbox(
                label="时间线与伏笔", lines=25, max_lines=40,
                placeholder="运行项目后自动加载..."
            )

        with gr.Tab("📝 剧本预览"):
            script_output = gr.Textbox(
                label="生成剧本", lines=30, max_lines=50,
                placeholder="运行项目后自动加载..."
            )

        with gr.Tab("✅ 校验报告"):
            report_output = gr.Textbox(
                label="校验报告", lines=20, max_lines=40,
                placeholder="运行项目后自动加载..."
            )

        # 加载已有项目
        with gr.Row():
            project_id_input = gr.Textbox(
                label="或加载已有项目ID（跳过运行，直接查看结果）",
                placeholder="输入项目ID，如 PRJ-20240730-xxxx"
            )
            load_btn = gr.Button("📂 加载项目")

        load_btn.click(
            fn=lambda pid: (
                setattr(web, "current_project_id", pid) or
                setattr(web, "current_project_dir", Path("workspace/projects") / pid) or
                web.refresh_all()
            ),
            inputs=[project_id_input],
            outputs=[char_output, world_output, timeline_output,
                     script_output, report_output],
        )

    return app


def main():
    """启动 Web UI"""
    if not HAS_GRADIO:
        print("❌ 请先安装 Gradio: pip install gradio")
        print("   或: pip install -e '.[dev]'")
        sys.exit(1)

    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
