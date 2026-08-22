"""Run the game from the project venv.

    .venv/bin/python3 -m tbb [--seed N]
"""
import argparse

from tbb.app.main import App


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m tbb")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed for the new campaign (default: 734102)")
    args = parser.parse_args(argv)
    app = App()
    if args.seed is not None:
        app.title_screen.seed_text = str(args.seed)
    app.run()


if __name__ == "__main__":
    main()