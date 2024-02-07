from cli.infrastructure import infras_typer
from cli.run import run_typer
from cli.agent import agent_typer
from cli.template import template_typer

from typer import Typer


app = Typer(no_args_is_help=True)
app.add_typer(infras_typer, name="infrastructures")
app.add_typer(run_typer, name="runs")
app.add_typer(agent_typer, name="agents")
app.add_typer(template_typer, name="templates")

if __name__ == "__main__":
    app()
