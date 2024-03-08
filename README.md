# Primal-Page

[![CI](https://github.com/ChrisgKent/primal-page/actions/workflows/pytest.yml/badge.svg)](https://github.com/ChrisgKent/primal-page/actions/workflows/pytest.yml)


This is the tooling for working with the primerschemes index

# CLI

**Usage**:

```console
$ [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `build-index`: Build an index.json file from all schemes...
* `create`: Create a new scheme in the required format
* `download-all`: Download all schemes from the index.json
* `download-scheme`: Download a scheme from the index.json
* `modify`: Modify an existing scheme's metadata...
* `regenerate`: Regenerate the info.json and README.md...
* `remove`: Remove a scheme's version from the repo,...

## `build-index`

Build an index.json file from all schemes in the directory

**Usage**:

```console
$ build-index [OPTIONS]
```

**Options**:

* `--gitaccount TEXT`: The name of the github account  [default: quick-lab]
* `--gitserver TEXT`: The name of the github server  [default: https://github.com/]
* `--parentdir PATH`: The parent directory  [default: .]
* `--git-commit-sha TEXT`: The git commit
* `--force / --no-force`: Force the creation of the index.json  [default: no-force]
* `--help`: Show this message and exit.

## `create`

Create a new scheme in the required format

**Usage**:

```console
$ create [OPTIONS] SCHEMEPATH
```

**Arguments**:

* `SCHEMEPATH`: The path to the scheme directory  [required]

**Options**:

* `--schemename TEXT`: The name of the scheme  [required]
* `--ampliconsize INTEGER RANGE`: Amplicon size  [x>=100; required]
* `--schemeversion TEXT`: Scheme version, default is parsed from config.json  [required]
* `--species INTEGER`: The species this scheme targets. Please use NCBI taxonomy ids  [required]
* `--schemestatus [withdrawn|deprecated|autogenerated|draft|tested|validated]`: Scheme status  [default: draft]
* `--citations TEXT`: Any associated citations. Please use DOI
* `--authors TEXT`: Any authors  [default: quick lab, artic network]
* `--primerbed PATH`: Manually specify the primer bed file, default is *primer.bed
* `--reference PATH`: Manually specify the referance.fasta file, default is *.fasta
* `--output PATH`: Where to output the scheme  [default: primerschemes]
* `--configpath PATH`: Where the config.json file is located
* `--algorithmversion TEXT`: The version of primalscheme or other
* `--description TEXT`: A description of the scheme
* `--derivedfrom TEXT`: Which scheme has this scheme been derived from
* `--primerclass [primerschemes]`: The primer class  [default: primerschemes]
* `--collection [ARTIC|MODJADJI|QUICK-LAB|COMMUNITY|WASTE-WATER|CLINAL-ISOLATES|WHOLE-GENOME|PANEL|MULTI-TARGET]`: The collection
* `--help`: Show this message and exit.

## `download-all`

Download all schemes from the index.json

**Usage**:

```console
$ download-all [OPTIONS]
```

**Options**:

* `--output PATH`: The directory the primerschemes dir will be created in  [required]
* `--index-url TEXT`: The URL to the index.json  [default: https://raw.githubusercontent.com/quick-lab/primerschemes/main/index.json]
* `--help`: Show this message and exit.

## `download-scheme`

Download a scheme from the index.json

**Usage**:

```console
$ download-scheme [OPTIONS] SCHEMENAME AMPLICONSIZE SCHEMEVERSION
```

**Arguments**:

* `SCHEMENAME`: The name of the scheme  [required]
* `AMPLICONSIZE`: Amplicon size  [required]
* `SCHEMEVERSION`: Scheme version  [required]

**Options**:

* `--output PATH`: The directory the primerschemes dir will be created in  [required]
* `--index-url TEXT`: The URL to the index.json  [default: https://raw.githubusercontent.com/quick-lab/primerschemes/main/index.json]
* `--help`: Show this message and exit.

## `modify`

Modify an existing scheme's metadata (info.json)

**Usage**:

```console
$ modify [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `add-author`: Append an author to the authors list in...
* `add-citation`: Append an citation to the authors list in...
* `add-collection`: Add a Collection to the Collection list in...
* `derivedfrom`: Replaces the derivedfrom in the info.json...
* `description`: Replaces the description in the info.json...
* `license`: Replaces the license in the info.json file
* `primerclass`: Change the primerclass field in the info.json
* `remove-author`: Remove an author from the authors list in...
* `remove-citation`: Remove an citation form the authors list...
* `remove-collection`: Remove an Collection from the Collection...
* `status`: Change the status field in the info.json

### `modify add-author`

Append an author to the authors list in the info.json file

**Usage**:

```console
$ modify add-author [OPTIONS] SCHEMEINFO AUTHOR
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `AUTHOR`: The author to add  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify add-citation`

Append an citation to the authors list in the info.json file

**Usage**:

```console
$ modify add-citation [OPTIONS] SCHEMEINFO CITATION
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `CITATION`: The citation to add  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify add-collection`

Add a Collection to the Collection list in the info.json file

**Usage**:

```console
$ modify add-collection [OPTIONS] SCHEMEINFO COLLECTION:{ARTIC|MODJADJI|QUICK-LAB|COMMUNITY|WASTE-WATER|CLINAL-ISOLATES|WHOLE-GENOME|PANEL|MULTI-TARGET}
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `COLLECTION:{ARTIC|MODJADJI|QUICK-LAB|COMMUNITY|WASTE-WATER|CLINAL-ISOLATES|WHOLE-GENOME|PANEL|MULTI-TARGET}`: The Collection to add  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify derivedfrom`

Replaces the derivedfrom in the info.json file

**Usage**:

```console
$ modify derivedfrom [OPTIONS] SCHEMEINFO DERIVEDFROM
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `DERIVEDFROM`: The new derivedfrom. Use 'None' to remove the derivedfrom  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify description`

Replaces the description in the info.json file

**Usage**:

```console
$ modify description [OPTIONS] SCHEMEINFO DESCRIPTION
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `DESCRIPTION`: The new description. Use 'None' to remove the description  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify license`

Replaces the license in the info.json file

**Usage**:

```console
$ modify license [OPTIONS] SCHEMEINFO LICENSE
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `LICENSE`: The new license. Use 'None' show the work is not licensed (Not recommended)  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify primerclass`

Change the primerclass field in the info.json

**Usage**:

```console
$ modify primerclass [OPTIONS] SCHEMEINFO PRIMERCLASS:{primerschemes}
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `PRIMERCLASS:{primerschemes}`: The primerclass to change to  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify remove-author`

Remove an author from the authors list in the info.json file

**Usage**:

```console
$ modify remove-author [OPTIONS] SCHEMEINFO AUTHOR
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `AUTHOR`: The author to remove  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify remove-citation`

Remove an citation form the authors list in the info.json file

**Usage**:

```console
$ modify remove-citation [OPTIONS] SCHEMEINFO CITATION
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `CITATION`: The citation to remove  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify remove-collection`

Remove an Collection from the Collection list in the info.json file

**Usage**:

```console
$ modify remove-collection [OPTIONS] SCHEMEINFO COLLECTION:{ARTIC|MODJADJI|QUICK-LAB|COMMUNITY|WASTE-WATER|CLINAL-ISOLATES|WHOLE-GENOME|PANEL|MULTI-TARGET}
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]
* `COLLECTION:{ARTIC|MODJADJI|QUICK-LAB|COMMUNITY|WASTE-WATER|CLINAL-ISOLATES|WHOLE-GENOME|PANEL|MULTI-TARGET}`: The Collection to remove  [required]

**Options**:

* `--help`: Show this message and exit.

### `modify status`

Change the status field in the info.json

**Usage**:

```console
$ modify status [OPTIONS] SCHEMEINFO
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]

**Options**:

* `--schemestatus [withdrawn|deprecated|autogenerated|draft|tested|validated]`: The scheme class  [default: SchemeStatus.DRAFT]
* `--help`: Show this message and exit.

## `regenerate`

Regenerate the info.json and README.md file for a scheme
    - Rehashes info.json's primer_bed_md5 and reference_fasta_md5
    - Regenerates the README.md file
    - Recalculate the artic-primerbed version
    - Updates the infoschema version to current

Ensures work/config.json has no absolute paths
    - Ensures hashes in config.json are removed

**Usage**:

```console
$ regenerate [OPTIONS] SCHEMEINFO
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]

**Options**:

* `--help`: Show this message and exit.

## `remove`

Remove a scheme's version from the repo, will also remove size and schemename directories if empty

**Usage**:

```console
$ remove [OPTIONS] SCHEMEINFO
```

**Arguments**:

* `SCHEMEINFO`: The path to info.json  [required]

**Options**:

* `--help`: Show this message and exit.

# Examples

### Adding a minimal scheme

For a simple scheme, only fasta file (--reference) and a bed file (--primerbed) are required. Alongside metadata of --schemename, --algorithmversion, --species, --authors.

```
primal-page create \
    --schemename example-scheme \
    --algorithmversion ps:100 \
    --ampliconsize 500 \
    --species 123  \
    --schemeversion v1.0.0 \
    --primerbed 'minimal-scheme/minimal.bed' \
    --reference 'minimal-scheme/ref.fasta' \
    --authors me \
    --authors you /
    'minimal-scheme' 
```

### Adding a custom scheme to quick-lab/primerschemes


> create a local fork of https://github.com/quick-lab/primerschemes

> Add the files to the forks primerschemes folder
```
primal-page create primal-page create ... --output ~/primerschemes/primerschemes
```

> Create a pull request 


# New Schemas

 ## PrimerNames Versions

 Expected primernames (col3) in the primer.bed file

 ### `V1`

This is the first standard for primernames. It follows the general pattern of `{scheme-name|uuid}_{amplicon-number}_{LEFT|RIGHT}` and an optional `{_alt}` to denote spike in primers.

Regex:

 ```V1_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)(_ALT[0-9]*|_alt[0-9]*)*$"```

Example:
```
SARS-CoV-2_10_LEFT
SARS-CoV-2_10_LEFT_alt1
```


### `V2`

This follows the pattern of `{scheme-name|uuid}_{amplicon-number}_{LEFT|RIGHT}_{primer-number}`. 
- This now enforces that splitting on `_` will produce a consistent length, allowing the safe indexing of attributes. 
- `primer-number` is not enforced to be continuous. Therefore, the `_0` numbered primer should not be thought of as the `original` and all other numbers as `alts`.


Example:
```
SARS-CoV-2_10_LEFT_0
SARS-CoV-2_10_LEFT_1
```

Regex:

```V2_PRIMERNAME = r"^[a-zA-Z0-9\-]+_[0-9]+_(LEFT|RIGHT)_[0-9]+$"```


## ARTIC-primer.bed Versions

These are rough guidelines for the format of the primer.bed file. The general format is based on the [.bed file](https://en.wikipedia.org/wiki/BED_(file_format)) and maintains compatibility with other tools.

colnames and indexes:
- `0 - chrom`: The name of the reference genome the primers are indexed to
- `1 - chromStart`: 0-based inclusive start coordinate
- `2 - chromEnd`: 0-based non-inclusive end coordinate
- `3 - primer-name`: Name of each primer
- `4 - pool`: The pool each primer should be added into. 1 based.
- `5 - strand`: Either `+` (forward) or `-` (reverse) primer
- `6 - primer-sequence`: The 5'-3' sequence of the primer



### V1
> Depreciated 

This was the original 6-col bedfile used very early in PrimalSchemes development, which excluded primer-sequence. 

### V2
> Legacy

This uses the 7 columns described above, alongside `V1:primernames`.
- Single chrom (reference) is expected
- No header lines

### V3
> Current

This uses the 7 columns described above, alongside `V2:primernames`.
- Multiple chrom (references)
- Circular primers are allowed. The start of x_LEFT can be greater than the end of x_RIGHT
- Header lines are used. Denoted with the `#` character 

 
## Scheme Version

In the form of `v{Major}.{Minor}.{Patch}`
- Major: New scheme being generated with differant input params
- Minor: Change to primers. Either additional / removal of primers
- Patch: No change to primers. Often used for rebalancing or change in formatting


Regex:

`VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"`


## Scheme Name

Must only contain `a-z`, `0-9`, and `-`. Cannot start or end with `-`

Regex:

`SCHEMENAME_PATTERN = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"`