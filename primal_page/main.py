import typer
import pathlib
from typing_extensions import Annotated
import shutil
import hashlib
import json
import github
import os
from primal_page.build_index import create_index
from primal_page.schemas import PrimerClass, SchemeStatus, Info

SCHEMENAME_PATTERN = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"

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


def regenerate_readme(path: pathlib.Path, info: Info, pngs):
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


# GithubUploader
# Grabs the environment variables GITHUB_TOKEN
class GithubUploader:
    repo: str
    token: str
    authorname: str
    authoremail: str

    def __init__(self, reponame: str, token: str, authorname: str, authoremail: str):
        self.reponame = reponame
        self.token = token
        self.authorname = authorname
        self.authoremail = authoremail

        # Grab the github repo
        self.github = github.Github(self.token)
        self.repo = self.github.get_repo(self.reponame)

    def push(self, path, message, content, branch="dev", update=False):
        author = github.InputGitAuthor(self.authorname, self.authoremail)
        source = self.repo.get_branch("master")

        self.repo.create_git_ref(
            ref=f"refs/heads/{branch}", sha=source.commit.sha
        )  # Create new branch from master
        if update:  # If file already exists, update it
            contents = self.repo.get_contents(
                path, ref=branch
            )  # Retrieve old file to get its SHA and path
            self.repo.update_file(
                contents.path,
                message,
                content,
                contents.sha,
                branch=branch,
                author=author,
            )  # Add, commit and push branch
        else:  # If file doesn't exist, create it
            self.repo.create_file(
                path, message, content, branch=branch, author=author
            )  # Add, commit and push branch


def hashfile(fname: pathlib.Path) -> str:
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def validate_primer_bed(primer_bed: pathlib.Path, fix: bool = False):
    """Validate a primer bed file"""
    with open(primer_bed, "r") as f:
        for lineindex, line in enumerate(f.readlines()):
            data = line.strip().split("\t")

            # Check for 7 columns
            if len(data) != 7:
                raise ValueError(
                    f"Line {lineindex} in {primer_bed} does not have 7 columns"
                )

            # Check for valid primername
            primername = data[3].split("_")
            if len(primername) == 4 and primername[-1].isdigit():
                # Valid name
                pass
            else:
                raise ValueError(
                    f"Line {lineindex} in {primer_bed} does not have a valid primername '{data[3]}'"
                )
    return True


