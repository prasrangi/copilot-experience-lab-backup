"""Build a portable content backup from a sanitized WordPress REST export."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen


class LocalLinks(HTMLParser):
    def __init__(self, source_url, replacements):
        super().__init__(convert_charrefs=False)
        self.source_url = source_url
        self.replacements = replacements
        self.parts = []

    def handle_starttag(self, tag, attrs):
        rewritten = []
        for name, value in attrs:
            if tag in ("img", "source") and name in ("srcset", "sizes"):
                continue
            if name in ("href", "src", "poster") and value:
                absolute = urljoin(self.source_url, value)
                key = absolute.split("#", 1)[0].split("?", 1)[0]
                if key in self.replacements:
                    value = self.replacements[key]
                    if "#" in absolute:
                        value += "#" + absolute.split("#", 1)[1]
            rewritten.append(
                name if value is None else f'{name}="{escape(value, quote=True)}"'
            )
        self.parts.append("<" + tag + (" " if rewritten else "") + " ".join(rewritten) + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.export.read_text(encoding="utf-8-sig"))
    if data.get("schemaVersion") != 1 or not data.get("posts"):
        raise ValueError("Expected a version-1 sanitized WordPress content export.")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("articles", "metadata", "media"):
        (root / name).mkdir(exist_ok=True)
    export_path = root / "wordpress-export.json"
    if args.export.resolve() != export_path:
        shutil.copyfile(args.export, export_path)

    site_host = urlsplit(data["siteUrl"]).hostname
    replacements = {}
    filenames = {}
    for post in data["posts"]:
        slug = re.sub(r"[^a-zA-Z0-9._-]", "-", post["slug"] or str(post["id"]))
        filename = f'{post["id"]}-{slug}.html'
        filenames[post["id"]] = filename
        replacements[post["link"].split("?", 1)[0]] = quote(filename)
    media_targets = {}
    for media in data["media"]:
        url = media["sourceUrl"]
        if urlsplit(url).scheme != "https" or urlsplit(url).hostname != site_host:
            raise ValueError(f"Unexpected media origin for attachment {media['id']}.")
        basename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        basename = re.sub(r"[^a-zA-Z0-9._-]", "-", basename)
        filename = f'{media["id"]}-{basename}'
        media_targets[media["id"]] = (url, filename)
        replacements[url] = "../media/" + quote(filename)
        for size in (media.get("sizes") or {}).values():
            size_url = size.get("source_url")
            if size_url:
                replacements[size_url] = "../media/" + quote(filename)

    def download(media):
        url, filename = media_targets[media["id"]]
        target = root / "media" / filename
        # Each retry is explicit; a failed attachment aborts the backup.
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={"User-Agent": "WordPressContentBackup/1.0"}), timeout=120) as response:
                    payload = response.read()
                    expected = response.headers.get("Content-Length")
                    if not payload or (expected and len(payload) != int(expected)):
                        raise ValueError(f"Incomplete attachment {media['id']}.")
                target.write_bytes(payload)
                break
            except (OSError, ValueError):
                if attempt == 2:
                    raise
        return {
            "id": media["id"],
            "sourceUrl": url,
            "path": "media/" + filename,
            "bytes": len(payload),
            "sha256": sha256(payload).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        media_manifest = list(pool.map(download, data["media"]))

    tags = {t["id"]: t["name"] for t in data["tags"]}
    categories = {c["id"]: c["name"] for c in data["categories"]}
    article_manifest = []
    for post in data["posts"]:
        local = LocalLinks(post["link"], replacements)
        local.feed(post["contentRendered"])
        local.close()
        tag_names = [tags[t] for t in post["tags"]]
        category_names = [categories[c] for c in post["categories"]]
        html = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(post["title"])}</title>'
            '<style>body{font:17px/1.65 system-ui,sans-serif;max-width:1000px;margin:32px auto;padding:0 20px;color:#172033}'
            'img{max-width:100%;height:auto}table{width:100%;table-layout:fixed;overflow-wrap:anywhere;border-collapse:collapse}'
            'th,td{border:1px solid #d8e0ec;padding:10px}pre{overflow:auto;background:#f4f7fb;padding:16px}'
            'blockquote{border-left:4px solid #155eef;padding:12px 20px;background:#eff6ff}'
            'summary{cursor:pointer;padding:12px;font-weight:700}figcaption{font-size:.85em;color:#526077}'
            '</style></head><body><nav><a href="../index.html">Backup index</a></nav>'
            f'<h1>{escape(post["title"])}</h1><p>{escape(post["author"])} · '
            f'{escape(post["date"])} · {escape(post["status"])}</p>'
            f'<p>Categories: {escape(", ".join(category_names))}<br>Tags: {escape(", ".join(tag_names))}</p>'
            + "".join(local.parts)
            + "</body></html>"
        )
        filename = filenames[post["id"]]
        article_path = root / "articles" / filename
        article_path.write_text(html, encoding="utf-8")
        write_json(root / "metadata" / f'{post["id"]}.json', post)
        article_manifest.append({
            "id": post["id"], "title": post["title"], "status": post["status"],
            "path": "articles/" + filename,
            "metadataPath": f'metadata/{post["id"]}.json',
            "sha256": sha256(article_path.read_bytes()).hexdigest(),
        })
    index = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Copilot Experience Lab backup</title>',
        '<body><h1>Copilot Experience Lab — content backup</h1>',
        f'<p>Exported {escape(data["exportedAt"])}</p><ul>',
    ]
    for post in article_manifest:
        index.append(f'<li><a href="{quote(post["path"])}">{escape(post["title"])}</a> ({post["status"]})</li>')
    index.append("</ul><p>Download or clone this repository and open this file locally. GitHub does not render HTML as a website.</p></body></html>")
    (root / "index.html").write_text("\n".join(index), encoding="utf-8")
    manifest = {
        "schemaVersion": 1, "exportedAt": data["exportedAt"], "sourceSite": data["siteUrl"],
        "articles": article_manifest, "media": media_manifest,
        "articleCount": len(article_manifest), "mediaCount": len(media_manifest),
        "mediaBytes": sum(m["bytes"] for m in media_manifest),
    }
    write_json(root / "manifest.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("articleCount", "mediaCount", "mediaBytes")}))


if __name__ == "__main__":
    main()
