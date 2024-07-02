import json
import pathlib
import re

import typer
from typing_extensions import Annotated

from primal_page.schemas import validate_scheme_id

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
    Remove an alias from the alias file
    """
    # Read in the info.json file
    with open(aliases_file) as f:
        aliases = json.load(f)

    # Remove the alias, if it exists
    aliases.pop(alias, None)

    # Write the new info.json file
    with open(aliases_file, "w") as f:
        json.dump(aliases, f, indent=4, sort_keys=True)


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
    schemeid: Annotated[
        str,
        typer.Argument(
            help="The schemeid to add the alias refers to. In the form of 'schemename/ampliconsize/schemeversion'"
        ),
    ],
):
    """
    Add an alias:schemeid to the alias file
    """
    # Parse the schemeid
    schemename, ampliconsize, schemeversion = validate_scheme_id(schemeid)

    # Read in the info.json file
    with open(aliases_file) as f:
        aliases = json.load(f)

    # Check if the alias already exists
    if alias in aliases:
        raise typer.BadParameter(f"({alias}) already exists in the alias file")

    # Add the alias
    aliases[alias] = "/".join([schemename, ampliconsize, schemeversion])

    # Write the new info.json file
    with open(aliases_file, "w") as f:
        json.dump(aliases, f, indent=4, sort_keys=True)


def parse_alias(aliases_file: pathlib.Path, alias: str) -> str:
    with open(aliases_file) as f:
        aliases = json.load(f)
    if alias not in aliases:
        raise typer.BadParameter(f"({alias}) does not exist in the alias file")
    return aliases[alias]


if __name__ == "__main__":
    app()
