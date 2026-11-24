import {api,waitJob} from './base.js'
export const replays=()=>api('/api/scenarios')
export async function simulate(data){
 const {job_id}=await api('/api/scenarios','POST',{...data,neighbors:Number(data.neighbors),percentile:Number(data.percentile)})
 return waitJob(job_id)
}
