from __future__ import annotations

from typing import Any, List

from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion
from langchain.automaton.open_ai_functions import OpenAIFunctionsRouter

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chat_models.base import BaseChatModel
from langchain.schema import ChatResult
from langchain.schema.messages import AIMessage, BaseMessage
from langchain.schema.runnable import RunnableLambda
from langchain.schema.output import ChatGeneration


class FakeChatOpenAI(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake-openai-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: List[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        additional_kwargs={
                            "function_call": {
                                "name": "accept",
                                "arguments": '{\n  "draft": "turtles"\n}',
                            }
                        },
                    )
                )
            ]
        )


def test_openai_functions_router(
    snapshot: SnapshotAssertion, mocker: MockerFixture
) -> None:
    def revise(notes: str) -> str:
        return f"Revised draft: {notes}!"

    def accept(draft: str) -> str:
        return f"Accepted draft: {draft}!"

    router = OpenAIFunctionsRouter(
        functions=[
            {
                "name": "revise",
                "description": "Sends the draft for revision.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "notes": {
                            "type": "string",
                            "description": "The editor's notes to guide the revision.",
                        },
                    },
                },
            },
            {
                "name": "accept",
                "description": "Accepts the draft.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "draft": {
                            "type": "string",
                            "description": "The draft to accept.",
                        },
                    },
                },
            },
        ],
        runnables={
            "revise": RunnableLambda(lambda x: revise(x["revise"])),
            "accept": RunnableLambda(lambda x: accept(x["draft"])),
        },
    )

    model = FakeChatOpenAI()

    chain = model.bind(functions=router.functions) | router

    assert chain.invoke("Something about turtles?") == "Accepted draft: turtles!"