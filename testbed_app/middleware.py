from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

middleware = [
    Middleware(GZipMiddleware),
    Middleware(CORSMiddleware, allow_origins=["app.example.io"]),
]
