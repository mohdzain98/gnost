from fastapi import FastAPI

from app.services.users import list_users


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/users")
    def users():
        return list_users()

    return app
