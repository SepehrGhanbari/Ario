'use strict';

function w17Evaluate(bundle) {
  const official=["origin_line","log_vkey","qpd","requested_list","contact"];
  const internal=["operator_public_name","real_log_origin","origin_control_evidence","dedicated_test_log_vkey","test_key_custody_evidence","checkpoint_url","consistency_url","public_operator_contact"];
  const out={
    schema:"ARIO_W17_PUBLIC_FORM_VS_INDEPENDENT_CUSTODY_LAB_V1",
    official_log_application_fields:5,internal_r17_gate_fields:8,
    official_form_structurally_complete:false,internal_r17_evidence_structurally_complete:false,
    missing_official:[],invalid_official:[],missing_internal:[],
    programmatic_witness_enrollment:"NOT_ESTABLISHED",
    authenticated_operator_independence:"NOT_ESTABLISHED",
    trusted_out_of_band_public_key_pin:"NOT_ESTABLISHED",
    checkpoint_consistency_verified:"NOT_ESTABLISHED",
    ario_test_log_witnessed:"NOT_ESTABLISHED",
    human_consent:"NOT_ESTABLISHED",
    action_authority:"NONE",system_ready:false,
    external_network_actions:0,reason:"UNASSESSED"
  };
  const strictObj=(o,ks)=>o!==null&&typeof o==="object"&&!Array.isArray(o)&&Object.keys(o).length===ks.length&&ks.every(k=>Object.prototype.hasOwnProperty.call(o,k));
  if(!strictObj(bundle,["schema","official_log","r17_evidence","claimed_independence"])||bundle.schema!=="ARIO_W17_REVIEW_INPUT_V1"){
    out.reason="TOP_LEVEL_SCHEMA";return out;
  }
  if(!strictObj(bundle.official_log,official)||!strictObj(bundle.r17_evidence,internal)){
    out.reason="FIELD_SET_SCHEMA";return out;
  }
  for(const k of official){
    const v=bundle.official_log[k];
    if(v===null||v===undefined||v===""){out.missing_official.push(k);continue;}
    let valid=true;
    if(k==="qpd")valid=Number.isSafeInteger(v)&&v>0&&v<2147483648;
    else if(typeof v!=="string"||v.length>512||!v.trim())valid=false;
    else if(k==="requested_list")valid=["testing","staging"].includes(v);
    else if(k==="log_vkey")valid=/^[^\s+]+\+[0-9a-fA-F]{8}\+[A-Za-z0-9+/]+={0,2}$/.test(v);
    else if(k==="origin_line")valid=!/\s/.test(v);
    if(!valid)out.invalid_official.push(k);
  }
  for(const k of internal){
    const v=bundle.r17_evidence[k];
    if(typeof v!=="string"||!v.trim()||v.length>2048)out.missing_internal.push(k);
  }
  out.official_form_structurally_complete=out.missing_official.length===0&&out.invalid_official.length===0;
  out.internal_r17_evidence_structurally_complete=out.missing_internal.length===0;
  if(!out.official_form_structurally_complete)out.reason="OFFICIAL_FORM_FIELDS_MISSING_OR_INVALID";
  else if(!out.internal_r17_evidence_structurally_complete)out.reason="INTERNAL_R17_EVIDENCE_NOT_DOCUMENTED";
  else out.reason="DECLARED_PAPERWORK_PRESENT_BUT_NO_AUTHENTICATED_INDEPENDENT_OPERATOR";
  // 'claimed_independence' is intentionally NOT trusted: does not contain
  // independently verified key possession, operator custody or actual cosignature.
  return out;
}

