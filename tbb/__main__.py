"""Run the game from the project venv.

    .venv/bin/python3 -m tbb [--seed N] [--new-game] [--frames K]
    .venv/bin/python3 -m tbb --dump-frames DIR
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
    parser.add_argument("--dump-frames", metavar="DIR",
                        help="render campaign, settlement, court, and battle PNGs")
    parser.add_argument("--save-smoke", metavar="SLOT",
                        help="write and load a pygame-free named save slot")
    args = parser.parse_args(argv)
    if args.save_smoke:
        from tbb.rules.campaign import Campaign
        from tbb.rules import constants as C
        from tbb.rules import persistence
        campaign = Campaign(args.seed if args.seed is not None else C.DEFAULT_SEED)
        persistence.save(campaign, args.save_smoke)
        if persistence.load(args.save_smoke) is None:
            raise RuntimeError("save smoke slot could not be loaded")
        return 0
    if args.dump_frames:
        from tbb.app.main import dump_frames
        from tbb.rules import constants as C
        dump_frames(args.dump_frames,
                    args.seed if args.seed is not None else C.DEFAULT_SEED)
        return 0
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
