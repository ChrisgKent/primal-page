import json
import pathlib
import shutil
from enum import Enum
from typing import Optional

import typer
from Bio import SeqIO
from typing_extensions import Annotated

from primal_page.__init__ import __version__
from primal_page.aliases import app as aliases_app
from primal_page.bedfiles import (
    BEDFileResult,
    BedfileVersion,
    determine_bedfile_version,
    regenerate_v3_bedfile,
    validate_bedfile,
)
from primal_page.build_index import create_index
from primal_page.dev import app as dev_app
from primal_page.download import app as download_app
from primal_page.errors import FileNotFound, InvalidReference, SchemeExists
from primal_page.logging import log
from primal_page.modify import app as modify_app
from primal_page.modify import (
    generate_files,
    hash_file,
    trim_file_whitespace,
)
from primal_page.schemas import (
    Collection,
    Info,
    IUPACAmbiguousDNA,
    Links,
    PrimerClass,
    SchemeStatus,
)


class FindResult(Enum):
    NOT_FOUND = 1
    FOUND = 2


# Create the typer app
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
app.add_typer(
    modify_app,
    name="modify",
    help="Modify an existing scheme's metadata (info.json)",
)
app.add_typer(
    download_app,
    name="download",
    help="Download schemes from the index.json",
)
app.add_typer(dev_app, name="dev", help="Development commands", hidden=True)
app.add_typer(aliases_app, name="aliases", help="Manage aliases")


def typer_callback_version(value: bool):
    if value:
        typer.echo(f"primal-page version: {__version__}")
        raise typer.Exit()


@app.callback()
def primal_page(
    value: Annotated[bool, typer.Option] = typer.Option(
        False, "--version", callback=typer_callback_version
    ),
):
    pass


def validate_ref_file(ref_file: pathlib.Path):
    """
    Validate the reference.fasta file
    :param ref_file: The path to the reference.fasta file
    :raises InvalidReference: If the reference.fasta file is invalid
    """
    # Very simple fasta validation
    try:
        records = SeqIO.index(ref_file, "fasta")
    except Exception as e:
        raise InvalidReference(f"Could not validate {ref_file}: {e}") from e

    for record in records.values():
        seq_bases = set(record.seq.upper())
        # Check DNA sequence
        if not seq_bases.issubset(IUPACAmbiguousDNA):
            raise InvalidReference(
                f"Invalid DNA bases ({', '.join(seq_bases.difference(IUPACAmbiguousDNA))}) found in {ref_file}: {record.id}"
            )
        if len(record.seq) == 0:
            raise InvalidReference(f"Empty sequence found in {ref_file}")


def find_ref(
    cli_reference: pathlib.Path | None,
    found_files: list[pathlib.Path],
    schemepath: pathlib.Path,
) -> pathlib.Path:
    """
    Find the reference.fasta file
    :param cli_reference: The reference.fasta file specified by the user. None if not specified
    :param found_files: A list of all files found in the scheme directory
    :param schemepath: The path to the scheme directory
    :return: The path to the reference.fasta file
    :raises FileNotFound: If the reference.fasta file cannot be found
    """
    # Search for reference.fasta
    if cli_reference is None:  # No reference specified
        # Search for a single *.fasta
        reference_list: list[pathlib.Path] = [
            path for path in found_files if path.name == ("reference.fasta")
        ]
        if len(reference_list) == 1:
            return reference_list[0]
        else:
            raise FileNotFound(
                f"Could not find a SINGLE reference.fasta file in {schemepath} or its subdirectories, found {len(reference_list)}. Please specify manually with --reference"
            )
    elif cli_reference.exists():
        validate_ref_file(cli_reference)
        return cli_reference
    else:
        raise FileNotFound(f"Could not find file at {cli_reference}")


