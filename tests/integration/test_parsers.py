from pathlib import Path

from app.parsers.generic_html import GenericHtmlParser
from app.parsers.generic_json import GenericJsonParser
from app.parsers.greenhouse import GreenhouseParser
from app.parsers.lever import LeverParser
from app.parsers.smartrecruiters import SmartRecruitersParser
from app.parsers.teamtailor import TeamtailorParser
from app.parsers.workable import WorkableParser
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
        job_url_template="https://jobs.zalando.com/en/jobs/{id}-{slug}",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].external_id == "2723255"
    assert jobs[0].location == "Berlin"
    assert jobs[0].url.startswith("https://jobs.zalando.com/en/jobs/2723255-")


def test_generic_json_parser_extracts_jobs_from_nested_payload():
    content = (FIXTURES / "generic_json.json").read_text(encoding="utf-8")
    parser = GenericJsonParser()
    source = SourceConfig(
        id="gj",
        company_name="Generic JSON",
        careers_url="https://api.example.com/jobs",
        parser_type="generic_json",
        parser_options={
            "jobs_path": "jobs.items",
            "fields": {
                "title": "jobTitle",
                "url": "jobUrl",
                "external_id": "jobId",
                "location": "meta.location",
                "description": "details.summary",
                "posted_at": "meta.publishedAt",
            },
        },
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "LLM Engineer"
    assert jobs[0].location == "Remote, Europe"


def test_smartrecruiters_parser_extracts_jobs_from_json():
    content = (FIXTURES / "smartrecruiters.json").read_text(encoding="utf-8")
    parser = SmartRecruitersParser()
    source = SourceConfig(
        id="sr",
        company_name="SmartRecruiters",
        careers_url="https://jobs.smartrecruiters.com/Example",
        parser_type="smartrecruiters",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].external_id == "sr-101"
    assert jobs[0].location == "Berlin, Germany, Data"


def test_teamtailor_parser_extracts_jobs_from_json():
    content = (FIXTURES / "teamtailor.json").read_text(encoding="utf-8")
    parser = TeamtailorParser()
    source = SourceConfig(
        id="tt",
        company_name="Teamtailor",
        careers_url="https://jobs.example.com",
        parser_type="teamtailor",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "Applied Scientist"
    assert jobs[0].url == "https://jobs.example.com/jobs/applied-scientist"


def test_workable_parser_extracts_jobs_from_json():
    content = (FIXTURES / "workable.json").read_text(encoding="utf-8")
    parser = WorkableParser()
    source = SourceConfig(
        id="wk",
        company_name="Workable",
        careers_url="https://apply.workable.com/example",
        parser_type="workable",
    )

    jobs = parser.parse(content, source)
    assert len(jobs) == 1
    assert jobs[0].title == "Computer Vision Engineer"
    assert jobs[0].location == "London, United Kingdom"
