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
    Determines the version of the primer name.

    Args:
        primername (str): The primer name to check.

    Returns:
        PrimerNameVersion: The version of the primer name.

    Raises:
        None.
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


class BEDFileResult(Enum):
    VALID = 0
    INVALID_VERSION = 1
    INVALID_STRUCTURE = 2


def validate_bedfile_line_structure(line: str) -> bool:
    """
    This function validates the structure of a bedfile line, but not the contents.

    Args:
        line (str): The line to be validated.

    Returns:
        bool: True if the line structure is valid, False otherwise.
    """
    line = line.strip()
    if line.startswith("#"):
        return True
    return re.search(BEDFILE_LINE, line) is not None


def validate_bedfile(bedfile: pathlib.Path) -> BEDFileResult:
    """
    This function reads in a bedfile, checks the structure of the file, and validates the primername versions.

    Args:
        bedfile (pathlib.Path): The path to the bedfile to be validated.

    Returns:
        BEDFileResult: The result of the bedfile validation. It can be one of the following:
            - BEDFileResult.INVALID_STRUCTURE: If the bedfile has an invalid structure.
            - BEDFileResult.INVALID_VERSION: If the bedfile has an invalid version.
            - BEDFileResult.VALID: If the bedfile is valid.
    """
    # Read in the bedfile string
    bedfile_str = bedfile.read_text()

    # Split the bedfile into lines
    bedlines = bedfile_str.split("\n")

    # Check each line
    for line in bedlines:
        if not validate_bedfile_line_structure(line):
            return BEDFileResult.INVALID_STRUCTURE

    # Check the bedfile names.
    match determine_bedfile_version(bedfile):
        case BedfileVersion.INVALID:
            return BEDFileResult.INVALID_VERSION
        case _:
            return BEDFileResult.VALID


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
        pool: int,
        strand: str,
        seq: str,
    ):
        self.chrom = chrom
        self.start = start
        self.end = end
        self.primername = primername
        self.pool = pool
        self.strand = strand
        self.seq = seq

        # Validate the primername
        if determine_primername_version(primername) == PrimerNameVersion.INVALID:
            raise ValueError(f"Invalid primername: {primername}")

        # Autogenerated fields
        self.prefix = primername.split("_")[0]
        self.amplicon_number = int(primername.split("_")[1])
        self.pn_direction = primername.split("_")[2]
        self.primernumber: int | None = None

    def __str__(self):
        return f"{self.chrom}\t{self.start}\t{self.end}\t{self.primername}\t{self.pool}\t{self.strand}\t{self.seq}"

    def parsed_primername(self, primernumber: int) -> str:
        return "_".join(
            [
                self.prefix,
                str(self.amplicon_number),
                self.pn_direction,
                str(primernumber),
            ]
        )

    def parsed_bedline(self) -> str:
        return f"{self.chrom}\t{self.start}\t{self.end}\t{self.primername if self.primernumber is None else self.parsed_primername(self.primernumber)}\t{self.pool}\t{self.strand}\t{self.seq}"


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
                pool=int(line[4]),
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

    with open(bedfilepath) as bedfile:
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


def regenerate_v3_bedfile(bedfile: pathlib.Path) -> str:
    """
    THIS FUNCTION MODIFIES THE BEDFILE. ONLY USE WHEN UPDATING THE BEDFILE VERSION.

    Convert a v2 bedfile to a v3 bedfile.
    :param bedfile: The v2 bedfile
    :return: The v3 bedfile
    """

    # Read in the bedfile
    bedlines, bedheader = read_bedlines(bedfile)

    # GUARD: If the bedfile is already v3, return the bedfile
    if determine_bedfile_version(bedfile) == BedfileVersion.V3:
        return bedfile.read_text()

    # Sort the bedlines by chrom and amplicon number
    bedlines = sorted(bedlines, key=lambda x: (x.chrom, x.amplicon_number))

    # Resolve alt primers
    # generate primerpairs
    # {chromname: {ampliconnumber: ([fbedlines], [rbedlines])}}
    sorted_bedlines: dict[str, dict[int, tuple[list[BedLine], list[BedLine]]]] = {}
    for line in bedlines:
        if line.chrom not in sorted_bedlines:
            sorted_bedlines[line.chrom] = {}

        if line.amplicon_number not in sorted_bedlines[line.chrom]:
            sorted_bedlines[line.chrom][line.amplicon_number] = ([], [])

        match line.strand:
            case "+":
                sorted_bedlines[line.chrom][line.amplicon_number][0].append(line)
            case "-":
                sorted_bedlines[line.chrom][line.amplicon_number][1].append(line)
            case _:
                raise ValueError(f"Invalid strand: {line.__str__()}")

    bedfile_str_list = bedheader

    # Calculate the primernumbers for alt primers
    for amplicon_number_dict in sorted_bedlines.values():
        for direction_list in amplicon_number_dict.values():
            fprimers, rprimers = direction_list

            # Sort and renumber the primers
            fprimers = sorted(fprimers, key=lambda x: x.seq)
            for i, line in enumerate(fprimers):
                line.primernumber = i + 1

                # Add the line to the bedfile
                bedfile_str_list.append(line.parsed_bedline())

            rprimers = sorted(rprimers, key=lambda x: x.seq)
            for i, line in enumerate(rprimers):
                line.primernumber = i + 1

                # Add the line to the bedfile
                bedfile_str_list.append(line.parsed_bedline())

    return "\n".join(bedfile_str_list)
