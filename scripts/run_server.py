from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable

from uvicorn import Config, Server

class _SelectorConfig(Config):
    def get_loop_factory(self) -> Callable[[], asyncio.AbstractEventLoop]:
        return asyncio.SelectorEventLoop

def main() -> None:
    config_cls = _SelectorConfig if sys.platform == "win32" else Config
    config = config_cls(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
    Server(config).run()

if __name__ == "__main__":
    main()
