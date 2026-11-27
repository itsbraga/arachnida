# Arachnida

Two command-line tools from the 42 cybersecurity piscine, both about the data that web content gives away:

| Tool | Role | Status |
|------|------|--------|
| **spider** | Crawls a website and downloads its images | Done |
| **scorpion** | Reads and displays the metadata (EXIF and others) of image files | In progress |

Both are written in Python. As the subject requires, nothing relies on `wget` or `scrapy`: crawling, parsing, downloading and robots.txt handling are implemented on top of `requests`, Beautiful Soup and lxml.

---

## Getting started

### Requirements

- Python **3.11.5 or later**. This is the minimum required by the pinned dependencies. Developed and tested on Python 3.14.4.
- Linux.

### Installation

Clone the repository and run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

`requirements-dev.txt` includes `requirements.txt` and adds `pytest`. The tests never touch the network: every HTTP call is replaced by a fake.

---

## Spider

### Usage

```
./spider [-r] [-l DEPTH] [-p PATH] URL
```

| Option | Meaning | Default |
|--------|---------|---------|
| `-r` | Follow links and download images recursively | off: only the start page |
| `-l DEPTH` | Maximum recursion depth. Requires `-r` | `5` |
| `-p PATH` | Destination directory, created if missing | `./data/` |
| `URL` | Start URL. Must use `http` or `https` and have a host | - |

Depth 0 is the start page, depth 1 the pages it links to, and so on. `-r -l 0` is valid and behaves like a run without `-r`.

### Examples

```bash
./spider https://books.toscrape.com/                    # images of the start page only
./spider -r https://books.toscrape.com/                 # recursive, depth 5
./spider -r -l 1 -p ./books https://books.toscrape.com/ # depth 1, saved in ./books
```

A run prints one line per page visited and per image saved, then a summary:

```
START  ---  args: recursive=True, max_depth=1, dest=books
******

[crawler] depth=0 visiting: https://books.toscrape.com/
[crawler] saved: books/<hash>_<name>.jpg
...

*****
DONE  ---  537 image(s) saved, 179 duplicate(s) skipped, 0 blocked by robots.txt
```

*(Figures measured on books.toscrape.com with `-r -l 1` at the time of writing.)*

### Exit status

| Code | Meaning |
|------|---------|
| `0` | At least one page was fetched |
| `1` | The destination is unusable, or no page could be fetched (start page unreachable, rejected or blocked by robots.txt) |
| `2` | Usage error (invalid option, URL or depth) |
| `130` | Interrupted with Ctrl+C |
| `141` | Output pipe closed by the reader, e.g. `./spider ... \| head` |

---

## How Spider works

### Crawl order

The crawl is a **Breadth-First Search** (BFS). A queue holds `(url, depth)` pairs. The start URL enters at depth 0. Each page taken from the queue is fetched and parsed, its images are downloaded, and, if its depth is below the limit, its unvisited links are added at `depth + 1`.

BFS visits every page at depth N before any page at depth N + 1. Interrupting a long crawl therefore leaves the pages closest to the start fully covered. A `visited` set ensures that each page is fetched at most once, even when pages link to each other in a loop.

### Scope

Only pages with the same **origin** as the start URL (scheme, host and port) are followed. Links to other sites are ignored, so the crawler cannot wander across the web.

Images are different. An image found on an in-scope page is downloaded even when it is hosted elsewhere, for example on a CDN. It is part of the page's content, but its links are never followed.

If the start URL redirects (for example `http://` to `https://`, or a language redirect), the scope moves to the redirect target. A redirect on any later page is accepted only if the target is in scope and has not been visited yet.

### Fetching

All HTTP traffic goes through a single function, which applies these rules to every request:

| Rule | Value |
|------|-------|
| Timeout | 10 s |
| Minimum delay between two requests | 0.5 s |
| Maximum HTML page size | 10 MB |
| Maximum image size | 20 MB |
| Maximum robots.txt size | 500 KiB (anything beyond is ignored) |
| User-Agent | `Arachnida/1.0 (School project)` |

Bodies are read in streaming mode and the read stops at the cap. An oversized response is never fully loaded into memory. A page is parsed only if its `Content-Type` is `text/html`.

