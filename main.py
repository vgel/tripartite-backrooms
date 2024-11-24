import datetime
import io
import pathlib
import random
import typing

import anthropic
import dotenv
import pydantic
import tenacity

TEMPLATES_DIR_PATH = "./participants"
TRACEFILE_PATH_TEMPLATE = "./logs/trace-{participants}-{dt}.txt"
SEPARATOR = "----------------------------------\n\n"
MAX_TURNS = 20
dotenv.load_dotenv(override=False)
client = anthropic.Client()


class ParticipantDef(pydantic.BaseModel):
    display: str
    model: str
    temperature: float
    messages: list["ParticipantDefMsg"]


class ParticipantDefMsg(pydantic.BaseModel):
    role: typing.Literal["user", "assistant"]
    content: str


class RoomMsg(pydantic.BaseModel):
    participant_id: str
    participant_display: str
    content: str

    def __str__(self) -> str:
        return f"{self.participant_display}: {self.content}"


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(anthropic.APIError),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
def generate(
    p_id: str, participants: dict[str, ParticipantDef], history: list[RoomMsg]
) -> RoomMsg:
    p_def = participants[p_id]

    anthropic_msgs: list[anthropic.types.MessageParam] = [
        {
            "role": m.role,
            "content": m.content,
        }
        for m in p_def.messages
    ]

    for m in history:
        if m.participant_id == p_id:
            anthropic_msgs.append({"role": "assistant", "content": str(m)})
        else:
            anthropic_msgs.append({"role": "user", "content": SEPARATOR + str(m)})

    # prefill
    prefill_content = "*" if p_id != "prophet" else ""  # TODO: hack
    anthropic_msgs.append(
        {
            "role": "assistant",
            "content": str(
                RoomMsg(
                    participant_id=p_id,
                    participant_display=p_def.display,
                    content=prefill_content,
                )
            ).strip(),
        }
    )
    message = client.messages.create(
        model=p_def.model,
        temperature=p_def.temperature,
        max_tokens=1024,
        messages=anthropic_msgs,
    )

    if len(message.content) != 1:
        raise RuntimeError("got multiple content blocks in response", message)
    elif message.content[0].type != "text":
        raise RuntimeError("content isn't text", message)
    else:
        text = prefill_content + message.content[0].text

    return RoomMsg(
        participant_id=p_id,
        participant_display=p_def.display,
        content=text,
    )


def run_room(
    participants: dict[str, ParticipantDef],
    tracefile: io.TextIOWrapper | None,
) -> list[RoomMsg]:
    def log(*values: object, sep: str = " ", end: str = "\n"):
        print(*values, sep=sep, end=end)
        if tracefile:
            print(*values, sep=sep, end=end, file=tracefile)
            tracefile.flush()

    for p_def in participants.values():
        log(f"{p_def.display}: {p_def.model} @ {p_def.temperature}")

    history: list[RoomMsg] = []
    for turn in range(MAX_TURNS):
        p_ids = list(participants.keys())
        random.shuffle(p_ids)
        for p_id in p_ids:
            response = generate(p_id, participants, history)
            log(f"\n\n- ({turn}) {SEPARATOR}{response}")
            history.append(response)

            if "^C^C" in str(response):
                log(f"\n\n* {participants[p_id].display} has ended the conversation.")
                return history

    log(f"\n\n* Conversation reached turn limit.")
    return history


def main():
    participants: dict[str, ParticipantDef] = {}
    for p in pathlib.Path(TEMPLATES_DIR_PATH).glob("*.json"):
        with open(p) as f:
            p_def = ParticipantDef.model_validate_json(f.read())
        participants[p.stem] = p_def

    tracefile_path = TRACEFILE_PATH_TEMPLATE.format(
        participants="_".join(sorted(participants.keys())),
        dt=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    with open(tracefile_path, "wt") as f:
        run_room(participants, f)


if __name__ == "__main__":
    main()
