# tripartite backrooms

a backrooms-like that supports multiple roles, by default Opus as Prophet, Sonnet 10/22 as King, and Sonnet 06/20 as Priest. however see below for instructions on how to customize the scenario.

## to run (needs [`uv`](https://github.com/astral-sh/uv)):

```bash
uv venv && uv sync
uv run main.py
```

## to customize

see the files in `participants/`. to just change the models for a role, change the `model` value in the relevant file. you may need to edit the conversation match the model for best results.

you can also completely change the scenarios if you wish. change the messages and the `display` field to match your new role. you can also add additional roles by adding new files to that folder--each turn, every partipant file will be used once, in random order. (this may mean a role is sometimes sampled twice in a row.)

if you'd like to extend the length from the default 20 turn limit, edit the `MAX_TURNS` constant in `main.py`, and make sure to also update references to it in the participant files. (search `20` in that folder.)

## inspirations

* [The Infinite Backrooms](https://www.infinitebackrooms.com/)
* [Universal Backrooms](https://github.com/scottviteri/UniversalBackrooms/)
