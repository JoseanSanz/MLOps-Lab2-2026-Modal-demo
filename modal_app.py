"""
Hosting of the backend on Modal.

Modal runs the Docker image of the API published in Docker Hub by the CI/CD pipeline
and serves the FastAPI app as a web endpoint (ASGI) with a public HTTPS URL:
    https://<modal-workspace>--calculator-api-serve.modal.run
(`modal deploy` prints it). The URL does not change between deployments, so it is
stored as the BACKEND_API_URL secret of the GitHub repository and used by the GUI.

Deploy (requires a Modal token: `uv run modal token new`, or MODAL_TOKEN_ID and
MODAL_TOKEN_SECRET as environment variables):
    make modal-deploy      # uv run modal deploy modal_app.py
Temporary deployment with logs while developing (stopped with Ctrl+C):
    make modal-serve       # uv run modal serve modal_app.py
"""

import os
import sys

import modal

# Image of the API in Docker Hub. The CI/CD pipeline sets DOCKER_IMAGE with the tag of
# the commit (<user>/calculator-api:<commit SHA>): with a new tag in every deployment,
# Modal always uses the new image instead of an image cached from a previous "latest".
DOCKER_IMAGE = os.environ.get(
    "DOCKER_IMAGE", "docker.io/joseansanz/calculator-api:latest"
)

image = modal.Image.from_registry(DOCKER_IMAGE)

app = modal.App("calculator-api")


# - No GPU: the calculator does not need it (a GPU would only spend credits). In Lab 3 (deep learning model for image prediction) we will see how to request one (adding gpu="T4").
# - scaledown_window: seconds without requests before the container is stopped. The
#   next request has to wait for a new container to start (cold start).
@app.function(image=image, scaledown_window=120)
@modal.asgi_app()
def serve():
    """Returns the FastAPI app included in the image; Modal serves it at a public URL."""
    # The code of the API is in /app inside the image (see the Dockerfile)
    sys.path.insert(0, "/app")
    # Imported here because the API only exists inside the image, not locally in Modal's
    # client when deploying
    # pylint: disable=import-outside-toplevel
    from api.api import app as fastapi_app

    return fastapi_app
