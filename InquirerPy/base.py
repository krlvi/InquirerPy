"""Module contains base class for prompts."""

from typing import Dict, List, Tuple

from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.styles.style import Style


class BaseSimplePrompt:
    """The base class for simple prompts.

    :param message: the question message to display
    :type message: str
    :param style: the style dictionary to apply
    :type style: Dict[str, str]
    :param default: set default answer to true
    :param symbol: the custom symbol to display infront of the question
    :type symbol: str
    """

    def __init__(self, message: str, style: Dict[str, str], symbol: str = "?") -> None:
        """Construct the base class for simple prompts."""
        self.message = message
        self.question_style = Style.from_dict(style)
        self.symbol = symbol
        self.status = {"answered": False, "result": None}
        self.kb = KeyBindings()

    def _get_prompt_message(self, pre_answer, post_answer) -> List[Tuple[str, str]]:
        display_message = []
        display_message.append(("class:symbol", self.symbol))
        display_message.append(("class:question", " %s " % self.message))
        if self.status["answered"]:
            display_message.append(post_answer)
        else:
            display_message.append(pre_answer)
        return display_message