from __future__ import annotations
from pydantic import BaseModel
from pydantic import TypeAdapter
from typing import List

class CardData(BaseModel):
    name: str
    passcode: int
    wikilink: str
    set_number: str
    rarity: str
    date_release: str

    @staticmethod
    def get_list_carddata(data: list[any]) -> list[CardData]:
        ta = TypeAdapter(list[CardData])
        m = ta.validate_python(data)
        return m
