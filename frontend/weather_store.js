import {api, waitJob} from './base.js'

export const blocks = () => api('/api/weather')
export const correctionBatches = () => api('/api/weather/corrections')
export const retryCorrection = id => api(`/api/weather/corrections/${encodeURIComponent(id)}/retry`, 'POST')
export async function retryAndWait(id) {
  const receipt = await retryCorrection(id)
  if (receipt?.job_id && ['queued', 'running'].includes(receipt.status)) {
    await waitJob(receipt.job_id)
  }
  return receipt
}

export async function record(data) {
  const receipt = await api('/api/weather', 'POST', {
    ...data,
    half_from: Number(data.half_from),
    temp_c: Number(data.temp_c),
    humidity: Number(data.humidity),
  })
  if (receipt?.job_id) {
    try {
      const result = await waitJob(receipt.job_id)
      return {...receipt, ...(result && typeof result === 'object' ? result : {}),
        message: '整批订正已重算并一次性切换；旧票气象依据与场租不变。'}
    } catch (error) {
      error.receipt = receipt
      throw error
    }
  }
  return receipt
}
