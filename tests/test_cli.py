import pathlib

from typer.testing import CliRunner

from primal_page.__init__ import __version__
from primal_page.main import app

runner = CliRunner()

# This uses pytest rather than unittest
# Run using: poetry run pytest


# Test the app can run with the version flag
def test_app_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
