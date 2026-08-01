"""Example plugin: logs all requests and responses."""
import logging

logger = logging.getLogger("owl-agent.plugin.example")

def on_request(method, url, **kwargs):
    logger.info(f"[Plugin] Request: {method} {url}")

def on_response(response, **kwargs):
    logger.info(f"[Plugin] Response: status={response.status}")

def on_error(error, attempt, url, **kwargs):
    logger.warning(f"[Plugin] Error on {url} (attempt {attempt}): {error}")
