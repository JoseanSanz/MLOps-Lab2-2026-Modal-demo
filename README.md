[![CICD](https://github.com/JoseanSanz/MLOps-Lab2-2026-Modal-demo/actions/workflows/CICD.yml/badge.svg)](https://github.com/JoseanSanz/MLOps-Lab2-2026-Modal-demo/actions/workflows/CICD.yml)

# MLOps-Lab2-2026-Modal-demo

Demo for the second lab of the MLOps subject, using **Modal** to host the backend and the GUI. It is
the same project as [MLOps-Lab2-demo](https://github.com/JoseanSanz/MLOps-Lab2-demo)
(which uses Render): only the hosting changes, so you can choose the
platform you prefer. A simple calculator is used as the application, so that the focus
is on the MLOps workflow. In this lab you will learn to:

* Organize a Python project with **uv** (dependencies pinned in `uv.lock`) and a **Makefile**.
* Test it with **pytest** (unit and integration tests) and check it with **black** and **pylint**.
* Expose the logic as a REST API with **FastAPI** (a microservice: the backend).
* **Containerize** the API with **Docker**.
* Build a **CI/CD pipeline** with **GitHub Actions** that tests the code, builds and
  publishes the image and deploys the backend and the GUI on **Modal**.
* Create a GUI with **Gradio** (the frontend, another service) that uses the deployed API.

## Architecture

```
                 git push (main)
 Developer ───────────────────────► GitHub ──► GitHub Actions (CICD.yml)
                                                 │
                    1. build ── format, lint, tests
                    2. docker ── build image, smoke test, push to Docker Hub
                    3. deploy-backend ── modal deploy ──► API (FastAPI) on Modal
                    4. deploy-gui ── modal deploy ──────► GUI (Gradio) on Modal
                                                                      │
                                                  POST /calculate ◄───┘
```

## Render or Modal?

| | Render ([MLOps-Lab2-demo](https://github.com/JoseanSanz/MLOps-Lab2-demo)) | Modal (this repository) |
|---|---|---|
| What it runs | API: the Docker image as a web service. GUI: a second web service built from `gui/` | API: the Docker image, served by `modal_app.py`. GUI: `gui_app.py`. Both with `@modal.asgi_app` |
| Configuration | In the web dashboard (service created by hand) | As code (`modal_app.py`) |
| Deployment from the CI | POST to a secret deploy hook of each service | `modal deploy modal_app.py` / `gui_app.py` with a Modal token |
| Idle service | Free instances sleep after ~15 min | The container stops after `scaledown_window` seconds |
| Cold start | Up to ~1 min | A few seconds |
| Free usage | Free instance type | Monthly free credits |

The GUI waits up to 60 s (Modal) or 90 s (Render) for the first request.

## Project structure

```
├── mylib/calculator.py        # business logic (shared by the CLI and the API)
├── cli/cli.py                 # command-line interface (click)
├── api/api.py                 # REST API (FastAPI): /, /health, /calculate
├── templates/home.html        # home page of the API
├── tests/                     # unit tests (logic, GUI) and integration tests (CLI, API)
├── gui/                       # Gradio GUI (frontend): a separate service
│   ├── app.py
│   └── requirements.txt       # dependencies of the GUI service only
├── modal_app.py               # hosting of the backend on Modal
├── gui_app.py                 # hosting of the GUI on Modal
├── Dockerfile                 # image of the API (only runtime dependencies)
├── Makefile                   # common tasks
├── pyproject.toml / uv.lock   # dependencies (runtime and dev group)
└── .github/workflows/CICD.yml # CI/CD pipeline
```

## Run it locally

Requirements: [uv](https://docs.astral.sh/uv/) (installed by `make install` if missing) and Docker.

```bash
make install          # installs all the dependencies (runtime + dev)
make all              # install + format-check + lint + test (what the CI does)

uv run python -m cli.cli add 1 2        # CLI
make run-api                            # API at http://localhost:8000/docs
make run-gui                            # Gradio GUI at http://localhost:7860 (in another terminal)
```

With Docker:

```bash
make docker-build     # docker build -t calculator-api .
make docker-run       # docker run --rm -p 8000:8000 calculator-api
curl http://localhost:8000/health
curl -X POST http://localhost:8000/calculate -d "op=add" -d "a=2" -d "b=3"
```

With Modal (after `uv run modal token new`; it uses the image published in Docker Hub):

```bash
make modal-serve      # temporary deployment with live logs (Ctrl+C to stop it)
make modal-deploy     # permanent deployment: prints the public URL of the API
API_URL=https://<url of the API> make modal-deploy-gui   # deployment of the GUI
```

When you change the dependencies, use `uv add <package>` (or `uv add --dev <package>`)
and commit `pyproject.toml` and `uv.lock` together: the CI and the Docker image install
exactly those versions.

## CI/CD pipeline

| Job | When | What it does |
|---|---|---|
| `build` | push and pull request to `main` | `make install`, `make format-check`, `make lint`, `make test` |
| `docker` | after `build` | builds the image and checks that the container answers `/health`; on `main` it pushes `:latest` and `:<commit SHA>` to Docker Hub |
| `deploy-backend` | push to `main` | `modal deploy modal_app.py` with the image of the commit (`:<commit SHA>`) |
| `deploy-gui` | push to `main` | `modal deploy gui_app.py`, passing the URL of the API (`BACKEND_API_URL`) |

Pull requests run the tests and build the image but never deploy.

### Setting up Modal (once)

1. Create an account at [modal.com](https://modal.com) and a token: `uv run modal token new`
   (or Settings → API Tokens in the dashboard).
2. Push the image to Docker Hub (first run of the pipeline, or `make docker-build` and
   `docker push`) and deploy once by hand: `make modal-deploy`.
3. Copy the URL that it prints, `https://<workspace>--calculator-api-serve.modal.run`,
   into the `BACKEND_API_URL` secret. The URL does not change in later deployments.
4. The GUI is deployed by the pipeline (`deploy-gui`): its URL,
   `https://<workspace>--calculator-gui-ui.modal.run`, is printed in the log of the job.

### Secrets (Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub user |
| `DOCKERHUB_TOKEN` | Docker Hub access token (Account settings → Personal access tokens) |
| `MODAL_TOKEN_ID` | Modal token id |
| `MODAL_TOKEN_SECRET` | Modal token secret |
| `BACKEND_API_URL` | public URL of the API on Modal (see above) |