### Parsing

Each page is parsed once with Beautiful Soup and lxml. Two kinds of URL are extracted:

- `<img src>`: an image if its path ends in `.jpg`, `.jpeg`, `.png`, `.gif` or `.bmp`.
- `<a href>`: an image if its path has one of those extensions, otherwise a page to crawl.

Relative URLs are resolved against the page URL, or against `<base href>` when the page declares one. Values starting with `javascript:`, `data:`, `mailto:`, `tel:` or `#`, and any scheme other than `http` and `https`, are discarded.

### Validating and saving images

The extension in a URL only says what the server *claims* the file is. After download, the first bytes of the file (its "magic bytes") decide its real format:

| Format | Magic bytes |
|--------|-------------|
| JPEG | `FF D8 FF` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| GIF | `47 49 46 38` (`GIF8`) |
| BMP | `42 4D` (`BM`) |

A file that matches none of them is rejected. The saved file takes the extension of the detected format, not the one in the URL.

Saved files are named `<hash>_<name>.<ext>`:

- `<hash>`: the first 8 hex characters of the SHA-256 of the content;
- `<name>`: the original file name without its extension, keeping only letters, digits, `.`, `_` and `-`, cut to 50 characters;
- `<ext>`: the detected format.

When the URL has no usable file name, the file is simply named `<hash>.<ext>`.

The file is first written as `<name>.part`, then renamed. An interrupted download never leaves a truncated image under its final name.

### Duplicates

An image is skipped, and counted as a duplicate, in two cases:

1. **Same URL** already handled: it is not downloaded again.
2. **Same content** under a different URL: the SHA-256 of the bytes is already known, so the file is not written again.

The first check avoids most network requests. The second catches the same image served from several addresses.

### robots.txt

Spider follows [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), the standard that lets a site tell crawlers which paths they may visit. Each origin's `/robots.txt` is fetched once, on first use, and the result is cached. Both pages and images are checked against it.

| Situation | Decision |
|-----------|----------|
| A group names `Arachnida` | That group's rules apply (several such groups are merged) |
| No group names `Arachnida` | The `*` group applies |
| Several rules match a path | The longest one wins; on equal length, `Allow` wins |
| `*` in a rule | Matches any sequence of characters |
| `$` at the end of a rule | The path must end there |
| `/robots.txt` itself | Always allowed |
| robots.txt answers 4xx | No restrictions |
| robots.txt answers 5xx, or the server is unreachable | Nothing is crawled on that origin |

A `Crawl-delay` line is honoured for that origin. It never goes below 0.5 s and is capped at 10 s, so a hostile value cannot freeze the crawl.

The parser is written by hand rather than using `urllib.robotparser`: the standard library only supports wildcards and longest-match from Python 3.14.5 onward.

### Interruption

Ctrl+C stops the crawl cleanly. Any partial `.part` file is removed, the summary is printed, and the exit status is 130.

---

## Security considerations

Everything Spider receives (HTML, URLs, headers, robots.txt, image bytes) comes from a server that may be hostile. The design treats it that way.

