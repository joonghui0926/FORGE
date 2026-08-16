from render_sdk import Workflows

from .tasks import app as pipeline_app


app = Workflows.from_workflows(pipeline_app)


if __name__ == "__main__":
    app.start()
