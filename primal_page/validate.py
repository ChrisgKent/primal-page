import pathlib

import typer
from click import UsageError
from primalbedtools.bedfiles import BedLineParser, PrimerNameVersion, group_primer_pairs
from typing_extensions import Annotated

from primal_page.schemas import (
    Info,
)

app = typer.Typer(no_args_is_help=True)


def validate_name(infopath: pathlib.Path):
    """
    Validate the schemename, ampliconsize, and schemeversion in the path, ReadME.md, and info.json
    :raises ValueError: If a mismatch is found
    :raises FileNotFoundError: If the ReadME.md does not exist
    """

    # Read in the info.json
    info = Info.model_validate_json(infopath.read_text())
    info_scheme_path = (
        info.schemename + "/" + str(info.ampliconsize) + "/" + info.schemeversion
    )

    # Check the ReadME.md
    readme = infopath.parent / "README.md"
    if not readme.exists():
        raise FileNotFoundError(f"{readme} does not exist")

    # Check the info version matches path version
    version_path = infopath.parent.name
    if info.schemeversion != version_path:
        raise ValueError(
            f"Version mismatch for {info_scheme_path}: info ({info.schemeversion}) != path ({version_path})"
        )

    # Check the amplicon size matches the schemepath
    ampliconsize_path = infopath.parent.parent.name
    if info.ampliconsize != int(ampliconsize_path):
        raise ValueError(
            f"Ampliconsize mismatch for {info_scheme_path}: info ({info.ampliconsize}) != path ({ampliconsize_path})"
        )

    # Check the schemepath matches the path
    schemeid_path = infopath.parent.parent.parent.name
    if info.schemename != schemeid_path:
        raise ValueError(
            f"Schemename mismatch for {info_scheme_path}: info ({info.schemename}) != path ({schemeid_path})"
        )

    # Check the readme has been updated
    readme = readme.read_text()
    if readme.find(info.schemename) == -1:
        raise ValueError(
            f"Scheme name ({info.schemename}) not found in {readme}: {info.schemename}"
        )
    if readme.find(str(info.ampliconsize)) == -1:
        raise ValueError(
            f"Amplicon size ({info.ampliconsize}) not found in {readme}: {info.ampliconsize}"
        )
    if readme.find(info.schemeversion) == -1:
        raise ValueError(
            f"Scheme version ({info.schemeversion}) not found in {readme}: {info.schemeversion}"
        )


def validate_bedfile(bedpath: pathlib.Path, strict: bool = True):
    """
    Uses primalbedtools to validate the bedfiles.
    :raises ValueError: If the bedfile contains old primer names
    """
    _header, bedlines = BedLineParser.from_file(bedpath)

    for bedline in bedlines:
        if bedline.primername_version != PrimerNameVersion.V2:
            raise ValueError(
                f"Bedfile {bedpath} contains old primer names ({bedline.primername})"
            )

    # Carry out strict checks
    if not strict:
        return

    # Look for both left and right primers
    primer_pairs = group_primer_pairs(bedlines)
    for fkmers, rkmers in primer_pairs:
        if not fkmers:
            raise ValueError(
                f"Missing forward primer for {rkmers[0].amplicon_prefix}_{rkmers[0].amplicon_number} in {bedpath}"
            )
        if not rkmers:
            raise ValueError(
                f"Missing reverse primer for {fkmers[0].amplicon_prefix}_{fkmers[0].amplicon_number} in {bedpath}"
            )


@app.command(no_args_is_help=True)
def scheme(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to info.json",
            readable=True,
            exists=True,
        ),
    ],
):
    """
    Validate a scheme
    """
    try:
        validate_name(schemeinfo)
        bedfile = schemeinfo.parent / "primer.bed"
        validate_bedfile(bedfile)
    except Exception as e:
        raise UsageError(message=str(e)) from e


@app.command(no_args_is_help=True)
def directory(
    directory: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to the directory",
            readable=True,
            exists=True,
            dir_okay=True,
        ),
    ],
):
    """
    Validate all schemes in a directory
    """
    errors = []
    for schemeinfo in directory.glob("**/info.json"):
        try:
            validate_name(schemeinfo)
        except Exception as e:
            errors.append(str(e))

        try:
            bedfile = schemeinfo.parent / "primer.bed"
            validate_bedfile(bedfile)
        except Exception as e:
            errors.append(str(e))

    if errors:
        raise UsageError(message="\n".join(errors))


if __name__ == "__main__":
    try:
        validate_bedfile(
            pathlib.Path("/Users/kentcg/primal-page/tests/test_input/v1.primer.bed")
        )
    except Exception as e:
        raise UsageError(message=str(e)) from e
