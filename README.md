# LLM Learning

A collection of notebooks and resources for learning about Large Language Models (LLMs).


### Setup

Install [Ollama](https://ollama.com/download)

Add the following to your `.envrc` file:

```sh
unset VIRTUAL_ENV
uv sync --locked
PATH_add .venv/bin
```

Install pre-commit:

```sh
pre-commit install
```

Then run:

```sh
jupyter-lab
```
