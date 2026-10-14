from pathlib import Path
import json
import numpy as np,pandas as pd
from analyze import ROOT,OUT
PAPER=ROOT/'paper';TAB=PAPER/'tables';TAB.mkdir(exist_ok=True)
SHORT={'Sunflower oil':'Crude seed oil'}
def name(s):return SHORT.get(s,s)
def num(x,d=2):return r'$\infty$' if not np.isfinite(x) else f'{x:.{d}f}'
def write(n,heads,rows,align=None):
 cols=align or 'l'+'r'*(len(heads)-1)
 s='\\begin{tabular}{'+cols+'}\n\\toprule\n'+' & '.join(heads)+r' \\'+'\n\\midrule\n'
 s+='\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)+'\n\\bottomrule\n\\end{tabular}\n'
 (TAB/(n+'.tex')).write_text(s)
def main():
 c=pd.read_csv(OUT/'coverage_2021.csv');write('coverage',['HS17','Product','Exporters','Importers','Routes','Mt','USD bn'],[[r.code,name(r['product']),r.exporters,r.importers,r.edges,f'{r.quantity_mt:.2f}',f'{r.value_billion_usd:.2f}'] for _,r in c.iterrows()])
 p=pd.read_csv(OUT/'panel_2021.csv');u=p[p.shock=='Ukraine'].set_index('product');b=p[p.shock=='Black Sea'].set_index('product')
 write('main',['Product',r'\multicolumn{3}{c}{Ukraine removal}',r'\multicolumn{3}{c}{Russia and Ukraine removal}'],[]) if False else None
 rows=[]
 for n in u.index:
  a=u.loc[n];bb=b.loc[n];rows.append([name(n)]+[num(100*x,2) for x in [a.rho_aggregate95,a.rho_frozen95,a.rho_swaps95,bb.rho_aggregate95,bb.rho_frozen95,bb.rho_swaps95]])
 write('main',['Product','Aggregate','Routes','Importers','Aggregate','Routes','Importers'],rows)
 p=TAB/'main.tex';s=p.read_text().replace('\\toprule\n','\\toprule\n & \\multicolumn{3}{c}{Ukraine removal} & \\multicolumn{3}{c}{Russia and Ukraine removal}\\\\\n\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\n');p.write_text(s)
 r=pd.read_csv(OUT/'robustness.csv');rp=r[(r['product']=='Soybeans')].pivot(index='spec',columns=['shock','policy'],values='rho95')
 labels={'all_current':'2021 support','union3':'2019--2021 union','persistent_material':'Persistent material routes','cap2':'Route ceiling: twice baseline','cap5':'Route ceiling: five times baseline','cap10':'Route ceiling: ten times baseline','value_units':'Nominal value units'}
 write('robust_soy',['Specification','Ukraine: routes','Ukraine: importers','Both: routes','Both: importers'],[[labels[s]]+[num(100*rp.loc[s,(sh,po)]) for sh in ['Ukraine','Black Sea'] for po in ['frozen','swaps']] for s in labels])
 f=pd.read_csv(OUT/'uniform_targets.csv');fp=f.pivot(index='product',columns=['shock','policy'],values='rho_uniform95')
 write('uniform',['Product','Ukraine: routes','Ukraine: importers','Both: routes','Both: importers'],[[name(n)]+[num(100*fp.loc[n,(sh,po)]) for sh in ['Ukraine','Black Sea'] for po in ['frozen','swaps']] for n in u.index])
 d=pd.read_csv(OUT/'historical_2022.csv');write('historical',['Product','2021 UA Mt','2022 UA Mt','New route (\\%)','Absent 3yr (\\%)'],[[name(r['product']),f'{r.Ukraine_exports_2021_mt:.3f}',f'{r.Ukraine_exports_2022_mt:.3f}',f'{100*r.new_route_share_2022:.2f}',f'{100*r.new_3yr_route_share_2022:.2f}'] for _,r in d.iterrows()])
 f=pd.read_csv(OUT/'minimum_withdrawals.csv');write('withdrawals',['Product','Growth (\\%)','Withdrawals (kt)','Surviving trade (\\%)'],[[name(r['product']),f'{100*r.rho95:.3f}',f'{1000*r.withdrawal_mt:.2f}',f'{100*r.withdrawal_share_surviving:.4f}'] for _,r in f.iterrows()])
 allp=pd.concat([pd.read_csv(x) for x in sorted(OUT.glob('panel_*.csv'))],ignore_index=True);s=allp[(allp['product']=='Soybeans')&(allp.shock=='Ukraine')].sort_values('year')
 write('years_soy',['Baseline year','Aggregate (\\%)','Routes (\\%)','Importers (\\%)','Difference (pp)'],[[int(r.year),num(100*r.rho_aggregate95),num(100*r.rho_frozen95),num(100*r.rho_swaps95),num(100*(r.rho_frozen95-r.rho_swaps95))] for _,r in s.iterrows()])
 cr=pd.concat([pd.read_csv(x) for x in OUT.glob('coverage_*.csv')]);write('year_coverage',['Year','Usable routes','USD bn','Mt'],[[int(y),int(g.edges.sum()),f'{g.value_billion_usd.sum():.2f}',f'{g.quantity_mt.sum():.2f}'] for y,g in cr.groupby('year')])
 vals=allp.filter(regex='^residual_').to_numpy().flatten();gaps=allp.filter(regex='^gap_').to_numpy().flatten()
 macros={'TotalRoutes':int(cr.edges.sum()),'TotalScenarios':len(allp),'FirstYear':int(cr.year.min()),'LastYear':int(cr.year.max()),'MaxResidual':f'{np.nanmax(vals):.2e}','MaxGap':f'{np.nanmax(gaps):.2e}','BaseRoutes':int(c.edges.sum()),'BaseValue':f'{c.value_billion_usd.sum():.2f}','BaseQuantity':f'{c.quantity_mt.sum():.2f}'}
 (PAPER/'numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in macros.items()))
 print(macros)
if __name__=='__main__':main()
