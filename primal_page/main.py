import hashlib
import json
import pathlib
import shutil
from enum import Enum
from typing import Optional

import typer
from typing_extensions import Annotated

from primal_page.bedfiles import (
    BEDFileResult,
    BedfileVersion,
    determine_bedfile_version,
    validate_bedfile,
)
from primal_page.build_index import create_index
from primal_page.download import download_all_func, download_scheme_func, fetch_index
from primal_page.modify import regenerate_files, regenerate_readme
from primal_page.schemas import (
    INFO_SCHEMA,
    Collection,
    Info,
    PrimerClass,
    SchemeStatus,
    validate_schemename,
    validate_schemeversion,
)


class FindResult(Enum):
    NOT_FOUND = 1
    FOUND = 2


# Create the typer app
app = typer.Typer()
modify_app = typer.Typer()
app.add_typer(
    modify_app,
    name="modify",
    help="Modify an existing scheme's metadata (info.json)",
)


def trim_file_whitespace(in_path: pathlib.Path, out_path: pathlib.Path):
    """
    Trim whitespace from the ends of a file.
        - Reads file into memory. Not suitable for large files
    """
    with open(in_path) as infile:
        input_file = infile.read().strip()

    with open(out_path, "w") as outfile:
        outfile.write(input_file)


def hashfile(fname: pathlib.Path) -> str:
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
    :raises FileNotFoundError: If the reference.fasta file cannot be found
    """
    # Search for reference.fasta
    if cli_reference is None:  # No reference specified
        # Search for a single *.fasta
        reference_list: list[pathlib.Path] = [
            path
            for path in found_files
            if path.name == ("reference.fasta") or path.name == ("referance.fasta")
        ]
        if len(reference_list) == 1:
            return reference_list[0]
        else:
            raise FileNotFoundError(
                f"Could not find a SINGLE reference.fasta file in {schemepath} or its subdirectories, found {len(reference_list)}. Please specify manually with --reference"
            )
    elif cli_reference.exists():
        # TODO validate the reference.fasta file
        return cli_reference
    else:
        raise FileNotFoundError(f"Could not find file at {cli_reference}")


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
    :raises FileNotFoundError: If the primer.bed file cannot be found
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
            raise FileNotFoundError(
                f"Could not find a SINGLE *.primer.bed file in {schemepath} or its subdirectories, found {len(primer_bed_list)}. Please specify manually with --primerbed"
            )
    elif cli_primerbed.exists():
        return cli_primerbed
    else:
        raise FileNotFoundError(f"Could not find file at {cli_primerbed}")


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


@app.command()
def create(
    schemepath: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to the scheme directory", readable=True),
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
            help="Manually specify the referance.fasta file, default is *.fasta",
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
):
    """Create a new scheme in the required format"""

    # Search for scheme repo for files
    found_files = [x for x in schemepath.rglob("*")]

    # Check for a single primer.bed file
    valid_primer_bed = find_primerbed(primerbed, found_files, schemepath)

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
            raise FileNotFoundError(
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
    )

    #####################################
    # Final validation and create files #
    #####################################
    # Everything needs to be validated before creating files

    # Check if the repo already exists
    repo_dir = output / schemename / str(ampliconsize) / schemeversion
    if repo_dir.exists():
        raise FileExistsError(f"{repo_dir} already exists")
    repo_dir.mkdir(parents=True)

    # If this fails it will deleted the half completed scheme
    # Need to check the repo doesnt already exist
    try:
        # Copy files and trim whitespace
        trim_file_whitespace(valid_primer_bed, repo_dir / "primer.bed")
        trim_file_whitespace(valid_ref, repo_dir / "reference.fasta")

        # Update the hashes in the info.json
        info.primer_bed_md5 = hashfile(repo_dir / "primer.bed")
        info.reference_fasta_md5 = hashfile(repo_dir / "reference.fasta")

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

        # Write info.json
        with open(repo_dir / "info.json", "w") as infofile:
            infofile.write(info.model_dump_json(indent=4))

        # Create a README.md with link to all pngs
        regenerate_readme(repo_dir, info, pngs)
    except Exception as e:
        # Cleanup
        shutil.rmtree(repo_dir)
        raise typer.BadParameter(f"{e}\nCleaning up {repo_dir}") from None


@modify_app.command()
def status(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    schemestatus: Annotated[
        SchemeStatus,
        typer.Option(
            help="The scheme class",
        ),
    ] = SchemeStatus.DRAFT,
):
    """Change the status field in the info.json"""

    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Change the status
    info.change_status(schemestatus)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def primerclass(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    primerclass: Annotated[
        PrimerClass, typer.Argument(help="The primerclass to change to")
    ],
):
    """Change the primerclass field in the info.json"""

    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Change the primerclass
    info.change_primerclass(primerclass)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def add_author(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
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

    info = json.load(schemeinfo.open())
    info = Info(**info)

    info.add_author(author, author_index)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def remove_author(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    author: Annotated[str, typer.Argument(help="The author to remove")],
):
    """Remove an author from the authors list in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    try:
        info.remove_author(author)
    except KeyError:
        raise typer.BadParameter(f"{author} is already not present") from None

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def reorder_authors(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    author_index: Annotated[
        Optional[str],
        typer.Argument(
            help="The indexes in the new order, seperated by spaces. e.g. 1 0 2. Any indexes not provided will be appended to the end"
        ),
    ] = None,
):
    """Reorder the authors in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Reorder interactively
    if author_index is None:
        # Current order
        typer.echo("Current order:")
        for index, author in enumerate(info.authors):
            typer.echo(f"{index}: {author}")

        # Get the new order
        new_order_str: str = typer.prompt(
            "Please provide the indexes in the new order, seperated by spaces. e.g. 1 0 2. Any indexes not provided will be appended to the end",
            type=str,
        )
        new_order = [int(x) for x in new_order_str.split()]
    else:  # Reorder via cli
        new_order = [int(x) for x in author_index.split()]

    try:
        info.reorder_authors(new_order)
    except ValueError as e:
        raise typer.BadParameter(f"{e}") from None
    except IndexError as e:
        raise typer.BadParameter(f"{e}") from None

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def add_citation(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    citation: Annotated[str, typer.Argument(help="The citation to add")],
):
    """Append an citation to the authors list in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Add the citation
    info.add_citation(citation)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def remove_citation(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    citation: Annotated[str, typer.Argument(help="The citation to remove")],
):
    """Remove an citation form the authors list in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    try:
        info.remove_citation(citation)
    except KeyError:
        raise typer.BadParameter(f"{citation} is already not present") from None

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def remove_collection(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    collection: Annotated[Collection, typer.Argument(help="The Collection to remove")],
):
    """Remove an Collection from the Collection list in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Check if collection is already not in the list
    try:
        info.remove_collection(collection)
    except KeyError:
        raise typer.BadParameter(f"{collection} is already not present") from None

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def add_collection(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    collection: Annotated[Collection, typer.Argument(help="The Collection to add")],
):
    """Add a Collection to the Collection list in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    info.add_collection(collection)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def description(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    description: Annotated[
        str,
        typer.Argument(
            help="The new description. Use 'None' to remove the description"
        ),
    ],
):
    """Replaces the description in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Change the description
    info.change_description(description.strip())

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def derivedfrom(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    derivedfrom: Annotated[
        str,
        typer.Argument(
            help="The new derivedfrom. Use 'None' to remove the derivedfrom"
        ),
    ],
):
    """Replaces the derivedfrom in the info.json file"""
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Add the derivedfrom
    info.change_derivedfrom(derivedfrom.strip())

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@modify_app.command()
def license(
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
    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Change the license
    info.change_license(license)

    # Write the validated info.json and regenerate the README
    regenerate_files(info, schemeinfo)


@app.command()
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


@app.command()
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
def download_all(
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


@app.command()
def download_scheme(
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


if __name__ == "__main__":
    app()
