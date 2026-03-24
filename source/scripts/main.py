import sys


sys.dont_write_bytecode = True


from core.bootstrap import configure_runtime
from gameplay.game import run


configure_runtime()


if __name__ == "__main__":
    run()