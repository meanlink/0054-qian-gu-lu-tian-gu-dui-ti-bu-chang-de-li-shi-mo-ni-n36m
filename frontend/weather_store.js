import {api} from './base.js'
export const blocks=()=>api('/api/weather')
export const record=data=>api('/api/weather','POST',{...data,half_from:Number(data.half_from),temp_c:Number(data.temp_c),humidity:Number(data.humidity)})
