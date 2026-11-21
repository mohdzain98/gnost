import json
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.routes import find_routes
from gnost.routes.models import join_paths
from gnost.scanner.engine import ScannerEngine


def project(tmp_path: Path, files: Dict[str, str]) -> Path:
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


def routes_of(root: Path) -> List[Tuple[str, str, str, str]]:
    scan = ScannerEngine(
        [PythonAdapter(), JavaScriptAdapter(), TypeScriptAdapter(), JavaAdapter()]
    ).scan(str(root))
    return [
        (r.method, r.path, r.handler, Path(r.file).relative_to(root).as_posix())
        for r in find_routes(scan)
    ]


# ---- helpers ----


def test_join_paths():
    assert join_paths("/api/", "users", "/{id}") == "/api/users/{id}"
    assert join_paths("", "") == "/"
    assert join_paths("/a", "/b/") == "/a/b/"
    assert join_paths("api", "") == "/api"


# ---- Python ----


def test_fastapi_prefixes_across_files(fixture_repo):
    routes = routes_of(fixture_repo("package_app"))
    assert ("GET", "/health", "health", "app/main.py") in routes
    assert (
        "GET",
        "/chat/api/v1/messages/{message_id}",
        "read_message",
        "app/api/v1/chat.py",
    ) in routes
    assert ("POST", "/chat/api/v1/messages", "send", "app/api/v1/chat.py") in routes
    assert ("PUT", "/chat/api/v1/bulk", "bulk", "app/api/v1/chat.py") in routes
    assert ("PATCH", "/chat/api/v1/bulk", "bulk", "app/api/v1/chat.py") in routes
    assert ("GET", "/notes", "helper", "app/api/v1/notes.py") in routes
    assert ("WS", "/ws/notes", "stream", "app/api/v1/notes.py") in routes


def test_flask_routes_blueprints_and_methods(tmp_path):
    root = project(
        tmp_path,
        {
            "app.py": (
                "from flask import Flask\n"
                "from users import bp\n"
                "app = Flask(__name__)\n"
                "app.register_blueprint(bp, url_prefix='/users')\n"
                "@app.route('/')\n"
                "def index(): ...\n"
                "@app.route('/login', methods=['GET', 'POST'])\n"
                "def login(): ...\n"
            ),
            "users.py": (
                "from flask import Blueprint\n"
                "bp = Blueprint('users', __name__)\n"
                "@bp.get('/<int:uid>')\n"
                "def show(uid): ...\n"
            ),
        },
    )
    assert routes_of(root) == [
        ("GET", "/", "index", "app.py"),
        ("GET", "/login", "login", "app.py"),
        ("POST", "/login", "login", "app.py"),
        ("GET", "/users/<int:uid>", "show", "users.py"),
    ]


def test_router_imported_into_another_module_and_nested_includes(tmp_path):
    root = project(
        tmp_path,
        {
            "main.py": (
                "from fastapi import FastAPI\nfrom api import root_router\n"
                "app = FastAPI()\napp.include_router(root_router, prefix='/v1')\n"
            ),
            "api.py": (
                "from fastapi import APIRouter\nfrom items import items\n"
                "root_router = APIRouter()\nroot_router.include_router(items, prefix='/items')\n"
            ),
            "items.py": (
                "from fastapi import APIRouter\nitems = APIRouter(prefix='/shop')\n"
                "@items.get('/{id}')\ndef one(id): ...\n"
            ),
        },
    )
    assert routes_of(root) == [("GET", "/v1/items/shop/{id}", "one", "items.py")]


def test_router_mounted_twice_gives_two_routes_and_cycles_terminate(tmp_path):
    root = project(
        tmp_path,
        {
            "main.py": (
                "from fastapi import FastAPI\nfrom r import r\napp = FastAPI()\n"
                "app.include_router(r, prefix='/v1')\napp.include_router(r, prefix='/v2')\n"
            ),
            "r.py": (
                "from fastapi import APIRouter\nr = APIRouter()\n"
                "r.include_router(r, prefix='/self')\n@r.get('/x')\ndef x(): ...\n"
            ),
        },
    )
    paths = {p for _, p, _, _ in routes_of(root)}
    assert {"/v1/x", "/v2/x"} <= paths


def test_unknown_decorator_receivers_and_dynamic_paths(tmp_path):
    root = project(
        tmp_path,
        {
            "a.py": (
                "from fastapi import FastAPI\napp = FastAPI()\nPREFIX = '/p'\n"
                "@something.get('/not-a-route')\ndef nope(): ...\n"
                "@app.get(PREFIX + '/x')\ndef dyn(): ...\n"
            ),
            "bad.py": "def broken(:\n",
        },
    )
    assert routes_of(root) == [("GET", "/<dynamic>", "dyn", "a.py")]


