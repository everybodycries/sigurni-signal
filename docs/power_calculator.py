"""Planerski Wh kalkulator; nije mjerenje autonomije."""
import argparse, json, math
def required_wh(daily_wh,days=3,efficiency=.85,usable_fraction=.9):
    values=(daily_wh,days,efficiency,usable_fraction)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values): raise ValueError('Finite numeric values required')
    if daily_wh<=0 or days<=0 or not 0<efficiency<=1 or not 0<usable_fraction<=1: raise ValueError('Consumption/days >0; factors in(0,1]')
    return daily_wh*days*1.3/(efficiency*usable_fraction)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--daily-wh',type=float,required=True);p.add_argument('--days',type=float,default=3)
    p.add_argument('--efficiency',type=float,default=.85);p.add_argument('--usable-fraction',type=float,default=.9)
    a=p.parse_args()
    print(json.dumps({'required_nominal_wh':required_wh(a.daily_wh,a.days,a.efficiency,a.usable_fraction),'reserve_fraction':.3,'measured_autonomy':False}))
if __name__=='__main__':main()
