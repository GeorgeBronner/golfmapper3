from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _client_ip(request: Request) -> str:
    # Behind nginx/docker every request arrives from the proxy's address, which
    # would make the rate limit global across all users. Key on the original
    # client (first X-Forwarded-For hop) when the header is present.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
