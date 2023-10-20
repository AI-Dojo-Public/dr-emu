from functools import wraps

import typer
import asyncio
import inspect

from overrides import override


class UTyper(typer.Typer):
    # https://github.com/tiangolo/typer/issues/88
    @override
    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)

        def add_runner(f):
            if inspect.iscoroutinefunction(f):

                @wraps(f)
                def runner(*args, **kwargs):
                    return asyncio.run(f(*args, **kwargs))

                decorator(runner)
            else:
                decorator(f)
            return f

        return add_runner
