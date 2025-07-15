from . token import *


class Lexer:
    """The Lexer takes an input string and provides a Token stream.

    Attributes:
        input_string (str): The input string following the rules of a formal language. 
        current_index (int): The Lexer's _internal_ position. Which character index the Lexer is currently reading.
        line (int): The Lexer's _external_ current line position. Which line of the input string is the current token located at?
        column (int): The Lexer's _external_ current column position. Which column of the momentary line in the input string is the current token located at?
        current_token (Token): The last fetched token that was fetched by `Lexer.next_token()`
    """
    
    def __init__(self, input_string: str):
        self.input_string = input_string
        self.current_index = 0
        self.line = 0
        self.column = 0
        self.current_token = None
        if not 'BEGIN' in self.input_string:
            raise Exception('Bitte füge ein BEGIN an den Anfang an.')
        if not 'END' in self.input_string:
            raise Exception('Bitte füge ein END an das Ende an.')
        self.cut_off()
        
    def cut_off(self):
        """Cuts off input string by searching for the first `BEGIN` and the last `END`. Cutting off everything _before_ the first `BEGIN` and _after_ the last `END`.

        Examples: Example
            >>> lexer = Lexer('This is garbage text BEGIN <HAPPY> "My poem about robots" END and some more garbage text.')
            >>> print(lexer.input_string)
            This is garbage text about BEGIN <HAPPY> "My poem about robots" END and some more garbage text.
            >>> lexer.cut_off()
            >>> print(lexer.input_string)
            BEGIN <HAPPY> "My poem about robots" END
        """
        self.input_string = self.input_string[self.input_string.find('BEGIN'):self.input_string.rfind('END') + 3]
    
    def _clear_spaces(self) -> bool:
        """Skips over all the spaces and newlines while keeping `current_index`, `line` and `column` up to date

        Returns:
            `True`, if the end of the input string is reached after that operation.
        """
        while self.current_index < len(self.input_string):
            symbol = self.input_string[self.current_index]
            if symbol.isspace():
                self.current_index += 1
                if symbol == '\n':
                    self.line += 1
                    self.column = 0
                else:
                    self.column += 1
            else:
                break

        return self.current_index >= len(self.input_string)

    def next_token(self) -> None:
        """Fetches the next token from the input string by setting `Lexer.current_token` to the Token type corresponding to what was read.

        Warning:
            The Lexer does not check for any syntax errors. As a result, the `EOF` fail-safe is implemented. 
            If the Lexer goes beyond the input string length, we set the current token to an `EOF`-Token by default.

        """
        if self.current_index >= len(self.input_string) or self._clear_spaces():
            cast(Token, self.current_token).id = Id.EOF
            return
        
        symbol = self.input_string[self.current_index]

        match symbol:
            case '>':
                self.current_token = Token(Id.RCHEVRON)
                self.current_index += 1
                self.column += 1    
            case '<':
                self.current_token = Token(Id.LCHEVRON)
                self.current_index += 1
                self.column += 1
            case ';':
                self.current_token = Token(Id.SEMICOLON)
                self.current_index += 1
                self.column += 1
            case '"':
                self.current_token = Token(Id.LITERAL)
                self.current_index += 1
                self.column += 1
            case '[':
                self.current_token = Token(Id.LSQBRACKET)
                self.current_index += 1
                self.column += 1
            case ']':
                self.current_token = Token(Id.RSQBRACKET)
                self.current_index += 1
                self.column += 1
            case _:
                selected_index = self.current_index
                while self.current_index < len(self.input_string):
                    symbol = self.input_string[self.current_index]
                    if symbol in ['<', '>', ';', '[', ']', '"']:
                        break
                    self.current_index += 1
                    self.column += 1
                res = self.input_string[selected_index:self.current_index].strip()
                if self.current_index == len(self.input_string) and res != 'END':
                    raise Exception('Unerwartetes Dateiende. Es fehlt ein Endsymbol für den Bezeichner (<, >, ", [, ])')
                self.current_token = Token(Id.IDENT, res)
