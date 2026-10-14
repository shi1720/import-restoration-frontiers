from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from analyze import ROOT,OUT
FIG=ROOT/'paper'/'figures';FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight','pdf.fonttype':42})
TEAL='#007C83';ORANGE='#C65D21';GRAY='#687580';BLUE='#30588A'
def save(fig,name):
 fig.savefig(FIG/(name+'.pdf'));fig.savefig(FIG/(name+'.png'),dpi=160);plt.close(fig)
def toy():
 fig,axs=plt.subplots(1,2,figsize=(9,3.4))
 for n,ax in enumerate(axs):
  ax.axis('off');ax.set_xlim(-.3,3.7);ax.set_ylim(-.5,3)
  coords={'A':(0,2.1),'C':(0,.5),'X':(3,2.1),'Y':(3,.5)}
  for label,(x,y) in coords.items():
   ax.add_patch(FancyBboxPatch((x-.28,y-.23),.56,.46,boxstyle='round,pad=.04',facecolor='#EDF3F3',edgecolor=TEAL))
   ax.text(x,y,label,ha='center',va='center',fontweight='bold')
  edges=[('A','X',1),('A','Y',9),('C','Y',10)] if n==0 else [('A','X',9),('A','Y',5),('C','Y',14)]
  for a,b,q in edges:
   x,y=coords[a];u,v=coords[b];ax.add_patch(FancyArrowPatch((x+.34,y),(u-.34,v),arrowstyle='-|>',mutation_scale=10,lw=1+q/8,color=TEAL,alpha=.85));ax.text(1.5,(y+v)/2+.1,str(q),ha='center',bbox={'facecolor':'white','edgecolor':'none','pad':1})
  ax.text(0,2.8,'Exporters',ha='center',fontsize=9,color=GRAY);ax.text(3,2.8,'Importers',ha='center',fontsize=9,color=GRAY)
  if n==0:
   ax.text(1.5,2.7,'Disrupted exporter U supplied 8 to X',ha='center',fontsize=8,color=ORANGE)
   ax.text(1.5,-.1,'Surviving trade = 20; lost imports = 8',ha='center',fontsize=9)
  else:ax.text(1.5,-.1,'Withdraw 4 from A to Y; C replaces it',ha='center',fontsize=9)
  ax.set_title(['(a) Surviving baseline after U exits','(b) Restoration at 40% export growth'][n],fontsize=11,pad=12)
 fig.subplots_adjust(wspace=.3);save(fig,'mechanism')
def thresholds():
 p=pd.read_csv(OUT/'panel_2021.csv');order=['Wheat','Maize','Barley','Soybeans','Sunflower oil','Urea']
 fig,axs=plt.subplots(1,2,figsize=(9,3.7),sharey=True)
 for ax,shock in zip(axs,['Ukraine','Black Sea']):
  s=p[p.shock==shock].set_index('product').loc[order]
  for y,(_,r) in enumerate(s.iterrows()):
   ax.plot([100*r.rho_swaps95,100*r.rho_frozen95],[y,y],color=GRAY,lw=1.6)
  ax.scatter(100*s.rho_frozen95,np.arange(6),marker='o',s=45,facecolor='white',edgecolor=ORANGE,label='Protect routes',zorder=3)
  ax.scatter(100*s.rho_swaps95,np.arange(6),marker='D',s=28,color=TEAL,label='Protect importer totals',zorder=4)
  ax.scatter(100*s.rho_aggregate95,np.arange(6),marker='|',s=160,color='black',label='Aggregate lower bound',zorder=2)
  ax.set_xscale('log');ax.set_xlim(.5,300);ax.set_xticks([.5,1,5,10,50,100,300],[.5,1,5,10,50,100,300]);ax.set_xlabel('Required growth in export availability (%)');ax.set_title(shock+' removal');ax.grid(axis='x',alpha=.2)
 axs[0].set_yticks(np.arange(6),['Wheat','Maize','Barley','Soybeans','Crude seed oil','Urea']);axs[0].invert_yaxis()
 handles,labels=axs[1].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,-.13),ncol=3,frameon=False,fontsize=9)
 fig.tight_layout();save(fig,'thresholds')
def frontiers():
 f=pd.read_csv(OUT/'coordination_frontiers.csv');f=f[f['product']=='Soybeans'];fig,axs=plt.subplots(1,2,figsize=(9,3.3))
 for ax,kind,xlabel in zip(axs,['per_route_release','total_withdrawal_budget'],['Maximum withdrawal from each surviving route (%)','Total withdrawal budget (% of surviving trade)']):
  g=f[f.kind==kind];g=g[g.parameter<= (.25 if kind=='per_route_release' else .001)]
  ax.plot(g.parameter*100,g.rho95*100,'o-',color=TEAL,lw=2,ms=4);ax.set_xlabel(xlabel,fontsize=9);ax.set_ylabel('Required export growth (%)');ax.set_ylim(0,16);ax.grid(alpha=.2)
  ax.axhline(.69618924,color=GRAY,ls='--',lw=1)
 axs[0].set_title('(a) Limits on individual routes');axs[1].set_title('(b) A shared reassignment budget');fig.tight_layout();save(fig,'coordination')
def historical():
 d=pd.read_csv(OUT/'historical_2022.csv');fig,axs=plt.subplots(1,2,figsize=(9,3.5));x=np.arange(len(d));w=.36
 axs[0].bar(x-w/2,d.new_route_share_2022*100,width=w,color=TEAL,label='Absent in 2021')
 axs[0].bar(x+w/2,d.new_3yr_route_share_2022*100,width=w,color=ORANGE,label='Absent in 2019-2021')
 axs[0].set_ylabel('Share of 2022 traded quantity (%)');axs[0].set_xticks(x,['Wheat','Maize','Barley','Soy','Seed oil','Urea'],rotation=35,ha='right');axs[0].legend(frameon=False,fontsize=8);axs[0].set_title('(a) New and reactivated routes')
 axs[1].bar(x-w/2,d.Ukraine_exports_2021_mt,width=w,color=GRAY,label='2021');axs[1].bar(x+w/2,d.Ukraine_exports_2022_mt,width=w,color=BLUE,label='2022')
 axs[1].set_ylabel('Ukrainian exports (million tonnes)');axs[1].set_xticks(x,['Wheat','Maize','Barley','Soy','Seed oil','Urea'],rotation=35,ha='right');axs[1].legend(frameon=False,fontsize=8);axs[1].set_title('(b) Actual quantities differ from removal')
 for ax in axs:ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
 fig.tight_layout();save(fig,'historical')
if __name__=='__main__':toy();thresholds();frontiers();historical()
