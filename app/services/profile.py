from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class UserProfile:
    user_name: str = "Default User"
    full_name: str = ""
    company_name: str = ""
    email: str = ""

class ProfileStore:
    def __init__(self,path:Path):
        self.path=path;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():self.save(UserProfile())
    def load(self):
        try:return UserProfile(**json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError,ValueError,TypeError,json.JSONDecodeError):return UserProfile()
    def save(self,profile:UserProfile):
        temp=self.path.with_suffix(".tmp");temp.write_text(json.dumps(asdict(profile),indent=2),encoding="utf-8");temp.replace(self.path)

