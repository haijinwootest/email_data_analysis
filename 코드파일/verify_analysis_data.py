from pathlib import Path
import pandas as pd, numpy as np, hashlib, json
B=Path('/mnt/data'); D=B/'email_analysis_datasets'
rawp=next(B.glob('Kevin_Hillstrom*.csv')); cleanp=B/'email_experiment_clean.csv'
a=pd.read_csv(rawp); b=pd.read_csv(cleanp); m=pd.read_csv(D/'email_analysis_master.csv')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
num=['recency','history','spend']; ds={}
for col in num:
 x=a[col];y=m[col];ds[col]={'equal':bool(x.equals(y)),'mean_before':float(x.mean()),'mean_after':float(y.mean()),'sd_before':float(x.std()),'sd_after':float(y.std()),'min':float(x.min()),'q25':float(x.quantile(.25)),'median':float(x.median()),'q75':float(x.quantile(.75)),'max':float(x.max())}
origcols=list(a.columns)
checks={'raw_clean_hash_equal':sha(rawp)==sha(cleanp),'raw_clean_equal':a.equals(b),'master_raw_cols_exact':m[origcols].equals(a),'master_cols':list(m.columns),'shape_before':list(a.shape),'shape_after':list(m.shape),'missing_before':int(a.isna().sum().sum()),'missing_after':int(m.isna().sum().sum()),'duplicates_before':int(a.duplicated().sum()),'duplicates_master_original_columns':int(m.duplicated(subset=origcols).sum()),'duplicates_after_full':int(m.duplicated().sum()),'unmapped_assignment':int(m.email_assigned.isna().sum()),'derived_mismatches':int((m.email_assigned!=m.segment.isin(['Mens E-Mail','Womens E-Mail']).astype(int)).sum()),'all_rowvalues_matching':bool(m[origcols].equals(a)), 'dist':ds}
basegrp=a.groupby('segment').agg(rows=('segment','size'),conv=('conversion','sum'),spend=('spend','sum')).sort_index(); mgr=m.groupby('segment').agg(rows=('segment','size'),conv=('conversion','sum'),spend=('spend','sum')).sort_index();checks['group_equal']=bool(basegrp.equals(mgr));checks['groups']=basegrp.reset_index().to_dict('records');checks['numeric_total']={'conversions':int(a.conversion.sum()),'spend':float(a.spend.sum())}
results={}
for name in ['q1_conversion_customer','q2_email_type_customer','q3_revenue_customer']:
 x=pd.read_csv(D/(name+'.csv'));ref=m[list(x.columns)];results[name]={'shape':list(x.shape),'value_match':bool(x.equals(ref)),'missing':int(x.isna().sum().sum())}
for name,key in [('q1_assignment_groups','email_assigned'),('q2_email_type_groups','segment'),('q3_revenue_groups','email_assigned')]:
 x=pd.read_csv(D/(name+'.csv'));ref=m.groupby(key).agg(assigned_rows=('conversion','size'),purchasers=('conversion','sum'),spend_total=('spend','sum')).reset_index(); xx=x.sort_values(key).reset_index(drop=True); rr=ref.sort_values(key).reset_index(drop=True)
 results[name]={'shape':list(x.shape),'key_equal':bool(xx[key].equals(rr[key])),'rows_equal':bool(xx.assigned_rows.equals(rr.assigned_rows)),'conv_equal':bool(xx.purchasers.equals(rr.purchasers)),'revenue_equal':bool(np.allclose(xx.spend_total,rr.spend_total,atol=1e-8,rtol=0)),'total_rows':int(x.assigned_rows.sum()),'total_conversions':int(x.purchasers.sum()),'total_spend':float(x.spend_total.sum())}
checks['derived_values']=m.email_assigned.value_counts().sort_index().to_dict();checks['other_datasets']=results
out=B/'email_data_integration_verification.json';out.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
