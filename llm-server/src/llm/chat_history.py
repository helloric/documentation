import os

class ChatHistory:
    """Chat History handler. Keeps track of questions and answers as if they were a chat."""

    def __init__(self):
        self.history = []
        self.cleanup_threshold = 10

    def _chat_as_role(self, message: str, role: str, clean: bool = False):
        if (clean and len(self.history) > self.cleanup_threshold):
            self.history.clear()
        self.history.append({'role': role, 'content': message})

    def chat_as_user(self, message: str, clean: bool = False):
        """Adds a message for the user (the one who asks the question)

        Args:
            message (str): The message to add
            clean (bool): Should the history be cleaned up after the cleanup threshold is reached?

        """
        self._chat_as_role(message, 'user', clean)
    
    def chat_as_llm(self, message: str, clean: bool = False):
        """Adds a message for the LLM (the one who has to handle the question)

        Args:
            message (str): The message to add
            clean (bool): Should the history be cleaned up after the cleanup threshold is reached?
        """
        self._chat_as_role(message, 'assistant', clean)

    def add_question_answer(self, question: str, answer: str, clean: bool = False):
        """Adds a question and answer at once to the history.

        Args:
            question (str): The question
            answer (str): The answer
            clean (bool): Should the history be cleaned up after the cleanup threshold is reached?
        """
        self.chat_as_user(question, clean)
        self.chat_as_llm(answer, clean)
