"""Main entry point for Cloudflare Worker."""

from workers import WorkerEntrypoint, Response


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return Response("Hello from cfmgr!")


