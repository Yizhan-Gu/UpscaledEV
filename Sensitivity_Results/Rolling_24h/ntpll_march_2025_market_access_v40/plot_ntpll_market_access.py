"""Paper figures from a certified matched NTPLL March run, no re-optimization."""
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, MultipleLocator, StrMethodFormatter
import numpy as np
import pandas as pd

from ntpll_market_access import AS, CASES, DT, FORECAST


def load_case(root, c):
    folder = root / "march" / c
    mode = "retail_only" if c == "retail" else "full"
    assert json.loads((folder/"PASS.json").read_text())["status"]=="PASS"
    key = f"2025_{FORECAST}_{mode}"
    read = lambda p: pd.read_csv(p,parse_dates=["Interval start"]).set_index("Interval start")
    traces = pd.concat([read(p) for p in sorted((folder/"Validation_Traces"/key).glob("*.csv"))])
    wm = pd.concat([read(p) for p in sorted((folder/"Plots/Solver_RT_Choices"/key).glob(f"*/RT_WM_profit_breakdown_{mode}.csv"))])
    accounts = read(folder/"interval_accounts.csv")
    assert traces.index.equals(accounts.index) and traces.index.equals(wm.index) and len(traces)==31*96
    diag = folder/"Diagnostics"/f"{FORECAST}_{mode}"
    ref = [json.loads(line) for line in (diag/"peak_reference.jsonl").read_text().splitlines()]
    rt = [line for line in ref if line["stage"]=="RT"]
    assert pd.DatetimeIndex([line["start"] for line in rt]).equals(traces.index)
    assert [line["horizon_intervals"] for line in rt]==[96]*(30*96)+list(range(96,0,-1))
    audit = pd.concat([read(p) for p in sorted((folder/"Plots/Solver_RT_Choices"/key).glob("*/RT_market_interval_audit_with_prices.csv"))])
    for prod, v in audit.groupby("Product",sort=False):
        assert v.index.equals(traces.index)
        dai, rti = v["DA quantity (kW)"],v["RT signed adjustment (kW)"]
        if prod == "Energy":
            np.testing.assert_allclose(dai,traces.p_DA_kW,atol=1e-6,rtol=0)
            np.testing.assert_allclose(rti,traces.p_RT_deviation_kW,atol=1e-6,rtol=0)
            reconstructed = (dai*v["DA LMP ($/kWh)"]+rti*v["RT LMP ($/kWh)"])*DT
        else:
            assert prod in AS
            np.testing.assert_allclose(dai+rti,traces[f"c_{prod}_actual_kW"],atol=1e-6,rtol=0)
            active = (-1 if prod=="RD" else 1)*v.Alpha*(dai+rti)
            reconstructed = DT*(dai*v["DA AS capacity price ($/kWh)"] +
                                  rti*v["RT AS capacity price ($/kWh)"] + active*v["RT LMP ($/kWh)"])
        np.testing.assert_allclose(reconstructed,v["Total product revenue ($)"],atol=5e-6,rtol=0)
    np.testing.assert_allclose(audit.groupby(level=0)["Total product revenue ($)"].sum(),
                               accounts["WM Revenue"],atol=2e-5,rtol=0)
    return traces.join(accounts), wm


