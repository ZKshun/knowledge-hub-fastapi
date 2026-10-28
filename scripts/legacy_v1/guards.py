from urllib.parse import urlsplit

TEST_DATABASE = "knowledge_hub_fastapi_test"


def validate_http_target(url: str) -> None:
    target = urlsplit(url)
    if (
        (target.scheme, target.hostname, target.port, target.path)
        not in {
            ("http", "127.0.0.1", 3101, ""),
            ("http", "localhost", 3101, ""),
        }
        or target.username
        or target.password
        or target.query
        or target.fragment
    ):
        raise ValueError("Capture requires isolated HTTP localhost:3101 without credentials")


def validate_database_targets(postgres_dsn: str, mongo_uri: str) -> None:
    for uri, schemes, port in (
        (postgres_dsn, {"postgres", "postgresql"}, 55432),
        (mongo_uri, {"mongodb"}, 57017),
    ):
        target = urlsplit(uri)
        if (
            target.scheme not in schemes
            or target.hostname not in {"127.0.0.1", "localhost"}
            or target.port != port
            or target.path != f"/{TEST_DATABASE}"
            or target.query
            or target.fragment
        ):
            raise ValueError("Capture requires isolated local databases and dedicated test ports")
