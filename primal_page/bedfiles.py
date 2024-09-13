import re
from enum import Enum

from primalbedtools.bedfiles import V1_PRIMERNAME, V2_PRIMERNAME

# Bedfile versions
## This doesn't parse the contents just the structure
BEDFILE_LINE = r"^\S+\t\d+\t\d+\t\S+\t\d+\t(\+|\-)\t[a-zA-Z]+$"


# bedfile versions
class BedfileVersion(Enum):
    """
    V1 bedfiles use a 6 col system
    V2 bedfiles use a 7 col system and V1 primernames
    V3 bedfiles use a 7 col system and V2 primernames
    """

    V1 = "v1.0"
    V2 = "v2.0"
    V3 = "v3.0"
    INVALID = "invalid"  # Not applicable


class BEDFileResult(Enum):
    VALID = 0
    INVALID_VERSION = 1
    INVALID_STRUCTURE = 2


class PrimerNameVersion(Enum):
    V1 = "v1"
    V2 = "v2"
    INVALID = "invalid"  # Not applicable


def determine_primername_version(primername: str) -> PrimerNameVersion:
    """
    Determines the version of the primer name.

    :param primername: The primer name to check.
    :type primername: str
    :return: The version of the primer name.
    :rtype: PrimerNameVersion
    :raises: None
    """
    if re.search(V2_PRIMERNAME, primername):
        return PrimerNameVersion.V2
    elif re.search(V1_PRIMERNAME, primername):
        return PrimerNameVersion.V1
    else:
        return PrimerNameVersion.INVALID


def convert_v1_primernames_to_v2(primername: str, primernumber=1) -> str:
    """
    Convert a v1 primername to a v2 primername. Cannot convert alt primers.

    :param primername: The v1 primername to convert.
    :type primername: str
    :param primernumber: The primernumber to add to the primername.
    :type primernumber: int
    :return: The v2 primername.
    :rtype: str
    :raises: ValueError
    """
    # Check if this is a v1 primername
    if determine_primername_version(primername) != PrimerNameVersion.V1:
        raise ValueError(f"{primername} is not a valid v1 primername")

    # Split the primername
    data = primername.split("_")
    # Remove the alt
    if "alt" in data[-1].lower():
        raise ValueError(f"{primername} is a v1 alt primername, cannot convert")

    # Add primernumber and return
    data.append(str(primernumber))
    return "_".join(data)


def validate_bedfile_line_structure(line: str) -> bool:
    """
    This function validates the structure of a bedfile line, but not the contents. Empty lines will error.
    :param line: The line to validate.
    :type line: str
    :return: Whether the line is valid or not.
    :rtype: bool
    """
    line = line.strip()
    if line.startswith("#"):
        return True
    return re.search(BEDFILE_LINE, line) is not None
