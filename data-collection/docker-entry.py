"""Container entry point for the `av-jobs` CLI.

The CLI asks for the Azure Translator key with a hidden prompt. When the
AZURE_TRANSLATOR_KEY environment variable is set, that value is used instead,
so the weekly run can work unattended. With the variable unset, the normal
interactive prompt appears (run the container with a terminal attached).
"""

import getpass
import os
import sys

key = os.environ.get("AZURE_TRANSLATOR_KEY", "").strip()
if key:
    getpass.getpass = lambda prompt="": key

from av_jobs.cli import main  # noqa: E402

sys.exit(main())
