import hashlib
import json
import pathlib

import typer
from Bio import SeqIO
from typing_extensions import Annotated

from primal_page.bedfiles import (
    determine_bedfile_version,
    regenerate_v3_bedfile,
)
from primal_page.logging import log
from primal_page.modify import generate_files, hash_file, trim_file_whitespace
from primal_page.schemas import (
    INFO_SCHEMA,
    BedfileVersion,
    Info,
)

app = typer.Typer(no_args_is_help=True)


@app.command(no_args_is_help=True)
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

    # Hash the reference.fasta file
    # If the hash is different, rewrite the file
    ref_hash = hash_file(scheme_path / "reference.fasta")
    ref_str = "".join(
        x.format("fasta") for x in SeqIO.parse(scheme_path / "reference.fasta", "fasta")
    )
    if ref_hash != hashlib.md5(ref_str.encode()).hexdigest():
        with open(scheme_path / "reference.fasta", "w") as ref_file:
            ref_file.write(ref_str)

    # if articbedversion not set then set it
    articbedversion = determine_bedfile_version(scheme_path / "primer.bed")
    if articbedversion == BedfileVersion.INVALID:
        raise typer.BadParameter(
            f"Could not determine artic-primerbed version for {scheme_path / 'primer.bed'}"
        )
    info_json["articbedversion"] = articbedversion.value

    # Regenerate the files hashes
    info_json["primer_bed_md5"] = hash_file(scheme_path / "primer.bed")
    info_json["reference_fasta_md5"] = hash_file(scheme_path / "reference.fasta")

    info = Info(**info_json)
    info.infoschema = INFO_SCHEMA

    #####################################
    # Final validation and create files #
    #####################################

    generate_files(info, schemeinfo)


@app.command(no_args_is_help=True)
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
                log.info(f"Regenerating {schemename}/{ampliconsize}/{schemeversion}")
                info = schemeversion / "info.json"
                if info.exists():
                    # Modify the primer.bed
                    bedfile_str = regenerate_v3_bedfile(schemeversion / "primer.bed")

                    # If the bedfile is the same, dont write it
                    if bedfile_str == (schemeversion / "primer.bed").read_text():
                        log.info(
                            f"No changes to {schemename}/{ampliconsize}/{schemeversion}/primer.bed"
                        )
                    else:
                        with open(schemeversion / "primer.bed", "w") as f:
                            f.write(bedfile_str)

                    # Regenerate the info.json + README.md last, as has they contain the md5s
                    regenerate(info)
