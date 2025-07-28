from typing import List
from .lexer import Lexer
from .token import *
from .expression import *

class ParseException(Exception):
    pass

class ResultException(Exception):
    pass

class Parser:

    def __init__(self, lexer: Lexer | str, max_words_between_pause : int = 16, max_emotions_between_pause : int = 3):
        """Initializes the Parser.
        
        Args:
            lexer (Lexer | str): The Lexer itself or a string that will be fed into a new Lexer.
            max_words_between_pause (int): If we perform a result analysis, this will be the maximum amount of words we allow between pauses such that the TTS stops yapping.
            max_emotions_between_pause (int): If we perform a result analysis, this will be the maximum amount of emotion switches we allow between pauses.
        """
        self.max_words_between_pause = max_words_between_pause
        self.max_emotions_between_pause = max_emotions_between_pause
        if isinstance(lexer, Lexer):
            self.lexer = lexer
        else:
            self.lexer = Lexer(lexer)

    def _lookahead(self, id: Id) -> bool:
        """Checks if the next token has a specific Id without consuming it or throwing an error if it isn't the case.

        Args:
            id (Id): The expected Id to match the current token against.
        
        Returns:
            is_correct_token (bool): Does the current Token match our expected Id?
        """
        if self.lexer.current_token.id == Id.IDENT: # type: ignore
            return self.lexer.current_token.get_keyword().id == id # type: ignore
        
        return self.lexer.current_token.id == id # type: ignore

    def _expect(self, id: Id):
        """Checks if the next token has a specific Id and consumes it in the process.

        Args:
            id (Id): The expected Id to match the current token against.
        
        Raises:
            Exception: If the next Token does not match the specific Id.
        """
        if not self._lookahead(id):
            self._error(id, cast(Token, self.lexer.current_token).id)
        
        self.lexer.next_token()

    def _expect_ident(self) -> str:
        """Checks if the next token is an Identifier, consuming it in the process.
        
        Raises:
            Exception: If the next Token does not match the specific Id.
        
        Returns:
            text (str): The Identifier text.
        """
        if not self._lookahead(Id.IDENT):
            self._error(Id.IDENT, cast(Token, self.lexer.current_token).id)
        text = cast(Token, self.lexer.current_token).ident
        self.lexer.next_token()
        return text

    def _expect_emotion(self) -> Emotion:
        """Checks if the next token is of type Emotion, consuming it in the process.

        Raises:
            Exception: If the next Token does not match the specific Id.
        
        Returns:
            emotion (Emotion): The Emotion stored in the Token.
        """
        if not self._lookahead(Id.EMOTION):
            self._error(Id.EMOTION, self.lexer.current_token.id) # type: ignore
        cast(Token, self.lexer.current_token).ident_to_keyword()
        emotion = cast(Token, self.lexer.current_token).emotion
        self.lexer.next_token()
        return cast(Emotion, emotion)
    
    def _error(self, expected: Id, got: Id):
        """Helper method that throws an error for unexpected Tokens.

        Args:
            expected (Id): The expected Token Id
            got (Id): The actual Token Id
        
        Raises:
            Exception: If this method is called.
        """
        raise ParseException(f'Unerwartetes Token (erwartet: {expected}, aber bekommen: {got}. Zeile: {self.lexer.line}, Spalte: {self.lexer.column})')
    
    def parse(self, result_analysis: bool = False) -> List[Expression]:
        """Executes the `Start` rule of the EBNF-Grammar. Collects all Expressions into a list.

        Args:
            result_analysis (bool): Should it perform a result analysis after collecting all the Expressions into a list?

        Returns:
            expressions (List[Expression]): The expressions that could've been collected from the Parser.
        
        Raises:
            Exception: If the Syntax does not match the Grammar.
        """
        self.lexer.next_token()
        self._expect(Id.BEGIN)

        if self._lookahead(Id.LSQBRACKET):
            self.lexer.next_token()
            self._expect(Id.MOVE)
            self._expect(Id.RSQBRACKET)
            text = self._literal()
            sequence = [MoveExpression(text)]
        else:
            emotion = self._emotion()
            text = self._literal()
            sequence : list[Expression] = [SpeechExpression(emotion, text)]
            
            while not self._lookahead(Id.END) and not self._lookahead(Id.EOF):
                
                if self._lookahead(Id.SEMICOLON):
                    self.lexer.next_token()
                    sequence.append(PauseExpression())
                emotion = self._emotion()
                text = self._literal()
                sequence.append(SpeechExpression(emotion, text))
        self._expect(Id.END)
        
        if result_analysis:
            self._result_analysis(sequence)
        return sequence
    
    def _emotion(self) -> Emotion:
        """Executes the `Emotion` rule of the EBNF-Grammar.

        Returns:
            emotion (Emotion): The Emotion that was found.
        """
        self._expect(Id.LCHEVRON)
        emotion = self._expect_emotion()
        self._expect(Id.RCHEVRON)
        return emotion

    def _literal(self) -> str:
        """Executes the `Literal` rule of the EBNF-Grammar.
        
        Returns:
            text (str): The Text that was found inbetween the literal-symbols.
        """
        self._expect(Id.LITERAL)
        text = self._expect_ident()
        self._expect(Id.LITERAL)
        return text
    
    def _result_analysis(self, sequence: List[Expression]):
        """Performs a result analysis on the speech sequence.

        A result analysis consists of checking certain data between PauseExpressions.

        We currently track two things:
        
        - Count of emotions between pauses
        
        - Count of words between pauses.

        If a certain threshold, that is set in the constructor, gets overstepped, this method raises an Exception, telling the LLM how to recalculate the answer.

        Args:
            sequence (List[Expression]): The sequence to perform a result analysis on.
        
        Examples: Example
            >>> parser = Parser('BEGIN <HAPPY> "I love my life so much and I can\\'t stop yapping about how much I love my life." <FRUSTRATED> "Woah!" END')
            >>> result = parser.parse(result_analysis=True)
            Error: Too many words between pauses.

            >>> parser = Parser('BEGIN <HAPPY> "Can\\'t" <FRUSTRATED> "decide" <BORED> "how" <CALM> "I" <SAD> "feel!" END')
            >>> result = parser.parse(result_analysis=True)
            Error: Too many emotions between pauses.
        """
        emotion_stack = []
        word_count = 0
        for i in range(0, len(sequence)):
            expr = sequence[i]
            if isinstance(expr, PauseExpression):
                emotion_stack.clear()
                word_count = 0
                continue
            if len(emotion_stack) > self.max_emotions_between_pause:
                raise ResultException('Du änderst deine Emotionen viel zu häufig zwischen Pausen.')
            if isinstance(expr, SpeechExpression):
                expr = cast(SpeechExpression, expr)
                word_count += len(expr.text.split(' '))
                if word_count > self.max_words_between_pause:
                    raise ResultException('Du benutzt zu viele Wörter zwischen Pausen. Pausiere ab und zu deine Sprache.')
                emotion_stack.append(expr.emotion)