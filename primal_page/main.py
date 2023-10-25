import typer
import pathlib
from typing_extensions import Annotated
import re
import shutil
import hashlib
import json
import github
import os
from enum import Enum
from primal_page.build_index import create_index


class PrimerClass(Enum):
    PRIMERSCHEMES = "primerschemes"
    PRIMERPANELS = "primerpanels"


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


LICENSE_TXT = """\n\n------------------------------------------------------------------------

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/) 

![](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)"""


def regenerate_readme(path: pathlib.Path, info_json: dict, pngs):
    with open(path / "README.md", "w") as readme:
        readme.write(
            f"# {info_json['schemename']} {info_json['ampliconsize']}bp {info_json['schemeversion']}\n\n"
        )
        readme.write(f"## Overviews\n\n")
        for png in pngs:
            readme.write(f"![{png.name}](work/{png.name})\n\n")

        readme.write(f"## Details\n\n")

        info_str = json.dumps(info_json, indent=4, sort_keys=True)

        readme.write(f"""```json\n{info_str}\n```\n\n""")

        readme.write(LICENSE_TXT)


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
    validated: Annotated[bool, typer.Option(help="Is the scheme validated")] = False,
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
):
    """Create a new scheme in the required format"""

    info_json = {
        "ampliconsize": ampliconsize,
        "schemeversion": None,
        "schemename": None,
        "primer.bed.md5": None,
        "reference.fasta.md5": None,
        "validated": validated,
        "citations": citations,
        "authors": authors,
        "algorithmversion": None,
    }

    # parse scheme version
    if not re.match(VERSION_PATTERN, schemeversion):
        raise ValueError(
            f"{schemeversion} is not a valid scheme version, must match be in form of v(int).(int).(int)"
        )
    else:
        info_json["schemeversion"] = schemeversion

    # parse scheme name
    if schemename is None:
        schemename = schemepath.name
    if not re.match(SCHEMENAME_PATTERN, schemename) or "--" in schemename:
        raise ValueError(
            f"{schemename} is not a valid scheme name, must match {SCHEMENAME_PATTERN}"
        )
    else:
        info_json["schemename"] = schemename

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
    config = [path for path in found_files if path.name == ("config.json")]
    if len(config) == 1:
        config = config[0]
    else:
        print(
            f"Could not find a SINGLE config.json file in {schemepath} or its subdirectories, found {len(config)}"
        )
        config = None

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
        and not x.name.endswith(".fasta")
        and not x.name.endswith(".png")
        and not x.name.endswith(".html")
        and not x.name.endswith(".db")  # Dont copy the mismatches db
        and x.name != ".DS_Store"  # Dont copy the macos file
        and x.is_file()
    ]

    # Read in the config.json file and grab some info
    if config is not None:
        with open(config, "r") as f:
            config_json = json.load(f)
            info_json["algorithmversion"] = config_json["primaldigest_version"]

    #####################################
    # Final validation and create files #
    #####################################
    # Everything needs to be validated before creating files

    ## Generate file hashes
    info_json["primer.bed.md5"] = hashfile(primer_bed)
    info_json["reference.fasta.md5"] = hashfile(reference)

    ## Check all key values are present
    for key, value in info_json.items():
        if value is None:
            raise ValueError(f"{key} is None")

    repo_dir = output / schemename / str(ampliconsize) / schemeversion
    try:
        repo_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise FileExistsError(f"{repo_dir} already exists")

    # Copy files
    shutil.copy(primer_bed, repo_dir / "primer.bed")
    shutil.copy(reference, repo_dir / "reference.fasta")

    working_dir = repo_dir / "work"
    working_dir.mkdir()
    if config is not None:
        shutil.copy(config, working_dir / "config.json")

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
    with open(repo_dir / "info.json", "w") as info:
        json.dump(info_json, info, indent=4, sort_keys=True)

    # Create a README.md with link to all pngs
    regenerate_readme(repo_dir, info_json, pngs)


@modify_app.command()
def add_validation(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Argument(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Change the valdiated field in the info.json file to True"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())
    if info["validated"]:
        raise ValueError(f"{scheme_path} is already validated")
    info["validated"] = True
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    # Update the README
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def remove_validation(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Argument(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Change the valdiated field in the info.json file to False"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())
    if not info["validated"]:
        raise ValueError(f"{scheme_path} is already invalidated")
    info["validated"] = False
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    # Update the README
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def add_author(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    author: Annotated[str, typer.Argument(help="The author to add")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Option(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Append an author to the authors list in the info.json file"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())

    # Check if author is already in the list
    if author in info["authors"]:
        raise ValueError(f"{author} is already in the authors list")
    info["authors"].append(author)
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)
    # Update the README
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def remove_author(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    author: Annotated[str, typer.Argument(help="The author to remove")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Option(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Remove an author from the authors list in the info.json file"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())

    # Check if author is already in the list
    if author not in info["authors"]:
        raise ValueError(f"{author} is not in the authors list")
    info["authors"].remove(author)
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)
    # Update the README
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)


@modify_app.command()
def add_citation(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    citation: Annotated[str, typer.Argument(help="The citation to add")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Option(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Append an citation to the authors list in the info.json file"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())
    if citation in info["citations"]:
        raise ValueError(f"{citation} is in the citation list")
    info["citation"].append(citation)
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    # Update the README
    repo_dir = schemeinfopath.parent
    pngs = [path for path in repo_dir.rglob("*.png")]
    regenerate_readme(repo_dir, info, pngs)


@modify_app.command()
def remove_citation(
    schemename: Annotated[str, typer.Argument(help="The name of the scheme")],
    ampliconsize: Annotated[int, typer.Argument(help="The amplicon size")],
    schemeversion: Annotated[str, typer.Argument(help="The scheme version")],
    citation: Annotated[str, typer.Argument(help="The citation to remove")],
    parentdir: Annotated[
        pathlib.Path,
        typer.Option(
            help=f"The path to the dir containing the primer* dirs",
            dir_okay=True,
            exists=True,
        ),
    ] = pathlib.Path("."),
    schemeclass: Annotated[
        PrimerClass,
        typer.Option(
            help="The scheme class",
        ),
    ] = PrimerClass.PRIMERSCHEMES.value,
):
    """Remove an citation form the authors list in the info.json file"""
    scheme_path = (
        parentdir / schemeclass.value / schemename / str(ampliconsize) / schemeversion
    )
    schemeinfopath = scheme_path / "info.json"

    if not scheme_path.exists():
        raise FileNotFoundError(f"Could not find version directory at {scheme_path}")
    if not schemeinfopath.exists():
        raise FileNotFoundError(f"Could not find info.json at {schemeinfopath}")

    info = json.load(schemeinfopath.open())
    if citation not in info["citations"]:
        raise ValueError(f"{citation} is not in the citation list")
    info["citation"].remove(citation)
    with open(schemeinfopath, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    # Update the README
    repo_dir = schemeinfopath.parent
    pngs = [path for path in repo_dir.rglob("*.png")]
    regenerate_readme(repo_dir, info, pngs)


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


if __name__ == "__main__":
    app()
