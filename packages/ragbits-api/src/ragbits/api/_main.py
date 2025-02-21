from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import uvicorn

class RagbitsAPI:
    """
    RagbitsAPI class for running API with Demo UI for testing purposes
    """
    def __init__(self):
        self.app = FastAPI()
        self.dist_dir = Path(__file__).parent / "ui-build"
        self.configure_app()
        self.setup_routes()

        
    def configure_app(self):
        """Configures middleware, CORS, and other settings."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:8000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        assets_dir = self.dist_dir / "assets"
        static_dir = self.dist_dir / "static"
        self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static")
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        

    def setup_routes(self):
        """Defines API routes."""
        @self.app.get("/", response_class=HTMLResponse) 
        def demo_ui_root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            return open(str(index_file)).read()
        

    def run(self, host="127.0.0.1", port=8000):
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)