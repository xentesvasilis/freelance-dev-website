"""Windows-friendly local development entry point."""
from app import create_app

if __name__ == "__main__":
    app = create_app()
    if app.config["PRODUCTION"]:
        raise SystemExit("Use a production WSGI server in production.")
    app.run(host="127.0.0.1", port=5000, debug=False)
