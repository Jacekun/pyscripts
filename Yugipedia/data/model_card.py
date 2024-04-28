from pydantic import BaseModel

class CardData(BaseModel):
    name: str
    passcode: int
    wikilink: str
    set_number: str
    rarity: str
    date_release: str
