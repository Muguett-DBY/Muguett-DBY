# Reuse the profile refresh setup

The profile uses checked-in SVGs, so viewing the README does not depend on a
statistics service responding at that moment. The contribution city, star badge
and earned-achievements section refresh in one daily job.

## Contribution city

1. Start with the [upstream setup guide](https://github.com/yoshi389111/github-profile-3d-contrib).
2. Copy [`scripts/profile-city-theme.json`](../scripts/profile-city-theme.json)
   into your profile repository and use it as `SETTING_JSON` in the action.
3. Keep `USERNAME` set to your own account, such as
   `${{ github.repository_owner }}`, and provide the built-in `GITHUB_TOKEN`.
4. The theme writes `profile-3d-contrib/custard-city.svg`. Change `fileName` if
   you want another output name, and update your README and publishing step to
   match.

The theme defines both light and dark colours. `growingAnimation` is disabled
for a still calendar. The [daily workflow](../.github/workflows/refresh-profile-city.yml)
shows the complete setup, including a daily schedule in `Australia/Sydney`.
GitHub can delay scheduled runs, so this is a daily refresh rather than an
exact-time guarantee.

## Total stars

[`scripts/refresh-stars.py`](../scripts/refresh-stars.py) uses only Python's
standard library. Copy it into `scripts/`, create an `assets/` directory, and run:

```yaml
- name: Refresh total stars
  run: python3 scripts/refresh-stars.py
  env:
    GITHUB_REPOSITORY_OWNER: ${{ github.repository_owner }}
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Link `assets/total-stars.svg` from your README and include it in the publishing
step. The number sums stars across all public repositories owned by the named
account, including forks and archived repositories. It is not the single-repo
milestone used by GitHub's Starstruck achievement.

## Already-earned achievements

[`scripts/refresh-achievements.py`](../scripts/refresh-achievements.py) also uses
only the Python standard library. Copy it into `scripts/` and add one marked
block to your profile README:

```html
<!-- earned-achievements:start -->
<!-- earned-achievements:end -->
```

```yaml
- name: Refresh earned achievements
  run: python3 scripts/refresh-achievements.py
  env:
    GITHUB_REPOSITORY_OWNER: ${{ github.repository_owner }}
```

The script reads the awards shown on your public GitHub profile and deduplicates
repeated entries. It wraps GitHub's badge images in self-contained SVG cards
under `assets/profile/achievements/` and updates the marked README block. Commit
both the cards and the README in your publishing step.

If your profile has no visible awards yet, add this step once an award appears.
An empty result or an unavailable badge image leaves the previous showcase in
place. The script relies on GitHub's public profile markup, which can change.

## Publishing without stale checkouts

Jobs that write artwork share one concurrency group and check out the current
default branch when they start. Otherwise, a queued job can use its older event
commit and fail to push after another refresh has already published changes.

Commit the intended SVGs and README after validation. The daily workflow can
still update the star badge and city if a badge image is temporarily unavailable.
You can run either profile workflow manually from the Actions tab.

## Credits and reuse terms

The contribution-city generator is by
[yoshi389111](https://github.com/yoshi389111/github-profile-3d-contrib), under its
own MIT license. The original helper scripts in this repository are available
under [PolyForm Noncommercial 1.0.0](../LICENSE); check those terms before reuse.
GitHub's badge artwork and third-party icons retain their respective rights.
See [credits](../CREDITS.md) and [license scope](LICENSE_SCOPE.md).
