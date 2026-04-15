from app.parsers.generic_html import GenericHtmlParser
from app.parsers.generic_json import GenericJsonParser
from app.parsers.greenhouse import GreenhouseParser
from app.parsers.lever import LeverParser
from app.parsers.smartrecruiters import SmartRecruitersParser
from app.parsers.teamtailor import TeamtailorParser
from app.parsers.workable import WorkableParser
from app.parsers.workday import WorkdayParser


PARSER_REGISTRY = {
    "greenhouse": GreenhouseParser(),
    "lever": LeverParser(),
    "workday": WorkdayParser(),
    "generic_html": GenericHtmlParser(),
    "generic_json": GenericJsonParser(),
    "smartrecruiters": SmartRecruitersParser(),
    "teamtailor": TeamtailorParser(),
    "workable": WorkableParser(),
}


def get_parser(parser_type: str):
    parser = PARSER_REGISTRY.get(parser_type)
    if parser is None:
        raise ValueError(f"Unknown parser type: {parser_type}")
    return parser
