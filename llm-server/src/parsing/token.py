from enum import Enum
from typing import cast

class Id(Enum):
    """The current ID list for the lexer. Types the token can be. The IDs can be split into various types.

    Attributes: Keywords:
        BEGIN (Id): The Token that should be at the beggining of a text.
        END (Id): The Token that should be at the end of a text.
        EMOTION (Id): A Token that should have `Token.emotion` set to a corresponding `Emotion`.
        MOVE (Id): This Token signals a Move-Command.

    Attributes: Symbols:
        LITERAL (Id): This Token type is fetched from reading `"`.
        SEMICOLON (Id): This Token type is fetched from reading `;`.
        LCHEVRON (Id): This Token type is fetched from reading `<`.
        RCHEVRON (Id): This Token type is fetched from reading `>`.
        LSQBRACKET (Id): This Token type is fetched from reading `[`.
        RSQBRACKET (Id): This Token type is fetched from reading `]`.

    Attributes: Other:
        IDENT (Id): This Token contains a general text area that could not be resolved into a Keyword or an Emotion. `Token.ident` should contain the text for this Token.
        EOF (Id): This Token type should be returned if the end of the input string is reached.

    """
    BEGIN = 0,
    EMOTION = 1,
    LITERAL = 2,
    IDENT = 3,
    SEMICOLON = 4,
    END = 5,
    LCHEVRON = 6,
    RCHEVRON = 7,
    EOF = 8,
    MOVE = 9,
    LSQBRACKET = 10,
    RSQBRACKET = 11,

class Emotion(Enum):
    """Represents the ways the speaker can sound later on when it speaks.

    Attributes:
        AMUSED (Emotion): The Speaker is amused.
        BORED (Emotion): The Speaker is bored.
        CALM (Emotion): The Speaker is calm.
        EXCITED (Emotion): The Speaker is excited.
        FRUSTRATED (Emotion): The Speaker is frustrated.
        HAPPY (Emotion): The Speaker is happy.
        SAD (Emotion): The Speaker is sad.
        WORRIED (Emotion): The Speaker is worried.
    """

    AMUSED = 0,
    BORED = 1,
    CALM = 2,
    EXCITED = 3,
    FRUSTRATED = 4,
    HAPPY = 5,
    SAD = 6,
    WORRIED = 7,

class Token:
    """
        Tokens represent a part of a String from a formal language input.
        They are used for easier handling later on in the Parser. As we do not need to worry about selecting just the right part of our string in that task.
    """

    def __init__(self, id: Id, ident: str = '', emotion: "Emotion | None" = None):
        """Creates a Token object.

        Arguments:
            id (Id): The ID of the token
            ident (str): The text of the identifier, if the token is an identifier token.
            emotion (Emotion | None): The emotion contained within the token, if the token is supposed to showcase an emotion.
        """
        self.id = id
        self.ident = ident
        self.emotion = emotion

    def ident_to_keyword(self) -> None:
        """Converts an identifier into an emotion or a keyword, if possible.
        
        Warning: Beware
            This mutates the attributes of the current Token, if the Token is a keyword.
        
        Raises:
            Exception: If the current Token is not an identifier.
        """
        keyword = self.get_keyword()
        if keyword is None:
            raise Exception(f'Can\'t convert Token to keyword. Expected: {Id.IDENT}. But got: {self.id}')
        else:
            self.id = cast(Token, keyword).id
            self.emotion = cast(Token, keyword).emotion
            self.ident = cast(Token, keyword).ident
    
    def get_keyword(self) -> "Token | None":
        """Creates a new Token object corresponding to the keyword, if possible.

        Returns:
            None (None): If the current token is not an identifier
            Token (Token): 
                The new Token object with added attributes, if the Token is an identifier.
                The `Token.emotion` parameter is set, if the identifier corresponds to an Emotion
                The `Token.ident` parameter is cleared, if the identifier is a Keyword.
        """
        if self.id != Id.IDENT:
            return None
        if self.ident in Emotion._member_names_:
            return Token(Id.EMOTION, emotion=cast(Emotion, Emotion._member_map_[self.ident]))
        elif self.ident in ['BEGIN', 'END', 'MOVE']:
            return Token(cast(Id, Id._member_map_[self.ident]))
        else:
            return self
