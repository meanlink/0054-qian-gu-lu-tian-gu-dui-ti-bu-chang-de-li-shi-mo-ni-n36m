import {h,badge} from './base.js'
import {heading} from './view.js'
import {venues} from './venue_store.js'
import {rangeLabel,span} from './hold_ruler.js'
import {cents,statuses} from './summer_clock.js'
export async function render(root){
 const data=await venues()
 const title=code=>data.venues.find(x=>x.code===code)?.title
 root.innerHTML=heading('预留场地','从八月排练档案按日期回看。用两处场地的人数容量和时租核对预留。')+`
 <div class="site-ledger"><section><h2>历史预留</h2>${data.holds.map(r=>`<article><h3>${h(r.title)} <small>${h(r.code)}</small></h3><p>${h(r.on_day)} · ${rangeLabel(r.from_block,r.to_block)} · ${r.heads} 人 ${badge(statuses[r.state])}${r.ticketing_paused?' '+badge('订正暂停出票','pending'):''}</p><p>${h(title(r.original))} → ${h(title(r.backup))}</p>${span(r)}</article>`).join('')}</section>
 <section class="panel"><h2>场地费用与容量</h2>${data.venues.map(v=>`<div class="venue-stock"><h3>${h(v.title)}</h3><p>${v.covered?'备选廊馆':'露天台'} · ${v.max_heads} 人 · ${cents(v.rate_per_half)}/半小时</p></div>`).join('')}</section></div>`
}