def test_django_urlconf_with_include_and_drf_router(tmp_path):
    root = project(
        tmp_path,
        {
            "proj/urls.py": (
                "from django.urls import path, include\nfrom . import views\n"
                "urlpatterns = [\n"
                "    path('', views.home),\n"
                "    path('api/', include('shop.urls')),\n"
                "]\n"
            ),
            "shop/urls.py": (
                "from django.urls import path, include\nfrom rest_framework.routers import DefaultRouter\n"
                "from .views import OrderViewSet, detail\n"
                "router = DefaultRouter()\nrouter.register('orders', OrderViewSet)\n"
                "urlpatterns = [\n"
                "    path('items/<int:pk>/', detail),\n"
                "    path('', include(router.urls)),\n"
                "]\n"
            ),
        },
    )
    routes = routes_of(root)
    assert ("ANY", "/", "views.home", "proj/urls.py") in routes
    assert ("ANY", "/api/items/<int:pk>/", "detail", "shop/urls.py") in routes
    assert ("ANY", "/api/orders", "OrderViewSet", "shop/urls.py") in routes


# ---- JavaScript / TypeScript ----


def test_express_routes_with_mounted_router(fixture_repo):
    routes = routes_of(fixture_repo("js_app"))
    assert ("GET", "/", "<inline>", "src/index.js") in routes
    assert ("GET", "/api/users", "list", "src/routes/users.js") in routes
    assert ("POST", "/api/users/:id", "<inline>", "src/routes/users.js") in routes


def test_express_ignores_http_clients_and_settings_getter(tmp_path):
    root = project(
        tmp_path,
        {
            "app.js": (
                "const express = require('express');\nconst axios = require('axios');\n"
                "const app = express();\n"
                "axios.get('/api/remote', handler);\n"
                "const mode = app.get('env');\n"
                "app.get('/ok', handler);\n"
                "app.all('/any', handler);\n"
            )
        },
    )
    assert routes_of(root) == [
        ("ANY", "/any", "handler", "app.js"),
        ("GET", "/ok", "handler", "app.js"),
    ]


def test_express_router_passed_in_as_a_parameter(tmp_path):
    root = project(
        tmp_path,
        {
            "routes.js": (
                "const express = require('express');\n"
                "module.exports = function (app) {\n  app.post('/hooks', ctrl.handle);\n};\n"
            )
        },
    )
    assert routes_of(root) == [("POST", "/hooks", "ctrl.handle", "routes.js")]


def test_nestjs_controllers(tmp_path):
    root = project(
        tmp_path,
        {
            "users.controller.ts": (
                "@Controller('users')\nexport class UsersController {\n"
                "  @Get()\n  findAll() {}\n"
                "  @Get(':id')\n  @UseGuards(Auth)\n  async findOne() {}\n"
                "  @Post()\n  create() {}\n}\n"
                "@Controller()\nexport class RootController {\n  @Get('ping')\n  ping() {}\n}\n"
            )
        },
    )
    assert routes_of(root) == [
        ("GET", "/ping", "RootController.ping", "users.controller.ts"),
        ("GET", "/users", "UsersController.findAll", "users.controller.ts"),
        ("POST", "/users", "UsersController.create", "users.controller.ts"),
        ("GET", "/users/:id", "UsersController.findOne", "users.controller.ts"),
    ]


# ---- Java ----


def test_spring_controller_routes(fixture_repo):
    routes = routes_of(fixture_repo("java_app"))
    base = "src/main/java/demo/GreetingController.java"
    assert ("GET", "/api/greet/{name}", "GreetingController.greet", base) in routes
    assert ("POST", "/api/greet/a", "GreetingController.create", base) in routes
    assert ("POST", "/api/greet/b", "GreetingController.create", base) in routes
    assert ("PUT", "/api/greet/x", "GreetingController.update", base) in routes


def test_java_class_without_controller_has_no_routes(tmp_path):
    root = project(
        tmp_path,
        {
            "A.java": 'public class A { @Override public String toString() { return ""; } }\n'
        },
    )
    assert routes_of(root) == []


# ---- reports ----


def _payload(root: Path) -> dict:
    from gnost.cli.commands.onboard import run

    out = root / "insights.json"
    run(path=str(root), json_out=str(out), insights_only=True)
    return json.loads(out.read_text(encoding="utf-8"))


def test_routes_in_json_match_schema_and_are_relative(fixture_repo):
    jsonschema = pytest.importorskip("jsonschema")
    from gnost.reporters.insights_json import load_schema

    root = fixture_repo("package_app")
    payload = _payload(root)
    jsonschema.validate(payload, load_schema())
    assert payload["schema_version"] == "1.4"
    assert payload["stats"]["routes"] == len(payload["routes"]) == 7
    assert all(not r["file"].startswith("/") for r in payload["routes"])
    assert {"method", "path", "handler", "file", "line", "framework"} == set(
        payload["routes"][0]
    )


def test_routes_section_in_onboard_md_and_terminal(fixture_repo, capsys):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("package_app")
    run(path=str(root))
    md = (root / ".gnost/ONBOARD.md").read_text(encoding="utf-8")
    assert (
        "## Routes" in md and "| GET | `/health` | `health` | `app/main.py:13` |" in md
    )
    assert "GET /health → health" in capsys.readouterr().out


def test_no_routes_section_when_there_are_none(fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("cyclic_py")
    run(path=str(root))
    assert "## Routes" not in (root / ".gnost/ONBOARD.md").read_text(encoding="utf-8")
