import os
from jinja2 import Environment, FileSystemLoader

from config import settings


def generate_report(job, traces) -> str:
    """
    Generate a PDF report for a completed job.
    Returns the path to the generated PDF file.
    """
    from weasyprint import HTML

    os.makedirs(settings.REPORT_DIR, exist_ok=True)

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report.html")

    html_content = template.render(job=job, traces=traces)

    output_path = os.path.join(settings.REPORT_DIR, f"report_{job.id}.pdf")
    HTML(string=html_content).write_pdf(output_path)

    return output_path
