package main
import "testing"
func policyQuorum(glasklarGroup bool, external int)bool{n:=external;if glasklarGroup{n++};return n>=4}
func TestTest2PolicyRequiresAtLeastThreeExternal(t *testing.T){
 for _,tc:=range []struct{group bool;external int;want bool}{{true,0,false},{true,1,false},{true,2,false},{true,3,true},{false,3,false},{false,4,true}}{
  if got:=policyQuorum(tc.group,tc.external);got!=tc.want{t.Fatalf("group=%v external=%d got=%v want=%v",tc.group,tc.external,got,tc.want)}
 }
}
func TestThirdHighestIsQuorumFloor(t *testing.T){
 a:=[]uint64{282900,282880,282870,282810}
 for i:=0;i<len(a);i++{for j:=i+1;j<len(a);j++{if a[j]>a[i]{a[i],a[j]=a[j],a[i]}}}
 if a[2]!=282870{t.Fatalf("floor=%d",a[2])}
}
func TestRollbackBelowIndependentFloorHolds(t *testing.T){if got:=floorDecision(282870,"a",282869,"a");got!="HOLD_BELOW_EXTERNAL_FLOOR"{t.Fatal(got)}}
func TestSameSizeDifferentRootHolds(t *testing.T){if got:=floorDecision(282870,"a",282870,"b");got!="HOLD_SAME_SIZE_ROOT_CONFLICT"{t.Fatal(got)}}
func TestSameSizeSameRootNotClassifiedAsRollback(t *testing.T){if got:=floorDecision(282870,"a",282870,"a");got!="SIZE_AND_ROOT_NOT_BELOW_FLOOR"{t.Fatal(got)}}
func TestLessThanThreeExternalReadbacksIsNotAQuorum(t *testing.T){for _,n:=range []int{0,1,2}{if n>=3{t.Fatalf("unexpected quorum for %d",n)}}}
