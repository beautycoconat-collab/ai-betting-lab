import argparse,json,hashlib,platform
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import scipy
from .models import MODELS,Base
from .dataset import build,split,manifest
from .queue import Queue

SCORES=[(0,0),(1,0),(0,1),(1,1),(2,0),(0,2),(2,1),(1,2),(2,2),(3,1)]

def reliability(probs,labels):
    p=np.asarray(probs);y=np.asarray(labels);bins=[];ece=0.
    for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
        mask=(p>=lo)&((p<=hi) if hi==1 else (p<hi));n=int(mask.sum())
        if n:
            pred=float(p[mask].mean());observed=float(y[mask].mean());ece+=n/len(p)*abs(pred-observed)
            bins.append({'lower':float(lo),'upper':float(hi),'n':n,'predicted':pred,'observed':observed})
    return {'ece':float(ece),'bins':bins}

def evaluate(model,rows):
    outcome=[];scorell=[];scoreb=[];tail_bounds=[];targets=[];top_p=[];top_y=[];cells={f'{h}-{a}':{'p':[],'y':[]} for h,a in SCORES};preds=[]
    for r in rows:
        d=model.predict(r['home'],r['away'],r['neutral']);x,y=r['home_goals'],r['away_goals'];o=d.outcome();label=0 if x>y else 1 if x==y else 2
        grid,tail=d.grid(30);tail_bounds.append(tail**2);phat=d.probability(x,y);scorell.append(-d.log_probability(x,y));scoreb.append(float(np.sum(grid*grid)-2*phat+1));outcome.append(o);targets.append(label)
        h,a=np.unravel_index(np.argmax(grid),grid.shape);top_p.append(float(grid[h,a]));top_y.append(int((h,a)==(x,y)))
        for h,a in SCORES:cells[f'{h}-{a}']['p'].append(d.probability(h,a));cells[f'{h}-{a}']['y'].append(int((h,a)==(x,y)))
        # Prediction file intentionally contains no true score.
        preds.append({'match_id':r['id'],'date':r['date'],'home':r['home'],'away':r['away'],'neutral':r['neutral'],'target':r['target'],'model':model.name,'training_end':model.training_end,'mode':'retrospective_holdout','distribution':d.export()})
    outcome=np.array(outcome);targets=np.array(targets);truth=np.eye(3)[targets]
    metrics={'n':len(rows),'brier_1x2':float(np.mean(np.sum((outcome-truth)**2,axis=1))),'log_loss_1x2':float(np.mean(-np.log(outcome[np.arange(len(rows)),targets]))),'score_log_loss':float(np.mean(scorell)),'score_brier':float(np.mean(scoreb)),'score_brier_tail_error_bound':float(max(tail_bounds)),'exact_score_hit_rate':float(np.mean(top_y)),'top_score_reliability':reliability(top_p,top_y),'score_cell_reliability':{k:reliability(v['p'],v['y']) for k,v in cells.items()},'outcome_reliability':{k:reliability(outcome[:,i],truth[:,i]) for i,k in enumerate(['H','D','A'])}}
    return metrics,preds

def run(rows,out,train_end,validation_end,test_end):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);train,val,test=split(rows,train_end,validation_end,test_end)
    if len(train)<100 or len(val)<30 or len(test)<30:raise ValueError('insufficient_partition_size')
    if len({r['target'] for r in rows})!=1:raise ValueError('mixed_targets')
    report={'evaluation_mode':'retrospective_static_holdout','notice':'Downloaded archives are not verified pre-match snapshots. Test results are never fed into fitting or selection.','created_at':datetime.now(timezone.utc).isoformat(),'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},'splits':{'train':manifest(train),'validation':manifest(val),'test':manifest(test)},'models':{},'target':rows[0]['target'],'external_source_weight':0.0}
    fitted={}
    # Fixed algorithm settings before validation; no test-based tuning/refitting.
    for key,cls in MODELS.items():
        model=cls().fit(train);model.save(out/(key+'.model.json'));m,_=evaluate(model,val);fitted[key]=model
        report['models'][key]={'fit':model.fit_info,'validation':m}
    chosen=min(report['models'],key=lambda k:report['models'][k]['validation']['score_log_loss'])
    report['validation_selected_model']=chosen
    for key,model in fitted.items():
        m,preds=evaluate(model,test);report['models'][key]['test']=m
        (out/(key+'.predictions.json')).write_text(json.dumps(preds,ensure_ascii=False,separators=(',',':')))
    labels=[{k:r[k] for k in ('id','date','home_goals','away_goals','source_url','snapshot_sha256','observed_at')} for r in test]
    (out/'test-outcomes.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2))
    (out/'dataset.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
    code={str(p.relative_to(Path(__file__).parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}
    report['code_hashes']=code
    report['calibration']='Reliability diagnostics only; no probability recalibration fitted. ECE depends on bins and sample size.'
    (out/'evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    summary={'counts':{k:report['splits'][k]['count'] for k in report['splits']},'validation_selected_model':chosen,'target':report['target'],'test_metrics':{k:{m:v['test'][m] for m in ['brier_1x2','log_loss_1x2','score_log_loss','score_brier','exact_score_hit_rate']} for k,v in report['models'].items()}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/lab.sqlite');p.add_argument('--source',default='international');p.add_argument('--competition');p.add_argument('--dataset');p.add_argument('--out',default='reports/phase2/international');p.add_argument('--start',default='2010-01-01');p.add_argument('--train-end',default='2020-01-01');p.add_argument('--validation-end',default='2022-01-01');p.add_argument('--test-end',default='2024-01-01');a=p.parse_args()
    if a.dataset:rows=json.loads(Path(a.dataset).read_text())
    else:
        q=Queue(a.db)
        try:rows,excluded=build(q.db,a.source,a.competition,a.start,a.test_end)
        finally:q.close()
        print(json.dumps({'prepared':len(rows),'excluded':excluded}))
    print(json.dumps(run(rows,a.out,a.train_end,a.validation_end,a.test_end),indent=2))
if __name__=='__main__':main()
