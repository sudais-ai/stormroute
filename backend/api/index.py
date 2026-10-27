"""
Vercel Python serverless entry for the StormRoute backend.

Vercel's @vercel/python runtime looks for an ASGI callable named ``app`` inside
``api/*.py``. Django provides one via ``stormroute.asgi.application``. The
backend is effectively stateless (no project models; SQLite stays unused), so
running it as a serverless function is safe for the assessment deploy.

The frontend (separate Vercel project, root ``frontend``) rewrites ``/api/(.*)``
requests to this deployment, so Django receives URLs already prefixed with
``/api/`` exactly like the local runserver setup.
"""

from stormroute.asgi import application as app
