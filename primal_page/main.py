import typer
import pathlib
from typing_extensions import Annotated
import shutil
import hashlib
import json
from typing import Optional
from enum import Enum
import requests

from primal_page.build_index import create_index
from primal_page.schemas import (
    PrimerClass,
    SchemeStatus,
    Info,
    determine_bedfile_version,
    BedfileVersion,
    validate_bedfile,
    BEDFILERESULT,
    Collection,
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


LICENSE_TXT_CC_BY_SA_4_0 = """\n\n------------------------------------------------------------------------

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/) 

![](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)"""


def trim_file_whitespace(in_path: pathlib.Path, out_path: pathlib.Path):
    """
    Trim whitespace from the ends of a file.
        - Reads file into memory. Not suitable for large files
    """
    with open(in_path, "r") as infile:
        input_file = infile.read().strip()

    with open(out_path, "w") as outfile:
        outfile.write(input_file)


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

        if info.description != None:
            readme.write(f"## Description\n\n")
            readme.write(f"{info.description}\n\n")

        readme.write(f"## Overviews\n\n")
        for png in pngs:
            readme.write(f"![{png.name}](work/{png.name})\n\n")

        readme.write(f"## Details\n\n")

        # Write the detials into the readme
        readme.write(f"""```json\n{info.model_dump_json(indent=4)}\n```\n\n""")

        if info.license == "CC BY-SA 4.0":
            readme.write(LICENSE_TXT_CC_BY_SA_4_0)


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
    schemestatus: Annotated[
        SchemeStatus, typer.Option(help="Scheme status")
    ] = SchemeStatus.DRAFT.value,  # type: ignore
    citations: Annotated[
        list[str], typer.Option(help="Any associated citations. Please use DOI")
    ] = [],
    authors: Annotated[list[str], typer.Option(help="Any authors")] = [
        "quick lab",
        "artic network",
    ],
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
        case BEDFILERESULT.VALID:
            pass
        case BEDFILERESULT.INVALID_VERSION:
            raise ValueError(
                f"Could not determine primerbed version for {valid_primer_bed}"
            )
        case BEDFILERESULT.INVALID_STRUCTURE:
            raise ValueError(
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
                raise ValueError(
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
    html = [path for path in found_files if path.name.endswith(".html")]
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
        authors=set(authors),
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
        for html in html:
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
        raise Exception(f"{e}\nCleaning up {repo_dir}")


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

    if info.status == schemestatus.value:
        raise ValueError(f"{schemeinfo} status is already {schemestatus}")
    else:
        info.status = schemestatus

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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
    """Append an author to the authors list in the info.json file"""

    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Check if author is already in the list
    info.primerclass = primerclass

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def add_author(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    author: Annotated[str, typer.Argument(help="The author to add")],
):
    """Append an author to the authors list in the info.json file"""

    info = json.load(schemeinfo.open())
    info = Info(**info)

    # Check if author is already in the list
    if author in info.authors:
        raise ValueError(f"{author} is already in the authors list")
    info.authors.add(author)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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

    # Check if author is already not in the list
    if author not in info.authors:
        raise ValueError(f"{author} is already not in the authors list")
    info.authors.remove(author)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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

    # Check if citation is already in the list
    if citation in info.citations:
        raise ValueError(f"{citation} is areadly in the citation list")
    info.citations.add(citation)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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

    if citation not in info.citations:
        raise ValueError(f"{citation} is not in the citation list")
    info.citations.remove(citation)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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
    if collection not in info.collections:
        raise ValueError(f"{collection} is already not in the collection list")
    info.collections.remove(collection)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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

    # Check if author is already not in the list
    if collection in info.collections:
        raise ValueError(f"{collection} is already in the collection list")
    info.collections.add(collection)

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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

    # Add the description
    if description == "None":
        info.description = None
    else:
        info.description = description.strip()

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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
    if derivedfrom == "None":
        info.derivedfrom = None
    else:
        info.derivedfrom = derivedfrom.strip()

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def license(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
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

    info.license = license.strip()

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


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
        raise ValueError(f"{schemeinfo} is not an info.json file")

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

    Ensures work/config.json has no absolute paths
        - Ensures hashes in config.json are removed
    """
    # Check that this is an info.json file (for safety)
    if schemeinfo.name != "info.json":
        raise ValueError(f"{schemeinfo} is not an info.json file")

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
        raise ValueError(
            f"Could not determine artic-primerbed version for {scheme_path / 'primer.bed'}"
        )
    info_json["articbedversion"] = articbedversion.value

    # Regenerate the files hashes
    info_json["primer_bed_md5"] = hashfile(scheme_path / "primer.bed")
    info_json["reference_fasta_md5"] = hashfile(scheme_path / "reference.fasta")

    info = Info(**info_json)

    # Get the pngs
    pngs = [path for path in scheme_path.rglob("*.png")]

    #####################################
    # Final validation and create files #
    #####################################

    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Regenerate the readme
    regenerate_readme(scheme_path, info, pngs)


@app.command()
def download(
    output: Annotated[pathlib.Path, typer.Option(help="Where to output the schemes")],
    index_url: Annotated[
        str, typer.Option(help="The URL to the index.json")
    ] = "https://raw.githubusercontent.com/quick-lab/primerschemes/main/index.json",
):
    """Download all schemes from the index.json"""
    # Download the index.json
    index = json.loads(requests.get(index_url).text)

    # Create the output directory
    output_primerschemes = output / "primerschemes"
    output_primerschemes.mkdir(exist_ok=False)

    # Grab the primerschemes
    primerschemes = index.get("primerschemes", {})

    # Download all the schemes
    for schemename in primerschemes:
        for ampliconsize in primerschemes[schemename]:
            for schemeversion in primerschemes[schemename][ampliconsize]:
                scheme = primerschemes[schemename][ampliconsize][schemeversion]
                scheme_dir = (
                    output_primerschemes
                    / schemename
                    / str(ampliconsize)
                    / schemeversion
                )
                scheme_dir.mkdir(parents=True, exist_ok=True)

                # Download the bedfile
                bedfile_url = scheme["primer_bed_url"]
                bedfile_text = requests.get(bedfile_url).text
                bedfile_hash = hashlib.md5(bedfile_text.encode()).hexdigest()
                # Check hashes before writing
                if bedfile_hash != scheme["primer_bed_md5"]:
                    raise ValueError(
                        f"Hash mismatch for {scheme['primer_bed_md5']}. Expected {scheme['primer_bed_md5']} but got {bedfile_hash}"
                    )
                # Write the file
                with open(scheme_dir / "primer.bed", "w") as f:
                    f.write(bedfile_text)

                # Download the reference
                reference_url = scheme["reference_fasta_url"]
                reference_text = requests.get(reference_url).text
                reference_hash = hashlib.md5(reference_text.encode()).hexdigest()
                # Check hashes before writing
                if reference_hash != scheme["reference_fasta_md5"]:
                    raise ValueError(
                        f"Hash mismatch for {scheme['reference_fasta_md5']}. Expected {scheme['reference_fasta_md5']} but got {reference_hash}"
                    )
                # Write the file
                with open(scheme_dir / "reference.fasta", "w") as f:
                    f.write(reference_text)

                # Download the info.json
                info_url = scheme["info_json_url"]
                info_text = requests.get(info_url).text
                # Write the file
                with open(scheme_dir / "info.json", "w") as f:
                    f.write(info_text)

                print(f"Downloaded:\t{schemename}/{ampliconsize}/{schemeversion}")


if __name__ == "__main__":
    app()
