"""Module contains the class to create a number prompt."""
from typing import TYPE_CHECKING, Any, Callable, Union, cast

from prompt_toolkit.application.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.cli import IsDone
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HorizontalAlign,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    DummyControl,
    FormattedTextControl,
)
from prompt_toolkit.layout.dimension import Dimension, LayoutDimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers.base import SimpleLexer

from InquirerPy.base.complex import BaseComplexPrompt
from InquirerPy.containers.instruction import InstructionWindow
from InquirerPy.containers.validation import ValidationWindow
from InquirerPy.enum import INQUIRERPY_QMARK_SEQUENCE
from InquirerPy.exceptions import InvalidArgument
from InquirerPy.utils import (
    InquirerPyDefault,
    InquirerPyKeybindings,
    InquirerPyMessage,
    InquirerPySessionResult,
    InquirerPyStyle,
    InquirerPyValidate,
)

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

__all__ = ["NumberPrompt"]


class NumberPrompt(BaseComplexPrompt):
    """Create a input prompts that only takes number as input."""

    def __init__(
        self,
        message: InquirerPyMessage,
        style: InquirerPyStyle = None,
        vi_mode: bool = False,
        default: InquirerPyDefault = 0,
        float_allowed: bool = False,
        max_allowed: Union[int, float] = None,
        min_allowed: Union[int, float] = None,
        decimal_symbol: str = ". ",
        qmark: str = INQUIRERPY_QMARK_SEQUENCE,
        amark: str = "?",
        instruction: str = "",
        long_instruction: str = "",
        validate: InquirerPyValidate = None,
        invalid_message: str = "Invalid input",
        transformer: Callable[[str], Any] = None,
        filter: Callable[[str], Any] = None,
        keybindings: InquirerPyKeybindings = None,
        wrap_lines: bool = True,
        raise_keyboard_interrupt: bool = True,
        mandatory: bool = True,
        mandatory_message: str = "Mandatory prompt",
        session_result: InquirerPySessionResult = None,
    ) -> None:
        super().__init__(
            message=message,
            style=style,
            vi_mode=vi_mode,
            qmark=qmark,
            amark=amark,
            transformer=transformer,
            filter=filter,
            invalid_message=invalid_message,
            validate=validate,
            instruction=instruction,
            long_instruction=long_instruction,
            wrap_lines=wrap_lines,
            raise_keyboard_interrupt=raise_keyboard_interrupt,
            mandatory=mandatory,
            mandatory_message=mandatory_message,
            session_result=session_result,
        )

        self._float = float_allowed
        self._is_float = Condition(lambda: self._float)
        self._max = max_allowed
        self._min = min_allowed
        self._value_error_message = "Remove any non-integer value"
        self._decimal_symbol = decimal_symbol
        self._ending_zero = False

        if isinstance(default, Callable):
            default = cast(Callable, default)(session_result)
        if self._float:
            default = float(cast(int, default))
        if self._float:
            if not isinstance(default, float):
                raise InvalidArgument(
                    f"{type(self).__name__} argument 'default' should return type of float"
                )
        elif not isinstance(default, int):
            raise InvalidArgument(
                f"{type(self).__name__} argument 'default' should return type of int"
            )
        self._default = default

        if keybindings is None:
            keybindings = {}
        self.kb_maps = {
            "down": [
                {"key": "down"},
                {"key": "c-n", "filter": ~self._is_vim_edit},
                {"key": "j", "filter": self._is_vim_edit},
            ],
            "up": [
                {"key": "up"},
                {"key": "c-p", "filter": ~self._is_vim_edit},
                {"key": "k", "filter": self._is_vim_edit},
            ],
            "left": [
                {"key": "left"},
                {"key": "c-b", "filter": ~self._is_vim_edit},
                {"key": "h", "filter": self._is_vim_edit},
            ],
            "right": [
                {"key": "right"},
                {"key": "c-f", "filter": ~self._is_vim_edit},
                {"key": "l", "filter": self._is_vim_edit},
            ],
            "focus": [{"key": Keys.Tab}, {"key": "s-tab"}],
            "input": [{"key": str(i)} for i in range(10)],
            "negative_toggle": [{"key": "-"}],
            **keybindings,
        }
        self.kb_func_lookup = {
            "down": [{"func": self._handle_down}],
            "up": [{"func": self._handle_up}],
            "left": [{"func": self._handle_left}],
            "right": [{"func": self._handle_right}],
            "focus": [{"func": self._handle_focus}],
            "input": [{"func": self._handle_input}],
            "negative_toggle": [{"func": self._handle_negative_toggle}],
        }

        @self.register_kb(Keys.Any)
        def _(_):
            pass

        self._whole_width = 1
        self._whole_buffer = Buffer(
            on_text_changed=self._on_whole_text_change,
            on_cursor_position_changed=self._on_cursor_position_change,
        )

        self._integral_width = 1
        self._integral_buffer = Buffer(
            on_text_changed=self._on_integral_text_change,
            on_cursor_position_changed=self._on_cursor_position_change,
        )

        self._whole_window = Window(
            height=LayoutDimension.exact(1) if not self._wrap_lines else None,
            content=BufferControl(
                buffer=self._whole_buffer,
                lexer=SimpleLexer("class:input"),
            ),
            width=lambda: Dimension(
                min=self._whole_width,
                max=self._whole_width,
                preferred=self._whole_width,
            ),
            dont_extend_width=True,
        )

        self._integral_window = Window(
            height=LayoutDimension.exact(1) if not self._wrap_lines else None,
            content=BufferControl(
                buffer=self._integral_buffer,
                lexer=SimpleLexer("class:input"),
            ),
            width=lambda: Dimension(
                min=self._integral_width,
                max=self._integral_width,
                preferred=self._integral_width,
            ),
        )

        self._layout = Layout(
            HSplit(
                [
                    VSplit(
                        [
                            Window(
                                height=LayoutDimension.exact(1)
                                if not self._wrap_lines
                                else None,
                                content=FormattedTextControl(self._get_prompt_message),
                                wrap_lines=self._wrap_lines,
                                dont_extend_height=True,
                                dont_extend_width=True,
                            ),
                            self._whole_window,
                            ConditionalContainer(
                                Window(
                                    height=LayoutDimension.exact(1)
                                    if not self._wrap_lines
                                    else None,
                                    content=FormattedTextControl(
                                        [("", self._decimal_symbol)]
                                    ),
                                    wrap_lines=self._wrap_lines,
                                    dont_extend_height=True,
                                    dont_extend_width=True,
                                ),
                                filter=self._is_float,
                            ),
                            ConditionalContainer(
                                self._integral_window, filter=self._is_float
                            ),
                        ],
                        align=HorizontalAlign.LEFT,
                    ),
                    ConditionalContainer(
                        Window(content=DummyControl()),
                        filter=~IsDone() & self._is_displaying_long_instruction,
                    ),
                    ValidationWindow(
                        invalid_message=self._get_error_message,
                        filter=self._is_invalid & ~IsDone(),
                        wrap_lines=self._wrap_lines,
                    ),
                    InstructionWindow(
                        message=self._long_instruction,
                        filter=~IsDone() & self._is_displaying_long_instruction,
                        wrap_lines=self._wrap_lines,
                    ),
                ]
            ),
        )

        self.focus = self._whole_window

        self._application = Application(
            layout=self._layout,
            style=self._style,
            key_bindings=self._kb,
            after_render=self._after_render,
        )

    def _on_rendered(self, _) -> None:
        self._whole_buffer.text = "0"
        self._whole_buffer.cursor_position = 0
        self._integral_buffer.text = "0"
        self._integral_buffer.cursor_position = 0

    def _handle_down(self, _) -> None:
        try:
            if not self.focus_buffer.text:
                self.focus_buffer.text = "0"
            else:
                self.focus_buffer.text = str(int(self.focus_buffer.text) - 1)
        except ValueError:
            self._set_error(message=self._value_error_message)

    def _handle_up(self, _) -> None:
        try:
            if not self.focus_buffer.text:
                self.focus_buffer.text = "0"
            else:
                self.focus_buffer.text = str(int(self.focus_buffer.text) + 1)
        except ValueError:
            self._set_error(message=self._value_error_message)

    def _handle_left(self, _) -> None:
        if (
            self.focus == self._integral_window
            and self.focus_buffer.cursor_position == 0
        ):
            self.focus = self._whole_window
        else:
            self.focus_buffer.cursor_position -= 1

    def _handle_right(self, _) -> None:
        if (
            self.focus == self._whole_window
            and self.focus_buffer.cursor_position == len(self.focus_buffer.text)
            and self._float
        ):
            self.focus = self._integral_window
        else:
            self.focus_buffer.cursor_position += 1

    def _handle_enter(self, _) -> None:
        pass

    def _handle_focus(self, _) -> None:
        if not self._float:
            return
        if self.focus == self._whole_window:
            self.focus = self._integral_window
        else:
            self.focus = self._whole_window

    def _handle_input(self, event: "KeyPressEvent") -> None:
        self.focus_buffer.insert_text(event.key_sequence[0].data)

    def _handle_negative_toggle(self, _) -> None:
        if self._whole_buffer.text.startswith("-"):
            self._whole_buffer.text = self._whole_buffer.text[1:]
        else:
            self._whole_buffer.text = f"-{self._whole_buffer.text}"

    def _on_whole_text_change(self, buffer: Buffer) -> None:
        self._whole_width = len(buffer.text) + 1
        self._on_text_change(buffer)

    def _on_integral_text_change(self, buffer: Buffer) -> None:
        self._integral_width = len(buffer.text) + 1
        self._on_text_change(buffer)

    def _on_text_change(self, buffer: Buffer) -> None:
        if buffer.text and buffer.text != "-":
            self.value = self.value
        if buffer.text.startswith("-") and buffer.cursor_position == 0:
            buffer.cursor_position = 1

    def _on_cursor_position_change(self, buffer: Buffer) -> None:
        if self.focus_buffer.text.startswith("-") and buffer.cursor_position == 0:
            buffer.cursor_position = 1

    @property
    def focus_buffer(self) -> Buffer:
        """Buffer: Current editable buffer."""
        if self.focus == self._whole_window:
            return self._whole_buffer
        else:
            return self._integral_buffer

    @property
    def focus(self) -> Window:
        """Window: Current focused window."""
        return self._focus

    @focus.setter
    def focus(self, value: Window) -> None:
        self._focus = value
        self._layout.focus(self._focus)

    @property
    def value(self) -> Union[int, float]:
        """Union[int, float]: The actual value of the prompt, combining and transforming all input buffer values."""
        try:
            if not self._float:
                return int(self._whole_buffer.text)
            else:
                self._ending_zero = (
                    self._integral_buffer.text.endswith("0")
                    if len(self._integral_buffer.text) > 1
                    else False
                )
                return float(f"{self._whole_buffer.text}.{self._integral_buffer.text}")
        except ValueError:
            self._set_error(self._value_error_message)
            return self._default

    @value.setter
    def value(self, value: Union[int, float]) -> None:
        if self._min is not None:
            value = max(value, self._min if not self._float else float(self._min))
        if self._max is not None:
            value = min(value, self._max if not self._float else float(self._max))
        if not self._float:
            self._whole_buffer.text = str(value)
        else:
            self._whole_buffer.text, integral_buffer_text = str(value).split(".")
            if self._ending_zero:
                self._integral_buffer.text = integral_buffer_text + "0"
            else:
                self._integral_buffer.text = integral_buffer_text
