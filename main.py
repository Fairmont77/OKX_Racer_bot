from okx import OKX
from colorama import Fore

if __name__ == "__main__":
    okx = OKX()
    try:
        okx.main()
    except Exception as e:
        print(Fore.RED + str(e))
        exit(1)
