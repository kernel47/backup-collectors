from context import CollectionContext
from exceptions import ParsingError
from parsers import baseline, logstash, pamela


def parse_for_scope(
    context: CollectionContext,
    records: list[dict],
    asset: str | None = None,
) -> list[dict]:
    """Select the parser explicitly from the requested scope."""
    if context.scope == "pamela":
        return pamela.parse(context.data_type, records)
    if context.scope == "logstash":
        return logstash.parse(context.data_type, records, asset)
    if context.scope == "baseline":
        return baseline.parse(records)
    raise ParsingError(f"No parser configured for scope: {context.scope}")