def draw_access(d, totals, output):
    ink, blue, teal, orange, purple, gray, grid = "#253746","#0072B2","#009E73","#D55E00","#A34D84","#647582","#DFE4EA"
    colors={"retail":gray,"energy":blue,"energy_as":teal}
    labels={"retail":"Retail only","energy":"Retail + energy","energy_as":"Retail + energy + AS"}
    components = ["scheduled_WM_energy","AS_deployment","AS_capacity","TOU Cost","PD Cost","NCD Cost"]
    amounts_by_case = totals[components+["Total Revenue"]]
    delta = amounts_by_case.subtract(amounts_by_case.loc["retail"])
    accounts = ["DA+RT\nenergy", "AS deploy.\nenergy", "AS\ncapacity", "TOU\nchange", "PD\nchange", "NCD\nchange", "Net\ngain"]
    fig = plt.figure(figsize=(7.4,5.35))
    gs = fig.add_gridspec(2,2,height_ratios=(1.16,1),left=.101,right=.977,
                          top=.891,bottom=.101,hspace=.60,wspace=.26)
    a=fig.add_subplot(gs[0,0])
    aa=fig.add_subplot(gs[0,1],sharey=a)
    b=fig.add_subplot(gs[1,0])
    c=fig.add_subplot(gs[1,1],sharex=b)
    for ax in (a,aa,b,c):
        ax.set_axisbelow(True)
        ax.grid(axis="y",color=grid,lw=.55)
        ax.spines[["right","top"]].set_visible(False)
        ax.tick_params(axis="both",length=2.6,pad=2,width=.65)
    paths=[]
    for case in ["energy","energy_as"]:
        paths.extend(np.r_[0.,np.cumsum(delta.loc[case,components].to_numpy())/1000])
    wmax, wmin=max(paths),min(paths)
    pad=max((wmax-wmin)*.13,.09)
    for ax,k in zip([a,aa],["energy","energy_as"]):
        amounts=delta.loc[k,components].to_numpy()/1000
        endpoints=np.r_[0,np.cumsum(amounts)]
        close=delta.loc[k,"Total Revenue"]/1000
        np.testing.assert_allclose(endpoints[-1],close,atol=1e-7)
        ax.axhline(0,color=gray,lw=.55)
        for i,x in enumerate(amounts):
            ax.bar(i,x,bottom=endpoints[i],width=.68,color=teal if x>=0 else orange,zorder=3)
            ax.hlines(endpoints[i+1],i+.34,i+.66,color=gray,lw=.62)
            offset=pad*.16
            if abs(x)>.095:
                ax.annotate(f"{x:+.2f}",(i,max(endpoints[i:i+2])+offset),
                            ha="center",va="bottom",fontsize=6.7,color=ink)
        ax.bar(6,close,width=.68,color=colors[k],zorder=3)
        ax.annotate(f"{close:+.2f}",(6,max(0.,close)+pad*.19),ha="center",va="bottom",
                    fontweight="bold",color=colors[k],fontsize=7.2)
        ax.set_ylim(wmin-pad*.48,wmax+pad)
        ax.set_xticks(np.arange(7),accounts,fontsize=6.25)
        ax.tick_params(axis="x",length=0,pad=4)
        ax.set_xlim(-.54,6.57)
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.set_title(labels[k],color=colors[k],fontweight="bold",loc="left",fontsize=8.1,pad=4)
    aa.tick_params(labelleft=False)
    a.set_ylabel("Change vs. retail only (kUSD)")
    a.text(0,1.24,"(a) Monthly net value by account",transform=a.transAxes,
           fontsize=10.1,fontweight="bold",va="top")
    days=d["retail"].resample("D").size().index.day.to_numpy()
    b.axhline(0,color=gray,lw=.6)
    for k in ("energy","energy_as"):
        dd=(d[k]["Total Revenue"]-d["retail"]["Total Revenue"]).resample("D").sum().cumsum()/1000
        b.plot(days,dd,color=colors[k],lw=1.35,label=labels[k])
        b.scatter(days[-1],dd.iloc[-1],s=12,color=colors[k],zorder=3)
    for k,ls in zip(("retail","energy","energy_as"),("--","-","-.")):
        pp=d[k].NCD_peak_kW.resample("D").last()
        c.step(days,pp,color=colors[k],ls=ls,lw=1.18,where="post",label=labels[k])
        c.scatter(days[-1],pp.iloc[-1],s=11,color=colors[k],zorder=3)
    b.set(ylabel="Gain vs. retail only (kUSD)")
    c.set(ylabel="Carried NCD peak (kW)")
    b.set_title("(b) Cumulative net gain",loc="left",fontsize=9.8,pad=7)
    c.set_title("(c) Formation of the billed peak",loc="left",fontsize=9.8,pad=7)
    for ax in [b,c]:
        ax.set(xlabel="Day in March",xlim=(.9,max(2,days[-1]+.65)),xticks=[i for i in [1,5,10,15,20,25,31] if i<=days[-1]])
        ax.yaxis.set_major_locator(MaxNLocator(5))
    c.legend(loc="best",frameon=True,facecolor="white",edgecolor="none",
             fontsize=7.1,handlelength=1.65)
    fig.savefig(output,dpi=300)
    plt.close(fig)


