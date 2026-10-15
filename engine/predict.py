"""Saved-model inference. Input fixture must not contain score labels."""
import argparse,json
from pathlib import Path
from .models import Base
FORBIDDEN={'home_goals','away_goals','home_score','away_score','result','score'}

def predict(model,fixture):
    if FORBIDDEN.intersection(fixture):raise ValueError('outcome_fields_not_allowed_in_fixture')
    from datetime import date
    date.fromisoformat(fixture['date'])
    if fixture['date']<=model.training_end:raise ValueError('fixture_not_after_training')
    if fixture['target']!=model.target:raise ValueError('score_definition_mismatch')
    if type(fixture['neutral']) is not bool:raise ValueError('neutral_status_required')
    known=set(getattr(model,'attack',getattr(model,'ratings',{})))
    return {'fixture':fixture,'model':model.name,'training_end':model.training_end,'unknown_teams':[t for t in (fixture['home'],fixture['away']) if known and t not in known],'distribution':model.predict(fixture['home'],fixture['away'],fixture['neutral']).export()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--fixture',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    result=predict(Base.load(a.model),json.loads(Path(a.fixture).read_text()));Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(a.out)
if __name__=='__main__':main()
