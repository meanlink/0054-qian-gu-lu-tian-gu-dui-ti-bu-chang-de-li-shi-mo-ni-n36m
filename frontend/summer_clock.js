export const halfTime=half=>String(Math.floor(half/2)).padStart(2,'0')+(half%2?':30':':00')
export const cents=whole=>new Intl.NumberFormat('zh-CN',{style:'currency',currency:'CNY'}).format(whole/100)
export const statuses={held:'待回放',proposed:'待结算',closed:'已锁档'}
