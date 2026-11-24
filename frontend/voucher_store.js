import {api} from './base.js'
export const tickets=()=>api('/api/vouchers')
export const issue=({code,from_block,to_block,memo})=>api('/api/vouchers/'+encodeURIComponent(code),'POST',{from_block:Number(from_block),to_block:Number(to_block),memo})
export const settle=({code,paid_cents})=>api('/api/vouchers/'+encodeURIComponent(code)+'/settle','POST',{paid_cents:Number(paid_cents)})
