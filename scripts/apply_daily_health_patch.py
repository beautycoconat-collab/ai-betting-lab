"""Apply the narrowly scoped daily-health integration to an existing repo.

Run from repository root. Refuses unexpected source changes; never edits DB,
workflows, migrations, or secrets. Re-running is idempotent.
"""
from pathlib import Path
import shutil


def apply(root=Path('.'), patch_root=None):
    root = Path(root).resolve()
    patch_root = Path(patch_root or Path(__file__).resolve().parents[1])
    target = root / 'dashboard/daily.py'
    if not target.is_file():
        raise FileNotFoundError('Expected existing dashboard/daily.py in repository root')
    raw = target.read_text(encoding='utf-8')
    import_line = 'from dashboard.daily_health import summary as daily_health_summary\n'
    quality_import = 'from dashboard.daily_quality import report as daily_quality_report\n'
    anchor_import = 'from dashboard.export import build as archive_projection\n'
    anchor_update = "output.update(engine_code_sha256=code_sha,fixtures=matches,connection='verified_source_worker',collection=collection,"
    if import_line not in raw:
        if raw.count(anchor_import) != 1:
            raise ValueError('Daily import anchor changed; inspect manually')
        raw = raw.replace(anchor_import, anchor_import + import_line)
    if quality_import not in raw:
        if raw.count(import_line) != 1:
            raise ValueError('Daily health import missing')
        raw = raw.replace(import_line, import_line + quality_import)
    if 'daily_automation=daily_health_summary(q.db, now)' not in raw:
        if raw.count(anchor_update) != 1:
            raise ValueError('Daily output anchor changed; inspect manually')
        raw = raw.replace(anchor_update, anchor_update + '\n            daily_automation=daily_health_summary(q.db, now),')
    if 'daily_quality=daily_quality_report(matches, now, collection)' not in raw:
        if raw.count('daily_automation=daily_health_summary(q.db, now),') != 1:
            raise ValueError('Daily health output missing')
        raw = raw.replace('daily_automation=daily_health_summary(q.db, now),',
                          'daily_automation=daily_health_summary(q.db, now),\n            daily_quality=daily_quality_report(matches, now, collection),')
    # Confirm both anchors before writing anything.
    if (raw.count(import_line) != 1 or raw.count(quality_import) != 1 or
        raw.count('daily_automation=daily_health_summary(q.db, now)') != 1 or
        raw.count('daily_quality=daily_quality_report(matches, now, collection)') != 1):
        raise ValueError('Patch validation failed')
    for relative in ('dashboard/daily_health.py', 'tests_dashboard/test_daily_health.py',
                     'dashboard/daily_quality.py', 'tests_dashboard/test_daily_quality.py'):
        destination = root / relative
        source = patch_root / relative
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise FileExistsError(f'Existing file differs: {relative}')
    for relative in ('dashboard/daily_health.py', 'tests_dashboard/test_daily_health.py',
                     'dashboard/daily_quality.py', 'tests_dashboard/test_daily_quality.py'):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(patch_root / relative, destination)
    if target.read_text(encoding='utf-8') != raw:
        target.write_text(raw, encoding='utf-8')
    return 'Applied daily health projection without enabling hosted automation.'


if __name__ == '__main__':
    print(apply())
