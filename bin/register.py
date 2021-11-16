import argparse
from pytesdaq.display import Register


if __name__ == "__main__":

    # ------------------
    # Input arguments
    # ------------------
    parser = argparse.ArgumentParser(description='Register data')
    parser.add_argument('--raw_path', type = str, help='Base path to raw  data (Default from setup.ini)')
    parser.add_argument('--group_name', type = str, help='Group name (optional)')
    parser.add_argument('--fridge_run', type=int, help='Fridge run number (optional)')
    parser.add_argument('--display_only', action='store_true',
                        help='Display group info. No registration')

    args = parser.parse_args()

    
    # check arguments
    if not args.raw_path:
        print('ERROR: Group path needs to be provided')
        exit(0)
    group_name = None
    if args.group_name:
        group_name = args.group_name

    display_only = False
    if args.display_only:
        display_only = args.display_only
        

    # register
    register = Register(args.raw_path,
                        group_name=group_name,
                        display_only=display_only)
    register.run()
    
    
