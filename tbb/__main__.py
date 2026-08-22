"""Run the game from the project venv.

    .venv/bin/python3 -m tbb [--seed N] [--new-game] [--frames K]
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m tbb")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed for the new campaign (default: 734102)")
    parser.add_argument("--new-game", action="store_true",
                        help="skip the title screen and open the campaign map")
    parser.add_argument("--resolve-battle", action="store_true",
                        help="auto-resolve any pending battle after launch")
    parser.add_argument("--frames", type=int, default=None,
                        help="exit after K rendered frames (smoke testing)")
    args = parser.parse_args(argv)
    from tbb.app.main import App

    app = App()
    if args.seed is not None:
        app.title_screen.seed_text = str(args.seed)
    if args.new_game:
        app.new_game()
        if args.resolve_battle:
            app.campaign.auto_resolve_pending()
    app.run(frames=args.frames)


if __name__ == "__main__":
    main()
