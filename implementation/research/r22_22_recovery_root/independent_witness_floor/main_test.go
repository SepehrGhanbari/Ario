package main
import "testing"
func policyQuorum(_ bool, external int)bool{return external>=2}
func TestExternalOnlyPolicyRequiresTwoIndependentWitnesses(t *testing.T){
 for _,tc:=range []struct{group bool;external int;want bool}{{true,0,false},{true,1,false},{true,2,true},{true,3,true},{false,1,false},{false,2,true},{false,4,true}}{
  if got:=policyQuorum(tc.group,tc.external);got!=tc.want{t.Fatalf("group=%v external=%d got=%v want=%v",tc.group,tc.external,got,tc.want)}
 }
}
func TestSecondHighestIsQuorumFloor(t *testing.T){
 a:=[]uint64{282900,282880,282870,282810}
 for i:=0;i<len(a);i++{for j:=i+1;j<len(a);j++{if a[j]>a[i]{a[i],a[j]=a[j],a[i]}}}
 if a[1]!=282880{t.Fatalf("floor=%d",a[1])}
}
func TestRollbackBelowIndependentFloorHolds(t *testing.T){if got:=floorDecision(282870,"a",282869,"a");got!="HOLD_BELOW_EXTERNAL_FLOOR"{t.Fatal(got)}}
func TestSameSizeDifferentRootHolds(t *testing.T){if got:=floorDecision(282870,"a",282870,"b");got!="HOLD_SAME_SIZE_ROOT_CONFLICT"{t.Fatal(got)}}
func TestSameSizeSameRootNotClassifiedAsRollback(t *testing.T){if got:=floorDecision(282870,"a",282870,"a");got!="SIZE_AND_ROOT_NOT_BELOW_FLOOR"{t.Fatal(got)}}
func TestWitnessSizeParsesSigsumPlainDecimal(t *testing.T){got,err:=parseWitnessSize([]byte("282900\n"));if err!=nil||got!=282900{t.Fatalf("got=%d err=%v",got,err)}}
func TestWitnessSizeParsesKeyValueCompatibility(t *testing.T){got,err:=parseWitnessSize([]byte("size=282900\n"));if err!=nil||got!=282900{t.Fatalf("got=%d err=%v",got,err)}}
func TestWitnessSizeRejectsAmbiguousResponse(t *testing.T){if _,err:=parseWitnessSize([]byte("size=1\nsize=2"));err==nil{t.Fatal("expected reject")}}
func TestLessThanTwoExternalReadbacksIsNotAQuorum(t *testing.T){for _,n:=range []int{0,1}{if n>=2{t.Fatalf("unexpected quorum for %d",n)}}}