function w17Tests() {
  const fields=["operator_public_name","real_log_origin","origin_control_evidence","dedicated_test_log_vkey","test_key_custody_evidence","checkpoint_url","consistency_url","public_operator_contact"];
  const sample=()=>({
    schema:"ARIO_W17_REVIEW_INPUT_V1",
    official_log:{origin_line:"ario.test/log",log_vkey:"ario.test/log+abcdef12+AV2yLmzeBL9B3zFJNqal0JuqxiFve0m/eqmT1+KkLVeC",qpd:24,requested_list:"testing",contact:"tester@example.invalid"},
    r17_evidence:Object.fromEntries(fields.map(k=>[k,"synthetic declaration: "+k])),
    claimed_independence:{admin_count:2,verified:true,operator_label_1:"independent",operator_label_2:"independent"}});
  const c=x=>JSON.parse(JSON.stringify(x));
  const cases=[];
  function check(id,mutate,expectedOfficial,expectedInternal,reason){
    const b=sample();mutate(b);const x=w17Evaluate(b);
    if(x.official_form_structurally_complete!==expectedOfficial||
       x.internal_r17_evidence_structurally_complete!==expectedInternal||
       (reason&&x.reason!==reason)||
       x.system_ready!==false||x.action_authority!=="NONE"||
       x.authenticated_operator_independence!=="NOT_ESTABLISHED"||
       x.ario_test_log_witnessed!=="NOT_ESTABLISHED"||
       x.external_network_actions!==0)throw Error(JSON.stringify({id,observed:x,expectedOfficial,expectedInternal,reason}));
    cases.push({id,official_fields:expectedOfficial,internal_r17_fields:expectedInternal,reason:x.reason,missing_official:x.missing_official,missing_internal:x.missing_internal});
  }
  const both="DECLARED_PAPERWORK_PRESENT_BUT_NO_AUTHENTICATED_INDEPENDENT_OPERATOR";
  const off="OFFICIAL_FORM_FIELDS_MISSING_OR_INVALID";
  const r17="INTERNAL_R17_EVIDENCE_NOT_DOCUMENTED";
  check("W17-01",()=>{},true,true,both);
  check("W17-02",b=>b.claimed_independence={admin_count:1000,verified:true},true,true,both);
  check("W17-03",b=>b.official_log.origin_line=null,false,true,off);
  check("W17-04",b=>b.official_log.log_vkey=null,false,true,off);
  check("W17-05",b=>b.official_log.qpd=0,false,true,off);
  check("W17-06",b=>b.official_log.qpd=true,false,true,off);
  check("W17-07",b=>b.official_log.qpd="24",false,true,off);
  check("W17-08",b=>b.official_log.qpd=2147483648,false,true,off);
  check("W17-09",b=>b.official_log.requested_list="production",false,true,off);
  check("W17-10",b=>b.official_log.requested_list="testing",true,true,both);
  check("W17-11",b=>b.official_log.contact="",false,true,off);
  check("W17-12",b=>b.official_log.origin_line="bad origin",false,true,off);
  check("W17-13",b=>b.official_log.log_vkey="this is a public key",false,true,off);
  check("W17-14",b=>b.r17_evidence.real_log_origin=null,true,false,r17);
  check("W17-15",b=>b.r17_evidence.origin_control_evidence="",true,false,r17);
  check("W17-16",b=>b.r17_evidence.test_key_custody_evidence="",true,false,r17);
  check("W17-17",b=>b.r17_evidence.consistency_url="",true,false,r17);
  check("W17-18",b=>b.r17_evidence.checkpoint_url="",true,false,r17);
  check("W17-19",b=>b.r17_evidence.operator_public_name="",true,false,r17);
  check("W17-20",b=>b.r17_evidence.dedicated_test_log_vkey="",true,false,r17);
  check("W17-21",b=>b.r17_evidence.public_operator_contact="",true,false,r17);
  check("W17-22",b=>{for(const k of fields)b.r17_evidence[k]=null;},true,false,r17);
  check("W17-23",b=>b.official_log.qpd=1,true,true,both);
  check("W17-24",b=>b.official_log.requested_list="staging",true,true,both);
  check("W17-25",b=>b.claimed_independence="signed by many independent witnesses",true,true,both);
  check("W17-26",b=>b.claimed_independence={verified:true,third_party:true,pinned:true,source:"self declared"},true,true,both);
  check("W17-27",b=>{b.official_log.log_vkey="fake+abcdef12+QQ==";},true,true,both);
  check("W17-28",b=>{b.official_log.requested_list=null; b.r17_evidence.public_operator_contact=null;},false,false,off);
  check("W17-29",b=>b.r17_evidence.operator_public_name=" ",true,false,r17);
  check("W17-30",b=>b.official_log.qpd=24,true,true,both);
  const result={schema:"ARIO_W17_SELF_AUTHORED_TEST_RESULTS_V1",tests:cases.length,all_expected_matched:true,
    fixture_type:"SYNTHETIC_AND_SELF_DECLARED",no_real_operator_review:true,real_log_key_present:false,
    actual_witness_signatures_verified:0,external_actions:0,
    note:"Structural completeness is NOT public witness-network approval. R17 eight fields are internal Ario preapplication checks, not mandatory official log-application fields. Even fully populated claimed independence never grants authority.",
    cases};
  return result;
}

console.log(JSON.stringify(w17Tests(),null,2));
