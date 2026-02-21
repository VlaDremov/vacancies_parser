from app.parsers.generic_html import GenericHtmlParser
from app.types import SourceConfig


def test_generic_parser_uses_anchor_job_card_href_when_no_inner_anchor():
    html = """
    <html>
      <body>
        <a class="job-card" href="/jobs/123">
          <h2 class="job-title">Senior Applied Scientist</h2>
          <p class="job-location">Berlin, Germany</p>
          <p class="job-desc">Applied Science & Research</p>
        </a>
      </body>
    </html>
    """

    source = SourceConfig(
        id="demo",
        company_name="Demo",
        careers_url="https://example.com/careers",
        parser_type="generic_html",
        selectors={
            "job_card": "a.job-card",
            "title": "h2.job-title",
            "location": "p.job-location",
            "description": "p.job-desc",
        },
    )

    parser = GenericHtmlParser()
    jobs = parser.parse(html, source)

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Applied Scientist"
    assert jobs[0].location == "Berlin, Germany"
    assert jobs[0].url == "https://example.com/jobs/123"
