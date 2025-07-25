from typing import Literal
import requests
import json
from .prompt import PromptManager, CONTEXT_LENGTH
from .chat_history import ChatHistory

class LLM:

    def __init__(self, model: str, language: Literal['en', 'de'] = 'de') -> None:
        self.model = model
        self.prompt_manager = PromptManager(language)
        self.chat_history = ChatHistory()

    def ask_with_history(self, text: str, chat_history: ChatHistory) -> str:
        """Sends a prompt to the LLM, with defined system prompt and a given custom chat history."""
        prompt = self.prompt_manager.get_current_prompt()
        ask = {'role': 'user', 'content': text}
        message = chat_history.history
        message.append(ask)
        message.insert(0, {'role': 'system', 'content': prompt})
        data = {
            'model': self.model,
            'messages': message,
            'stream': False,
            'options': {
                'num_ctx': CONTEXT_LENGTH
            }
        }
        response = requests.post('http://localhost:25565/api/chat', json=data, stream=False)
        text_response = (json.loads(response.text)['message'])['content']

        return text_response

    def ask(self, text: str) -> str:
        """Sends a prompt to the LLM, with defined system prompt and the default chat history."""
        return self.ask_with_history(text, self.chat_history)
    
    @staticmethod
    def command(model: str, command: str) -> str:
        """Gives raw prompting to the LLM, bypassing the context windows, i.e. the system prompt."""
        data = {
            'prompt': command,
            'model': model,
            'stream': False
        }

        response = requests.post('http://localhost:25565/api/generate', json=data, stream=False)

        return json.loads(response.text)['response']