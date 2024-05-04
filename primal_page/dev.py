import json
import pathlib

import typer
from typing_extensions import Annotated

from primal_page.bedfiles import (
    determine_bedfile_version,
    regenerate_v3_bedfile,
)
from primal_page.modify import hashfile, regenerate_files, trim_file_whitespace
from primal_page.schemas import (
    INFO_SCHEMA,
    BedfileVersion,
    Info,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def regenerate(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
):
    """
    Regenerate the info.json and README.md file for a scheme
        - Rehashes info.json's primer_bed_md5 and reference_fasta_md5
        - Regenerates the README.md file
        - Recalculate the artic-primerbed version
        - Updates the infoschema version to current

    Ensures work/config.json has no absolute paths
        - Ensures hashes in config.json are removed
    """
    # Check that this is an info.json file (for safety)
    if schemeinfo.name != "info.json":
        raise typer.BadParameter(f"{schemeinfo} is not an info.json file")

    # Get the scheme path
    scheme_path = schemeinfo.parent

    # Get the info
    info_json = json.load(schemeinfo.open())

    # Trim whitespace from primer.bed and reference.fasta
    trim_file_whitespace(scheme_path / "primer.bed", scheme_path / "primer.bed")
    trim_file_whitespace(
        scheme_path / "reference.fasta", scheme_path / "reference.fasta"
    )

    # if articbedversion not set then set it
    articbedversion = determine_bedfile_version(scheme_path / "primer.bed")
    if articbedversion == BedfileVersion.INVALID:
        raise typer.BadParameter(
            f"Could not determine artic-primerbed version for {scheme_path / 'primer.bed'}"
        )
    info_json["articbedversion"] = articbedversion.value

    # Regenerate the files hashes
    info_json["primer_bed_md5"] = hashfile(scheme_path / "primer.bed")
    info_json["reference_fasta_md5"] = hashfile(scheme_path / "reference.fasta")

    info = Info(**info_json)
    info.infoschema = INFO_SCHEMA

    #####################################
    # Final validation and create files #
    #####################################

    regenerate_files(info, schemeinfo)


@app.command()
def migrate(
    primerschemes: Annotated[pathlib.Path, typer.Argument(help="The parent directory")],
):
    """
    THIS MODIFIES THE SCHEMES IN PLACE. USE WITH CAUTION
        Regenerates all schemes in the primerschemes directory.
        Mainly used for migrating to the new info.json schema.
    """
    # Get all the schemes
    for schemename in primerschemes.iterdir():
        if not schemename.is_dir():
            continue
        for ampliconsize in schemename.iterdir():
            if not ampliconsize.is_dir():
                continue
            for schemeversion in ampliconsize.iterdir():
                if not schemeversion.is_dir():
                    continue
                print(f"Regenerating {schemeversion}")
                info = schemeversion / "info.json"
                if info.exists():
                    # Modify the primer.bed
                    bedfile_str = regenerate_v3_bedfile(schemeversion / "primer.bed")

                    # If the bedfile is the same, dont write it
                    if bedfile_str == (schemeversion / "primer.bed").read_text():
                        print("No changes to primer.bed")
                    else:
                        with open(schemeversion / "primer.bed", "w") as f:
                            f.write(bedfile_str)

                    # Regenerate the info.json + README.md last, as has they contain the md5s
                    regenerate(info)