"""CLI 入口

Usage:
    aiproduce init --name "项目名" --source novel.txt
    aiproduce run --thin-slice --project <PROJECT_ID>
    aiproduce status
    aiproduce wizard
"""

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AIproduce - 商用级小说改剧本多智能体系统"""
    pass


@cli.command()
@click.option("--name", "-n", required=True, help="项目名称")
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="原著文件路径")
@click.option("--format", "-f", default="网剧", type=click.Choice(["短剧", "网剧", "漫剧"]), help="改编形式")
@click.option("--episodes", "-e", default=24, type=int, help="目标集数")
@click.option("--duration", "-d", default=45, type=int, help="单集时长（分钟）")
def init(name, source, format, episodes, duration):
    """初始化新项目"""
    from src.cli.commands import init_project
    init_project(name, source, format, episodes, duration)


@cli.command()
@click.option("--project", "-p", default=None, help="项目ID")
@click.option("--thin-slice", is_flag=True, help="运行最小可行验证链路")
@click.option("--full", is_flag=True, help="运行完整工作流")
@click.option("--novel", "-n", default=None, type=click.Path(exists=True), help="直接从小说文件运行（自动创建项目）")
@click.option("--name", default="QuickRun", help="自动创建项目时的项目名称")
def run(project, thin_slice, full, novel, name):
    """运行改编工作流"""
    from src.cli.commands import run_workflow

    if novel:
        # 从小说文件直接运行：先 init 再 thin-slice
        from src.cli.commands import init_project
        from src.agents.scheduler import SchedulerAgent

        agent = SchedulerAgent()
        result = agent.execute(
            action="init",
            project_name=name,
            source_file_path=novel,
        )
        project = result["project_id"]

    run_workflow(project, thin_slice=thin_slice or bool(novel), full=full)


@cli.command()
@click.option("--project", "-p", default=None, help="项目ID（不指定则列出所有）")
def status(project):
    """查看项目进度"""
    from src.cli.commands import show_status
    show_status(project)


@cli.command()
def wizard():
    """交互式项目配置向导"""
    from src.cli.commands import run_wizard
    run_wizard()


@cli.command()
@click.option("--project", "-p", default=None, help="项目ID")
def report(project):
    """输出成本统计报告"""
    from src.cli.commands import show_report
    show_report(project)


@cli.command()
@click.option("--port", "-p", default=7860, type=int, help="Web 服务端口")
@click.option("--share", is_flag=True, help="生成公网共享链接")
def web(port, share):
    """启动 Gradio Web UI"""
    try:
        from src.web.app import main as web_main
        import gradio as gr
        app = gr.Blocks()
        from src.web.app import create_ui
        app = create_ui()
        app.launch(
            server_name="127.0.0.1",
            server_port=port,
            share=share,
            show_error=True,
        )
    except ImportError:
        import sys
        print("❌ 请先安装 Gradio: pip install gradio")
        print("   或: pip install -e '.[dev]'")
        sys.exit(1)


if __name__ == "__main__":
    cli()
