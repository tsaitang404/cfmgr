"""Request routing module."""

import json
from collections.abc import Callable

from workers import Response


class Router:
    """Simple HTTP request router."""

    def __init__(self):
        """Initialize router."""
        self.routes: dict[str, dict[str, Callable]] = {}
        self.route_patterns: list = []

    def add_route(self, path: str, method: str, handler: Callable) -> None:
        """Register a route handler.

        Args:
            path: URL path pattern
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            handler: Async handler function
        """
        if path not in self.routes:
            self.routes[path] = {}
        self.routes[path][method] = handler

    def get(self, path: str, handler: Callable) -> None:
        """Register a GET route."""
        self.add_route(path, "GET", handler)

    def post(self, path: str, handler: Callable) -> None:
        """Register a POST route."""
        self.add_route(path, "POST", handler)

    def put(self, path: str, handler: Callable) -> None:
        """Register a PUT route."""
        self.add_route(path, "PUT", handler)

    def delete(self, path: str, handler: Callable) -> None:
        """Register a DELETE route."""
        self.add_route(path, "DELETE", handler)

    async def handle(self, request) -> Response:
        """Handle incoming request.

        Args:
            request: Incoming request

        Returns:
            Response object
        """
        url = str(request.url)
        path = (
            url.split("?")[0].split("://")[-1].split("/", 1)[1]
            if "/" in url.split("://")[-1]
            else "/"
        )
        method = request.method

        # Try exact path match
        if path in self.routes and method in self.routes[path]:
            handler = self.routes[path][method]
            return await handler(request)

        # Return 404
        return Response(
            json.dumps({"error": "Not found"}),
            status=404,
            headers={"Content-Type": "application/json"},
        )


def create_router() -> Router:
    """Create and configure the application router.

    Returns:
        Configured Router instance
    """
    router = Router()

    # Health check
    async def health(request) -> Response:
        return Response(
            json.dumps({"status": "ok", "version": "0.1.0"}),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # D1 routes
    async def list_tables(request) -> Response:
        return Response(
            json.dumps({"message": "D1 tables endpoint - implement in main handler"}),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # R2 routes
    async def list_objects(request) -> Response:
        return Response(
            json.dumps({"message": "R2 objects endpoint - implement in main handler"}),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # Register routes
    router.get("/health", health)
    router.get("/api/d1/tables", list_tables)
    router.get("/api/r2/objects", list_objects)

    return router
