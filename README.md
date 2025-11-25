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

### Database Setup

Add to your `.envrc` file:

```sh
# postgres
export PGHOST=localhost
export PGPORT=54222
export PGUSER=llm_learning
export PGDATABASE=llm_learning
export DATABASE_URL=postgresql+psycopg://llm_learning@localhost:54222/llm_learning
```

Start container services:

```sh
docker-compose up -d
```
