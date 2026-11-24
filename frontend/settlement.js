import {h,empty,badge} from './base.js'
import {heading,feedback,choices} from './view.js'
import {wire} from './forms.js'
import {venues} from './venue_store.js'
import {replays} from './replay_store.js'
import {tickets,issue,settle} from './voucher_store.js'
import {halfTime,cents} from './summer_clock.js'
import {rangeLabel} from './hold_ruler.js'
export async function render(root,session){
 const [board,list,records]=await Promise.all([venues(),replays(),tickets()])
 const authorized=session.role==='reviewer'
 const open=board.holds.filter(r=>r.state==='held'&&list.some(x=>x.code===r.code))
 root.innerHTML=heading('票据与场租','调整票按回放替场窗半小时计费。签发、结算后均保留历史案件锁档。')+`
 <div class="rental-ledger"><section><h2>具备回放的预留</h2>${open.map(r=>`<article class="panel"><h3>${h(r.title)}</h3>${authorized?`<form class="compact-form" data-issue><input name="code" type="hidden" value="${h(r.code)}">
 <div class="rental-hours"><label>起始<select name="from_block">${choices(list.find(x=>x.code===r.code).replay_window.filter(b=>b.backup),x=>halfTime(x.half),x=>x.half)}</select></label>
 <label>截至<select name="to_block">${choices(list.find(x=>x.code===r.code).replay_window.filter(b=>b.backup),x=>halfTime(x.half+1),x=>x.half+1)}</select></label></div>
 <label>归档说明<input name="memo" placeholder="历史替场试算" required minlength="4"></label><button>签发调整票</button>${feedback}</form>`:''}</article>`).join('')||empty('先在替场回放页生成档案。')}</section>
 <section><h2>票据留底</h2>${records.map(r=>`<article class="panel"><h3>${h(r.title)} · ${rangeLabel(r.from_block,r.to_block)}</h3><p>${h(r.moved_to)} · ${cents(r.estimate_cents)} · ${badge(r.state==='closed'?'场租已锁档':'等待复核场租')}</p><p>${h(r.memo)}</p>
 ${r.state!=='closed'&&authorized?`<form class="compact-form" data-settle><input name="code" value="${h(r.hold)}" type="hidden"><label>实收（分）<input name="paid_cents" type="number" required value="${r.estimate_cents}"></label><button>对账并锁档</button>${feedback}</form>`:''}</article>`).join('')||empty('签发后在此查看票据与结算。')}</section></div>`
 for(const form of root.querySelectorAll('[data-issue]'))wire(form,issue,()=>render(root,session))
 for(const form of root.querySelectorAll('[data-settle]'))wire(form,settle,()=>render(root,session))
}
