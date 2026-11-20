"""Load and validate RSS feed configuration."""

from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

import yaml

FEEDS_FILE = Path(__file__).resolve().parent.parent / "feeds.yaml"


class FeedConfig(TypedDict):
    name: str
    url: str
    category: str


def load_feeds(path: str | Path = FEEDS_FILE) -> list[FeedConfig]:
    """Load feeds from YAML and validate their required fields."""
    config_path = Path(path)

    with config_path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or not isinstance(config.get("feeds"), list):
        raise ValueError(f"{config_path} must contain a 'feeds' list.")

    feeds = []

    for index, item in enumerate(config["feeds"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Feed {index} in {config_path} must be a mapping.")

        values = {}
        for field in ("name", "url", "category"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Feed {index} in {config_path} needs a non-empty "
                    f"'{field}' value."
                )
            values[field] = value.strip()

        parsed_url = urlsplit(values["url"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(
                f"Feed {index} in {config_path} has an invalid URL: "
                f"{values['url']!r}."
            )

        feeds.append(FeedConfig(**values))

    return feeds
