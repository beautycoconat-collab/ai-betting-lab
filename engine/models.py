"""Numerical score models. Infinite-support PMF, explicit display tail, no LLM."""
import json,math
from pathlib import Path
from itertools import groupby
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson,skellam

RATE_MIN=0.02
RATE_MAX=8.0

def ordered(rows):
    if not rows:raise ValueError('empty_training')
    rows=sorted(rows,key=lambda r:(r['date'],r['id']))
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate_training_match')
    for r in rows:
        if r['home']==r['away'] or r['home_goals'] is None or r['away_goals'] is None:raise ValueError('invalid_training_row')
        if type(r['neutral']) is not bool:raise ValueError('unknown_neutral_venue')
        if any(type(r[k]) is not int or r[k]<0 for k in ('home_goals','away_goals')):raise ValueError('invalid_goals')
    if len({r['target'] for r in rows})!=1:raise ValueError('mixed_score_definitions')
    return rows

class ScoreDistribution:
    def __init__(self,home_rate,away_rate,rho=0.0):
        self.home_rate=float(home_rate);self.away_rate=float(away_rate);self.rho=float(rho)
        if not all(math.isfinite(v) for v in (home_rate,away_rate,rho)) or not RATE_MIN<=home_rate<=RATE_MAX or not RATE_MIN<=away_rate<=RATE_MAX:raise ValueError('invalid_rates')
        if min(self.tau(h,a) for h,a in ((0,0),(0,1),(1,0),(1,1)))<=0:raise ValueError('invalid_dc_tau')
    def tau(self,h,a):
        l,m,r=self.home_rate,self.away_rate,self.rho
        return {(0,0):1-l*m*r,(0,1):1+l*r,(1,0):1+m*r,(1,1):1-r}.get((h,a),1.0)
    def log_probability(self,h,a):
        if type(h) is not int or type(a) is not int or h<0 or a<0:raise ValueError('invalid_score')
        return float(poisson.logpmf(h,self.home_rate)+poisson.logpmf(a,self.away_rate)+math.log(self.tau(h,a)))
    def probability(self,h,a):return math.exp(self.log_probability(h,a))
    def grid(self,max_goals=20):
        if not 1<=max_goals<=100:raise ValueError('grid_bounds')
        p=np.outer(poisson.pmf(np.arange(max_goals+1),self.home_rate),poisson.pmf(np.arange(max_goals+1),self.away_rate))
        for h,a in ((0,0),(0,1),(1,0),(1,1)):p[h,a]*=self.tau(h,a)
        tail=float(poisson.sf(max_goals,self.home_rate)+poisson.cdf(max_goals,self.home_rate)*poisson.sf(max_goals,self.away_rate))
        return p,tail
    def outcome(self):
        l,m=self.home_rate,self.away_rate
        c=l*m*self.rho*math.exp(-l-m)
        p=np.array([skellam.sf(0,l,m)+c,skellam.pmf(0,l,m)-2*c,skellam.cdf(-1,l,m)+c],dtype=float)
        if np.any(p<0) or not np.isclose(p.sum(),1,atol=1e-10):raise ValueError('outcome_mass')
        return p
    def export(self,max_goals=20):
        grid,tail=self.grid(max_goals)
        top=sorted(((float(grid[h,a]),h,a) for h in range(len(grid)) for a in range(len(grid))),reverse=True)[:5]
        return {'home_rate':self.home_rate,'away_rate':self.away_rate,'rho':self.rho,'pmf':'Poisson(h;home_rate)*Poisson(a;away_rate)*DixonColesTau(h,a;rho)','support':'all nonnegative integer pairs','grid_max_goals':max_goals,'grid':grid.tolist(),'outside_grid_probability':tail,'p_1x2':self.outcome().tolist(),'top_scores':[{'score':f'{h}-{a}','probability':p} for p,h,a in top]}

def rates(z):
    z=np.asarray(z,dtype=float)
    low,high=math.log(RATE_MIN),math.log(RATE_MAX)
    v=np.exp(np.clip(z,low,high));mask=((z>low)&(z<high)).astype(float)
    return v,mask

