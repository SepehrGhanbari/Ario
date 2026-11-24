package main
import "testing"
func TestBoundedResolution(t *testing.T) {
 cases:=[]struct{name string; matches []match; complete bool; n int; want string}{
 {"older",[]match{{1,oldChecksum}},true,2,"KNOWN_CANDIDATE_RECOVERED_IN_BOUNDED_SAMPLED_SUFFIX_ONLY"},
 {"forward",[]match{{1,oldChecksum},{2,newChecksum}},true,4,"KNOWN_CANDIDATE_RECOVERED_IN_BOUNDED_SAMPLED_SUFFIX_ONLY"},
 {"incomplete",[]match{{1,newChecksum}},false,4,"HOLD_INCOMPLETE_SCAN"},
 {"opaque",[]match{{1,newChecksum},{2,"unknown"}},true,4,"HOLD_OPAQUE_SIGNER_ENTRY"},
 {"regression",[]match{{1,newChecksum},{2,oldChecksum}},true,4,"HOLD_SCOPE_SEQUENCE_REGRESSION"},
 {"empty",nil,true,0,"HOLD_NO_KNOWN_ENTRY"},
 }
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){n,s:=resolve(c.matches,c.complete);if n!=c.n||s!=c.want{t.Fatalf("%d %s",n,s)}})}
}
