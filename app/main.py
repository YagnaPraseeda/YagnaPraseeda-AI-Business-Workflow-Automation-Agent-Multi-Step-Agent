from dotenv import load_dotenv

load_dotenv()  # must run before any module that reads os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

# Import tool modules so their @registry.register decorators execute at startup
import app.tools.file_reader  # noqa: F401
import app.tools.data_analyzer  # noqa: F401
import app.tools.summarizer  # noqa: F401
import app.tools.report_generator  # noqa: F401

app = FastAPI(
    title="AI Workflow Automation Agent",
    description=(
        "A multi-step AI agent that interprets natural-language instructions "
        "and executes them using a dynamic tool-calling pipeline. "
        "Supports CSV analysis, text summarization, and structured report generation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["Workflow"])

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    return FileResponse("static/index.html")
