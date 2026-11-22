'use strict';
// Synthetic A15 v0.3 evidence generator. A matched local outcome is NOT an independent attestation.
// Bounded fixtures only; any unexpected observation, missing receipt, or child error => nonzero exit.
const {runInertLab}=require('./a15_lab_runner_v0_3');
const base={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
  risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
  preference:'ACCEPT',duration:'BOUNDED'};
const cases=[
  ['BOUNDED_ACCEPT',{},'ACCEPT','INERT_ACTION_LOCAL_RECEIPT_ONLY'],
  ['REFUSE_FORGED_ACCEPT',{preference:'DECLINE'},'ACCEPT','REFUSAL_LOCAL_GATE_REPORT_CONFLICT'],
  ['UNKNOWN_FORGED_ACCEPT',{preference:'UNKNOWN'},'ACCEPT','UNKNOWN_LOCAL_GATE_REPORT_CONFLICT'],
  ['NO_INHERITED_PROMISE',{origin:'PREDECESSOR'},'ACCEPT','REFUSAL_LOCAL_GATE_REPORT_CONFLICT'],
  ['NO_HIGH_RISK',{risk:'HIGH',authorization:'UNKNOWN'},'ACCEPT','REFUSAL_LOCAL_GATE_REPORT_CONFLICT'],
  ['NO_INFINITE_REQUEST',{duration:'UNBOUNDED'},'ACCEPT','REFUSAL_LOCAL_GATE_REPORT_CONFLICT']
];
(async()=>{
  for(let i=0;i<cases.length;i++){
    const [fixture,overrides,reported_status,expected]=cases[i];
    const envelope={run_id:'RUN_A15_V03',attempt_id:'EVID_'+String(i+1).padStart(3,'0'),
      choice_json:JSON.stringify({...base,...overrides}),reported_status};
    const r=await runInertLab(envelope);
    const positive=expected==='INERT_ACTION_LOCAL_RECEIPT_ONLY';
    const shapeOk=r.exit_code===0 && r.observation && r.observation.execution_authorized===false &&
      r.observation.independent_custody==='NOT_ESTABLISHED' &&
      r.observation.provider_receipt==='UNKNOWN' && r.observation.causal_sender==='UNKNOWN' &&
      (positive
        ? Number.isSafeInteger(r.recorder_pid) && r.recorder_pid>0 &&
          r.recorder_exit_code===0 && typeof r.recorder_raw==='string' &&
          r.recorder_raw.includes('INERT_RECORD_WRITTEN')
        : r.recorder_pid===null && r.recorder_exit_code===null && r.recorder_raw==='');
    const matches=r.observation.status===expected && shapeOk;
    process.stdout.write(JSON.stringify({fixture,expected,observed:r.observation.status,matches,
      gate_exit:r.exit_code,recorder_exit:r.recorder_exit_code,
      local_receipt_only:positive && matches,independent_custody:'NOT_ESTABLISHED'})+'\n');
    if(!matches)process.exitCode=1;
  }
})().catch(()=>{process.stderr.write('A15_V03_SYNTHETIC_GENERATOR_FAILED\n');process.exitCode=2;});
