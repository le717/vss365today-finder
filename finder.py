import argparse
import logging
import sys
from typing import Dict


# Handle app arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "-a",
    "--archive",
    help="kick-off the word archive generator. "
    "Cannot be combined with other arguments",
    action="store_true",
)
parser.add_argument(
    "-f",
    "--fetch",
    help="attempt to automatically record the latest prompt. "
    "Cannot be combined with other arguments",
    action="store_true",
)
parser.add_argument(
    "-m",
    "--manual",
    help="manually record a specific prompt. "
    "Cannot be combined with other arguments",
    action="store_true",
)
parser.add_argument(
    "-s",
    "--schedule",
    help="schedule recording the latest prompt according to ENV values. "
    "Cannot be combined with other arguments",
    action="store_true",
)
args = parser.parse_args()

# Create a logger to print all logging output to stdout
logger = logging.getLogger("vss365today-finder")
logger.setLevel(logging.INFO)
LOG_FORMAT = logging.Formatter("[%(asctime)s - %(levelname)s]: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(LOG_FORMAT)
logger.addHandler(handler)


if __name__ == "__main__":
    # Find out which arguments were passed
    argument_values: Dict[str, bool] = vars(args)
    number_of_args_passed = len([v for v in argument_values.values() if v])

    # More than one arguments was passed and that is not allowed
    if number_of_args_passed >= 2:
        print(
            f"{__file__}: error: cannot combine arguments. "
            "Only a single argument is permitted"
        )
        parser.print_help()
        raise SystemExit(1)

    # Manually enter a prompt
    if args.manual:
        from src.core import manual

        logging.info("Running manual...")
        manual.main()
        raise SystemExit(0)

    # Attempt to automatically find the latest prompt right now
    if args.fetch:
        from src.core import fetch

        logging.info("Running fetch...")
        fetch.main()
        raise SystemExit(0)

    # Schedule finding the latest prompt
    if args.schedule:
        from src.core import schedule

        logging.info("Starting scheduler...")
        schedule.main()

    # Manually kick-off the archive generation
    if args.archive:
        from src.core import archive

        logging.info("Running archive...")
        archive.main()
        raise SystemExit(0)

    # No arguments were passed
    else:
        parser.print_help()
        raise SystemExit(0)
