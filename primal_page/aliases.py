import json
import pathlib
import re

import typer
from typing_extensions import Annotated

from primal_page.logging import log
from primal_page.schemas import validate_schemename

app = typer.Typer(no_args_is_help=True)

ALIASES_PATTERN = r"^[a-z0-9][a-z0-9-.]*[a-z0-9]$"


def validate_alias(alias: str) -> str:
    if not re.match(ALIASES_PATTERN, alias):
        raise typer.BadParameter(
            f"({alias}). Must only contain a-z, 0-9, and -. Cannot start or end with -"
        )
    return alias


@app.command(no_args_is_help=True)
def remove(
    aliases_file: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to the alias file to write to",
            exists=True,
            file_okay=True,
            writable=True,
        ),
    ],
    alias: Annotated[
        str,
        typer.Argument(
            help="The alias to add",
            # No callback here because we don't want to validate removing the alias
        ),
    ],
):
    """
    Remove an alias from the alias file. Does nothing if the alias does not exist
    """
    # Read in the info.json file
    with open(aliases_file) as f:
        aliases = json.load(f)

    # Remove the alias, if it exists
    removed_aliases = aliases.pop(alias, None)
    if removed_aliases is None:
        log.info(f"Alias ([blue]{alias}[/blue]) does not exist. Doing nothing.")
        return
    log.info(f"Removed alias: ([blue]{removed_aliases}[/blue])")

    # Write the new info.json file
    with open(aliases_file, "w") as f:
        json.dump(aliases, f, sort_keys=True)


@app.command(no_args_is_help=True)
def add(
    aliases_file: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to the alias file to write to",
            exists=True,
            file_okay=True,
            writable=True,
        ),
    ],
    alias: Annotated[
        str,
        typer.Argument(
            help="The alias to add",
            callback=validate_alias,
        ),
    ],
    schemename: Annotated[
        str,
        typer.Argument(
            help="The schemename the alias refers to", callback=validate_schemename
        ),
    ],
):
    """
    Add an alias:schemename to the alias file
    """
    # Read in the info.json file
    with open(aliases_file) as f:
        try:
            aliases = json.load(f)
        except json.JSONDecodeError:
            aliases = {}

    # Check if the alias already exists
    if alias in aliases:
        log.info(f"Alias ([blue]{alias}[/blue]) already exists. Doing nothing.")
        return
    log.info(f"Added alias: ([blue]{alias}[/blue]) -> ([blue]{schemename}[/blue])")

    # Add the alias
    # typer will have already validated the schemename
    aliases[alias] = schemename

    # Write the new info.json file
    with open(aliases_file, "w") as f:
        json.dump(aliases, f, sort_keys=True)


if __name__ == "__main__":
    app()
