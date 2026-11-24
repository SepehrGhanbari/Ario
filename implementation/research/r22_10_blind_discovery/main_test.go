package main
import "testing"
func TestResolution(t *testing.T) {
 first:=match{10,"first"}
 next:=match{11,"opaque"}
 cases:=[]struct{name string; ms []match; complete bool; n int; status string}{
 {"blind",[]match{first,next},true,1,"HOLD_OPAQUE_NEW_SIGNED_COMMITMENT"},
 {"missing",[]match{next},true,0,"HOLD_BOOTSTRAP_NOT_FOUND"},
 {"incomplete",[]match{first,next},false,1,"HOLD_INCOMPLETE_SCAN"},
 {"old-only",[]match{first},true,0,"NO_NEW_MATCH_IN_SAMPLED_SUFFIX"},
 {"repeat",[]match{first,{11,"first"}},true,0,"HOLD_ORDER_OR_DUPLICATE"},
 {"order",[]match{first,{9,"opaque"}},true,0,"HOLD_ORDER_OR_DUPLICATE"},
 }
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){n,s:=resolve(c.ms,10,"first",c.complete);if n!=c.n||s!=c.status{t.Fatalf("%d %s",n,s)}})}
}