def draw_retail(frame, day, output):
    from matplotlib.patches import Patch
    date=pd.Timestamp(day)
    raw=frame.loc[date:date+pd.Timedelta(hours=23.75)]
    assert len(raw)==96
    traces=raw
    load, pv, gi, ev, bess, soc, tou, evmax = (traces[col].to_numpy() for col in ("p_load_kW", "p_PV_kW", "p_GI_kW", "p_EV_kW", "p_BESS_kW", "SOC", "TOU_$/kWh", "P_EV_max_kW"))
    prev=frame.loc[frame.index<date].iloc[-1] if date.day>1 else None
    peak=raw[["PD_peak_kW","NCD_peak_kW"]].to_numpy()
    peak_state=np.vstack([np.zeros((1,2)) if prev is None else prev[["PD_peak_kW","NCD_peak_kW"]].to_numpy(),peak])
    init_soc=.5 if prev is None else prev.SOC
    net=load-pv
    hour=np.arange(96)*DT
    edges=np.arange(97)*DT
    tc,pc,nc=np.cumsum(np.vstack([np.zeros(3),-raw[["TOU Cost","PD Cost","NCD Cost"]].to_numpy()]),axis=0).T
    bill=tc+pc+nc
    j=int(np.argmax(gi))
    ink, blue, teal, orange, purple, gold, gray, grid = ("#253746", "#0072B2", "#009E73", "#D55E00", "#A34D84", "#9E6C00", "#647582", "#DCE2E7")
    fig, axes = plt.subplots(3,2,figsize=(7.3,4.5),sharex=True)
    fig.subplots_adjust(left=.094,right=.928,bottom=.106,top=.900,wspace=.27,hspace=.51)
    a,b,c,d,e,f=axes.flat
    for ax,title,unit in zip(axes.flat,("(a) Retail energy rate","(b) Passive site profiles",
        "(c) EV charging","(d) BESS dispatch and state","(e) Meter and carried peaks","(f) Accrued retail costs"),
        ("USD/kWh","kW","kW","kW","kW","USD")):
        ax.set_title(title,loc="left",pad=14)
        ax.set_xlim(0,24)
        ax.xaxis.set_major_locator(MultipleLocator(4))
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:02.0f}:00"))
        ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.set_ylabel(unit,labelpad=3)
        ax.set_axisbelow(True)
        ax.grid(axis="y",color=grid,linewidth=.50)
        ax.tick_params(axis="both",length=2.5,pad=2.2,width=.65)
        ax.tick_params(axis="x",labelbottom=ax in (e,f))
        ax.spines[["right","top"]].set_visible(False)
    def step(ax,y,label,color,ls="-",lw=.85):
        return ax.stairs(y,edges,label=label,color=color,linewidth=lw,linestyle=ls,baseline=None)
    def key(ax,n,handles=None):
        kw=dict(loc="lower left",bbox_to_anchor=(0,1.03),ncol=n,handlelength=1.55,
                handletextpad=.37,columnspacing=.85,borderpad=0,borderaxespad=0,frameon=False)
        ax.legend(**kw) if handles is None else ax.legend(handles=handles,**kw)
    a.axvspan(16,21,color=gold,alpha=.13,lw=0,label="On-peak window")
    step(a,tou,"TOU",blue)
    a.set_ylim(tou.min()-.014,tou.max()+.012)
    a.yaxis.set_major_formatter(StrMethodFormatter("{x:.2f}"))
    key(a,2,a.get_legend_handles_labels()[0][::-1])
    step(b,load,"Building",gray,"--")
    step(b,net,"Building + PV",blue)
    step(b,pv,"PV",teal)
    key(b,3)
    c.bar(hour+DT/2,ev,width=.193,color=blue,linewidth=0,label="Delivered")
    step(c,evmax,"Available limit",gray,"--")
    key(c,2,c.get_legend_handles_labels()[0][::-1])
    d.axhline(0,color=gray,lw=.48)
    d.bar(hour+DT/2,bess,color=np.where(bess>=0,blue,orange),linewidth=0,width=.193)
    ds=d.twinx()
    ds.spines["top"].set_visible(False)
    ds.set(ylim=(0,100),yticks=[0,25,50,75,100])
    ds.tick_params(length=2.5,width=.65,colors=purple)
    ds.set_ylabel("SOC (%)",color=purple,labelpad=2.5)
    ss,=ds.step(edges,np.r_[init_soc,soc]*100,where="post",label="SOC",color=purple,lw=.9)
    key(d,3,[Patch(color=blue,label="Charge"),Patch(color=orange,label="Discharge"),ss])
    step(e,gi,"Meter",blue)
    e.step(edges,peak_state[:,0],where="post",label="PD peak",color=purple,ls="--",lw=.82)
    e.step(edges,peak_state[:,1],where="post",label="NCD peak",color=orange,ls=":",lw=1.10)
    e.scatter(hour[j]+DT/2,gi[j],s=9,color=blue,zorder=4)
    key(e,3)
    for v,name,color,ls,lw in zip((bill,tc,pc,nc),("Total","TOU","PD","NCD"),(ink,blue,purple,orange),
                                  ("-","--","-.",":"),(1.05,.83,.83,1.04)):
        f.step(edges,v,where="post",label=name,color=color,ls=ls,lw=lw)
    f.text(.035,.88,f"Daily PD: ${pc[-1]:.2f}  |  NCD: ${nc[-1]:.2f}",fontsize=7,
           va="top",transform=f.transAxes,color=ink)
    key(f,4)
    fig.supxlabel("Local time",fontsize=8.3,y=.016)
    fig.savefig(output,dpi=300)
    plt.close(fig)


