// R63 G8: disposable Windows CI-only integrated peer SID + two synthetic actor signatures + durable native CNG use.
// NOT a production signer or independent Ario custody. NO REAL KEYS. Never executes on founder's laptop.
using System;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Security.Principal;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class G9IntegratedBroker {
    const string Epoch="research_nov_2026_no_signer";
    const string BaseHead="6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1";
    const string CandidateHead="52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c";
    const string Version="ARIO_R63_G9_DISPOSABLE_ONLY_V1";
    static readonly CngProvider Provider=CngProvider.MicrosoftSoftwareKeyStorageProvider;
    [DllImport("ncrypt.dll", ExactSpelling=true, EntryPoint="NCryptSignHash")]
    static extern int NCryptSignHash(SafeNCryptKeyHandle key, IntPtr padding,
      byte[] digest, int digestLen, byte[] sig, int capacity, out int written, int flags);

    static void Need(bool ok,string why) { if(!ok) throw new InvalidOperationException(why); }
    static bool IsHash(string s) { return s!=null && Regex.IsMatch(s,"^[a-f0-9]{64}$"); }
    static byte[] UTF(string s) { return new UTF8Encoding(false,true).GetBytes(s); }
    static string Hash(byte[] b) { using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant(); }
    static byte[] Digest(byte[] b) { using(var h=SHA256.Create()) return h.ComputeHash(b); }
    static void NewDurable(string path, byte[] bytes) {
       using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
           f.Write(bytes,0,bytes.Length);f.Flush(true);
       }
    }
    static string KeyName(string folder) {
       string basename=new DirectoryInfo(folder).Name;
       Need(Regex.IsMatch(basename,"^(normal|before|after|receipt|veto|bad|revoked|rogue)$"),"HOLD_INVALID_CASE");
       string run=new DirectoryInfo(Directory.GetParent(folder).FullName).Name;
       Need(Regex.IsMatch(run,"^ArioR63G9_[a-f0-9]{8}$"),"HOLD_WRONG_DISPOSABLE_ROOT");
       return "ARIO_R63_G9_CI_ONLY_"+run.Substring(10)+"_"+basename;
    }
    static string Challenge(string caseName,string nonce,string ident,string role,string decision,string payloadHash) {
       return Version+"\n"+Epoch+"\n"+BaseHead+"\n"+CandidateHead+"\n"+caseName+"\n"+
              nonce+"\n"+ident+"\n"+role+"\n"+decision+"\n"+payloadHash+"\n";
    }
    static byte[] ToSign(string caseName,string nonce,string ident,string payloadHash) {
       return Digest(UTF("ARIO_R63_G9_NATIVE_SIGN_USE_V1\n"+Epoch+"\n"+BaseHead+"\n"+CandidateHead+"\n"+caseName+"\n"+nonce+"\n"+ident+"\n"+payloadHash+"\n"));
    }
    static byte[] Pub(CngKey key) { return key.Export(CngKeyBlobFormat.EccPublicBlob); }
    static bool VerifyActor(byte[] pub,string signature,string caseName,string nonce,string id,string role,string decision,string payloadHash) {
       byte[] sig;
       try { sig=Convert.FromBase64String(signature); } catch(FormatException) { return false; }
       if(sig.Length!=64)return false;
       try {
           using(var key=CngKey.Import(pub,CngKeyBlobFormat.EccPublicBlob))
           using(var ecdsa=new ECDsaCng(key)) {
             return ecdsa.VerifyHash(Digest(UTF(Challenge(caseName,nonce,id,role,decision,payloadHash))),sig);
           }
       } catch(CryptographicException) {return false;}
    }
    // This creates TWO DIFFERENT ephemeral *synthetic* actor keys in one CI admin process.
    // It never exports actor private keys. Thus key separation from runner admin is NOT established.
    public static string Fixture(string root) {
       Need(Directory.Exists(root),"HOLD_ROOT_MISSING");
       string payloadHash=Hash(File.ReadAllBytes(Path.Combine(root,"payload.bin")));
       NewDurable(Path.Combine(root,"payload.sha256"),UTF(payloadHash+"\n"));
       using(var founderKey=CngKey.Create(CngAlgorithm.ECDsaP256,null,new CngKeyCreationParameters()))
       using(var arioKey=CngKey.Create(CngAlgorithm.ECDsaP256,null,new CngKeyCreationParameters()))
       using(var founder=new ECDsaCng(founderKey))
       using(var ario=new ECDsaCng(arioKey)) {
          byte[] fpub=Pub(founderKey), apub=Pub(arioKey);
          Need(Hash(fpub)!=Hash(apub),"HOLD_DUPLICATED_SYNTHETIC_ACTOR_KEYS");
          NewDurable(Path.Combine(root,"founder.pub"),fpub);
          NewDurable(Path.Combine(root,"ario.pub"),apub);
          string[] cases={"normal","before","after","receipt","veto","bad","revoked","rogue"};
          for(int i=0;i<cases.Length;i++) {
             string folder=Path.Combine(root,cases[i]);Directory.CreateDirectory(folder);
             string nonce=new string("abcdef12"[i],64), ident=new string("12345678"[i],64);
             string decision=cases[i]=="veto" ? "VETO" : "ALLOW";
             byte[] fsig=founder.SignHash(Digest(UTF(Challenge(cases[i],nonce,ident,"FOUNDER","ALLOW",payloadHash))));
             byte[] asig=ario.SignHash(Digest(UTF(Challenge(cases[i],nonce,ident,"ARIO",decision,payloadHash))));
             if(cases[i]=="bad")fsig[0]^=1; // invalid founder approval with still-valid Ario approval
             string request="SIGN "+cases[i]+" "+nonce+" "+ident+" "+decision+" "+
                  Convert.ToBase64String(fsig)+" "+Convert.ToBase64String(asig)+" "+"CLAIMED_READER\n";
             NewDurable(Path.Combine(folder,"request.txt"),UTF(request));
             if(cases[i]=="revoked") NewDurable(Path.Combine(folder,"revoked.flag"),UTF("SYNTHETIC_REVOKED\n"));
          }
       }
       return "G9_EPHEMERAL_TWO_ACTOR_FIXTURES=PASS";
    }
    static string ReceiptCheck(string folder, string caseName,string nonce,string ident,string payloadHash) {
       string receiptPath=Path.Combine(folder,"receipt-public.txt");
       if(!File.Exists(receiptPath))return "";
       byte[] bytes=File.ReadAllBytes(receiptPath);
       string[] lines;
       try { lines=new UTF8Encoding(false,true).GetString(bytes).Split('\n'); }
       catch(DecoderFallbackException) {return "HOLD_CORRUPT_RECEIPT";}
       if(lines.Length!=8||lines[0]!="ARIO_R63_G9_RECEIPT_V1"||lines[1]!="case="+caseName||
          lines[2]!="nonce="+nonce||lines[3]!="ident="+ident||lines[4]!="payload_sha256="+payloadHash||lines[7]!="")
          return "HOLD_CORRUPT_RECEIPT";
       if(!lines[5].StartsWith("pub=" )||!lines[6].StartsWith("sig="))return "HOLD_CORRUPT_RECEIPT";
       byte[] pub,sig;
       try { pub=Convert.FromBase64String(lines[5].Substring(4));sig=Convert.FromBase64String(lines[6].Substring(4)); }
       catch(FormatException){return "HOLD_CORRUPT_RECEIPT";}
       if(sig.Length!=64)return "HOLD_CORRUPT_RECEIPT";
       try {
           using(var publicKey=CngKey.Import(pub,CngKeyBlobFormat.EccPublicBlob))
           using(var signer=new ECDsaCng(publicKey)) {
               if(!signer.VerifyHash(ToSign(caseName,nonce,ident,payloadHash),sig))return "HOLD_CORRUPT_RECEIPT";
           }
       } catch(CryptographicException) {return "HOLD_CORRUPT_RECEIPT";}
       // The public key must match the key that the surviving process can reopen.
       string keyName=KeyName(folder);
       if(!CngKey.Exists(keyName,Provider))return "HOLD_ORIGINAL_KEY_MISSING";
       using(var key=CngKey.Open(keyName,Provider)) {
           if(Hash(Pub(key))!=Hash(pub))return "HOLD_KEY_CHANGED";
       }
       return "SIGNED_"+Convert.ToBase64String(bytes);
    }
    
    // Custodian token is a synthetic OS-separated monotonic use fence.
    // No independently controlled network endpoint or pinned server key is implied.
    static string ExternalConsume(string pipeName,string caseName,string nonce,string ident,string ph) {
      if(!Regex.IsMatch(pipeName??"","^ArioR63G9C_[a-f0-9]{8}$"))return "HOLD_EXTERNAL_CUSTODY_UNAVAILABLE";
      string token=Hash(UTF("ARIO-R63/G9/CONSUME/v1|"+Epoch+"|"+BaseHead+"|"+CandidateHead+"|"+caseName+"|"+nonce+"|"+ident+"|"+ph));
      try {
        using(var pipe=new NamedPipeClientStream(".",pipeName,PipeDirection.InOut,PipeOptions.None,TokenImpersonationLevel.Impersonation)) {
          pipe.Connect(3500);
          byte[] req=UTF("CONSUME "+token+"\n");
          pipe.Write(req,0,req.Length);pipe.Flush();
          string result=ReadLine(pipe);
          return result=="G9_CUSTODY_GRANTED"?result:
             (result=="HOLD_EXTERNAL_SPENT"?result:"HOLD_EXTERNAL_CUSTODY_UNAVAILABLE");
        }
      } catch(Exception) {return "HOLD_EXTERNAL_CUSTODY_UNAVAILABLE";}
    }

    static string Handle(string folder,string request,string phase,string custodyPipe) {
       string[] t=request.Split(' ');
       if(t.Length!=8||t[0]!="SIGN"||t[1]!=new DirectoryInfo(folder).Name||
          !IsHash(t[2])||!IsHash(t[3])||(t[4]!="ALLOW" && t[4]!="VETO")||
          t[5].Length>100||t[6].Length>100||t[7].Length>60) return "HOLD_INVALID_REQUEST";
       string caseName=t[1], nonce=t[2], ident=t[3], decision=t[4];
       byte[] payload=File.ReadAllBytes(Path.Combine(Directory.GetParent(folder).FullName,"payload.bin"));
       string ph=Hash(payload);
       if(File.ReadAllText(Path.Combine(Directory.GetParent(folder).FullName,"payload.sha256")).Trim()!=ph)
           return "HOLD_PAYLOAD_CHANGED";
       byte[] fp=File.ReadAllBytes(Path.Combine(Directory.GetParent(folder).FullName,"founder.pub"));
       byte[] ap=File.ReadAllBytes(Path.Combine(Directory.GetParent(folder).FullName,"ario.pub"));
       if(Hash(fp)==Hash(ap))return "HOLD_DUPLICATE_ACTOR_IDENTITY";
       if(!VerifyActor(fp,t[5],caseName,nonce,ident,"FOUNDER","ALLOW",ph) ||
          !VerifyActor(ap,t[6],caseName,nonce,ident,"ARIO",decision,ph))
           return "HOLD_BAD_ACTOR_APPROVAL";
       if(decision!="ALLOW")return "HOLD_ARIO_VETO";
       if(File.Exists(Path.Combine(folder,"revoked.flag")))return "HOLD_REVOKED";
       string intentPath=Path.Combine(folder,"use-intent.txt");
       string intent="ARIO_R63_G9_DURABLE_INTENT_V1\n"+caseName+"\n"+nonce+"\n"+ident+"\n"+ph+"\n";
       if(File.Exists(intentPath)) {
          if(File.ReadAllText(intentPath)!=intent)return "HOLD_INTENT_DIFFERENT";
          string receipt=ReceiptCheck(folder,caseName,nonce,ident,ph);
          return receipt.Length>0?receipt:"HOLD_UNCERTAIN";
       }
       if(phase=="recovery")return "HOLD_NO_PREVIOUS_DURABLE_INTENT";
       // Permanent remote consume is required before local durable intent and CNG.
       string custody=ExternalConsume(custodyPipe,caseName,nonce,ident,ph);
       if(custody!="G9_CUSTODY_GRANTED")return custody;
       // Strict durable consumption before making any call to native NCryptSignHash.
       NewDurable(intentPath,UTF(intent));
       if(phase=="before")Environment.Exit(73);
       string keyName=KeyName(folder);
       CngKey k;
       if(CngKey.Exists(keyName,Provider))k=CngKey.Open(keyName,Provider);
       else {
           var p=new CngKeyCreationParameters();p.Provider=Provider;
           p.ExportPolicy=CngExportPolicies.None;p.KeyUsage=CngKeyUsages.Signing;
           k=CngKey.Create(CngAlgorithm.ECDsaP256,keyName,p);
       }
       using(k) {
         byte[] digest=ToSign(caseName,nonce,ident,ph), signature=new byte[64];int written=0;
         NewDurable(Path.Combine(folder,"public-pin.sha256"),UTF(Hash(Pub(k))+"\n"));
         NewDurable(Path.Combine(folder,"native-enter.txt"),UTF("NCryptSignHash ENTER 1\n"));
         int status=NCryptSignHash(k.Handle,IntPtr.Zero,digest,digest.Length,signature,signature.Length,out written,0);
         if(status!=0||written!=64)throw new CryptographicException("HOLD_NATIVE_SIGN_FAILED_"+status);
         NewDurable(Path.Combine(folder,"native-return.txt"),UTF("NCryptSignHash RETURN 1\n"));
         if(phase=="after")Environment.Exit(73); // real process dies AFTER native return BEFORE receipt
         byte[] pub=Pub(k);
         using(var publicKey=CngKey.Import(pub,CngKeyBlobFormat.EccPublicBlob))
         using(var checker=new ECDsaCng(publicKey))
            Need(checker.VerifyHash(digest,signature),"HOLD_PUBLIC_VERIFY_FAILED");
         string contents="ARIO_R63_G9_RECEIPT_V1\ncase="+caseName+"\nnonce="+nonce+"\nident="+ident+"\npayload_sha256="+ph+"\npub="+Convert.ToBase64String(pub)+"\nsig="+Convert.ToBase64String(signature)+"\n";
         byte[] bytes=UTF(contents);
         NewDurable(Path.Combine(folder,"receipt-public.txt"),bytes);
         if(phase=="receipt")Environment.Exit(73); // durable receipt, response was NEVER sent
         return "SIGNED_"+Convert.ToBase64String(bytes);
       }
    }
    static string ReadLine(Stream s) {
        byte[] buf=new byte[2048];int n=0;
        while(n<buf.Length) {int b=s.ReadByte();if(b<0)throw new IOException("EOF");if(b==10)return new UTF8Encoding(false,true).GetString(buf,0,n);buf[n++]=(byte)b;}
        throw new IOException("OVERSIZED_RPC");
    }
    static void WriteReply(Stream s,string reply) {byte[] b=UTF(reply+"\n");s.Write(b,0,b.Length);s.Flush();}
    public static string Serve(string root,string caseName,string pipeName,string writerSid,string readerSid,int count,string phase,string custodyPipe) {
       Need(WindowsIdentity.GetCurrent().User.Value==writerSid,"HOLD_WRITER_OS_SID_MISMATCH");
       Console.WriteLine("G9_WRITER_OS_SID="+writerSid);Console.Out.Flush();
       Need(Regex.IsMatch(pipeName,"^ArioR63G9_[a-f0-9]{8}$"),"HOLD_UNEXPECTED_PIPE_NAME");
       Need(count>0&&count<=12,"HOLD_BAD_CLIENT_COUNT");
       Need(phase=="normal"||phase=="recovery"||phase=="before"||phase=="after"||phase=="receipt","HOLD_WRONG_PHASE");
       string folder=Path.Combine(root,caseName);
       Need(Directory.Exists(folder),"HOLD_CASE_MISSING");
       var acl=new PipeSecurity();
       acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.AuthenticatedUserSid,null),PipeAccessRights.ReadWrite,AccessControlType.Allow));
       acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(writerSid),PipeAccessRights.FullControl,AccessControlType.Allow));
       acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.LocalSystemSid,null),PipeAccessRights.FullControl,AccessControlType.Allow));
       for(int i=0;i<count;i++) {
          using(var server=new NamedPipeServerStream(pipeName,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.None,8192,8192,acl)) {
             server.WaitForConnection();
             string peer="",reply="HOLD_PEER_IDENTITY";
             try {
               string req=ReadLine(server);
               server.RunAsClient(delegate() {using(var ident=WindowsIdentity.GetCurrent()){if(ident.User!=null)peer=ident.User.Value;}});
               if(peer==readerSid)reply=Handle(folder,req,phase,custodyPipe);
             } catch(Exception e) {
               reply="HOLD_SERVER_ERROR";
               Console.Error.WriteLine("G9_ERROR="+e.GetType().Name+" "+e.Message);
             }
             Console.WriteLine("G9_CLIENT_OS_SID="+peer+" REPLY="+(reply.StartsWith("SIGNED_")?"SIGNED_RECEIPT":reply));
             Console.Out.Flush();Console.Error.Flush();
             try{WriteReply(server,reply);}catch(IOException){}
          }
       }
       return "G9_NATIVE_BROKER_PROCESSED_"+count;
    }
    public static string Client(string pipeName,string requestPath,string expectedSid) {
       Need(WindowsIdentity.GetCurrent().User.Value==expectedSid,"HOLD_CLIENT_OS_SID_MISMATCH");
       using(var client=new NamedPipeClientStream(".",pipeName,PipeDirection.InOut,PipeOptions.None,TokenImpersonationLevel.Impersonation)) {
          client.Connect(15000);
          byte[] data=File.ReadAllBytes(requestPath);
          Need(data.Length<1200&&data.Length>100,"HOLD_CLIENT_INPUT_BOUNDS");
          try {
             client.Write(data,0,data.Length);client.Flush();
             return ReadLine(client);
          } catch(IOException) {return "NO_ACK";}
       }
    }
    // Separate public-only audit: NEVER opens a CNG private key and never calls NCryptSignHash.
    public static string PublicAudit(string folder, string root) {
       string[] req=File.ReadAllText(Path.Combine(folder,"request.txt")).Trim().Split(' ');
       Need(req.Length==8 && req[0]=="SIGN","HOLD_BAD_ORIGINAL_REQUEST");
       string cas=req[1], nonce=req[2], ident=req[3];
       string payloadHash=Hash(File.ReadAllBytes(Path.Combine(root,"payload.bin")));
       byte[] bytes=File.ReadAllBytes(Path.Combine(folder,"receipt-public.txt"));
       string[] lines=new UTF8Encoding(false,true).GetString(bytes).Split('\n');
       Need(lines.Length==8 && lines[0]=="ARIO_R63_G9_RECEIPT_V1" && lines[1]=="case="+cas &&
          lines[2]=="nonce="+nonce && lines[3]=="ident="+ident && lines[4]=="payload_sha256="+payloadHash && lines[7]=="", "HOLD_WRONG_RECEIPT_CONTEXT");
       Need(lines[5].StartsWith("pub=")&&lines[6].StartsWith("sig="),"HOLD_RECEIPT_FORMAT");
       byte[] pub=Convert.FromBase64String(lines[5].Substring(4));
       byte[] sig=Convert.FromBase64String(lines[6].Substring(4));
       Need(sig.Length==64,"HOLD_SIGNATURE_LENGTH");
       string pin=File.ReadAllText(Path.Combine(folder,"public-pin.sha256")).Trim();
       Need(pin==Hash(pub),"HOLD_PUBLIC_PIN_CHANGED");
       using(var pubKey=CngKey.Import(pub,CngKeyBlobFormat.EccPublicBlob))
       using(var verifier=new ECDsaCng(pubKey)) {
           Need(verifier.VerifyHash(ToSign(cas,nonce,ident,payloadHash),sig),"HOLD_PUBLIC_SIGNATURE_INVALID");
       }
       return "G9_SEPARATE_PUBLIC_RECEIPT_VERIFY=PASS "+Hash(bytes);
    }
    public static string Cleanup(string root) {
       string[] cases={"normal","before","after","receipt","veto","bad","revoked","rogue"};
       int removed=0;
       foreach(string n in cases) {
          string kn=KeyName(Path.Combine(root,n));
          if(CngKey.Exists(kn,Provider)) {
              using(var k=CngKey.Open(kn,Provider))k.Delete();
              Need(!CngKey.Exists(kn,Provider),"HOLD_KEY_REMOVAL_FAILED_"+n);removed++;
          }
       }
       return "G9_TEMP_CNG_KEYS_REMOVED="+removed;
    }
}


