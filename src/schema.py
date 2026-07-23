from typing import Literal 
from pydantic import BaseModel, ConfigDict, Field
SUMMARY_STYLE= Literal["bullets", "executive", "technical"] # Prevent the model from returning unsupported styles
SUMMARY_VERSION= Literal["v1", "v2", "v3"]

class SummaryOutput(BaseModel):
    model_config= ConfigDict(extra="forbid") # Rejects unexpected fields.

    title: str = Field(min_length=1) # Prevents empty titles, overviews, key points 
    style: SUMMARY_STYLE
    overview: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    risks_or_limitations: list[str] 