def optimize(fun,x,bounds):
    fit=minimize(fun,np.asarray(x,float),jac=True,method='L-BFGS-B',bounds=bounds,options={'maxiter':1200,'ftol':1e-11,'gtol':1e-6,'maxls':50})
    if not fit.success or not np.isfinite(fit.fun):raise RuntimeError('optimizer_failed:'+str(fit.message))
    return fit.x,{'converged':True,'iterations':int(fit.nit),'objective':float(fit.fun)}

class Base:
    name='base'
    def metadata(self,rows):
        self.training_end=rows[-1]['date'];self.target=rows[0]['target'];self.n_train=len(rows)
    def check(self,home,away,neutral):
        if home==away or type(neutral) is not bool:raise ValueError('invalid_fixture')
    def save(self,path):
        data={'format_version':1,'model':self.name,'state':self.__dict__}
        Path(path).write_text(json.dumps(data,sort_keys=True,ensure_ascii=False,indent=2))
    @staticmethod
    def load(path):
        x=json.loads(Path(path).read_text())
        if x['format_version']!=1 or x['model'] not in MODELS:raise ValueError('unsupported_model')
        m=MODELS[x['model']]();m.__dict__.update(x['state']);return m

class ConstantPoisson(Base):
    name='baseline'
    def fit(self,rows):
        rows=ordered(rows);self.metadata(rows)
        self.h=float(np.clip(np.mean([r['home_goals'] for r in rows]),RATE_MIN,RATE_MAX));self.a=float(np.clip(np.mean([r['away_goals'] for r in rows]),RATE_MIN,RATE_MAX))
        self.fit_info={'converged':True,'method':'training_goal_means'};return self
    def predict(self,home,away,neutral=False):
        self.check(home,away,neutral);return ScoreDistribution(self.h,self.a)

class EloGoals(Base):
    name='elo'
    def __init__(self,k=20.0,home_advantage=60.0):self.k=k;self.home_advantage=home_advantage
    def fit(self,rows):
        rows=ordered(rows);self.metadata(rows);rating={};features=[];y=[];x=[]
        for day,batch in groupby(rows,key=lambda r:r['date']):
            group=list(batch);deltas={}
            for r in group:
                h,a=r['home'],r['away'];rh,ra=rating.get(h,1500.),rating.get(a,1500.)
                diff=(rh-ra)/400;nonneutral=float(not r['neutral']);features.append([1,nonneutral,diff]);x.append(r['home_goals']);y.append(r['away_goals'])
                expected=1/(1+10**(-(rh-ra+self.home_advantage*nonneutral)/400))
                actual=1 if x[-1]>y[-1] else .5 if x[-1]==y[-1] else 0
                delta=self.k*(actual-expected);deltas[h]=deltas.get(h,0)+delta;deltas[a]=deltas.get(a,0)-delta
            for team,delta in deltas.items():rating[team]=rating.get(team,1500.)+delta
        f=np.array(features);fa=np.column_stack([np.ones(len(rows)),np.zeros(len(rows)),-f[:,2]]);x=np.array(x);y=np.array(y)
        def objective(v):
            l,ml=rates(f@v);m,mm=rates(fa@v)
            loss=np.mean(l-x*np.log(l)+m-y*np.log(m))+.01*v[2]**2
            grad=(f.T@((l-x)*ml)+fa.T@((m-y)*mm))/len(x);grad[2]+=.02*v[2]
            return loss,grad
        v,info=optimize(objective,[math.log(max(.1,y.mean())),.2,.3],[(-3,2),(-1,1),(0,3)])
        self.coefficients=v.tolist();self.ratings=rating;self.fit_info=info;return self
    def predict(self,home,away,neutral=False):
        self.check(home,away,neutral);v=np.array(self.coefficients);diff=(self.ratings.get(home,1500)-self.ratings.get(away,1500))/400
        l,_=rates(np.array([1,float(not neutral),diff])@v);m,_=rates(np.array([1,0,-diff])@v)
        return ScoreDistribution(l,m)

