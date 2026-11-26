package main
import (
 "testing"
 "encoding/hex"
)
func policyQuorum(_ bool, external int)bool{return external>=2}
func TestExternalOnlyPolicyRequiresTwoIndependentWitnesses(t *testing.T){
 for _,tc:=range []struct{group bool;external int;want bool}{{true,0,false},{true,1,false},{true,2,true},{true,3,true},{false,1,false},{false,2,true},{false,4,true}}{
  if got:=policyQuorum(tc.group,tc.external);got!=tc.want{t.Fatalf("group=%v external=%d got=%v want=%v",tc.group,tc.external,got,tc.want)}
 }
}
func TestRollbackBelowIndependentFloorHolds(t *testing.T){if got:=floorDecision(282812,"root",282811,"root");got!="HOLD_BELOW_EXTERNAL_FLOOR"{t.Fatal(got)}}
func TestSameSizeDifferentRootHolds(t *testing.T){if got:=floorDecision(282811,"root-a",282811,"root-b");got!="HOLD_SAME_SIZE_ROOT_CONFLICT"{t.Fatal(got)}}
func TestSameSizeSameRootNotClassifiedAsRollback(t *testing.T){if got:=floorDecision(282811,"root",282811,"root");got!="SIZE_AND_ROOT_NOT_BELOW_FLOOR"{t.Fatal(got)}}
func TestOneExternalWitnessIsNotAQuorum(t *testing.T){if policyQuorum(false,1){t.Fatal("one external witness must not pass")}}


func TestParseRemoraStatusCheckpoint(t *testing.T) {
 raw := "# litewitness remora.n621.de\n\n## Logs\n\n- sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d\n  (size 282811, root f1ofv4COOmNlLAgXpWjFC5llrxnU/Q+vmP5CYWa5D/c=)\n"
 size,root,err:=parseRemoraStatus([]byte(raw))
 if err!=nil || size!=282811 || hex.EncodeToString(root[:])!="7f5a1fbf808e3a63652c0817a568c50b9965af19d4fd0faf98fe426166b90ff7" { t.Fatalf("size=%d root=%x err=%v",size,root,err) }
}
func TestParseRemoraStatusRejectsMissingLog(t *testing.T) {
 if _,_,err:=parseRemoraStatus([]byte("# litewitness\n"));err==nil{t.Fatal("expected missing log reject")}
}

func TestPreviousRepoSnapshotRollbackAgainstNewFloor(t *testing.T){if got:=floorDecision(282813,"root-new",282812,"root-old");got!="HOLD_BELOW_EXTERNAL_FLOOR"{t.Fatal(got)}}
