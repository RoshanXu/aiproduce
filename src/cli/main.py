"""CLI 入口

Usage:
    aiproduce init --name "项目名" --source novel.txt
    aiproduce run --thin-slice
    aiproduce status
    aiproduce wizard
"""

import click
from pathlib import Path


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
@click.option("--project", "-p", default=None, help="项目ID（不指定则使用最近项目）")
@click.option("--thin-slice", is_flag=True, help="运行最小可行验证链路（Thin Slice）")
@click.option("--full", is_flag=True, help="运行完整21节点工作流")
def run(project, thin_slice, full):
    """运行改编工作流"""
    from src.cli.commands import run_workflow
    run_workflow(project, thin_slice=thin_slice, full=full)


@cli.command()
@click.option("--project", "-p", default=None, help="项目ID")
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


if __name__ == "__main__":
    cli()