class TeamPoisson(Base):
    name='poisson'
    def __init__(self,half_life_days=730.,ridge=.01):self.half_life_days=half_life_days;self.ridge=ridge
    def fit(self,rows):
        from datetime import date
        rows=ordered(rows);self.metadata(rows);teams=sorted({r[k] for r in rows for k in ('home','away')});index={t:i for i,t in enumerate(teams)};n=len(teams)
        ih=np.array([index[r['home']] for r in rows]);ia=np.array([index[r['away']] for r in rows]);x=np.array([r['home_goals'] for r in rows]);y=np.array([r['away_goals'] for r in rows]);venue=np.array([not r['neutral'] for r in rows],float)
        ages=np.array([(date.fromisoformat(self.training_end)-date.fromisoformat(r['date'])).days for r in rows]);w=np.exp(-math.log(2)*ages/self.half_life_days);w/=w.sum()
        dc=self.name=='dixon_coles'
        def objective(v):
            a=v[2:2+n]-np.mean(v[2:2+n]);d=v[2+n:2+2*n]-np.mean(v[2+n:2+2*n]);rho=v[-1] if dc else 0.
            l,ml=rates(v[0]+v[1]*venue+a[ih]+d[ia]);m,mm=rates(v[0]+a[ia]+d[ih])
            tau=np.ones(len(x));dl=np.zeros(len(x));dm=np.zeros(len(x));dr=np.zeros(len(x))
            for mask,value,al,am,ar in [((x==0)&(y==0),1-l*m*rho,-m*rho,-l*rho,-l*m),((x==0)&(y==1),1+l*rho,np.full(len(x),rho),np.zeros(len(x)),l),((x==1)&(y==0),1+m*rho,np.zeros(len(x)),np.full(len(x),rho),m),((x==1)&(y==1),np.full(len(x),1-rho),np.zeros(len(x)),np.zeros(len(x)),-np.ones(len(x)))]:
                tau[mask]=value[mask];dl[mask]=al[mask];dm[mask]=am[mask];dr[mask]=ar[mask]
            if np.any(tau<=0):raise ValueError('invalid_tau_during_fit')
            loss=float(np.sum(w*(l-x*np.log(l)+gammaln(x+1)+m-y*np.log(m)+gammaln(y+1)-np.log(tau))))+self.ridge*(np.mean(a*a)+np.mean(d*d))
            gl=w*(l-x-dl*l/tau)*ml;gm=w*(m-y-dm*m/tau)*mm
            ga=np.bincount(ih,weights=gl,minlength=n)+np.bincount(ia,weights=gm,minlength=n);gd=np.bincount(ia,weights=gl,minlength=n)+np.bincount(ih,weights=gm,minlength=n)
            ga-=ga.mean();gd-=gd.mean();ga+=2*self.ridge*a/n;gd+=2*self.ridge*d/n
            grad=np.r_[np.sum(gl+gm),np.sum(gl*venue),ga,gd]
            if dc:grad=np.r_[grad,-np.sum(w*dr/tau)]
            return loss,grad
        start=np.r_[math.log(max(.1,y.mean())),.2,np.zeros(2*n)]
        bounds=[(-3,2),(-1,1)]+[(-2,2)]*(2*n)
        if dc:start=np.r_[start,-.02];bounds.append((-.12,.015))
        v,info=optimize(objective,start,bounds)
        self.mu=float(v[0]);self.home_advantage=float(v[1]);self.attack={t:float(v[2+i]-np.mean(v[2:2+n])) for t,i in index.items()};self.defence={t:float(v[2+n+i]-np.mean(v[2+n:2+2*n])) for t,i in index.items()};self.rho=float(v[-1]) if dc else 0.;self.fit_info=info
        return self
    def predict(self,home,away,neutral=False):
        self.check(home,away,neutral)
        l,_=rates(self.mu+self.home_advantage*(not neutral)+self.attack.get(home,0)+self.defence.get(away,0));m,_=rates(self.mu+self.attack.get(away,0)+self.defence.get(home,0))
        return ScoreDistribution(l,m,self.rho)

class DixonColes(TeamPoisson):name='dixon_coles'
MODELS={'baseline':ConstantPoisson,'elo':EloGoals,'poisson':TeamPoisson,'dixon_coles':DixonColes}
