import pathlib
import re
from enum import Enum


# Primername versions
V2_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)_[0-9]+$"
V1_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)(_ALT[0-9]*|_alt[0-9]*)*$"


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


# Bedfile versions
## This doesn't parse the contents just the structure
BEDFILE_LINE = r"^\S+\t\d+\t\d+\t\S+\t\d+\t(\+|\-)\t[a-zA-Z]+$"


class BEDFILERESULT(Enum):
    VALID = 0
    INVALID_VERSION = 1
    INVALID_STRUCTURE = 2


def validate_bedfile_line_structure(line: str) -> bool:
    line = line.strip()
    if line.startswith("#"):
        return True
    return re.search(BEDFILE_LINE, line) is not None


def validate_bedfile(bedfile: pathlib.Path) -> BEDFILERESULT:
    # Read in the bedfile string
    bedfile_str = bedfile.read_text()

    # Split the bedfile into lines
    bedlines = bedfile_str.split("\n")

    # Check each line
    for line in bedlines:
        if not validate_bedfile_line_structure(line):
            return BEDFILERESULT.INVALID_STRUCTURE

    # Check the bedfile names.
    match determine_bedfile_version(bedfile):
        case BedfileVersion.INVALID:
            return BEDFILERESULT.INVALID_VERSION
        case _:
            return BEDFILERESULT.VALID


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


def determine_bedfile_version(input: list[list] | pathlib.Path) -> BedfileVersion:
    """
    Determine the bedfile version
    :param input: Either the bedfile lines as a list or the bedfile path
    :return: The bedfile version
    """
    if isinstance(input, pathlib.Path):
        bedlines, _ = read_bed_file(input)
    else:
        bedlines = input

    # If 6 cols then v1
    if len(bedlines[0]) == 6:
        return BedfileVersion.V1

    # If 7 cols then v2 or v3
    # Check from primername
    primernames = [x[3] for x in bedlines]
    primer_name_versions = {determine_primername_version(x) for x in primernames}
    if primer_name_versions == {PrimerNameVersion.V1}:
        return BedfileVersion.V2
    elif primer_name_versions == {PrimerNameVersion.V2}:
        return BedfileVersion.V3
    # Invalid if we get here
    # Mix of v1, v2 or invalid
    return BedfileVersion.INVALID


class BedLine:
    def __init__(
        self,
        chrom: str,
        start: int,
        end: int,
        primername: str,
        score: int,
        strand: str,
        seq: str,
    ):
        self.chrom = chrom
        self.start = start
        self.end = end
        self.name = primername
        self.score = score
        self.strand = strand
        self.seq = seq

    def __str__(self):
        return f"{self.chrom}\t{self.start}\t{self.end}\t{self.name}\t{self.score}\t{self.strand}\t{self.seq}"


def read_bedlines(bedfilepath: pathlib.Path) -> tuple[list[BedLine], list[str]]:
    """
    Reads a bed file and returns a list of BedLine objects.

    :return: bedfile_list
    """
    bedfile_list, bedfile_header = read_bed_file(bedfilepath)
    bedlines = []
    for line in bedfile_list:
        bedlines.append(
            BedLine(
                chrom=line[0],
                start=int(line[1]),
                end=int(line[2]),
                primername=line[3],
                score=int(line[4]),
                strand=line[5],
                seq=line[6],
            )
        )
    return bedlines, bedfile_header


def read_bed_file(bedfilepath: pathlib.Path) -> tuple[list[list[str]], list[str]]:
    """
    Reads a bed file and returns a list of lists of strings.

    :return: bedfile_list, bedfile_header
    """

    with open(bedfilepath, "r") as bedfile:
        bedfile_list: list[list[str]] = []
        bedfile_header: list[str] = []

        for line in bedfile:
            line = line.strip()
            # Header line
            if line.startswith("#"):
                bedfile_header.append(line)
            elif line:  # If not empty
                bedfile_list.append(line.split("\t"))

    return bedfile_list, bedfile_header
