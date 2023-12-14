from pydantic import BaseModel, PositiveInt
from pydantic.functional_validators import AfterValidator
from typing import Annotated
import re
from enum import Enum

SCHEMENAME_PATTERN = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"

# Primername versions
V2_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)_[0-9]+$"
V1_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)(_ALT|_alt)*$"


class PrimerNameVersion(Enum):
    V1 = "v1"
    V2 = "v2"
    INVALID = "invalid"  # Not applicable


def determine_primername_version(primername: str) -> PrimerNameVersion:
    """
    Determine the primername version
    :param primername: The primername to check
    :return: The primername version
    """
    if re.search(V2_PRIMERNAME, primername):
        return PrimerNameVersion.V2
    elif re.search(V1_PRIMERNAME, primername):
        return PrimerNameVersion.V1
    else:
        return PrimerNameVersion.INVALID


def convert_v1_primernames_to_v2(primername: str) -> str:
    """
    Convert a v1 primername to a v2 primername. Cannot handle alt primers
    :param primername: The v1 primername
    :return: The v2 primername
    """
    # Check if this is a v1 primername
    if determine_primername_version(primername) != PrimerNameVersion.V1:
        raise ValueError(f"{primername} is not a valid v1 primername")

    # Split the primername
    data = primername.split("_")
    # Remove the alt
    if data[-1] == "alt" or data[-1] == "ALT":
        raise ValueError(f"{primername} is a v1 alt primername, cannot convert")

    data.append("0")
    # Join back together
    return "_".join(data)


class PrimerClass(Enum):
    PRIMERSCHEMES = "primerschemes"
    PRIMERPANELS = "primerpanels"


class SchemeStatus(Enum):
    WITHDRAWN = "withdrawn"
    DEPRECATED = "deprecated"
    AUTOGENERATED = "autogenerated"
    DRAFT = "draft"
    TESTING = "tested"
    VALIDATED = "validated"


def validate_schemeversion(version: str) -> str:
    if not re.match(VERSION_PATTERN, version):
        raise ValueError(
            f"Invalid version: {version}. Must match be in form of v(int).(int).(int)"
        )
    return version


def validate_schemename(schemename: str) -> str:
    if not re.match(SCHEMENAME_PATTERN, schemename):
        raise ValueError(
            f"Invalid schemename: {schemename}. Must only contain a-z, 0-9, and -. Cannot start or end with -"
        )
    return schemename


def not_empty(x: list | set) -> list | set:
    if len(x) == 0:
        raise ValueError("Cannot be empty")
    return x


class Info(BaseModel):
    ampliconsize: PositiveInt
    schemeversion: Annotated[str, AfterValidator(validate_schemeversion)]
    schemename: Annotated[str, AfterValidator(validate_schemename)]
    primer_bed_md5: str
    reference_fasta_md5: str
    status: SchemeStatus
    citations: set[str]
    authors: Annotated[set[str], AfterValidator(not_empty)]
    algorithmversion: str
    species: Annotated[set[int | str], AfterValidator(not_empty)]
    license: str = "CC BY-SA 4.0"
    primerclass: PrimerClass = PrimerClass.PRIMERSCHEMES
    infoschema: str = "v1.1.0"
    # Add the optional fields
    description: str | None = None
    derivedfrom: str | None = None


if __name__ == "__main__":
    info = Info(
        ampliconsize=400,
        schemeversion="v0.0.0",
        schemename="test",
        primer_bed_md5="hello",
        reference_fasta_md5="world",
        status=SchemeStatus.DRAFT,
        citations=set(),
        authors=set("artic"),
        algorithmversion="test",
        species=set("sars-cov-2"),
    )

    # indexv = IndexVersion(
    #    ampliconsize=400,
    #    schemeversion="v0.0.0",
    #    schemename="test",
    #    primer_bed_md5="hello",
    #    reference_fasta_md5="world",
    #    status=SchemeStatus.DRAFT,
    #    citations=[],
    #    authors=[],
    #    algorithmversion="test",
    #    species=[1, "hello", 1],
    #    IndexVersion="test",
    # )

    print(info.model_dump_json(indent=4))

    info.authors.add("hello")
    print(info.model_dump_json(indent=4))

    # print(indexv.model_dump_json(indent=4))
