import json

import httpx
from rich import print, print_json


async def log_request(request: httpx.Request):
    """Log the request body."""
    if request.content:
        try:
            req_json = json.loads(request.content)
            print(
                f"[bold cyan]>>> REQUEST[/bold cyan] {request.method} {request.url}"
            )
            print_json(data=req_json)
        except json.JSONDecodeError:
            pass


async def log_response(response: httpx.Response):
    """Log the response body."""
    await response.aread()
    try:
        resp_json = json.loads(response.content)
        print(
            f"[bold green]<<< RESPONSE[/bold green] {response.status_code}"
        )
        print_json(data=resp_json)
    except json.JSONDecodeError:
        pass


def get_http_client(
    debug_http: bool = False,
) -> httpx.AsyncClient | None:
    """Return a custom HTTP client with logging if enabled."""
    if debug_http:
        return httpx.AsyncClient(
            event_hooks={
                "request": [log_request],
                "response": [log_response],
            }
        )
    return None
