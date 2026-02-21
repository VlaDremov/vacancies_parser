from pathlib import Path

from app.parsers.generic_html import GenericHtmlParser
from app.parsers.greenhouse import GreenhouseParser
from app.parsers.lever import LeverParser
from app.parsers.workday import WorkdayParser
from app.types import SourceConfig

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parsers"


def test_greenhouse_parser_extracts_jobs():
    content = (FIXTURES / "greenhouse.html").read_text(encoding="utf-8")
    parser = GreenhouseParser()
    source = SourceConfig(
        id="gh",
        company_name="GH",
        careers_url="https://boards.greenhouse.io/example",
        parser_type="greenhouse",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "Machine Learning Engineer"


def test_lever_parser_extracts_jobs():
    content = (FIXTURES / "lever.html").read_text(encoding="utf-8")
    parser = LeverParser()
    source = SourceConfig(
        id="lv",
        company_name="LV",
        careers_url="https://jobs.lever.co/example",
        parser_type="lever",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "Data Scientist"


def test_workday_parser_extracts_jobs_from_json_blob():
    content = (FIXTURES / "workday.html").read_text(encoding="utf-8")
    parser = WorkdayParser()
    source = SourceConfig(
        id="wd",
        company_name="WD",
        careers_url="https://example.wd5.myworkdayjobs.com/en-US/example/jobs",
        parser_type="workday",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "Applied Scientist"


def test_generic_parser_extracts_jobs_using_selectors():
    content = (FIXTURES / "generic.html").read_text(encoding="utf-8")
    parser = GenericHtmlParser()
    source = SourceConfig(
        id="gen",
        company_name="GEN",
        careers_url="https://example.com",
        parser_type="generic_html",
        selectors={
            "job_card": ".job-card",
            "title": ".job-title",
            "link": "a",
            "location": ".job-location",
            "description": ".job-description",
        },
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "ML Ops Engineer"


def test_generic_parser_extracts_jobs_from_json_data_payload():
    content = """
    {
      "data": [
        {
          "id": "2723255",
          "title": "Senior Applied Scientist - CRM (All Genders)",
          "offices": ["Berlin"]
        }
      ]
    }
    """
    parser = GenericHtmlParser()
    source = SourceConfig(
        id="zal",
        company_name="Zalando",
        careers_url="https://jobs.zalando.com/en/jobs",
        parser_type="generic_html",
        extra={"json_job_url_template": "https://jobs.zalando.com/en/jobs/{id}-{slug}"},
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].external_id == "2723255"
    assert jobs[0].url.startswith("https://jobs.zalando.com/en/jobs/2723255-")
