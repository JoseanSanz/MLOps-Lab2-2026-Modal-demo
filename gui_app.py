"""
Hosting of the GUI (Gradio) on Modal.

The GUI is a service of its own, separated from the backend (modal_app.py): Modal
builds a small image with the dependencies of gui/requirements.txt and the gui/
folder, and serves the Gradio app at a public HTTPS URL:
    https://<modal-workspace>--calculator-gui-ui.modal.run
(`modal deploy` prints it).

The URL of the backend is read from the API_URL environment variable when deploying
(the CI/CD pipeline sets it from the BACKEND_API_URL secret) and passed to the
container as an environment variable.

Deploy (requires a Modal token, as modal_app.py):
    API_URL=https://<url of the API> make modal-deploy-gui
"""

import os
import sys

import modal

image = (
    modal.Image.debian_slim(python_version="3.13").pip_install_from_requirements(
        "gui/requirements.txt"
    )
    # The code is added at the end: changing it does not rebuild the dependencies
    .add_local_dir("gui", remote_path="/root/gui")
)

app = modal.App("calculator-gui")

backend = modal.Secret.from_dict({"API_URL": os.environ.get("API_URL", "")})


# - max_containers=1: Gradio keeps the state of each session in memory, so all the
#   requests of a user must reach the same container (one is enough for the lab).
# - concurrent: that container answers several users at the same time.
# - scaledown_window: seconds without requests before the container is stopped.
@app.function(image=image, secrets=[backend], max_containers=1, scaledown_window=120)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def ui():
    """Returns the Gradio app mounted on a FastAPI app; Modal serves it."""
    # The GUI is only imported inside the container (gradio is not installed in
    # Modal's client when deploying)
    # pylint: disable=import-outside-toplevel
    sys.path.insert(0, "/root")
    import gradio as gr
    from fastapi import FastAPI

    from gui.app import demo

    return gr.mount_gradio_app(FastAPI(), demo, path="/")
