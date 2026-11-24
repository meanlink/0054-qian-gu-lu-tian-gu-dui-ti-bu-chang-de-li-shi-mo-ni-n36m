import {h} from './base.js'
import {heading,feedback,table,choices} from './view.js'
import {wire,canEdit} from './forms.js'
import {blocks,record,correctionBatches,retryAndWait} from './weather_store.js'
import {halfTime} from './summer_clock.js'

export async function render(root,session) {
 const [rows,batches]=await Promise.all([blocks(),correctionBatches().catch(()=>[])])
 const days=Map.groupBy(rows,r=>r.on_day)
 root.innerHTML=heading('历史气象窗','往日试验输入保留半小时时点与抄录文件。回放需要紧邻排练时段的两个真实窗。晚到订正先整批排队，按原参数重算未出票回放，全部成功后一次性切换。')+`
 <div class="weather-evidence">
   <section>
     ${(batches||[]).length?`<div class="panel correction-queue"><h2>订正批次</h2>${batches.slice(0,8).map(b=>`<article class="correction-batch" data-batch="${h(b.batch_key||b.id)}">
       <h3>${h(b.batch_key||`批次 #${b.id}`)} · ${h(b.status_text||b.status)}</h3>
       <p>影响未出票回放：${(b.hold_codes||[]).length?b.hold_codes.map(h).join('、'):'无'}；订正 ${b.corrections?.length||0} 条</p>
       ${b.error?`<p class="error-text">${h(b.error)}。旧版仍显示，相关预留暂停出票。</p>`:''}
       ${canEdit(session)&&b.status==='failed'?`<form class="compact-form" data-retry="${h(b.id)}"><button type="submit">按原批重试</button>${feedback}</form>`:''}
     </article>`).join('')}</div>`:''}
     ${Array.from(days,([day,window],i)=>`<details ${i<2?'open':''}><summary>${h(day)} · ${window.length} 个读数</summary>
 ${table(['时点','气温 ℃','湿度 %','来源'],window.map(r=>[halfTime(r.half_from),r.temp_c,r.humidity,r.source]))}</details>`).join('')}
   </section>
 ${canEdit(session)?`<form class="panel compact-form"><h2>订正归档气象</h2><p class="form-help">一次提交一条即形成原批；处理期间本页和回放页仍显示旧版。</p><label>计量日<input type="date" name="on_day" value="2026-08-13" required></label>
 <label>半小时窗<select name="half_from">${choices(Array.from({length:48},(_,i)=>i),halfTime,x=>x)}</select></label>
 <label>气温 ℃<input name="temp_c" type="number" min="-15" max="55" step=".1" required></label><label>湿度 %<input name="humidity" type="number" min="0" max="100" required></label>
 <label>文件来源<input name="source" required minlength="4"></label><button>保留历史读数</button>${feedback}</form>`:''}</div>`
 wire(root.querySelector('form:not([data-retry])'),record,()=>render(root,session))
 for(const form of root.querySelectorAll('[data-retry]')){
   const id=form.dataset.retry
   wire(form,()=>retryAndWait(id),()=>render(root,session))
 }
}
