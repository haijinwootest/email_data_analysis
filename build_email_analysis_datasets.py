"""Build Hillstrom experiment analysis datasets without modifying original data.
Usage: python build_email_analysis_datasets.py
"""
from pathlib import Path
import json, hashlib
import pandas as pd

BASE=Path(__file__).resolve().parent
SOURCE=BASE/'email_experiment_clean.csv'
RAW=BASE/'Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv'
OUT=BASE/'email_analysis_datasets'
OUT.mkdir(exist_ok=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1048576),b''): h.update(c)
    return h.hexdigest()

def snapshot(df):
    return {'rows':len(df),'conversions':int(df.conversion.sum()),
            'spend_cents':int(round(df.spend.sum()*100)),
            'by_segment':{k:{'rows':int(v['rows']),'conversions':int(v['conversions']),
              'spend_cents':int(round(v['spend']*100))} for k,v in
              df.groupby('segment',sort=True).agg(rows=('segment','size'),conversions=('conversion','sum'),spend=('spend','sum')).to_dict('index').items()}}

raw_hash=sha256(RAW); clean_hash=sha256(SOURCE)
if raw_hash!=clean_hash: raise ValueError('Approved unchanged-source rule violated: hashes differ')
df=pd.read_csv(SOURCE)
expected=['recency','history_segment','history','mens','womens','zip_code','newbie','channel','segment','visit','conversion','spend']
assert df.columns.tolist()==expected
assert len(df)==64000 and df.isna().sum().sum()==0
assert set(df.segment)=={'Mens E-Mail','Womens E-Mail','No E-Mail'}
assert set(df.conversion)=={0,1}
assert (df.spend>=0).all()
base=snapshot(df)

master=df.copy()
master['email_assigned']=master.segment.map({'Mens E-Mail':1,'Womens E-Mail':1,'No E-Mail':0}).astype('int8')
assert master[expected].equals(df)
assert snapshot(master)==base

# Question-level observation tables. No joins or group-level replication.
q1=master[['segment','email_assigned','conversion']].copy()
q2=master[['segment','conversion']].copy() # retains control for incremental contrasts
q3=master[['segment','email_assigned','conversion','spend']].copy()

# Support tables: mutually exclusive groups; no conversion to effect metrics yet.
def summary(data, group):
    out=(data.groupby(group,dropna=False,sort=True)
          .agg(assigned_rows=('conversion','size'),purchasers=('conversion','sum'),spend_total=('spend','sum'))
          .reset_index())
    return out
q1summary=summary(master, 'email_assigned')
q2summary=summary(master, 'segment')
q3summary=summary(master, 'email_assigned')

files={
 'email_analysis_master.csv':master,
 'q1_conversion_customer.csv':q1,
 'q2_email_type_customer.csv':q2,
 'q3_revenue_customer.csv':q3,
 'q1_assignment_groups.csv':q1summary,
 'q2_email_type_groups.csv':q2summary,
 'q3_revenue_groups.csv':q3summary,
}
for name,data in files.items():
    data.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.12g')
    reloaded=pd.read_csv(OUT/name)
    assert len(reloaded)==len(data),name
    assert reloaded.columns.tolist()==data.columns.tolist(),name

assert len(q1)==len(q2)==len(q3)==len(master)==len(df)
assert int(q1.conversion.sum())==int(df.conversion.sum())
assert int(q2.conversion.sum())==int(df.conversion.sum())
assert int(q3.conversion.sum())==int(df.conversion.sum())
assert abs(q3.spend.sum()-df.spend.sum())<1e-7
for s in [q1summary,q2summary,q3summary]:
    assert s.assigned_rows.sum()==len(df)
    assert s.purchasers.sum()==int(df.conversion.sum())
    assert abs(s.spend_total.sum()-df.spend.sum())<1e-7
assert int((master.email_assigned==1).sum())==42694
assert int((master.email_assigned==0).sum())==21306

manifest={'input':{'file':SOURCE.name,'rows':len(df),'columns':len(df.columns),'raw_sha256':raw_hash,'clean_sha256':clean_hash},
          'join':{'performed':False,'before_rows':len(df),'after_rows':len(master),'key':'none; no customer ID in data'},
          'observation_unit':'one row per experiment assignment (per plan; customer uniqueness not verifiable without ID)',
          'dates':'no date/time column; 14-day observation from project plan only',
          'derived_columns':[{'name':'email_assigned','rule':'1 if Mens E-Mail or Womens E-Mail else 0'}],
          'source_snapshot':base,'source_rows_deleted':0,'source_values_modified':0,
          'files':[{ 'file':name,'rows':len(data),'columns':data.columns.tolist(),'sha256':sha256(OUT/name)} for name,data in files.items()],
          'checks':{'raw_equals_clean_bytewise':raw_hash==clean_hash,'master_12_source_columns_unchanged':master[expected].equals(df),'no_rows_added_or_removed':len(master)==len(df),'group_sizes_and_revenue_reconcile':True,'unmatched_join_keys':'not applicable','dup_rows_original':int(df.duplicated().sum())}}
with open(OUT/'validation_manifest.json','w',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
print(json.dumps({'files':[(name,len(data),len(data.columns)) for name,data in files.items()],'source_snapshot':base,'manifest':str(OUT/'validation_manifest.json')},ensure_ascii=False,indent=2))
