from app.pagination import build_additional_page_urls
from app.types import SourceConfig


def test_query_param_pagination_generates_follow_up_pages():
    source = SourceConfig(
        id="wise",
        company_name="Wise",
        careers_url="https://wise.jobs/jobs",
        parser_type="generic_html",
        extra={
            "pagination": {
                "strategy": "query_param",
                "max_pages": 4,
                "page_param": "page",
            }
        },
    )

    urls = build_additional_page_urls(source)
    assert urls == [
        "https://wise.jobs/jobs?page=2",
        "https://wise.jobs/jobs?page=3",
        "https://wise.jobs/jobs?page=4",
    ]


def test_offset_limit_pagination_generates_offsets():
    source = SourceConfig(
        id="zalando",
        company_name="Zalando",
        careers_url="https://jobs.zalando.com/en/jobs",
        parser_type="generic_html",
        extra={
            "pagination": {
                "strategy": "offset_limit",
                "max_pages": 3,
                "limit": 15,
                "url_template": "https://jobs.zalando.com/search?q=&filters=%7B%7D&limit={limit}&offset={offset}",
            }
        },
    )

    urls = build_additional_page_urls(source)
    assert urls == [
        "https://jobs.zalando.com/search?q=&filters=%7B%7D&limit=15&offset=15",
        "https://jobs.zalando.com/search?q=&filters=%7B%7D&limit=15&offset=30",
    ]