def find_primerbed(
    cli_primerbed: pathlib.Path | None,
    found_files: list[pathlib.Path],
    schemepath: pathlib.Path,
) -> pathlib.Path:
    """
    Find the primer.bed file
    :param cli_primerbed: The primer.bed file specified by the user. None if not specified
    :param found_files: A list of all files found in the scheme directory
    :param schemepath: The path to the scheme directory
    :return: The path to the primer.bed file
    :raises FileNotFound: If the primer.bed file cannot be found
    """
    # Search for primer.bed
    if cli_primerbed is None:  # No primer.bed specified
        # Search for a single *.primer.bed
        primer_bed_list: list[pathlib.Path] = [
            path for path in found_files if path.name.endswith("primer.bed")
        ]
        if len(primer_bed_list) == 1:
            return primer_bed_list[0]
        else:
            raise FileNotFound(
                f"Could not find a SINGLE *.primer.bed file in {schemepath} or its subdirectories, found {len(primer_bed_list)}. Please specify manually with --primerbed"
            )
    elif cli_primerbed.exists():
        return cli_primerbed
    else:
        raise FileNotFound(f"Could not find file at {cli_primerbed}")


def find_config(
    cli_config: pathlib.Path | None,
    found_files: list[pathlib.Path],
    schemepath: pathlib.Path,
) -> tuple[FindResult, pathlib.Path | None]:
    """
    Find the config.json file
    :param cli_config: The config.json file specified by the user. None if not specified
    :param found_files: A list of all files found in the scheme directory
    :param schemepath: The path to the scheme directory
    :return: The path to the config.json file
    """
    # Search for config.json
    if cli_config is None:  # No config.json specified
        # Search for a single config.json
        config_list: list[pathlib.Path] = [
            path for path in found_files if path.name == ("config.json")
        ]
        match len(config_list):
            case 1:
                return (FindResult.FOUND, config_list[0])
            case _:
                return (FindResult.NOT_FOUND, None)

    elif cli_config.exists():
        # TODO validate the config.json file
        return (FindResult.FOUND, cli_config)
    else:
        return (FindResult.NOT_FOUND, None)


