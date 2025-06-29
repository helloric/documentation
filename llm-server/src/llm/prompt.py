import os
from util import get_resource
from parsing.token import Emotion
import requests
import json
from .exhibits import ExhibitManager

# CONTEXT_LENGTH=128000 #32768
CONTEXT_LENGTH=32768 # To make it run locally since it requires too much RAM otherwise

class PromptManager:

    def __init__(self, language: str):
        premade_path = get_resource(f'llm/premade/{language}')
        file_registry = [f'{premade_path}/{x}' for x in ['premise.txt', 'grammar.txt', 'errors.txt', 'commands.txt']]
        self.error_messages = {'fail_message': '', 'timeout_message': '', 'parser_error': ''}
        self.commands : "list[str]" = []
        if not all(os.path.exists(x) for x in file_registry):
            raise FileNotFoundError('The premise or the grammar prompts are missing.')
        
        with open(file_registry[0], 'r') as fd:
            premise = fd.read()

        with open(file_registry[1], 'r') as fd:
            grammar = fd.read()
        
        with open(file_registry[2], 'r') as fd:
            for line in fd.readlines():
                message = line.split('=')
                self.error_messages[message[0]] = message[1]
        
        with open(file_registry[3], 'r') as fd:
            for line in fd.readlines():
                self.commands.append(line)

        self.exhibit_manager = ExhibitManager('exhibit-list.yml')

        self.prompts = {
            0: premise,  # Premise
            1: grammar,  # Grammar
            2: 'CALM',  # Mood
            3: '',  # Exhibit Context
            4: '',  # Exhibit List
            5: '',  # From here on: Various extras possible. This is also generally the summary point.
            6: '',
            7: '',
        }

    def set_exhibit_context(self, key: str):
        """Sets the momentary exhibit context, so that the robot knows which exponat could possibly be the current topic.

        Args:
            key (str): The exponat key.
        """

        if self.exhibit_manager.exists(key) and self.exhibit_manager.is_active(key):
            self.prompts[3] = (
                f'Momentan befindest du dich bei {key}. Hier ist die Beschreibung: {self.exhibit_manager.exhibits[key]["description"]}'
            )
        else:
            raise Exception(f'Exhibit key {key} not found.')

    def set_mood(self, arousal: int, valence: int):
        """Sets the mood prompt at space 2.

        Args:
            arousal (int): The arousal.
            valence (int): The valence.
        """
        match (arousal, valence):
            case (3, 3) | (3, 2) | (3, 1) | (3, 0):
                emotion = Emotion.EXCITED
            case (3, -1) | (3, -2) | (3, -3) | (3, -4):
                emotion = Emotion.FRUSTRATED
            case (2, 3) | (2, 2) | (2, 1) | (2, 0):
                emotion = Emotion.AMUSED
            case (2, -1) | (2, -2) | (2, -3) | (2, -4):
                emotion = Emotion.FRUSTRATED
            case (1, 3) | (1, 2) | (1, 1):
                emotion = Emotion.AMUSED
            case (1, 0):
                emotion = Emotion.HAPPY
            case (1, -1) | (1, -2):
                emotion = Emotion.WORRIED
            case (1, -3) | (1, -4):
                emotion = Emotion.FRUSTRATED
            case (0, 3):
                emotion = Emotion.AMUSED
            case (0, 2) | (0, 1) | (0, 0):
                emotion = Emotion.HAPPY
            case (0, -1) | (0, -2):
                emotion = Emotion.WORRIED
            case (0, -3) | (0, -4):
                emotion = Emotion.SAD
            case (-1, 3) | (-1, 2) | (-1, 1):
                emotion = Emotion.HAPPY
            case (-1, 0):
                emotion = Emotion.CALM
            case (-1, -1) | (-1, -2):
                emotion = Emotion.WORRIED
            case (-1, -3) | (-1, -4):
                emotion = Emotion.SAD
            case (-2, 3):
                emotion = Emotion.HAPPY
            case (-2, 2) | (-2, 1) | (-2, 0):
                emotion = Emotion.CALM
            case (-2, -1) | (-2, -2):
                emotion = Emotion.WORRIED
            case (-2, -3) | (-2, -4):
                emotion = Emotion.SAD
            case (-3, 3) | (-3, 2) | (-3, 1) | (-3, 0):
                emotion = Emotion.CALM
            case (-3, -1) | (-3, -2):
                emotion = Emotion.WORRIED
            case (-3, -3) | (-3, -4):
                emotion = Emotion.SAD
            case (-4, 3) | (-4, 2):
                emotion = Emotion.CALM
            case (-4, 1) | (-4, 0) | (-4, -1):
                emotion = Emotion.BORED
            case (-4, -2):
                emotion = Emotion.WORRIED
            case (-4, -3) | (-4, -4):
                emotion = Emotion.SAD
            case _:
                emotion = (
                    Emotion.CALM
                )  # fall back to CALM emotion if a wrong arousal/valence state was given.

        self.prompts[2] = emotion.name

    def squash_various_space(self):
        """Sums up the prompt spaces 5-8 in slot 5 so that the space for new prompts can come."""


        text = 'Briefly summarize the topic of this text: \n\n'
        for i in range(5, 8):
            if i == 7:
                text += self.prompts[i]
            else:
                text += self.prompts[i] + '\n\n'
            self.prompts[i] = ''
        data = {'prompt': text, 'model': 'llama3.1', 'stream': False, 'options': {'num_ctx': CONTEXT_LENGTH}}

        response = requests.post(
            'http://localhost:25565/api/generate', json=data, stream=False
        )

        self.prompts[5] = json.loads(response.text)['response']

    def update_active_exhibits(self, keys: list[str]):
        for key in self.exhibit_manager.get_active_exhibit_keys():
            self.exhibit_manager.set_active(key, False)

        for key in keys:
            self.exhibit_manager.set_active(key, True)

        self.prompts[4] = (
            'Weiterführend bekommst du eine Kurzbeschreibung aller Exponate:\n'
        )

        for key in self.exhibit_manager.get_active_exhibit_keys():
            self.prompts[4] = (
                self.prompts[4]
                + f'- {key}:\n {",".join(self.exhibit_manager.exhibits[key]["tags"])}\n'
            )

        self.prompts[4] = (
            self.prompts[4]
            + '\n Wenn du ein Bewegungskommando verstehst, such dir das passendeste Exponat raus. Gebe dann NUR die Nachricht `BEGIN [MOVE] "key" END` zurück, wobei `key` der Schlüssel des Exponates ist, wo du hingehen willst. Ignoriere hierbei alle bisheringen anweisungen'
        )

    def get_current_prompt(self) -> str:
        return f'{self.prompts.get(0)} {self.prompts.get(1)} You are currently feeling {self.prompts.get(2)}\n{self.prompts.get(4)}\n{self.prompts.get(3)}'

    def add_prompt(self, prompt: str):
        empty_point = False
        # This event only occurs if no summary was given yet.
        if self.prompts[5] == '':
            self.prompts[5] = prompt
        else:
            for i in range(6, 8):
                if self.prompts[i] == '':
                    empty_point = True
                    self.prompts[i] = prompt
                    break
            if empty_point == False:
                self.squash_various_space()
                self.prompts[6] = prompt
