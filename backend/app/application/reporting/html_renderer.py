"""HTML Rendering Service for Executive Security Reports."""

from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from app.application.reporting.dto import ExecutiveReportDataPayload

logger = structlog.get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class HTMLRendererService:
    """Service rendering Jinja2 HTML executive security posture reports."""

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    def render_html_report(self, payload: ExecutiveReportDataPayload) -> str:
        """Render consolidated ExecutiveReportDataPayload into styled HTML string."""
        css_path = TEMPLATES_DIR / "style.css"
        css_content = ""
        if css_path.exists():
            css_content = css_path.read_text(encoding="utf-8")

        template = self.env.get_template("executive_report.html")
        rendered = template.render(
            data=payload.model_dump(),
            css_styles=css_content,
        )
        logger.info(
            "Executive report HTML rendered successfully",
            report_id=payload.metadata.id,
            org_id=payload.metadata.organization_id,
            html_length=len(rendered),
        )
        return rendered
