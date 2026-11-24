import {halfTime} from './summer_clock.js'
export const bands=rows=>`<ol class="heat-bands">${rows.map(w=>`<li data-move="${w.backup}"><time>${halfTime(w.half)}</time><strong>${w.value} ℃</strong><small>${w.backup?'替场窗':'原场窗'}</small></li>`).join('')}</ol>`
