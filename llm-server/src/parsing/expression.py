from .token import Emotion
from typing import cast

class Expression:
    """The standard Expression Object. Should never be used directly as it neither contains no valueable data nor can we make any statements about it."""
    def __str__(self) -> str:
        return 'Expression()'
    
    def __eq__(self, value: object) -> bool:
        return isinstance(self, value.__class__) and isinstance(value, self.__class__)

class SpeechExpression(Expression):
    """A Speech Expression. Represents a cut-off part of a speech that will be read by the TTS with in a certain emotional tone."""

    def __init__(self, emotion: Emotion, text: str):
        """Initializes the Speech Expression.
        
        Args:
            emotion (Emotion): The emotional tone that the text should be read in.
            text (str): The text that should be read.
        """
        self.emotion = emotion
        self.text = text
    
    def __str__(self) -> str:
        return f'SpeechExpression(emotion={self.emotion}, text="{self.text}")'

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value) and self.emotion == cast(SpeechExpression, value).emotion and self.text == cast(SpeechExpression, value).text
        
    
class PauseExpression(Expression):
    """A Pause Expression. Represents a pause inbetween speeches."""
    def __str__(self) -> str:
        return "PauseExpression()"
    
class MoveExpression(Expression):
    """A Move Expression. Saves a Movement-Command to some Exhibit."""

    def __init__(self, exhibit_key: str):
        self.exhibit_key = exhibit_key