def main(root, out):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.4,"axes.labelsize":8.2,
        "axes.titlesize":9.1,"axes.titleweight":"bold","axes.edgecolor":"#A4ADB5","axes.linewidth":.65,
        "text.color":"#253746","axes.labelcolor":"#253746","xtick.color":"#253746","ytick.color":"#253746",
        "xtick.labelsize":8.0,"ytick.labelsize":8.0,"legend.fontsize":7.1,"savefig.dpi":300})
    d={k:load_case(root,k) for k in CASES}
    traces={k:x[0] for k,x in d.items()}
    inputs=["p_load_kW","p_PV_kW","LMP_DA_$/kWh","LMP_RT_$/kWh","TOU_$/kWh"]
    for k in ("energy","energy_as"):
        pd.testing.assert_frame_equal(traces["retail"][inputs],traces[k][inputs])
    for k,(trace,wm) in d.items():
        for stage,qty in (("DA","p_DA_kW"),("RT","p_RT_deviation_kW")):
            np.testing.assert_allclose(wm[f"p_{stage}_profit"], trace[qty]*trace[f"LMP_{stage}_$/kWh"]*DT, atol=1e-6,rtol=0)
    totals=pd.read_csv(root/"march_comparison.csv").set_index("case")
    draw_access(traces,totals,out/"fig_04_ntpll_march_market_access.png")
    day="2025-03-02"
    draw_retail(traces["retail"],day,out/"fig_05_ntpll_retail_only_20250302_6panel.png")
    print(totals.to_string())
    for k, (x,wm) in d.items():
        def point(stamp):
            return {q:float(x.loc[stamp,q]) for q in ["p_GI_kW","p_load_kW","p_PV_kW","p_BESS_kW","p_EV_kW","p_DA_kW","p_RT_deviation_kW","SOC"]}
        peak=x.p_GI_kW.idxmax()
        print(k, "NCD time",str(peak),point(peak))
        print(k, "WM DA/RT energy USD",wm.p_DA_profit.sum(),wm.p_RT_profit.sum())
        print(k, "energy USD: RT-priced actual position and DA price spread",
              DT*(x.p_actual_kW*x["LMP_RT_$/kWh"]).sum(),
              DT*(x.p_DA_kW*(x["LMP_DA_$/kWh"]-x["LMP_RT_$/kWh"])).sum())
        print(k, "AS capacity USD", {p: wm.filter(regex=f"^c_{p}.*capacity$").sum().sum() for p in AS})
        print(k, "AS deployment USD", {p: wm.filter(regex=f"^c_{p}.*energy$").sum().sum() for p in AS})
        print(k, "time blocks",x.groupby(pd.cut(x.index.hour,[0,6,10,16,21,24],right=False),
                                          observed=True)[["charge_kWh","discharge_kWh"]].sum().to_dict())
        rd=x.loc[pd.Timestamp(day):pd.Timestamp(day)+pd.Timedelta(hours=23.75)]
        print(k,day,"actual peak",rd.p_GI_kW.idxmax(),point(rd.p_GI_kW.idxmax()))
        print(k,day,rd[["WM Revenue","TOU Cost","PD Cost","NCD Cost","EV kWh","charge_kWh","discharge_kWh"]].sum().to_dict(),
              "pre06 charges",rd.loc[rd.index.hour<6,"charge_kWh"].sum(),
              "midday charge",rd.loc[(rd.index.hour>=10)&(rd.index.hour<16),"charge_kWh"].sum(),
              "onpeak discharge",rd.loc[(rd.index.hour>=16)&(rd.index.hour<21),"discharge_kWh"].sum())
    for k in ("energy","energy_as"):
        de=(traces[k][["WM Revenue","TOU Cost","PD Cost","NCD Cost","Total Revenue"]]
            -traces["retail"][["WM Revenue","TOU Cost","PD Cost","NCD Cost","Total Revenue"]]).resample("D").sum()
        print(k,"min/max daily gain",de.loc[[de["Total Revenue"].idxmin(),de["Total Revenue"].idxmax()]].to_string(),
              "down days",len(de[de["Total Revenue"] < -1e-6]))
        print(k,"largest NCD difference day",de.loc[[de["NCD Cost"].abs().idxmax()]].to_string())
        print(k,"cumulative positive beginning",de["Total Revenue"].cumsum().loc[lambda s:s>0].head(4).to_dict())
    inc=traces["energy_as"].select_dtypes("number")-traces["energy"].select_dtypes("number")
    print("Incremental AS-over-energy:",inc.resample("D").sum()[["WM Revenue","TOU Cost","PD Cost","NCD Cost","Total Revenue"]].sum().to_dict())
    for k,x in traces.items():
        peak=x.p_GI_kW.idxmax()
        print("Market conditions at",str(peak))
        for j,y in traces.items():
            print(j, y.loc[peak,["TOU_$/kWh","LMP_DA_$/kWh","LMP_RT_$/kWh","p_GI_kW","p_EV_kW","p_BESS_kW",
                                  "p_DA_kW","p_RT_deviation_kW","NCD_peak_kW","c_RU_actual_kW","c_RD_actual_kW",
                                  "c_SP_actual_kW","c_NSP_actual_kW"]].to_dict())
    for k,x in traces.items():
        print(k, "prices/dispatch around peak",x.loc[x.p_GI_kW.idxmax(),["TOU_$/kWh","LMP_RT_$/kWh","p_BESS_kW","SOC"]].to_dict())


if __name__=="__main__":
    main(*map(Path,sys.argv[1:]))
