"""CLI 命令实现（占位，阶段1-4逐步实现）"""

import click
from pathlib import Path


def init_project(name: str, source: str, format: str, episodes: int, duration: int):
    """初始化新项目"""
    click.echo(f"\n📂 创建项目: {name}")
    click.echo(f"   原著文件: {source}")
    click.echo(f"   改编形式: {format} | {episodes}集 × {duration}分钟")
    click.echo(f"\n⏳ 项目初始化功能将在阶段1实现")
    click.echo(f"   届时将支持: 创建工作区目录、配置模型参数、生成项目ID\n")


def run_workflow(project: str | None, thin_slice: bool = False, full: bool = False):
    """运行工作流"""
    if thin_slice:
        click.echo("\n🚀 运行 Thin Slice 验证链路")
        click.echo("   链路: N01→N02→N03→N04→N07→N09→N11→N12")
        click.echo(f"\n⏳ Thin Slice 功能将在阶段4实现\n")
    elif full:
        click.echo("\n🚀 运行完整21节点工作流")
        click.echo(f"\n⏳ 完整工作流功能将在阶段4实现\n")
    else:
        click.echo("\n请指定运行模式: --thin-slice 或 --full\n")


def show_status(project: str | None = None):
    """显示项目进度"""
    click.echo(f"\n📊 项目进度")
    click.echo(f"\n⏳ 进度查看功能将在阶段1实现\n")


def run_wizard():
    """交互式配置向导"""
    click.echo("\n🧙 项目配置向导")
    click.echo("=" * 40)

    name = click.prompt("项目名称", type=str)
    source = click.prompt("原著文件路径", type=str)
    format_choice = click.prompt(
        "改编形式",
        type=click.Choice(["短剧", "网剧", "漫剧"]),
        default="网剧",
    )
    episodes = click.prompt("目标集数", type=int, default=24)
    duration = click.prompt("单集时长（分钟）", type=int, default=45)

    click.echo(f"\n📋 配置确认:")
    click.echo(f"   项目: {name}")
    click.echo(f"   原著: {source}")
    click.echo(f"   改编: {format_choice} | {episodes}集 × {duration}分钟")
    if click.confirm("\n确认创建项目?"):
        init_project(name, source, format_choice, episodes, duration)


def show_report(project: str | None = None):
    """显示成本统计"""
    from src.utils.token_counter import token_counter
    token_counter.print_report()
