import sys_vars
from requests.exceptions import HTTPError

from src.helpers import api


__all__ = ["main"]


def main() -> bool:
    # Generate a new archive file
    try:
        api.post("archive")
    # The generation failed. We don't need to move on
    except HTTPError:
        print("Unable to create archive file!")
        return False

    # Get the downloads directory content
    dir_contents = sorted(
        sys_vars.get_path("DOWNLOADS_PATH").glob("*.xlsx"), reverse=True
    )

    # Determine what old archive file(s) should be deleted
    # We only ever want 2 files at a time: yesterday and today
    files_to_delete = []
    if len(dir_contents) >= 3:
        files_to_delete.extend(dir_contents[2:])

    # Delete all the old archive files
    for old_file in files_to_delete:
        old_file.unlink()
    print("Archive file successfully created")
    return True
