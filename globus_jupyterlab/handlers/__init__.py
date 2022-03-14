import os
import logging
from types import ModuleType
from typing import List, Tuple

from notebook.utils import url_path_join
from notebook.base.handlers import APIHandler
from jupyter_server.serverapp import ServerWebApplication
from tornado.web import StaticFileHandler
from globus_jupyterlab.handlers import login, config


log = logging.getLogger(__name__)

HANDLER_MODULES = (login, config)


def get_handlers(modules: List[ModuleType], base_url: str, url_path: str) -> List[Tuple[str, APIHandler]]:
    """
    Fetch handlers from a list of modules. This style is taken from Jupyterhub,
    which declares `default_handlers` on each of its handler modules and adds
    them to a list here:
    https://github.com/jupyterhub/jupyterhub/blob/main/jupyterhub/handlers/login.py#L168
    Given a list of handler modules, this function will append the base_url and
    url_path to each handler endpoint, which can then be passed straight to a
    ServerWebApplication
    """
    handlers = []
    for module in modules:
        for url, api_handler in module.default_handlers:
            mounted_url = url_path_join(base_url, url_path, url)
            log.info(f'Server Extension mounted {mounted_url}')
            handlers.append((mounted_url, api_handler))
    return handlers


def setup_handlers(web_app: ServerWebApplication, url_path: str):
    """
    Setup main webapp handlers. Automatically adds all handlers
    defined in HANDLER_MODULES.
    """
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]

    handlers = get_handlers(HANDLER_MODULES, base_url, url_path)
    web_app.add_handlers(host_pattern, handlers)

    # Prepend the base_url so that it works in a JupyterHub setting
    doc_url = url_path_join(base_url, url_path, "public")
    doc_dir = os.getenv(
        "JLAB_SERVER_EXAMPLE_STATIC_DIR",
        os.path.join(os.path.dirname(__file__), "public"),
    )
    handlers = [("{}/(.*)".format(doc_url), StaticFileHandler, {"path": doc_dir})]
    web_app.add_handlers(".*$", handlers)