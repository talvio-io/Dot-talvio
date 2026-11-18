# OWNER ACTION — one-time setup: image decode workflow

The 10,000 NFT images cannot be pushed as binary files through the Muse
GitHub connector, so they are staged in this repo as base64 text files under
`b64/nft/images/<id>.txt`. One small GitHub Actions workflow decodes them into
real images at `nft/images/<id>.webp` and removes the staged text files.

The connector is not allowed to create files under `.github/workflows/`
(GitHub returns 403), so the project owner adds this file once, via the
GitHub website:

1. Open this repo on github.com → **Add file** → **Create new file**.
2. Name the file exactly: `.github/workflows/decode-b64.yml`
3. Paste the YAML below, then **Commit changes**.

After that, the workflow runs automatically on every push that touches
`b64/**` (and can be started manually from the Actions tab →
"Decode base64 images" → Run workflow). Each run decodes any staged files,
commits the resulting `.webp` images, and deletes the processed `.txt` files.

```yaml
name: Decode base64 images
on:
  push:
    paths:
      - 'b64/**'
  workflow_dispatch:
permissions:
  contents: write
concurrency:
  group: decode-b64
  cancel-in-progress: false
jobs:
  decode:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Decode staged images
        run: |
          set -euo pipefail
          found=0
          while IFS= read -r -d '' f; do
            rel="${f#b64/}"
            out="${rel%.txt}.webp"
            mkdir -p "$(dirname "$out")"
            base64 -d "$f" > "$out"
            rm "$f"
            found=1
          done < <(find b64 -type f -name '*.txt' -print0)
          if [ "$found" = "1" ]; then
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add -A
            git commit -m "Decode staged NFT images from base64"
            git push
          else
            echo "No staged base64 files found."
          fi
```
