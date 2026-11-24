import {mount} from './base.js'
import {render as venues} from './venues.js'
import {render as weather} from './weather.js'
import {render as scenarios} from './scenarios.js'
import {render as settlement} from './settlement.js'

const pages = {
  venues: '预留场地',
  weather: '历史气象窗',
  scenarios: '替场回放',
  settlement: '票据与场租'
}
const renderers = {venues, weather, scenarios, settlement}
mount({title: '迁鼓 · 露天鼓队替补场地历史模拟', kicker: '港堤鼓队 · 历史替场回放', pages, render: (key, root, session) => renderers[key](root, session)})
