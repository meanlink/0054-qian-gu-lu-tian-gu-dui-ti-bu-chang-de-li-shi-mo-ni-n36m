import {halfTime} from './summer_clock.js'
export function rangeLabel(start,end){return `${halfTime(start)}–${halfTime(end)}`}
export function span(r) {
 return `<div class="hold-ruler" role="img" aria-label="${rangeLabel(r.from_block,r.to_block)}"><span style="--start:${r.from_block/48*100}%;--width:${(r.to_block-r.from_block)/48*100}%"></span></div>`
}