| Risk | Mitigation |
|------|------------|
| **Path traversal** through a crafted file name (`../../.bashrc`) | Only the last path segment is kept, filtered to `[A-Za-z0-9._-]`, prefixed with a hash and given an extension chosen by the program |
| **Memory exhaustion** from a huge or endless response | Streaming reads with a size cap for every type of content |
| **Hanging connections** | 10s timeout on every request |
| **Disguised files** (an HTML page or script named `.jpg`) | Format decided by magic bytes, not by the extension or `Content-Type` |
| **Dangerous URL schemes** (`javascript:`, `file:`, `data:`) | Only `http` and `https` are followed |
| **Leaving the target site** | Same-origin scope; out-of-scope redirects are refused |
| **ReDoS** through a crafted robots.txt rule ([CWE-1333](https://cwe.mitre.org/data/definitions/1333.html)) | Wildcards are matched by an iterative function with a single backtrack point, not by a regex. Its cost grows with `len(pattern) × len(path)` at worst, never exponentially |
| **Server overload** | 0.5s minimum between requests, plus robots.txt `Crawl-delay` |

### A note on dependencies

During development, Dependabot reported vulnerabilities in `soupsieve`, the CSS selector engine bundled with Beautiful Soup. Analysis showed that they are only reachable through CSS selectors (`select()`, `select_one()`, `.css`), which the code never uses: all lookups go through `find()` and `find_all()`.

The alerts were nonetheless fixed by upgrading. The patched versions require Python 3.11.5 or later, which is why that is the minimum version. `tests/test_security.py` remains as a second line of defence: it fails if a CSS selector call ever appears in `src/`.

---

## Testing

129 tests, run with `pytest`. None of them uses the network.

| File | Covers |
|------|--------|
| `test_cli.py` | Defaults, combined flags, invalid depths and URLs |
| `test_url_utils.py` | Normalisation, origin, scope |
| `test_parser.py` | Link extraction, `<base href>`, rejected schemes |
| `test_fetcher.py` | Size caps, Content-Type, errors, robots.txt fetching, Crawl-delay bounds |
| `test_downloader.py` | Magic bytes, file naming, atomic writes |
| `test_crawler.py` | BFS on a fake site: depth, scope, redirects, duplicates, robots.txt |
| `test_robots.py` | Group selection, longest match, wildcards, status codes, ReDoS timing |
| `test_security.py` | No CSS selector call anywhere in `src/` |

---

## Deliberate choices

- **BFS rather than DFS.** The depth limit means "distance from the start page". With BFS, each page's depth is the shortest path to it; with DFS, a page reached first through a long path could be cut off although it sits one click from the start.
- **Same-origin scope for pages.** The subject does not define how far the crawler may go. Staying on the start origin is the safest reading.
- **robots.txt is always honoured**, with no option to disable it. A crawler that respects site rules is the expected default.

---

## Known limitations

- **No JavaScript.** Images inserted by scripts are invisible to Spider.
- **Only `<img src>` and `<a href>`.** `srcset`, `<picture>`/`<source>` and CSS backgrounds are not read.
- **Extensionless image URLs are missed.** Image detection relies on the URL extension before download (`/photo?id=42` is treated as a page).
- **Redirects are checked after the fact.** `requests` follows a redirect before robots.txt can be checked for the target. A refused target is fetched but not used.
- **Percent-encoded characters are not decoded** in robots.txt matching: `/%7Euser` and `/~user` are treated as different paths.
- **Sequential crawl.** One request at a time.
- **Global throttle.** The delay is measured from the last request to *any* host. This is sometimes slower than needed.
- The `visiting` line is printed before the robots.txt check, so a blocked page still appears as visited in the log.

---

## Scorpion

*In progress.*

---

## Layout

```
arachnida/
├── spider                  # launcher (./spider)
├── src/
│   ├── common/
│   │   └── colors.py       # ANSI colours and info / warn / error helpers
│   ├── spider/
│   │   ├── main.py         # entry point, destination check, exit codes
│   │   ├── cli.py          # argument parsing
│   │   ├── crawler.py      # BFS, scope, redirects, duplicates
│   │   ├── fetcher.py      # all HTTP requests: throttle, timeouts, size caps
│   │   ├── parser.py       # URL extraction from HTML
│   │   ├── downloader.py   # magic bytes, file naming, atomic write
│   │   ├── robots.py       # RFC 9309 parser and per-origin cache
│   │   └── url_utils.py    # normalisation, origin, scope
│   └── scorpion/
├── tests/
├── pytest.ini
├── requirements.txt
└── requirements-dev.txt
```

---

## References

- [Requests documentation](https://requests.readthedocs.io/)
- [Beautiful Soup documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [lxml](https://lxml.de/)
- [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309)
- [RFC 3986: URI Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986)
- [CWE-1333: Inefficient Regular Expression Complexity](https://cwe.mitre.org/data/definitions/1333.html)
- [List of file signatures (magic bytes)](https://en.wikipedia.org/wiki/List_of_file_signatures)
- [pytest documentation](https://docs.pytest.org/)
- [Python `collections.deque`](https://docs.python.org/3/library/collections.html#collections.deque)