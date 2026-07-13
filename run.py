from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from app import create_app
from config import DemoConfig

app = create_app()
demo_app = create_app(DemoConfig)

# Sous /demo : exactement la même application, mais forcée en mode démo
# (voir config.DemoConfig et app/demo.py) — utile quand le sous-domaine
# demo.* (voir DEMO_SUBDOMAIN) n'est pas configurable dans l'environnement
# d'hébergement.
application = DispatcherMiddleware(app, {"/demo": demo_app})

if __name__ == "__main__":
    run_simple("127.0.0.1", 5000, application, use_reloader=True, use_debugger=True)
