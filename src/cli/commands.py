"""CLI 命令实现"""

import click
from pathlib import Path


def init_project(name: str, source: str, format: str, episodes: int, duration: int):
    """初始化新项目并运行 N01"""
    from src.agents.scheduler import SchedulerAgent

    agent = SchedulerAgent()
    result = agent.execute(
        action="init",
        project_name=name,
        source_file_path=source,
        adaptation_format=format,
        target_episodes=episodes,
        episode_duration=duration,
    )

    project_id = result["project_id"]
    print(f"\n✅ 项目创建成功!")
    print(f"   ID:     {project_id}")
    print(f"   名称:   {name}")
    print(f"   字数:   {result['total_words']:,}")
    print(f"   工作区: {result['workspace_dir']}")
    print(f"\n💡 下一步: aiproduce run --thin-slice --project {project_id}")


def run_workflow(project: str | None = None, thin_slice: bool = False, full: bool = False):
    """运行工作流"""
    if thin_slice:
        # 如果有 project_id，则从数据库加载配置后继续运行
        # 否则需要提供 source 文件
        if project:
            _continue_thin_slice(project)
        else:
            click.echo("\n请指定项目ID: --project <PROJECT_ID>")
            click.echo("或使用 aiproduce init 创建新项目后运行")
            click.echo("或使用 aiproduce run --thin-slice --novel <文件路径> 从小说文件直接开始\n")
    elif full:
        click.echo("\n🚀 运行完整21节点工作流")
        click.echo("⏳ 完整工作流功能将在阶段4实现\n")
    else:
        click.echo("\n请指定运行模式: --thin-slice 或 --full\n")


def _continue_thin_slice(project_id: str):
    """从已有项目继续运行 Thin Slice"""
    from src.db.engine import init_db, get_session
    from src.db.repository import ProjectRepository
    from pathlib import Path

    db_path = Path("workspace/projects") / project_id / "db.sqlite"
    if not db_path.exists():
        click.echo(f"\n❌ 项目不存在: {project_id}")
        return

    init_db(db_path)
    with get_session() as session:
        repo = ProjectRepository(session)
        record = repo.get(project_id)
        if not record:
            click.echo(f"\n❌ 项目记录不存在: {project_id}")
            return

        config = record.config_json

    # 获取项目配置
    source_file = config.get("source_file_path", "")
    project_name = config.get("project_name", "")
    adaptation_format = config.get("adaptation_format", "网剧")
    target_episodes = config.get("target_episodes", 24)
    episode_duration = config.get("episode_duration_min", 45)
    genre = config.get("genre", "古装")
    model_name = config.get("model_name", "claude-sonnet-5")

    if not source_file or not Path(source_file).exists():
        click.echo(f"\n❌ 原著文件不存在: {source_file}")
        return

    # 运行 Thin Slice
    from src.workflow.runner import WorkflowRunner

    runner = WorkflowRunner()
    runner.run_thin_slice(
        project_name=project_name,
        source_file_path=source_file,
        adaptation_format=adaptation_format,
        target_episodes=target_episodes,
        episode_duration=episode_duration,
        genre=genre,
        model_name=model_name,
    )


def show_status(project: str | None = None):
    """显示项目进度"""
    if not project:
        # 列出所有项目
        workspace = Path("workspace/projects")
        if workspace.exists():
            projects = list(workspace.iterdir())
            if projects:
                click.echo(f"\n📂 共 {len(projects)} 个项目:\n")
                for p in sorted(projects, key=lambda x: x.name, reverse=True):
                    summary_file = p / "work" / "deconstruction" / "phase1_summary.json"
                    status = "✅ 已解构" if summary_file.exists() else "📄 已创建"
                    click.echo(f"  {p.name}  {status}")
            else:
                click.echo("\n📂 暂无项目\n")
        else:
            click.echo("\n📂 暂无项目\n")
        return

    # 详细状态
    workspace = Path("workspace/projects") / project
    if not workspace.exists():
        click.echo(f"\n❌ 项目不存在: {project}")
        return

    click.echo(f"\n📊 项目状态: {project}")

    # 检查各阶段产出
    checks = [
        ("N01 项目初始化", (workspace / "db.sqlite").exists()),
        ("N02 原著解构", (workspace / "work" / "deconstruction" / "global_summary.json").exists()),
        ("N03 资产库", (workspace / "assets" / "characters" / "v1.0.json").exists()),
        ("N04 改编策划", (workspace / "work" / "planning").exists()),
        ("N07 分集大纲", (workspace / "work" / "outlines").exists()),
        ("N11 剧本生成", (workspace / "work" / "drafts").exists()),
    ]

    for name, done in checks:
        icon = "✅" if done else "⏳"
        click.echo(f"  {icon} {name}")


def run_wizard():
    """交互式项目配置向导"""
    click.echo("\n🧙 AIproduce 项目配置向导")
    click.echo("=" * 40)

    name = click.prompt("项目名称", type=str)
    source = click.prompt("原著文件路径", type=str)

    # 检查文件
    if not Path(source).exists():
        click.echo(f"⚠️  文件不存在: {source}")
        if not click.confirm("继续创建？"):
            return

    format_choice = click.prompt(
        "改编形式",
        type=click.Choice(["短剧", "网剧", "漫剧"]),
        default="网剧",
    )
    episodes = click.prompt("目标集数", type=int, default=24)
    duration = click.prompt("单集时长（分钟）", type=int, default=45)
    genre = click.prompt(
        "题材类型",
        type=click.Choice(["古装", "现代", "架空", "都市", "悬疑", "科幻", "言情"]),
        default="古装",
    )

    click.echo(f"\n📋 配置确认:")
    click.echo(f"   项目: {name}")
    click.echo(f"   原著: {source}")
    click.echo(f"   改编: {format_choice} | {episodes}集 × {duration}分钟")
    click.echo(f"   题材: {genre}")

    if click.confirm("\n确认创建项目?"):
        init_project(name, source, format_choice, episodes, duration)

        if click.confirm("\n是否立即运行 N01→N02→N03 解构分析?"):
            # 运行完整 Thin Slice 阶段1
            from src.workflow.runner import WorkflowRunner
            runner = WorkflowRunner()
            runner.run_thin_slice(
                project_name=name,
                source_file_path=source,
                adaptation_format=format_choice,
                target_episodes=episodes,
                episode_duration=duration,
                genre=genre,
            )


def show_report(project: str | None = None):
    """显示成本统计"""
    from src.utils.token_counter import token_counter
    token_counter.print_report()
