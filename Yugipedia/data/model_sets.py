from __future__ import annotations
from typing import Union, List, Dict
from pydantic import BaseModel, Field
from pydantic import TypeAdapter

class Printrequest(BaseModel):
    label: str
    key: str
    redi: str
    typeid: str
    mode: int
    format: Union[bool, str]

class ReleaseDate(BaseModel):
    timestamp: int
    raw: str

class Printouts(BaseModel):
    prefix: List[str] = Field(alias='Prefix')
    release_date: List[ReleaseDate] = Field(alias='Release date')

class Result(BaseModel):
    printouts: Printouts
    fulltext: str
    fullurl: str
    namespace: int
    exists: int
    displaytitle: str


class WikiSet(BaseModel):
    printrequests: List[Printrequest]
    results: Dict[str, Result]
    serializer: str
    version: int
    rows: int
    
    @staticmethod
    def fromJson(data) -> WikiSet:
        ta = TypeAdapter(WikiSet)
        m = ta.validate_python(data)
        return m
