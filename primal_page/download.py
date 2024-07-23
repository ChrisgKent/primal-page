import hashlib
import json
import pathlib

import requests
import typer
from typing_extensions import Annotated

from primal_page.logging import log
from primal_page.schemas import validate_schemename, validate_schemeversion

app = typer.Typer(no_args_is_help=True)


def validate_hashes(input_text: str, expected_hash: str, output_file: pathlib.Path):
    """
    Validate the hash of the input text. If the hash does not match the expected hash, raise a ValueError.
    If the hash does match, write the input text to the output file.
    """
    input_hash = hashlib.md5(input_text.encode()).hexdigest()
    if input_hash != expected_hash:
        raise ValueError(
            f"WARNING: HASH MISMATCH: Expected {expected_hash} but got {input_hash}. File not saved to disk."
        )

    # Write the file
    with open(output_file, "w") as f:
        f.write(input_text)


def download_scheme_func(
    schemename: str,
    ampliconsize: str,
    schemeversion: str,
    index: dict,
    output_dir: pathlib.Path,
):
    # Grab the primerschemes
    primerschemes = index.get("primerschemes", {})

    # Grab the scheme
    scheme = (
        primerschemes.get(schemename, {}).get(ampliconsize, {}).get(schemeversion, {})
    )
    if not scheme:
        raise ValueError(
            f"Scheme {schemename}/{ampliconsize}/{schemeversion} not found in index.json"
        )

    # Create the output directory
    scheme_dir = output_dir / schemename / str(ampliconsize) / schemeversion
    scheme_dir.mkdir(parents=True, exist_ok=True)

    # Download the bedfile
    bedfile_url = scheme["primer_bed_url"]
    bedfile_text = requests.get(bedfile_url).text

    # Validate the hash before write the file
    validate_hashes(bedfile_text, scheme["primer_bed_md5"], scheme_dir / "primer.bed")

    # Download the reference
    reference_url = scheme["reference_fasta_url"]
    reference_text = requests.get(reference_url).text

    # Validate the hash before write the file
    validate_hashes(
        reference_text,
        scheme["reference_fasta_md5"],
        scheme_dir / "reference.fasta",
    )

    # Download the info.json
    info_url = scheme["info_json_url"]
    info_text = requests.get(info_url).text
    # Write the file
    with open(scheme_dir / "info.json", "w") as f:
        f.write(info_text)

    log.info(f"Downloaded:\t{schemename}/{ampliconsize}/{schemeversion}")


def fetch_index(index_url: str) -> dict:
    """Download the index.json and return it as a dict"""
    try:
        r = requests.get(index_url)
        r.raise_for_status()
        index_json = json.loads(r.text)
        return index_json
    except requests.exceptions.HTTPError as err:
        raise err
    except json.JSONDecodeError as err:
        raise err


def download_all_func(index: dict, output: pathlib.Path):
    """Download all schemes from the index.json"""

    # Grab the primerschemes
    primerschemes = index.get("primerschemes", {})

    # Download all the schemes
    # Create a list of all schemes
    for schemename in primerschemes:
        for ampliconsize in primerschemes[schemename]:
            for schemeversion in primerschemes[schemename][ampliconsize]:
                download_scheme_func(
                    schemename, ampliconsize, schemeversion, index, output
                )


@app.command(no_args_is_help=True)
def all(
    output: Annotated[
        pathlib.Path,
        typer.Option(help="The directory the primerschemes dir will be created in"),
    ],
    index_url: Annotated[
        str, typer.Option(help="The URL to the index.json")
    ] = "https://raw.githubusercontent.com/quick-lab/primerschemes/main/index.json",
):
    """Download all schemes from the index.json"""
    # Fetch the index and store in memory
    index = fetch_index(index_url)

    # Create the output directory
    output_primerschemes = output / "primerschemes"
    output_primerschemes.mkdir(exist_ok=True)

    download_all_func(output=output, index=index)


@app.command(no_args_is_help=True)
def scheme(
    schemename: Annotated[
        str,
        typer.Argument(help="The name of the scheme", callback=validate_schemename),
    ],
    ampliconsize: Annotated[int, typer.Argument(help="Amplicon size")],
    schemeversion: Annotated[
        str, typer.Argument(help="Scheme version", callback=validate_schemeversion)
    ],
    output: Annotated[
        pathlib.Path,
        typer.Option(help="The directory the primerschemes dir will be created in"),
    ],
    index_url: Annotated[
        str, typer.Option(help="The URL to the index.json")
    ] = "https://raw.githubusercontent.com/quick-lab/primerschemes/main/index.json",
):
    """Download a scheme from the index.json"""

    # Fetch the index and store in memory
    index = fetch_index(index_url)

    # Create the output directory
    output_primerschemes = output / "primerschemes"
    output_primerschemes.mkdir(exist_ok=True)

    download_scheme_func(
        output_dir=output_primerschemes,
        index=index,
        schemename=schemename,
        ampliconsize=str(ampliconsize),
        schemeversion=schemeversion,
    )
