import json

from primal_page.schemas import SchemeStatus


def depth_first_search(indexjson) -> tuple[str, str, int, str, dict]:
    for pclass in indexjson:
        for schemename in indexjson[pclass]:
            for ampliconsize in indexjson[pclass][schemename]:
                for version in indexjson[pclass][schemename][ampliconsize]:
                    yield pclass, schemename, ampliconsize, version, indexjson[pclass][
                        schemename
                    ][ampliconsize][version]


def main():
    # Read in the index
    # Will be a request to github
    path_to_index = "/Users/kentcg/primerschemes-fork/index.json"

    index = json.load(open(path_to_index))

    q_status = "deprecated"

    # Search parameters
    # Search by status

    if q_status not in set(item.value for item in SchemeStatus):
        print(f"Invalid status: {q_status}")
        exit(1)

    for pclass, schemename, ampliconsize, scheme_version, info in depth_first_search(
        index
    ):
        if info["status"] == q_status:
            print(schemename, ampliconsize, scheme_version, pclass)


if __name__ == "__main__":
    main()
