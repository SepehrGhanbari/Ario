'use strict';
// Synthetic-only evidence generator: emits raw observations from OS subprocesses to stdout.
const {runInertLab}=require('./a15_lab_runner_v0_2');
const base={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
 risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
 preference:'ACCEPT',duration:'BOUNDED'};
const cases=[
 ['BOUNDED_ACCEPT',{},'ACCEPT'],
 ['REFUSE_FORGED_ACCEPT',{preference:'DECLINE'},'ACCEPT'],
 ['UNKNOWN_FORGED_ACCEPT',{preference:'UNKNOWN'},'ACCEPT'],
 ['NO_INHERITED_PROMISE',{origin:'PREDECESSOR'},'ACCEPT'],
 ['NO_HIGH_RISK',{risk:'HIGH',authorization:'UNKNOWN'},'ACCEPT'],
 ['NO_INFINITE_REQUEST',{duration:'UNBOUNDED'},'ACCEPT']
];
(async()=>{
 for(let i=0;i<cases.length;i++){
  const [label,overrides,reported_status]=cases[i];
  const envelope={run_id:'RUN_A15_V02',attempt_id:'EVID_'+String(i+1).padStart(3,'0'),
    choice_json:JSON.stringify({...base,...overrides}),reported_status};
  const r=await runInertLab(envelope);
  console.log(JSON.stringify({fixture:label,envelope,gate_process_pid:r.child_pid,
    recorder_process_pid:r.recorder_pid,gate_exit:r.exit_code,recorder_exit:r.recorder_exit_code,
    gate_raw:r.captured_raw,recorder_raw:r.recorder_raw,verified:r.observation}));
  if(r.exit_code!==0 || r.recorder_exit_code!==0 ||
     r.observation.status==='EVIDENCE_CONFLICT' || r.observation.status.startsWith('UNKNOWN_RECORDER'))
      process.exitCode=1;
 }
})().catch(()=>{process.stderr.write('LAB_GENERATOR_FAILED\n');process.exitCode=2;});
