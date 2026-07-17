"""Responsible for communicating with the model"""

class DocumentSummarizer:
    def __init__(self, model):
        self.model= model

    def summarize(self, system_promt: str, user_prompt: str) -> str:
        pass