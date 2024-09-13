import hashlib
import pathlib
from typing import Optional

import typer
from typing_extensions import Annotated

from primal_page.logging import log
from primal_page.schemas import (
    Collection,
    Info,
    Links,
    PrimerClass,
    SchemeStatus,
)

LICENSE_TXT_CC_BY_SA_4_0 = """\n\n------------------------------------------------------------------------

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/) 

![](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)"""

app = typer.Typer(no_args_is_help=True)


def trim_file_whitespace(in_path: pathlib.Path, out_path: pathlib.Path):
    """
    Trim whitespace from the ends of a file.
        - Reads file into memory. Not suitable for large files
    """
    inlines = []
    with open(in_path) as infile:
        for line in infile:
            inlines.append(line.strip() + "\n")

    with open(out_path, "w") as outfile:
        outfile.writelines(inlines)


def hash_file(fname: pathlib.Path) -> str:
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def regenerate_readme(path: pathlib.Path, info: Info, pngs: list[pathlib.Path]):
    """
    Regenerate the README.md file for a scheme

    :param path: The path to the scheme directory
    :type path: pathlib.Path
    :param info: The scheme information
    :type info: Info
    :param pngs: The list of PNG files
    :type pngs: list[pathlib.Path]
    """

    with open(path / "README.md", "w") as readme:
        readme.write(
            f"# {info.schemename} {info.ampliconsize}bp {info.schemeversion}\n\n"
        )

        readme.write(
            f"[primalscheme labs](https://labs.primalscheme.com/detail/{info.schemename}/{info.ampliconsize}/{info.schemeversion})\n\n"
        )

        if info.description is not None:
            readme.write("## Description\n\n")
            readme.write(f"{info.description}\n\n")

        readme.write("## Overviews\n\n")
        for png in pngs:
            readme.write(f"![{png.name}](work/{png.name})\n\n")

        readme.write("## Details\n\n")

        # Write the details into the readme
        readme.write(f"""```json\n{info.model_dump_json(indent=4)}\n```\n\n""")

        if info.license == "CC BY-SA 4.0":
            readme.write(LICENSE_TXT_CC_BY_SA_4_0)

        log.debug(f"Regenerated README.md for {info.get_schemepath()}")


def write_info_json(info: Info, schemeinfo: pathlib.Path):
    """
    Write the validated info.json to the scheme directory
    :param info: The validated info.json
    :type info: Info
    :param schemeinfo: The path to the info.json file
    :type schemeinfo: pathlib.Path
    """
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))
    log.debug(f"Regenerated info.json for {info.get_schemepath()}")


def generate_files(info: Info, schemeinfo: pathlib.Path, pngs: list[pathlib.Path] = []):
    # Write the validated info.json

    if schemeinfo.name != "info.json":
        schemeinfo = schemeinfo / "info.json"

    write_info_json(info, schemeinfo)

    # Update the README
    scheme_path = schemeinfo.parent
    regenerate_readme(scheme_path, info, pngs)