@app.command(no_args_is_help=True)
def create(
    schemepath: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to the primerscheme directory", readable=True),
    ],
    schemename: Annotated[
        str,
        typer.Option(help="The name of the scheme"),
    ],
    ampliconsize: Annotated[
        int,
        typer.Option(help="Amplicon size", min=100),
    ],
    schemeversion: Annotated[
        str,
        typer.Option(
            help="Scheme version, default is parsed from config.json",
        ),
    ],
    species: Annotated[
        list[int],
        typer.Option(
            help="The species this scheme targets. Please use NCBI taxonomy ids"
        ),
    ],
    authors: Annotated[list[str], typer.Option(help="Any authors")],
    schemestatus: Annotated[
        SchemeStatus, typer.Option(help="Scheme status")
    ] = SchemeStatus.DRAFT.value,  # type: ignore
    citations: Annotated[
        list[str], typer.Option(help="Any associated citations. Please use DOI")
    ] = [],
    primerbed: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Manually specify the primer bed file, default is *primer.bed",
            readable=True,
        ),
    ] = None,
    reference: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Manually specify the reference.fasta file, default is *.fasta",
            readable=True,
        ),
    ] = None,
    output: Annotated[
        pathlib.Path,
        typer.Option(help="Where to output the scheme", writable=True),
    ] = pathlib.Path("primerschemes"),
    configpath: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Where the config.json file is located", readable=True, exists=True
        ),
    ] = None,
    algorithmversion: Annotated[
        Optional[str], typer.Option(help="The version of primalscheme or other")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option(help="A description of the scheme")
    ] = None,
    derivedfrom: Annotated[
        Optional[str],
        typer.Option(help="Which scheme has this scheme been derived from"),
    ] = None,
    primerclass: Annotated[
        PrimerClass, typer.Option(help="The primer class")
    ] = PrimerClass.PRIMERSCHEMES.value,  # type: ignore
    collection: Annotated[
        Optional[list[Collection]], typer.Option(help="The collection")
    ] = None,
    link_protocol: Annotated[
        list[str], typer.Option(help="Optional link to protocol")
    ] = [],
    link_validation: Annotated[
        list[str], typer.Option(help="Optional link to validation data")
    ] = [],
    links_homepage: Annotated[
        list[str], typer.Option(help="Optional link to homepage")
    ] = [],
    link_vendor: Annotated[
        list[str], typer.Option(help="Optional link to vendors")
    ] = [],
    link_misc: Annotated[
        list[str], typer.Option(help="Optional miscellaneous link")
    ] = [],
    fix: Annotated[bool, typer.Option(help="Attempt to fix the scheme")] = False,
):
    """Create a new scheme in the required format"""

    # Search for scheme repo for files
    found_files = [x for x in schemepath.rglob("*")]

    # Check for a single primer.bed file
    valid_primer_bed = find_primerbed(
        cli_primerbed=primerbed, found_files=found_files, schemepath=schemepath
    )

    match validate_bedfile(valid_primer_bed):
        case BEDFileResult.VALID:
            pass
        case BEDFileResult.INVALID_VERSION:
            raise typer.BadParameter(
                f"Could not determine primerbed version for {valid_primer_bed}"
            )
        case BEDFileResult.INVALID_STRUCTURE:
            raise typer.BadParameter(
                f"Invalid primerbed structure for {valid_primer_bed}. Please ensure it is a valid 7 column bedfile"
            )
    # Get primerbed version
    primerbed_version: BedfileVersion = determine_bedfile_version(valid_primer_bed)

    if primerbed_version != BedfileVersion.V3:
        if fix:
            try:
                bedfile_str = regenerate_v3_bedfile(valid_primer_bed)
            except Exception as e:
                raise typer.BadParameter(
                    f"Could not fix the primerbed file: {e}"
                ) from e
        else:
            raise typer.BadParameter(
                f"Primerbed version {primerbed_version.value} is not supported. Please update to v3.0 bedfile (See FAQ), or try with --fix to attempt to parse."
            )

    # Find the reference.fasta file
    valid_ref = find_ref(reference, found_files, schemepath)

    # Search for config.json
    status, conf_path = find_config(configpath, found_files, schemepath)
    config_json: None | dict = None  # type: ignore
    if status == FindResult.FOUND and conf_path is not None:  # Second check is for mypy
        configpath = conf_path
        # Read in the config
        config_json: dict = json.load(configpath.open())
        # Remove some paths from the config
        config_json.pop("output_dir", None)
        # These hashes are no longer used, so remove to prevent confusion
        md5s_keys_to_remove = {k for k in config_json.keys() if k.endswith("md5")}
        for k in md5s_keys_to_remove:
            config_json.pop(k)

        if algorithmversion is None:
            if "algorithmversion" in config_json.keys():
                algorithmversion = str(config_json["algorithmversion"])
            else:
                raise typer.BadParameter(
                    f"algorithmversion not specified in {configpath}. Please specify manually with --algorithmversion"
                )

    elif status == FindResult.NOT_FOUND:
        if algorithmversion is None:
            raise FileNotFound(
                f"Could not find a config.json file in {schemepath}. Please specify manually with --configpath or specify algorithmversion with --algorithmversion"
            )

    # Multiple pngs/htmls/msas are allowed
    # The single check is mainly to prevent multiple schemes via providing the wrong directory
    # At this point we know we have a single scheme, due to having a single primer.bed, reference.fasta, and config.json

    # Search for pngs
    pngs = [path for path in found_files if path.name.endswith(".png")]
    # Search for html
    htmls = [path for path in found_files if path.name.endswith(".html")]
    # Search for msas
    msas = [
        path
        for path in found_files
        if path.name.endswith(".fasta") and path.name != "reference.fasta"
    ]

    # Copy all additional files to working directory
    # This is done to prevent preserve the original files
    misc_files_to_copy = [
        x
        for x in found_files
        if not x.name.endswith("primer.bed")
        and not x.name.endswith("config.json")
        and not x.name.endswith("info.json")
        and not x.name.endswith(".fasta")
        and not x.name.endswith(".png")
        and not x.name.endswith(".html")
        and not x.name.endswith(".db")  # Dont copy the mismatches db
        and x.name != ".DS_Store"  # Dont copy the macos file
        and x.is_file()
    ]

    # Create the collections set
    collections = {x for x in collection} if collection is not None else set()

    # Create the links set
    links = Links(
        protocols=link_protocol,
        validation=link_validation,
        homepage=links_homepage,
        vendors=link_vendor,
        misc=link_misc,
    )
    # Create the info.json
    # Generate the md5s
    info = Info(
        ampliconsize=ampliconsize,
        schemeversion=schemeversion,
        schemename=schemename,
        primer_bed_md5="NONE",  # Will be updated later
        reference_fasta_md5="NONE",  # Will be updated later
        status=schemestatus,
        citations=set(citations),
        authors=authors,
        algorithmversion=algorithmversion,  # type: ignore
        species=set(species),
        description=description,
        derivedfrom=derivedfrom,
        primerclass=primerclass,
        articbedversion=primerbed_version,
        collections=collections,
        links=links,
    )

    #####################################
    # Final validation and create files #
    #####################################
    # Everything needs to be validated before creating files

    # Check if the repo already exists
    repo_dir = output / schemename / str(ampliconsize) / schemeversion
    if repo_dir.exists():
        raise SchemeExists(f"{repo_dir} already exists")
    repo_dir.mkdir(parents=True)

    # If this fails it will deleted the half completed scheme
    # Need to check the repo doesn't already exist
    try:
        # Copy files and trim whitespace
        if fix:
            with open(repo_dir / "primer.bed", "w") as bedfile:
                bedfile.write(bedfile_str)
        else:
            trim_file_whitespace(valid_primer_bed, repo_dir / "primer.bed")
        # parse the reference.fasta file
        with open(repo_dir / "reference.fasta", "w") as ref_file:
            records = list(SeqIO.parse(valid_ref, "fasta"))
            # Ensure the sequence is uppercase
            for r in records:
                r.seq = r.seq.upper()
            SeqIO.write(records, ref_file, "fasta")

        # Update the hashes in the info.json
        info.primer_bed_md5 = hash_file(repo_dir / "primer.bed")
        info.reference_fasta_md5 = hash_file(repo_dir / "reference.fasta")

        working_dir = repo_dir / "work"
        working_dir.mkdir()

        if config_json is not None:
            # Write out the config.json
            with open(working_dir / "config.json", "w") as configfile:
                json.dump(config_json, configfile, indent=4, sort_keys=True)

        # Copy over misc files
        for misc_file in misc_files_to_copy:
            shutil.copy(misc_file, working_dir / misc_file.name)

        # Copy the pngs
        for png in pngs:
            shutil.copy(png, working_dir / png.name)
        # Copy the htmls
        for html in htmls:
            shutil.copy(html, working_dir / html.name)
        # Copy the msas
        for msa in msas:
            shutil.copy(msa, working_dir / msa.name)

        # Write out the info.json and readme
        generate_files(info, repo_dir)

    except Exception as e:
        # Cleanup
        shutil.rmtree(repo_dir)
        raise typer.BadParameter(f"{e}\nCleaning up {repo_dir}") from e


