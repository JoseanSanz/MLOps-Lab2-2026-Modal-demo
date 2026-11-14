"""
Uploads the hf_space/ folder (the GUI) to the Hugging Face Space.

It is run by the deploy-hf job of the CI/CD pipeline, but it can also be run locally.
The script does not read the GitHub secrets directly: it reads environment variables
of the process that runs it. In the CI they are created by the `env:` block of the
job from the repository secrets; locally, you define them in the command line.

Environment variables:
    HF_TOKEN   Hugging Face token with write permission (required)
    HF_SPACE   Space id, e.g. "username/MLOps-Lab2-demo-modal" (required)
    API_URL    public URL of the backend (REST API), wherever it is hosted (optional):
               stored as a variable of the Space, where app.py reads it
    GIT_SHA    commit being deployed (optional): used in the commit message

Run locally:
    HF_TOKEN=... HF_SPACE=user/MLOps-Lab2-demo-modal uv run python scripts/deploy_hf_space.py
"""

import os
from pathlib import Path

from huggingface_hub import HfApi

# hf_space/ folder of the repository (in the CI, the copy made by actions/checkout)
SPACE_DIR = Path(__file__).resolve().parent.parent / "hf_space"


def main():
    """Creates the Space if needed, sets API_URL and uploads hf_space/."""
    # Required variables: a KeyError stops the script if any of them is missing
    space_id = os.environ["HF_SPACE"]
    api = HfApi(token=os.environ["HF_TOKEN"])

    # Creates the Space the first time (does nothing if it already exists)
    api.create_repo(space_id, repo_type="space", space_sdk="gradio", exist_ok=True)

    # The URL of the backend is stored as a variable of the Space: Hugging Face
    # passes it as an environment variable to the GUI, where app.py reads it
    api_url = os.environ.get("API_URL")
    if api_url:
        api.add_space_variable(space_id, "API_URL", api_url)

    sha = os.environ.get("GIT_SHA", "local")[:7]
    api.upload_folder(
        folder_path=SPACE_DIR,
        repo_id=space_id,
        repo_type="space",
        commit_message=f"Deploy from GitHub ({sha})",
    )
    print(f"Space updated: https://huggingface.co/spaces/{space_id}")


if __name__ == "__main__":
    main()
