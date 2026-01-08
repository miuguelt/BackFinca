"""
Compresión ligera (gzip) para respuestas JSON/text sin dependencias externas.
"""

import gzip
import logging
from io import BytesIO

from flask import request

logger = logging.getLogger(__name__)


def init_compression(app):
    min_size = int(app.config.get("COMPRESS_MIN_SIZE", app.config.get("COMPRESSION_MIN_SIZE", 1024)))
    level = int(app.config.get("COMPRESS_LEVEL", 6))

    @app.after_request
    def _gzip_response(response):
        try:
            # No comprimir sin body / streaming / already encoded
            if response.direct_passthrough:
                return response
            if response.status_code in (204, 304):
                return response
            if response.headers.get("Content-Encoding"):
                return response

            accept = request.headers.get("Accept-Encoding", "") if request else ""
            if "gzip" not in accept.lower():
                return response

            content_type = (response.mimetype or "").lower()
            if not (content_type.startswith("application/json") or content_type.startswith("text/")):
                return response

            data = response.get_data()
            if not data or len(data) < min_size:
                return response

            buf = BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=level) as gz:
                gz.write(data)
            compressed = buf.getvalue()

            response.set_data(compressed)
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed))

            # Merge Vary
            existing = response.headers.get("Vary")
            vary_parts = []
            if existing:
                vary_parts.extend([p.strip() for p in existing.split(",") if p.strip()])
            vary_parts.append("Accept-Encoding")
            seen = set()
            merged = []
            for p in vary_parts:
                if p not in seen:
                    merged.append(p)
                    seen.add(p)
            response.headers["Vary"] = ", ".join(merged)
            return response
        except Exception:
            logger.debug("No se pudo aplicar gzip a la respuesta", exc_info=True)
            return response

    return app