@app.command(no_args_is_help=True)
def build_index(
    gitaccount: Annotated[
        str,
        typer.Option(help="The name of the github account"),
    ] = "quick-lab",
    gitserver: Annotated[
        str,
        typer.Option(help="The name of the github server"),
    ] = "https://github.com/",
    parentdir: Annotated[
        pathlib.Path, typer.Option(help="The parent directory")
    ] = pathlib.Path("."),
    git_commit_sha: Annotated[
        Optional[str], typer.Option(help="The git commit")
    ] = None,
    force: Annotated[
        bool, typer.Option(help="Force the creation of the index.json")
    ] = False,
):
    """Build an index.json file from all schemes in the directory"""

    create_index(gitserver, gitaccount, parentdir, git_commit_sha, force)


@app.command(no_args_is_help=True)
def remove(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
):
    """Remove a scheme's version from the repo, will also remove size and schemename directories if empty"""
    # Check that this is an info.json file (for safety)
    if schemeinfo.name != "info.json":
        raise typer.BadParameter(f"{schemeinfo} is not an info.json file")

    # Remove the schemeversion directory
    shutil.rmtree(schemeinfo.parent)

    # Move up the path and remove the size directory if empty
    size_dir = schemeinfo.parent.parent
    if len(list(size_dir.iterdir())) == 0:
        size_dir.rmdir()

    # Move up the path and remove the schemename directory if empty
    scheme_dir = size_dir.parent
    if len(list(scheme_dir.iterdir())) == 0:
        scheme_dir.rmdir()

    log.info(f"Removed {schemeinfo}")


if __name__ == "__main__":
    app()
