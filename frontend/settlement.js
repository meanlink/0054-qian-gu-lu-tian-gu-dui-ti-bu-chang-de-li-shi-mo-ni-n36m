import {h,badge} from './base.js'
import {heading,feedback,table} from './view.js'
import {wire} from './forms.js'
import {venues} from './venue_store.js'
import {replays} from './replay_store.js'
import {tickets,issue,settle} from './voucher_store.js'
import {halfTime,cents} from './summer_clock.js'
import {rangeLabel} from './hold_ruler.js'

function basisPanel(record) {
 const basis=record.weather_basis||record.weather_snapshot||record.weather_evidence||record.basis
 if(!basis) return '<p class="basis-missing">旧票未附带结构化气象快照；场租仍按本票金额结算。</p>'
 const blocks=basis.weather_blocks||[]
 const params=basis.parameters||{}
 const analogs=basis.analogs||basis.backtest?.analogs||[]
 return `<details class="weather-basis"><summary>出票时气象依据</summary>
   <p>原参数：${h(params.neighbors ?? '—')} 个相似日 · P${h(params.percentile ?? '—')}；相似日 ${h((analogs||[]).join('、')||'—')}</p>
   <p>留后 MAE：${h(basis.backtest?.mae ?? '样本不足')}；快照含 ${blocks.length} 条气象读数。后续订正不改变本依据。</p>
   ${table(['时点','气温 ℃','湿度 %','来源'],blocks.filter?blocks.filter(r=>r.half_from>=28&&r.half_from<=33).map(r=>[`${r.on_day} ${halfTime(r.half_from)}`,r.temp_c,r.humidity,r.source]):[])}
 </details>`
}

export async function render(root,session){
 const [board,list,records]=await Promise.all([venues(),replays(),tickets()])
 const authorized=session.role==='reviewer'
 const ready=board.holds.filter(r=>r.state==='held'&&list.some(x=>x.code===r.code))
 const open=ready.filter(r=>!r.ticketing_paused)
 const paused=ready.filter(r=>r.ticketing_paused)
 root.innerHTML=heading('票据与场租','调整票按回放替场窗半小时计费。签发、结算后均保留历史案件锁档；出票时冻结气象依据，晚到订正只重算未出票演次，场租照原票结算。')+`
 <div class="rental-ledger"><section><h2>具备回放的预留</h2>
 ${paused.map(r=>`<article class="panel paused-ticket"><h3>${h(r.title)}</h3>
   <p class="pause-note">相关气象订正批次正在排队/重算，工作台仍显示旧版；本预留暂停出票。</p>
   <button type="button" disabled aria-disabled="true">订正期间暂停出票</button></article>`).join('')}
 ${open.map(r=>{
   const replay=list.find(x=>x.code===r.code)
   const backupBlocks=(replay.replay_window||[]).filter(b=>b.backup)
   return `<article class="panel"><h3>${h(r.title)}</h3>${authorized?`<form class="compact-form" data-issue><input name="code" type="hidden" value="${h(r.code)}">
 <div class="rental-hours"><label>起始<select name="from_block">${backupBlocks.map(x=>`<option value="${x.half}">${halfTime(x.half)}</option>`).join('')}</select></label>
 <label>截至<select name="to_block">${backupBlocks.map(x=>`<option value="${x.half+1}">${halfTime(x.half+1)}</option>`).join('')}</select></label></div>
 <label>归档说明<input name="memo" placeholder="历史替场试算" required minlength="4"></label><button>签发调整票</button>${feedback}</form>`:'<p>仅复核员可签发调整票。</p>'}</article>`
 }).join('')||(!paused.length?emptyState():'')}</section>
 <section><h2>票据留底</h2>${records.map(r=>`<article class="panel"><h3>${h(r.title)} · ${rangeLabel(r.from_block,r.to_block)}</h3><p>${h(r.moved_to)} · ${cents(r.estimate_cents)} · ${badge(r.state==='closed'?'场租已锁档':'等待复核场租',r.state)}</p><p>${h(r.memo)}</p>
 ${basisPanel(r)}
 ${r.state!=='closed'&&authorized?`<form class="compact-form" data-settle><input name="code" value="${h(r.hold)}" type="hidden"><label>实收（分）<input name="paid_cents" type="number" required value="${r.estimate_cents}"></label><button>对账并锁档</button>${feedback}</form>`:''}</article>`).join('')||emptyState('签发后在此查看票据与结算。')}</section></div>`
 for(const form of root.querySelectorAll('[data-issue]'))wire(form,issue,()=>render(root,session))
 for(const form of root.querySelectorAll('[data-settle]'))wire(form,settle,()=>render(root,session))
}

function emptyState(message='先在替场回放页生成档案。'){
 return `<p class="empty-state">${h(message)}</p>`
}
