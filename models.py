from dataclasses import dataclass, field


@dataclass
class Job:
    uid: str                 # globally unique key used for de-duplication
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    source: str = ""
    remote_flag: bool = False      # source explicitly says remote
    detail_url: str = ""           # optional URL to lazily fetch the description
    extra: dict = field(default_factory=dict)
