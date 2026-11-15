"""Entry point."""

from app.api import create_app
from app.services.users import list_users


def main() -> None:
    create_app()
    print(list_users())


if __name__ == "__main__":
    main()
