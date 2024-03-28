import pathlib

from primal_page.schemas import Info

LICENSE_TXT_CC_BY_SA_4_0 = """\n\n------------------------------------------------------------------------

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/) 

![](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)"""


def regenerate_readme(path: pathlib.Path, info: Info, pngs: list[pathlib.Path]):
    """
    Regenerate the README.md file for a scheme

    :param path: The path to the scheme directory
    :type path: pathlib.Path
    :param info: The scheme information
    :type info: Info
    :param pngs: The list of PNG files
    :type pngs: list[pathlib.Path]
    """

    with open(path / "README.md", "w") as readme:
        readme.write(
            f"# {info.schemename} {info.ampliconsize}bp {info.schemeversion}\n\n"
        )

        if info.description is not None:
            readme.write("## Description\n\n")
            readme.write(f"{info.description}\n\n")

        readme.write("## Overviews\n\n")
        for png in pngs:
            readme.write(f"![{png.name}](work/{png.name})\n\n")

        readme.write("## Details\n\n")

        # Write the detials into the readme
        readme.write(f"""```json\n{info.model_dump_json(indent=4)}\n```\n\n""")

        if info.license == "CC BY-SA 4.0":
            readme.write(LICENSE_TXT_CC_BY_SA_4_0)


def regenerate_files(info: Info, schemeinfo: pathlib.Path):
    # Write the validated info.json
    with open(schemeinfo, "w") as infofile:
        infofile.write(info.model_dump_json(indent=4))

    # Update the README
    scheme_path = schemeinfo.parent
    pngs = [path for path in scheme_path.rglob("*.png")]
    regenerate_readme(scheme_path, info, pngs)
