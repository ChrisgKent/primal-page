import pathlib

import typer
from click import UsageError
from primalbedtools.bedfiles import BedLineParser, PrimerNameVersion, group_primer_pairs
from typing_extensions import Annotated

from primal_page.logging import log
from primal_page.modify import hash_file
from primal_page.schemas import Info, validate_ref_select_file

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


def validate_hashes(infopath: pathlib.Path):
    """
    Reads in the info.json and checks the hashes for ./primer.bed and ./reference.fasta
    """
    # Read in the info.json
    info = Info.model_validate_json(infopath.read_text())
    info_scheme_path = (
        info.schemename + "/" + str(info.ampliconsize) + "/" + info.schemeversion
    )

    # Check the hashes
    if info.primer_bed_md5 != hash_file(infopath.parent / "primer.bed"):
        raise ValueError(
            f"MD5 mismatch for {info_scheme_path}:primer.bed: info ({info.primer_bed_md5}) != file ({hash_file(infopath.parent / 'primer.bed')})"
        )

    if info.reference_fasta_md5 != hash_file(infopath.parent / "reference.fasta"):
        raise ValueError(
            f"MD5 mismatch for {info_scheme_path}:reference.fasta: info ({info.reference_fasta_md5}) != file ({hash_file(infopath.parent / 'reference.fasta')})"
        )


def validate_ref_selection(infopath: pathlib.Path):
    # Read in the info.json
    info = Info.model_validate_json(infopath.read_text())
    info_scheme_path = (
        info.schemename + "/" + str(info.ampliconsize) + "/" + info.schemeversion
    )

    # Check the ref-selection
    if info.refselect is None:
        return

    for chrom, data in info.refselect.items():
        file_path = infopath.parent / data["filename"]
        # Check the file exists
        if not file_path.is_file():
            raise FileNotFoundError(f"{file_path} is not a file")

        # Check the md5
        file_md5 = hash_file(file_path)
        if data["md5"] != file_md5:
            raise ValueError(
                f"MD5 mismatch for {info_scheme_path}:{chrom}: info ({data['md5']}) != file ({file_md5})"
            )
        # Revalidate the ref-select file
        validate_ref_select_file(
            info=info, chrom=chrom, ref_select=file_path, infopath=infopath
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
    Validate a single scheme
    """

    # Get the schemename
    scheme_name = f"{schemeinfo.parent.parent.parent.name}/{schemeinfo.parent.parent.name}/{schemeinfo.parent.name}"

    errors = []

    try:
        validate_name(schemeinfo)
    except Exception as e:
        errors.append(str(e))
    try:
        bedfile = schemeinfo.parent / "primer.bed"
        validate_bedfile(bedfile)
    except Exception as e:
        errors.append(str(e))
    try:
        validate_hashes(schemeinfo)
    except Exception as e:
        errors.append(str(e))
    try:
        validate_ref_selection(schemeinfo)
    except Exception as e:
        errors.append(str(e))

    if errors:
        log.error(f"[red]Errored[/red]:\t[blue]{scheme_name}[/blue]")
        raise UsageError(message="\n".join(errors))
    else:
        log.info(f"[green]Success[/green]:\t[blue]{scheme_name}[/blue]")


@app.command(no_args_is_help=True)
def all_schemes(
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
    Validate all schemes in a directory. Calls the scheme command for each scheme.
    """
    errors = []
    for schemeinfo in directory.glob("**/info.json"):
        try:
            scheme(schemeinfo)
        except Exception as e:
            errors.append(str(e))

    if errors:
        raise UsageError(message="\n".join(errors))
