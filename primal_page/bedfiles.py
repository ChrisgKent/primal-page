from enum import Enum

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
