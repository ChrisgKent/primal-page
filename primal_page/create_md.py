import argparse
import pathlib
import json
import sys
import datetime


def cli():
    description = "Generates a primerscheme from an MSA"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--schemedir",
        help="The top level of the scheme",
        type=pathlib.Path,
        required=True,
    )
    parser.add_argument(
        "--outdir",
        help="The top level of the scheme",
        type=pathlib.Path,
        required=True,
    )

    args = parser.parse_args()

    if not args.outdir.is_dir():
        raise sys.exit(f"{args.output} not a directory")  # type: ignore

    return args


def create_md(
    html_figs: list[pathlib.Path],
    bed_file: pathlib.Path,
    config: pathlib.Path,
    outdir: pathlib.Path,
    scheme_name: str,
    url: str,
):
    """
    Creates a markdown page for a primerscheme, for use with Jekyll.

    :param html_figs: A list of paths to the html figures.
    :param bed_file: A path to the bed file.
    :param config: A path to the config file.
    :param outdir: A path to the output directory.
    :param scheme_name: The name of the scheme.
    :param url: The full name of the scheme {scheme_name}-{len}-{version}.
    """

    # Create some data
    scheme_date = datetime.datetime.now().strftime("%Y-%m-%d")

    page_path = outdir / str(scheme_date + "-" + url + ".md")
    if page_path.exists():
        sys.exit(f"{page_path} already exists")

    version = "v0.0.1"

    ## Create the header string
    header = f"""---\nlayout: post\ntitle: "{scheme_name}"\ncategories: CATEGORY-1 CATEGORY-2\ndescription: PrimerScheme for {scheme_name} {version}\npermalink: /schemes/{url}/\n---\n\n"""

    # Write the file
    with open(page_path, "w") as page:
        # Write the header to the file
        page.write(header + "\n")

        # Write the Scheme figure
        for fig in html_figs:
            with open(fig, "r") as html_fig:
                page.write(html_fig.read() + "\n")

        page.write("## Bedfile\n")

        # Write the bed file
        page.write("```" + "\n")
        # Write the bed file
        with open(bed_file, "r") as bed:
            page.write(bed.read() + "\n")
        page.write("```" + "\n")

        # Write the config file
        config_json = json.load(open(config, "r"))

        page.write("## Config\n\n")
        page.write("```json" + "\n")
        page.write(json.dumps(config_json) + "\n")
        page.write("```" + "\n")

    return page_path
