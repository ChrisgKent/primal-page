import pathlib
import json
import sys
import hashlib
from primal_page.schemas import PrimerClass


def hashfile(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def create_rawlink(repo, scheme_name, length, version, file, pclass) -> str:
    return f"https://raw.githubusercontent.com/{repo}/main/{pclass}/{scheme_name}/{length}/{version}/{file}"


def parse_version(
    version_path: pathlib.Path, repo_url, scheme_name, length, version, pclass
) -> dict[str, str]:
    version_dict = dict()

    # Read in the info.json file
    with open(version_path / "info.json") as f:
        info_dict = json.load(f)

    # Grab index.json fields
    version_dict["algorithmversion"] = info_dict["algorithmversion"]
    version_dict["status"] = info_dict["status"]
    version_dict["authors"] = info_dict["authors"]
    version_dict["citations"] = info_dict["citations"]
    version_dict["species"] = info_dict["species"]
    version_dict["license"] = info_dict["license"]
    version_dict["primerclass"] = info_dict["primerclass"]
    version_dict["schemename"] = info_dict["schemename"]
    version_dict["schemeversion"] = info_dict["schemeversion"]
    version_dict["ampliconsize"] = info_dict["ampliconsize"]
    version_dict["articbedversion"] = info_dict["articbedversion"]

    # Add a check for collections in the info.json file
    if "collections" in info_dict:
        version_dict["collections"] = info_dict["collections"]
    else:
        version_dict["collections"] = {}

    # Add the primer.bed file
    primerbed = version_path / "primer.bed"
    version_dict["primer_bed_url"] = create_rawlink(
        repo_url, scheme_name, length, version.name, primerbed.name, pclass
    )
    version_dict["primer_bed_md5"] = hashfile(primerbed)

    # Add the reference.fasta file
    reference = version_path / "reference.fasta"
    version_dict["reference_fasta_url"] = create_rawlink(
        repo_url, scheme_name, length, version.name, reference.name, pclass
    )
    version_dict["reference_fasta_md5"] = hashfile(reference)

    # Add the info.json file url
    version_dict["info_json_url"] = create_rawlink(
        repo_url, scheme_name, length, version.name, "info.json", pclass
    )

    # Check the hashes in the info.json file match the generated hashes
    if version_dict["primer_bed_md5"] != info_dict["primer_bed_md5"]:
        raise ValueError(
            f"Hash mismatch for {version_dict['primer_bed_md5']}. Expected {version_dict['primer_bed_md5']} but got {info_dict['primer_bed_md5']}"
        )
    if version_dict["reference_fasta_md5"] != info_dict["reference_fasta_md5"]:
        raise ValueError(
            f"Hash mismatch for {version_dict['reference_fasta_md5']}. Expected {version_dict['reference_fasta_md5']} but got {info_dict['reference_fasta_md5']}"
        )

    return version_dict


def parse_length(length_path, repo_url, scheme_name, length, pclass) -> dict[str, str]:
    length_dict = dict()

    # Get all the versions
    for version in length_path.iterdir():
        # Only add directories
        if not version.is_dir():
            continue

        # Parse the version
        version_dict = parse_version(
            version_path=version,
            repo_url=repo_url,
            scheme_name=scheme_name,
            length=length.name,
            version=version,
            pclass=pclass,
        )

        # Add the version to the length dict
        length_dict[version.name] = version_dict

    return length_dict


def parse_scheme(scheme_path, repo_url, scheme_name, pclass) -> dict[str, str]:
    scheme_dict = dict()

    # Get all the lengths
    for length in scheme_path.iterdir():
        # Only add directories
        if not length.is_dir():
            continue

        # Parse the length
        length_dict = parse_length(
            length_path=length,
            repo_url=repo_url,
            scheme_name=scheme_name,
            length=length,
            pclass=pclass,
        )

        # Add the length to the scheme dict
        scheme_dict[length.name] = length_dict

    return scheme_dict


def traverse_json(json_dict):
    """Depth first search of the json_dict"""
    for pclass, pclass_dict in json_dict.items():
        for scheme_name, scheme_dict in pclass_dict.items():
            for length, length_dict in scheme_dict.items():
                for version in length_dict.keys():
                    yield (pclass, scheme_name, length, version)


def check_consistency(existing_json, new_json):
    """
    Checks that paths contained in both existing_json and new_json have the same hashes (files unaltered)
    """
    # Find all paths
    existing_paths: set[tuple[str, str, str, str]] = {
        x for x in traverse_json(existing_json)
    }
    # Find all new paths
    new_paths = {x for x in traverse_json(new_json)}

    # Find all the paths that are in both
    intersection = existing_paths & new_paths

    for path in intersection:
        # Check that the reference hashes are the same
        existing_ref_hash = existing_json[path[0]][path[1]][path[2]][path[3]][
            "reference_fasta_md5"
        ]
        new_ref_hash = new_json[path[0]][path[1]][path[2]][path[3]][
            "reference_fasta_md5"
        ]
        if existing_ref_hash != new_ref_hash:
            raise ValueError(
                f"Hash changed for {path[0]}/{path[1]}/{path[2]}/{path[3]}/reference.fasta. Expected {existing_ref_hash} but got {new_ref_hash}"
            )

        # Check that the primer.bed hashes are the same
        existing_bed_hash = existing_json[path[0]][path[1]][path[2]][path[3]][
            "primer_bed_md5"
        ]
        new_bed_hash = new_json[path[0]][path[1]][path[2]][path[3]]["primer_bed_md5"]
        if existing_ref_hash != new_ref_hash:
            raise ValueError(
                f"Hash changed for {path[0]}/{path[1]}/{path[2]}/{path[3]}/primer.bed. Expected {existing_bed_hash} but got {new_bed_hash}"
            )


def create_index(
    server_url,
    repo_url,
    parent_dir=pathlib.Path("."),
    git_commit: str | None = None,
    force: bool = False,
):
    """
    Create an index JSON file for the given server and repository URLs.

    Args:
        server_url (str): The URL of the server.
        repo_url (str): The URL of the repository.
        parent_dir (str, optional): The parent directory path containing the primerscheme dir. index.json will be writem to parent_dir/index.json Defaults to ".".
        git_commit (str, optional): The git commit hash. Defaults to None.
        force (bool, optional): Force the creation of the index.json file. Allowing the change of hashes

    Returns:
        bool: True if the index JSON file is created successfully, False otherwise.
    """
    # For any Scheme, we can generate a JSON file with the following format:
    json_dict = dict()
    # Ensure the parent_dir is a pathlib.Path
    if type(parent_dir) == str:
        parent_dir = pathlib.Path(parent_dir)
    # Parse panels and schemes
    pclasses = [i.value for i in PrimerClass]
    for pclass in pclasses:
        # Create a dict to hold all the pclass data
        pclass_dict = dict()
        for path in (parent_dir / pclass).iterdir():
            # Only add directories
            if not path.is_dir() or path.name.startswith("."):
                continue

            # Get the Scheme name
            scheme_name = path.name
            pclass_dict[scheme_name] = parse_scheme(path, repo_url, scheme_name, pclass)

            print(f"parsed {pclass}/{scheme_name}")

        # Add the pclass to the json_dict
        json_dict[pclass] = pclass_dict

    if not force:
        # Read in the existing index.json file
        with open(parent_dir / "index.json") as f:
            existing_json_dict: dict = json.load(f)
            # Remove the github commit sha
            _old_commit = existing_json_dict.pop("github-commit-sha", None)

        # Check persistence of existing key files
        check_consistency(existing_json_dict, json_dict)

    # Update the github commit
    if git_commit is not None:
        json_dict["github-commit-sha"] = (
            git_commit  # This is added so that the index.json changes when the github commit changes
        )

    with open(parent_dir / "index.json", "w") as f:
        json.dump(json_dict, f, indent=4, sort_keys=True)

    return True


if __name__ == "__main__":
    server_url = sys.argv[1]
    repo_url = sys.argv[2]

    create_index(server_url, repo_url)
