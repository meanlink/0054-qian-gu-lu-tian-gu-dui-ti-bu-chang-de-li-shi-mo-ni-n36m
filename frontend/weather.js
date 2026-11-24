import {h} from './base.js'
import {heading,feedback,table,choices} from './view.js'
import {wire,canEdit} from './forms.js'
import {blocks,record} from './weather_store.js'
import {halfTime} from './summer_clock.js'
export async function render(root,session) {
 const rows=await blocks()
 const days=Map.groupBy(rows,r=>r.on_day)
 root.innerHTML=heading('历史气象窗','往日试验输入保留半小时时点与抄录文件。回放需要紧邻排练时段的两个真实窗。')+`
 <div class="weather-evidence"><section>${Array.from(days,([day,window],i)=>`<details ${i<2?'open':''}><summary>${h(day)} · ${window.length} 个读数</summary>
 ${table(['时点','气温 ℃','湿度 %','来源'],window.map(r=>[halfTime(r.half_from),r.temp_c,r.humidity,r.source]))}</details>`).join('')}</section>
 ${canEdit(session)?`<form class="panel compact-form"><h2>订正归档气象</h2><label>计量日<input type="date" name="on_day" value="2026-08-13" required></label>
 <label>半小时窗<select name="half_from">${choices(Array.from({length:48},(_,i)=>i),halfTime,x=>x)}</select></label>
 <label>气温 ℃<input name="temp_c" type="number" min="-15" max="55" step=".1" required></label><label>湿度 %<input name="humidity" type="number" min="0" max="100" required></label>
 <label>文件来源<input name="source" required minlength="4"></label><button>保留历史读数</button>${feedback}</form>`:''}</div>`
 wire(root.querySelector('form'),record,()=>render(root,session))
}
