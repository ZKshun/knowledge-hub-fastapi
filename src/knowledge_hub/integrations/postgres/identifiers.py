from sqlalchemy import BigInteger, Text, cast, literal
from sqlalchemy.sql.elements import Cast


def bigint_parameter(value: str) -> Cast[int]:
    # Keep PostgreSQL's syntax/range and errors; Python int() accepts different
    # Unicode digits/whitespace and rejects valid PG16 radix prefixes.
    return cast(literal(value, type_=Text()), BigInteger())
