# Carson Strachan's referee profile

The dashboard shows career totals, season and monthly charts, rink and partner rankings, and a filterable game log. Hockey seasons run from June 1 through May 31.

## Publish the dashboard for the first time

1. Extract the ZIP. In GitHub Desktop, select `warpedcanadian/referee-profile` and choose **Repository → Show in Explorer**.
2. Copy the contents of the extracted folder into that checkout. Include `.github`, `.gitignore`, and `site/.nojekyll`. Keep the site's files inside `site` so the included Pages workflow can find them.
3. In GitHub Desktop, review the changes, select the dashboard files, commit to `main`, and push to origin.
4. In the GitHub repository, open **Settings → Pages** and select **GitHub Actions** as the source. In **Actions → Publish referee profile**, select **Run workflow** on `main` if the first push did not start a deployment.
5. After the workflow succeeds, open [the referee profile](https://warpedcanadian.github.io/referee-profile/).

[GitHub Pages publishing settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## Update the dashboard each month

1. Save the full workbook with the latest games on `RawData`.
2. In the checkout, double-click **Refresh-Dashboard.cmd** and choose the workbook. The tool prints the total games and last game date and updates `site/data/games.json`.
3. Review the count and date. In GitHub Desktop, commit the change to `site/data/games.json` and push. GitHub Pages updates after the workflow succeeds.

The refresh reads `RawData` directly. It supports the original layout and a native `Games` table on that tab. The workbook stays on your computer. The public file contains game dates, rinks, levels, hours, solo status, and partners listed by first name and last initial. Fees, game numbers, notes, equipment fields, and full partner names are excluded. The exporter keeps a local `.local/partner-map.json` to distinguish partners who share the same public label. Git ignores that folder.

Add or update locations on the `Rinks` tab using the `Rink` (or `Site`), `City`, and `State` columns. Use one row per rink and match the `Site` name on `RawData`. Full state names and postal abbreviations both work. The refresh adds these locations to the public file and places markers at city points from the [2024 U.S. Census Gazetteer](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2024.html). The map uses [2024 Census state boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html). When a city lacks a matching Census point, the dropdown still shows the city and state.

The Windows launcher uses the bundled Codex Python runtime when available. On another computer with Python installed, run `py -3 -m pip install -r requirements.txt` once from the checkout. To refresh from a terminal, run `py -3 scripts/export_games.py --workbook "C:\path\to\Refereeing Tracking.xlsx"`.
