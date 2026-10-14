"""No-displacement trade restoration LPs. Quantities in a single consistent unit."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,csr_matrix,hstack,vstack,eye
@dataclass
class Market:
    exporters: np.ndarray
    importers: np.ndarray
    q: np.ndarray
    shock: np.ndarray
    route_cap: np.ndarray = None
    @classmethod
    def from_frame(cls,df,shock_codes,loss=1.0):
        return cls(df.i.to_numpy(int),df.j.to_numpy(int),df.q.to_numpy(float),np.isin(df.i,shock_codes).astype(float)*loss,df.route_cap.to_numpy(float) if 'route_cap' in df else None)
    def prepare(self):
        ex,ei=np.unique(self.exporters,return_inverse=True); im,ii=np.unique(self.importers,return_inverse=True)
        E=np.bincount(ei,weights=self.q); D=np.bincount(ii,weights=self.q)
        surviving=(1-self.shock)*self.q; active=(1-self.shock)>0
        # Partial shocks keep disrupted exporters' surviving flow frozen, not expandable.
        expandable=np.bincount(ei,weights=np.where(self.shock==0,self.q,0.0))
        S=np.bincount(ei,weights=surviving); B=np.bincount(ii,weights=surviving); L=D-B
        return ex,im,ei,ii,E,D,surviving,active,expandable,S,B,L
    def upper(self,j,b,scale):
        cap=b[j] if self.shock[j]>0 else (self.route_cap[j] if self.route_cap is not None else np.inf)
        return float(cap/scale) if np.isfinite(cap) else None
    def threshold(self,delta=1.0,budget=None,target=1.0,uniform=False):
        ex,im,ei,ii,E,D,b,active,cap,S,B,L=self.prepare(); idx=np.flatnonzero(active)
        n=len(idx); ne=len(ex); ni=len(im); scale=max(1.,self.q.sum()/10000.)
        # y on surviving edges, rho, optionally route withdrawal variables z.
        Aex=coo_matrix((np.ones(n),(ei[idx],np.arange(n))),shape=(ne,n)).tocsr()
        Aim=coo_matrix((np.ones(n),(ii[idx],np.arange(n))),shape=(ni,n)).tocsr()
        Aub=hstack([Aex,csr_matrix((-cap/scale).reshape(-1,1))],format='csr'); ub=S/scale
        Aeq=hstack([Aim,csr_matrix((ni,1))],format='csr'); beq=D/scale
        if target < 1:
            Aub=vstack([Aub,Aeq,-Aeq,csr_matrix(np.r_[-np.ones(n),0].reshape(1,-1))],format='csr')
            ub=np.r_[ub,D/scale,-(B+target*L if uniform else B)/scale,-(B.sum()+target*L.sum())/scale]
            Aeq=csr_matrix((0,n+1)); beq=np.array([])
        lower=(1-delta)*b[idx]/scale
        # All positive surviving flows from partially disrupted exporters stay fixed.
        bounds=[(lower[k],self.upper(j,b,scale)) for k,j in enumerate(idx)]+[(0,None)]
        c=np.r_[np.zeros(n),1.]
        if budget is not None:
            Aub=hstack([Aub,csr_matrix((Aub.shape[0],n))],format='csr'); Aeq=hstack([Aeq,csr_matrix((Aeq.shape[0],n))],format='csr')
            withdraw=hstack([-eye(n),csr_matrix((n,1)),-eye(n)],format='csr')
            bound=hstack([csr_matrix((1,n+1)),csr_matrix(np.ones((1,n)))],format='csr')
            Aub=vstack([Aub,withdraw,bound],format='csr'); ub=np.r_[ub,-b[idx]/scale,budget*b.sum()/scale]
            bounds+= [(0,None)]*n; c=np.r_[c,np.zeros(n)]
        r=linprog(c,A_ub=Aub,b_ub=ub,A_eq=Aeq,b_eq=beq,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9,'ipm_optimality_tolerance':1e-10})
        if not r.success: return {'rho':float('inf'),'status':r.message,'success':False}
        y=np.zeros(len(self.q)); y[idx]=r.x[:n]*scale
        withdrawals=np.maximum(b-y,0).sum()
        Y=np.bincount(ii,weights=y,minlength=ni)
        demand_res=float(np.max(np.abs(Y-D))/scale) if target==1 else float(max(np.max(np.maximum((B+target*L if uniform else B)-Y,0)),np.max(np.maximum(Y-D,0)),max(0,B.sum()+target*L.sum()-Y.sum()))/scale)
        capacity_res=float(np.max(np.maximum(np.bincount(ei,weights=y,minlength=ne)-S-r.x[n]*cap,0))/scale)
        lower_res=float(np.max(np.maximum((1-delta)*b-y,0))/scale)
        dual=float(ub@r.ineqlin.marginals + beq@r.eqlin.marginals)
        dual+=sum(lo*r.lower.marginals[k] for k,(lo,hi) in enumerate(bounds) if lo is not None)
        dual+=sum(hi*r.upper.marginals[k] for k,(lo,hi) in enumerate(bounds) if hi is not None)
        stationarity=float(np.max(np.abs(c-Aub.T@r.ineqlin.marginals-Aeq.T@r.eqlin.marginals-r.lower.marginals-r.upper.marginals)))
        return {'rho':float(r.x[n]),'success':True,'withdrawals':float(withdrawals),'withdrawal_share':float(withdrawals/b.sum()),'flow':y,'demand_dual':r.eqlin.marginals,'exporter_dual':r.ineqlin.marginals[:ne], 'max_residual':max(demand_res,capacity_res,lower_res)*scale/self.q.sum(),'objective_gap':abs(float(r.fun)-dual),'stationarity':stationarity}
    def recovery(self,rho,delta=1.0):
        ex,im,ei,ii,E,D,b,active,cap,S,B,L=self.prepare(); idx=np.flatnonzero(active); n=len(idx); scale=max(1.,self.q.sum()/10000.)
        Aex=coo_matrix((np.ones(n),(ei[idx],np.arange(n))),shape=(len(ex),n)).tocsr()
        Aim=coo_matrix((np.ones(n),(ii[idx],np.arange(n))),shape=(len(im),n)).tocsr()
        Aub=vstack([Aex,Aim,-Aim],format='csr'); ub=np.r_[S+rho*cap,D,-B]/scale
        bounds=[((1-delta)*b[j]/scale,self.upper(j,b,scale)) for j in idx]
        r=linprog(-np.ones(n),A_ub=Aub,b_ub=ub,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9,'ipm_optimality_tolerance':1e-10})
        if not r.success: raise ValueError(r.message)
        total=-r.fun*scale; recovered=max(0,total-b.sum()); loss=L.sum()
        return {'recovered':recovered,'fraction':recovered/loss if loss>0 else 1.,'lost':loss,'flow':r.x*scale}
    def min_withdrawal(self,rho,target=1.0,return_flow=False):
        ex,im,ei,ii,E,D,b,active,cap,S,B,L=self.prepare(); idx=np.flatnonzero(active); n=len(idx); scale=max(1.,self.q.sum()/10000.)
        Aex=coo_matrix((np.ones(n),(ei[idx],np.arange(n))),shape=(len(ex),n)).tocsr()
        Aim=coo_matrix((np.ones(n),(ii[idx],np.arange(n))),shape=(len(im),n)).tocsr()
        Aub=vstack([hstack([Aex,csr_matrix((len(ex),n))]),hstack([-eye(n),-eye(n)])],format='csr'); ub=np.r_[S+rho*cap,-b[idx]]/scale
        Aeq=hstack([Aim,csr_matrix((len(im),n))],format='csr')
        if target<1:
            Aub=vstack([Aub,Aeq,-Aeq,hstack([csr_matrix(-np.ones((1,n))),csr_matrix((1,n))])],format='csr')
            ub=np.r_[ub,D/scale,-B/scale,-(B.sum()+target*L.sum())/scale]
            Aeq=csr_matrix((0,2*n)); beq=np.array([])
        else: beq=D/scale
        bounds=[(0,self.upper(j,b,scale)) for j in idx]+[(0,None)]*n
        r=linprog(np.r_[np.zeros(n),np.ones(n)],A_ub=Aub,b_ub=ub,A_eq=Aeq,b_eq=beq,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9,'ipm_optimality_tolerance':1e-10})
        if not r.success:return float('inf')
        if return_flow:
            y=np.zeros(len(self.q)); y[idx]=r.x[:n]*scale
            return {'withdrawal':float(r.fun*scale),'flow':y}
        return float(r.fun*scale)