@app.command(no_args_is_help=True)
def add_link(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    linkfield: Annotated[
        str,
        typer.Argument(
            help=f"The link field to add to. {', '.join(Links.model_fields.keys())}"
        ),
    ],
    link: Annotated[
        str,
        typer.Argument(help="The link to add."),
    ],
):
    """
    Add a link to the selected link field to the info.json
    """
    info = Info.model_validate_json(schemeinfo.read_text())

    try:
        info.links.append_link(linkfield, link)
        log.info(
            f"Added link: [blue]{link}[/blue] to [blue]{linkfield}[/blue] for {info.get_schemepath()}"
        )
    except AttributeError:
        raise typer.BadParameter(
            f"{linkfield} is not a valid link field. Please choose from {', '.join(Links.model_fields.keys())}"
        ) from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def remove_link(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json",
            readable=True,
            exists=True,
            writable=True,
        ),
    ],
    linkfield: Annotated[
        str,
        typer.Argument(
            help=f"The link field to remove from. {', '.join(Links.model_fields.keys())}"
        ),
    ],
    link: Annotated[
        str,
        typer.Argument(help="The link to remove."),
    ],
):
    """
    Add a link to the selected link field to the info.json
    """
    info = Info.model_validate_json(schemeinfo.read_text())

    try:
        info.links.remove_link(linkfield, link)
        log.info(
            f"Removed link: [blue]{link}[/blue] from [blue]{linkfield}[/blue] for {info.get_schemepath()}"
        )
    except AttributeError:
        raise typer.BadParameter(
            f"{linkfield} is not a valid link field. Please choose from {', '.join(Links.model_fields.keys())}"
        ) from None
    except ValueError:
        raise typer.BadParameter(
            f"{link} is not in links[{linkfield}]: {info.links.getattr(linkfield)}"
        ) from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def add_author(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    author: Annotated[str, typer.Argument(help="The author to add")],
    author_index: Annotated[
        Optional[int],
        typer.Option(
            help="The 0-based index to insert the author at. Default is the end"
        ),
    ],
):
    """Append an author to the authors list in the info.json file"""

    info = Info.model_validate_json(schemeinfo.read_text())

    info.add_author(author, author_index)
    log.info(f"Added author: [blue]{author}[/blue] to {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def remove_author(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    author: Annotated[str, typer.Argument(help="The author to remove")],
):
    """Remove an author from the authors list in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    try:
        info.remove_author(author)
        log.info(f"Removed author: [blue]{author}[/blue] from {info.get_schemepath()}")
    except KeyError:
        raise typer.BadParameter(f"{author} is already not present") from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def reorder_authors(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    author_index: Annotated[
        Optional[str],
        typer.Argument(
            help="The indexes in the new order, separated by spaces. e.g. 1 0 2. Any indexes not provided will be appended to the end"
        ),
    ] = None,
):
    """Reorder the authors in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Reorder interactively
    if author_index is None:
        # Current order
        typer.echo("Current order:")
        for index, author in enumerate(info.authors):
            typer.echo(f"{index}: {author}")

        # Get the new order
        new_order_str: str = typer.prompt(
            "Please provide the indexes in the new order, separated by spaces. e.g. 1 0 2. Any indexes not provided will be appended to the end",
            type=str,
        )
        new_order = [int(x) for x in new_order_str.split()]
    else:  # Reorder via cli
        new_order = [int(x) for x in author_index.split()]

    try:
        info.reorder_authors(new_order)
        log.info(f"Reordered authors in {info.get_schemepath()}")
    except ValueError as e:
        raise typer.BadParameter(f"{e}") from None
    except IndexError as e:
        raise typer.BadParameter(f"{e}") from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def add_citation(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    citation: Annotated[str, typer.Argument(help="The citation to add")],
):
    """Append an citation to the authors list in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Add the citation
    info.add_citation(citation)
    log.info(f"Added citation: [blue]{citation}[/blue] to {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def remove_citation(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    citation: Annotated[str, typer.Argument(help="The citation to remove")],
):
    """Remove an citation form the authors list in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_bytes())

    try:
        info.remove_citation(citation)
        log.info(
            f"Removed citation: [blue]{citation}[/blue] from to {info.get_schemepath()}"
        )
    except KeyError:
        raise typer.BadParameter(f"{citation} is already not present") from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def remove_collection(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    collection: Annotated[Collection, typer.Argument(help="The Collection to remove")],
):
    """Remove an Collection from the Collection list in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Check if collection is already not in the list
    try:
        info.remove_collection(collection)
        log.info(
            f"Removed collection: [blue]{collection}[/blue] from to {info.get_schemepath()}"
        )
    except KeyError:
        raise typer.BadParameter(f"{collection} is already not present") from None

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def add_collection(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    collection: Annotated[Collection, typer.Argument(help="The Collection to add")],
):
    """Add a Collection to the Collection list in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    info.add_collection(collection)
    log.info(f"Added collection: [blue]{collection}[/blue] to {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_description(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    description: Annotated[
        str,
        typer.Argument(
            help="The new description. Use 'None' to remove the description"
        ),
    ],
):
    """Replaces the description in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Change the description
    info.change_description(description.strip())
    log.info(f"Changed description for {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_derivedfrom(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    derivedfrom: Annotated[
        str,
        typer.Argument(
            help="The new derivedfrom. Use 'None' to remove the derivedfrom"
        ),
    ],
):
    """Replaces the derivedfrom in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Add the derivedfrom
    info.change_derivedfrom(derivedfrom.strip())
    log.info(f"Changed derivedfrom for {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_license(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    license: Annotated[
        str,
        typer.Argument(
            help="The new license. Use 'None' show the work is not licensed (Not recommended)"
        ),
    ],
):
    """Replaces the license in the info.json file"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Change the license
    info.change_license(license)
    log.info(f"Changed license for {info.get_schemepath()}")

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_status(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    schemestatus: Annotated[
        SchemeStatus,
        typer.Argument(
            help="The scheme class",
        ),
    ] = SchemeStatus.DRAFT,
):
    """Change the status field in the info.json"""

    info = Info.model_validate_json(schemeinfo.read_text())

    # Change the status
    info.change_status(schemestatus)
    log.info(
        f"Changed status to [blue]{schemestatus}[/blue] for {info.get_schemepath()}"
    )

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_primerclass(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    primerclass: Annotated[
        PrimerClass, typer.Argument(help="The primerclass to change to")
    ],
):
    """Change the primerclass field in the info.json"""

    info = Info.model_validate_json(schemeinfo.read_text())

    # Change the primerclass
    info.change_primerclass(primerclass)
    log.info(
        f"Changed primerclass to [blue]{primerclass}[/blue] for {info.get_schemepath()}"
    )

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def change_contactinfo(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
    contactinfo: Annotated[
        Optional[str],
        typer.Argument(
            help="The contact information for this scheme. Use 'None' to remove the contact info",
        ),
    ],
):
    """Change the contactinfo field in the info.json"""
    info = Info.model_validate_json(schemeinfo.read_text())

    # Change the contactinfo
    info.change_contactinfo(contactinfo)
    log.info(
        f"Changed contactinfo to [blue]{contactinfo}[/blue] for {info.get_schemepath()}"
    )

    # Write the validated info.json and regenerate the README
    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
def regenerate(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json", readable=True, exists=True, writable=True
        ),
    ],
):
    """
    Validates the info.json and regenerate the README.md
    """
    info = Info.model_validate_json(schemeinfo.read_text())
    generate_files(info, schemeinfo)
