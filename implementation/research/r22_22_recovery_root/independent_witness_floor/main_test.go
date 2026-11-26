package main
import "testing"
func policyQuorum(_ bool, external int)bool{return external>=2}
func TestExternalOnlyPolicyRequiresTwoIndependentWitnesses(t *testing.T){
 for _,tc:=range []struct{group bool;external int;want bool}{{true,0,false},{true,1,false},{true,2,true},{true,3,true},{false,1,false},{false,2,true},{false,4,true}}{
  if got:=policyQuorum(tc.group,tc.external);got!=tc.want{t.Fatalf("group=%v external=%d got=%v want=%v",tc.group,tc.external,got,tc.want)}
 }
}
func TestRollbackBelowIndependentFloorHolds(t *testing.T){if got:=floorDecision(282811,"root",282810,"root");got!="HOLD_BELOW_EXTERNAL_FLOOR"{t.Fatal(got)}}
func TestSameSizeDifferentRootHolds(t *testing.T){if got:=floorDecision(282811,"root-a",282811,"root-b");got!="HOLD_SAME_SIZE_ROOT_CONFLICT"{t.Fatal(got)}}
func TestSameSizeSameRootNotClassifiedAsRollback(t *testing.T){if got:=floorDecision(282811,"root",282811,"root");got!="SIZE_AND_ROOT_NOT_BELOW_FLOOR"{t.Fatal(got)}}
func TestOneExternalWitnessIsNotAQuorum(t *testing.T){if policyQuorum(false,1){t.Fatal("one external witness must not pass")}}