public static class G9ExternalSyntheticCustodian {
  static void Need(bool ok,string msg){if(!ok)throw new InvalidOperationException(msg);}
  static byte[] UTF(string x){return new UTF8Encoding(false,true).GetBytes(x);}
  static string ReadLine(Stream p){
    byte[] b=new byte[256];int at=0;
    while(at<b.Length){int x=p.ReadByte();if(x<0)throw new IOException("EOF");if(x==10)return new UTF8Encoding(false,true).GetString(b,0,at);b[at++]=(byte)x;}
    throw new IOException("OVERLONG");
  }
  public static string Serve(string pipeName,string ledger,string ownSid,string brokerSid,int requests){
    Need(Regex.IsMatch(pipeName,"^ArioR63G9C_[a-f0-9]{8}$"),"BAD_CUSTODY_PIPE");
    Need(WindowsIdentity.GetCurrent().User.Value==ownSid,"WRONG_CUSTODIAN_TOKEN");
    Need(Directory.Exists(ledger),"MISSING_SEPARATE_LEDGER");
    Need(requests>0&&requests<=8,"BAD_REQUEST_COUNT");
    var acl=new PipeSecurity();
    acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.AuthenticatedUserSid,null),PipeAccessRights.ReadWrite,AccessControlType.Allow));
    acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(ownSid),PipeAccessRights.FullControl,AccessControlType.Allow));
    int total=0;
    for(int i=0;i<requests;i++){
      using(var p=new NamedPipeServerStream(pipeName,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.None,4096,4096,acl)){
        p.WaitForConnection();
        string response="HOLD_CUSTODY_IO",peer="";
        try {
          string req=ReadLine(p);
          p.RunAsClient(delegate(){using(var w=WindowsIdentity.GetCurrent()){if(w.User!=null)peer=w.User.Value;}});
          string[] parts=req.Split(' ');
          if(peer!=brokerSid)response="HOLD_CUSTODY_WRONG_PEER";
          else if(parts.Length!=2||parts[0]!="CONSUME"||!Regex.IsMatch(parts[1],"^[a-f0-9]{64}$"))response="HOLD_CUSTODY_BAD_TOKEN";
          else {
            string path=Path.Combine(ledger,parts[1]+".used");
            try {
              using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){
                byte[] marker=UTF("G9_SYNTHETIC_SPENT\n"+parts[1]+"\n");
                f.Write(marker,0,marker.Length);f.Flush(true);
              }
              response="G9_CUSTODY_GRANTED";
            } catch(IOException) { response=File.Exists(path)?"HOLD_EXTERNAL_SPENT":"HOLD_CUSTODY_IO"; }
          }
        } catch(Exception e){Console.Error.WriteLine("G9_CUSTODIAN_FAIL="+e.GetType().Name);response="HOLD_CUSTODY_IO";}
        Console.WriteLine("G9_CUSTODY_PEER="+peer+" RESPONSE="+response);
        Console.Out.Flush();Console.Error.Flush();
        try{byte[] msg=UTF(response+"\n");p.Write(msg,0,msg.Length);p.Flush();}catch(IOException){}
        total++;
      }
    }
    return "G9_CUSTODIAN_PROCESSED_"+total;
  }
}
