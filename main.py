"""Thin entrypoint kept for `python main.py`. The real startup lives in
kantan_cms_mcp.__main__ so it, the console script (`kantan-cms-mcp`), and
`python -m kantan_cms_mcp` all share one code path. See that module for the
required environment variables."""
from kantan_cms_mcp.__main__ import main

if __name__ == "__main__":
    main()
