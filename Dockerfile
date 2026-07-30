# AIproduce Docker 镜像
#
# 构建:  docker build -t aiproduce .
# 运行:  docker run -p 7860:7860 -v aiproduce_workspace:/app/workspace aiproduce
# Web:   docker run -p 7860:7860 -v aiproduce_workspace:/app/workspace aiproduce web
# CLI:   docker run --rm -v aiproduce_workspace:/app/workspace aiproduce run --thin-slice --novel /app/tests/fixtures/sample_novel_chapter.md --name "测试"

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="AIproduce"
LABEL org.opencontainers.image.description="商用级小说改剧本多智能体系统"
LABEL org.opencontainers.image.version="0.1.0"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# 先拷贝依赖文件，利用 Docker 缓存层
COPY pyproject.toml .

# 只安装依赖（不安装项目本身，避免 editable 报错）
RUN pip install --no-cache-dir \
    langgraph>=0.2.0 \
    langchain>=0.3.0 \
    langchain-anthropic>=0.3.0 \
    langchain-openai>=0.3.0 \
    chromadb>=0.5.0 \
    sqlalchemy>=2.0.0 \
    pydantic>=2.0.0 \
    pyyaml>=6.0 \
    click>=8.0.0 \
    rich>=13.0.0 \
    tiktoken>=0.7.0 \
    jinja2>=3.0.0 \
    gradio>=5.0.0

# 拷贝项目源码
COPY --chown=appuser:appuser . .

# 安装项目包（非 editable 模式）
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || true

# 预下载 ChromaDB ONNX 模型（避免首次运行时下载）
RUN python -c "import chromadb; chromadb.PersistentClient(path='/tmp/chroma_init')" 2>/dev/null || true

# 创建数据卷目录
RUN mkdir -p /app/workspace/projects /app/workspace/uploads /app/workspace/logs \
    && chown -R appuser:appuser /app/workspace

USER appuser

# 默认暴露 Gradio Web UI 端口
EXPOSE 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 默认启动 Web UI
ENTRYPOINT ["python", "-m", "src.cli.main"]
CMD ["web", "--port", "7860"]
