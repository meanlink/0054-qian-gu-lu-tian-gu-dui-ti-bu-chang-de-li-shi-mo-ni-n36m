import {h,empty} from './base.js'
import {heading,choices,feedback} from './view.js'
import {wire,canEdit} from './forms.js'
import {venues} from './venue_store.js'
import {replays,simulate} from './replay_store.js'
import {bands} from './heat_bands.js'
export async function render(root,session){
 const [list,board]=await Promise.all([replays(),venues()])
 root.innerHTML=heading('替场回放','以演前两段气温与湿度匹配过去日期，再回放各半小时的相似日分位。')+`
 <div class="replay-board">${canEdit(session)?`<form class="panel compact-form"><h2>选择历史演次</h2><label>预留单<select name="hold">${choices(board.holds.filter(x=>x.state==='held'),x=>x.title)}</select></label>
 <label>相似日期数<input name="neighbors" type="number" value="3" min="2" max="10" required></label>
 <label>分位数<input name="percentile" type="number" value=".8" min=".5" max=".99" step=".01" required></label><button>重放下半场</button>${feedback}</form>`:''}
 <section>${list.map(r=>`<article><h2>${h(r.code)} · ${r.percentile}</h2>${bands(r.replay_window)}
 <p>相似日期 ${h(r.backtest.analogs.join('、'))}</p><p>留后 MAE ${r.backtest.mae??'样本不足'} · ${r.backtest.comparison_blocks} 个回测窗</p></article>`).join('')||empty('尚无历史回放，先录入相似日期和完整演前窗。')}</section></div>`
 wire(root.querySelector('form'),simulate,()=>render(root,session))
}
