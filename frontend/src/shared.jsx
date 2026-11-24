import React,{useEffect,useRef} from 'react';
import {Database} from 'lucide-react';
export async function request(path,options={}) {
 const response=await fetch(path,options);
 let body; try {body=await response.json();} catch {throw new Error('The server returned an unreadable response.');}
 if(!response.ok) throw new Error(typeof body.detail==='string'?body.detail:`Request failed (${response.status}). Check the filters or server setup.`);
 return body;
}
export function Chart({data,layout={},height=280}) {
 const ref=useRef(null);
 useEffect(()=>{let active=true;let plot;
  import('plotly.js-dist-min').then(module=>{plot=module.default;if(active&&ref.current)plot.react(ref.current,data,{paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'Inter,Arial,sans-serif',size:11,color:'#6a777a'},margin:{t:18,r:16,b:45,l:48},height,xaxis:{showgrid:false,zeroline:false},yaxis:{gridcolor:'#edf0f0',zeroline:false},...layout},{responsive:true,displayModeBar:false});});
  return()=>{active=false;if(plot&&ref.current)plot.purge(ref.current);};},[data,layout,height]);
 return <div ref={ref} role="img" aria-label={layout.title?.text||'Interactive historical data chart'} style={{minHeight:height}}/>;
}
export function Metric({title,value,note,icon:Icon,tone=''}) {return <article className="metric"><div className="metric-top"><span>{title}</span><span className={'metric-icon '+tone}><Icon size={18}/></span></div><strong data-testid={title}>{value}</strong><p>{note}</p></article>;}
export function Panel({title,subtitle,children,extra}) {return <section className="panel"><div className="panel-header"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div>{extra}</div>{children}</section>;}
export function Empty({children}) {return <div className="empty"><Database size={28}/><p>{children}</p></div>;}