@app.command()
def create(
    schemepath: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to the scheme directory", readable=True),
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
    ] = SchemeStatus.DRAFT.value,
    citations: Annotated[list[str], typer.Option(help="Any associated citations")] = [],
    authors: Annotated[list[str], typer.Option(help="Any authors")] = [
        "quick lab",
        "artic network",
    ],
    schemename: Annotated[
        str,
        typer.Option(help="The name of the scheme, default is the directory name"),
    ] = None,
    primerbed: Annotated[
        pathlib.Path,
        typer.Option(
            help="Manually specify the primer bed file, default is *primer.bed",
            readable=True,
        ),
    ] = None,
    reference: Annotated[
        pathlib.Path,
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
        pathlib.Path,
        typer.Option(
            help="Where the config.json file is located", readable=True, exists=True
        ),
    ] = None,
    algorithmversion: Annotated[
        str, typer.Option(help="The version of primalscheme or other")
    ] = None,
    description: Annotated[
        str, typer.Option(help="A description of the scheme")
    ] = None,
):
    """Create a new scheme in the required format"""

    # Search for scheme repo for files
    found_files = [x for x in schemepath.rglob("*")]

    # Search for a single *.primer.bed
    if primerbed is None:
        primer_bed = [path for path in found_files if path.name.endswith("primer.bed")]
        if len(primer_bed) == 1:
            primer_bed = primer_bed[0]
        else:
            raise FileNotFoundError(
                f"Could not find a SINGLE *.primer.bed file in {schemepath} or its subdirectories, found {len(primer_bed)}. Please specify manually with --primerbed"
            )
    elif not primerbed.exists():
        raise FileNotFoundError(f"Could not find file at {primerbed}")

    # Search for reference.fasta
    if reference is None:
        # Search for a single *.fasta
        reference = [
            path
            for path in found_files
            if path.name == ("reference.fasta") or path.name == ("referance.fasta")
        ]
        if len(reference) == 1:
            reference = reference[0]
        else:
            raise FileNotFoundError(
                f"Could not find a SINGLE reference.fasta file in {schemepath} or its subdirectories, found {len(reference)}. Please specify manually with --reference"
            )
    elif not reference.exists():
        raise FileNotFoundError(f"Could not find file at {reference}")

    # Search for config.json
    if configpath is None:
        config = [path for path in found_files if path.name == ("config.json")]
        if len(config) == 1:
            configpath = config[0]

        else:
            raise FileNotFoundError(
                f"Could not find a SINGLE config file in {schemepath} or its subdirectories, found {len(config)}. Please specify manually with --config"
            )
    # Read in the config
    config_json: dict = json.load(configpath.open())
    # Read in the config.json file and grab some info

    # parse the config.json to get algorithm
    if algorithmversion is None and "algorithmversion" in config_json.keys():
        algorithmversion = config_json["algorithmversion"]
    elif algorithmversion is not None:
        algorithmversion = algorithmversion
    else:
        raise ValueError(
            f"Could not find primaldigest_version in config.json, please specify manually with --algorithmversion, in form of 'algorithmversion':'version'"
        )

    # Remove some paths from the config
    if "output_dir" in config_json.keys():
        config_json.pop("output_dir")

    # Multiple pngs/htmls/msas are allowed
    # The single check is mainly to prevent multiple schemes via providing the wrong directory
    # At this point we know we have a single scheme

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

    # Create the info.json
    # Generate the md5s
    info = Info(
        ampliconsize=ampliconsize,
        schemeversion=schemeversion,
        schemename=schemename,
        primer_bed_md5=hashfile(primer_bed),
        reference_fasta_md5=hashfile(reference),
        status=schemestatus,
        citations=citations,
        authors=authors,
        algorithmversion=algorithmversion,
        species=species,
        description=description,
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
        # Copy files
        shutil.copy(primer_bed, repo_dir / "primer.bed")
        shutil.copy(reference, repo_dir / "reference.fasta")

        working_dir = repo_dir / "work"
        working_dir.mkdir()

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
        raise Exception(f"{e}\Cleaning up {repo_dir}")


@modify_app.command()
def change_status(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
    schemestatus: Annotated[
        SchemeStatus,
        typer.Option(
            help="The scheme class",
        ),
    ] = SchemeStatus.DRAFT.value,
):
    """Change the status field in the info.json"""

    info = json.load(schemeinfo.open())
    info = Info(**info)

    if info.status == schemestatus.value:
        raise ValueError(f"{schemeinfo} status is already {schemestatus.values}")
    else:
        info.status = schemestatus.value

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


@app.command()
def build_index(
    gitaccount: Annotated[
        str,
        typer.Argument(help="The name of the github account"),
    ] = "quick-lab",
    gitserver: Annotated[
        str,
        typer.Argument(help="The name of the github server"),
    ] = "https://github.com/",
):
    """Build an index.json file from all schemes in the directory"""

    create_index(gitserver, gitaccount)


@app.command()
def remove(
    schemeinfo: Annotated[
        pathlib.Path,
        typer.Argument(help="The path to info.json", readable=True, exists=True),
    ],
):
    """Remove a scheme's version from the repo, this can leave an empty schemename/size directory"""
    # Check that this is an info.json file (for safety)
    if schemeinfo.name != "info.json":
        raise ValueError(f"{schemeinfo} is not an info.json file")

    # Remove the schemeversion directory
    shutil.rmtree(schemeinfo.parent)


if __name__ == "__main__":
    app()
