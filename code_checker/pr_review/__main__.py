"""``python -m code_checker.pr_review`` 入口。"""

import sys

from code_checker.pr_review.cli import main

if __name__ == "__main__":
    sys.exit(main())
