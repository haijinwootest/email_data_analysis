"""Approved no-change preparation of Hillstrom email experiment data.

Usage: python prepare_email_experiment.py
No rows, values, dtypes, or columns are modified. Original CSV stays untouched.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import pandas as pd

DIR = Path(__file__).resolve().parent
SOURCE = DIR / 'Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv'
OUTPUT = DIR / 'email_experiment_clean.csv'
LOG = DIR / 'email_experiment_preprocessing_log.json'
REQUIRED = ['segment', 'conversion', 'spend']

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def profile(df):
    grouped = df.groupby('segment', dropna=False).agg(
        rows=('segment','size'), conversions=('conversion','sum'),
        spend_sum=('spend','sum'), spend_mean=('spend','mean')).sort_index()
    return {
        'rows': len(df), 'columns': len(df.columns), 'column_names': df.columns.tolist(),
        'dtypes': {k:str(v) for k,v in df.dtypes.items()},
        'missing_by_column': {k:int(v) for k,v in df.isna().sum().items()},
        'duplicate_rows': int(df.duplicated().sum()),
        'zero_spend_rows': int(df['spend'].eq(0).sum()),
        'total_conversions': int(df['conversion'].sum()),
        'total_spend': round(float(df['spend'].sum()), 2),
        'groups': {str(name): {
            'rows':int(row['rows']), 'conversions':int(row['conversions']),
            'spend_sum':round(float(row['spend_sum']),2),
            'spend_mean':float(row['spend_mean'])}
            for name,row in grouped.iterrows()}
    }

def main():
    if SOURCE.resolve() == OUTPUT.resolve():
        raise RuntimeError('Source and output cannot be the same file')
    original_hash_before = digest(SOURCE)
    original = pd.read_csv(SOURCE)
    missing = set(REQUIRED)-set(original.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')
    # Approved operation: preserve all original bytes rather than rewriting CSV.
    shutil.copyfile(SOURCE, OUTPUT)
    cleaned = pd.read_csv(OUTPUT)
    before, after = profile(original), profile(cleaned)
    checks = {
        'original_unchanged': digest(SOURCE) == original_hash_before,
        'byte_for_byte_identical': digest(SOURCE) == digest(OUTPUT),
        'dataframe_equal': original.equals(cleaned),
        'schema_equal': before['column_names'] == after['column_names'] and before['dtypes'] == after['dtypes'],
        'group_aggregates_equal': before['groups'] == after['groups'],
        'all_profile_checks_equal': before == after,
    }
    if not all(checks.values()):
        raise AssertionError('No-change preservation verification failed')
    log = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'decision': 'Do not clean/transform; preserve raw observations under the latest approval',
        'source_file': SOURCE.name, 'output_file': OUTPUT.name,
        'operations': [
            {'target':'all columns and rows','condition':'no deletion, imputation, recoding, winsorization, or type conversion approved',
             'action':'no transformation; byte-exact copy to distinct file',
             'deleted_rows':0, 'modified_values':0, 'created_columns':0}],
        'before':before, 'after':after, 'checks':checks,
        'source_sha256':digest(SOURCE),'output_sha256':digest(OUTPUT),
        'kpi_impact':'No change: all group denominators, conversions, and spend totals preserved',
        'limitations': ['Customer-level uniqueness cannot be proven without true customer ID',
                        '14-day window and randomization require source documentation']}
    LOG.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source':SOURCE.name,'output':OUTPUT.name,'log':LOG.name,
                      'before':before,'checks':checks,'operations':log['operations']},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
