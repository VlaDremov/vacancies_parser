from app.fetcher import _detect_blocked


def test_detect_blocked_does_not_flag_recaptcha_or_cloudflare_scripts():
    html = """
    <html>
      <head><title>Careers</title></head>
      <body>
        <script src="https://www.google.com/recaptcha/api.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/gsap.min.js"></script>
      </body>
    </html>
    """

    assert _detect_blocked(content=html, status_code=200) is None


def test_detect_blocked_flags_known_challenge_title():
    html = "<html><head><title>Just a moment...</title></head><body></body></html>"
    reason = _detect_blocked(content=html, status_code=200)

    assert reason is not None
    assert reason.startswith("title:")


def test_detect_blocked_flags_http_block_status_codes():
    html = "<html><head><title>Careers</title></head><body></body></html>"
    assert _detect_blocked(content=html, status_code=403) == "http_403"
