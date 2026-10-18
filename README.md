# Copilot Experience Lab — blog content backup

This repository is a point-in-time **content backup**, not a complete WordPress database or Azure disaster-recovery backup.

## Contents

- `wordpress-export.json`: saved article content, original WordPress block HTML, rendered HTML, status, dates, author display names, categories, tags, and attachment metadata.
- `articles/`: portable HTML copies using the local images in `media/`.
- `metadata/`: per-article recovery metadata, including the original block HTML.
- `media/`: original attachment files. The latest snapshot includes only media referenced by published articles; earlier backups also retained unattached library assets.
- `manifest.json`: article and media inventory, export timestamp, sizes, and SHA-256 integrity hashes.
- `index.html`: local article index.
- `prepare_backup.py`: standard-library-only utility for packaging a fresh sanitized export.

The export deliberately excludes passwords, authentication cookies, API tokens, database credentials, user-account records, comments, and Azure secrets.

The repository is public. Refreshes must exclude unpublished article content and media used only by drafts. Previously committed files and commit history are retained; `manifest.json` identifies the files in the current snapshot.

## Read the backup offline

Clone or download the repository, then open `index.html` in a browser. Images are stored locally; they do not depend on the live Azure website. WordPress theme behavior and plugin-specific interactive features are not reproduced exactly. Links outside the backed-up articles may still point to the original website.

## Recover article content

1. Provision a working WordPress site and its infrastructure separately.
2. Restore media from `media/`, using `manifest.json` to map original URLs to backup files.
3. Recreate categories and tags from `wordpress-export.json`.
4. Restore each article using `contentRaw` from its JSON metadata to retain WordPress block markup.
5. Map taxonomy and attachment IDs to the new site, update media URLs, and check authors, dates, status, links, captions, and formatting.
6. Verify the restored site before making it public.

WordPress numeric IDs are site-specific. These JSON files are not a one-click WordPress importer.

## Refreshing this backup

Export a new sanitized WordPress REST snapshot with the same version-1 schema, then run:

```powershell
python .\prepare_backup.py --export C:\path\to\wordpress-export.json --output .
```

Review removed/renamed content separately: the packaging utility does not delete previously backed-up files automatically. Verify the new manifest, then commit and push.

This initial backup is manual. No scheduled GitHub Actions workflow or credentials have been configured.

## Keep separate backups

Retain MySQL backups, Azure Blob recovery protection, deployment source, and a tested restore procedure separately. This repository does not contain a database dump, website settings, custom theme/plugin source, or source Word documents.
