// R63 G4 synthetic Windows peer SID gate. Separate-account pipes only.
// No real Ario keys, signers, services or production journals.
using System;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Diagnostics;

public static class G4PipeGate {
  static void Need(bool p,string reason){if(!p)throw new InvalidOperationException(reason);}
  static string ReadRequest(Stream pipe) {
    byte[] raw=new byte[256];int at=0;
    while(at<raw.Length){
      int c=pipe.ReadByte();
      if(c<0)throw new IOException("INCOMPLETE_REQUEST");
      if(c==10)return new UTF8Encoding(false,true).GetString(raw,0,at);
      raw[at++]=(byte)c;
    }
    throw new IOException("OVERSIZE_REQUEST");
  }
  static void WriteReply(Stream pipe,string reply) {
    byte[] b=Encoding.ASCII.GetBytes(reply+"\n");pipe.Write(b,0,b.Length);pipe.Flush();
  }
  static string Journal(string python,string script,string dir,string nonce,string id) {
    Need(Regex.IsMatch(nonce,"^[0-9a-f]{64}$") && Regex.IsMatch(id,"^[0-9a-f]{64}$"),"BAD_IDS");
    var psi=new ProcessStartInfo();
    psi.FileName=python;
    psi.Arguments="-I -B \""+script+"\" --commit \""+dir+"\" "+nonce+" "+id;
    psi.UseShellExecute=false;psi.CreateNoWindow=true;
    psi.RedirectStandardOutput=true;psi.RedirectStandardError=true;
    using(var p=Process.Start(psi)){
      if(!p.WaitForExit(15000)){try{p.Kill();}catch{};throw new TimeoutException("JOURNAL_TIMEOUT");}
      string output=p.StandardOutput.ReadToEnd().Trim();
      string err=p.StandardError.ReadToEnd();
      Need(p.ExitCode==0,"JOURNAL_FAILED_"+err);
      Need(output=="RESERVED_ONLY_NO_SIGN" || output=="ALREADY_RESERVED_NO_APPEND" ||
            output=="HOLD_UNCERTAIN" || output=="HOLD_BAD_IDENTIFIER", "INVALID_JOURNAL_RESPONSE");
      return output;
    }
  }
  public static string Serve(string pipeName,string expectedReaderSid,string writerSid,
                             string python,string script,string dir,int count,string logPath) {
    Need(Regex.IsMatch(pipeName,"^ArioR63G4_[a-zA-Z0-9]{6,20}$"),"BAD_PIPE_NAME");
    Need(count>0 && count<=16,"BAD_CONNECTION_LIMIT");
    var serverSid=WindowsIdentity.GetCurrent().User.Value;
    Need(serverSid==writerSid,"WRONG_SERVER_TOKEN_SID");
    var acl=new PipeSecurity();
    // Lab allows authenticated users to CONNECT so rogue peers are explicitly
    // rejected at the OS-token gate (not by the claimed user in the payload).
    acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.AuthenticatedUserSid,null),
                                        PipeAccessRights.ReadWrite,AccessControlType.Allow));
    acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(writerSid),
                                        PipeAccessRights.FullControl,AccessControlType.Allow));
    acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.LocalSystemSid,null),
                                        PipeAccessRights.FullControl,AccessControlType.Allow));
    int accepted=0,refused=0;
    using(var log=new StreamWriter(new FileStream(logPath,FileMode.CreateNew,FileAccess.Write,FileShare.Read),new UTF8Encoding(false))){
      for(int i=0;i<count;i++) {
        using(var pipe=new NamedPipeServerStream(pipeName,PipeDirection.InOut,1,
                  PipeTransmissionMode.Byte,PipeOptions.None,4096,4096,acl)) {
          pipe.WaitForConnection();
          string request="";string actualSid="";string result="HOLD_PEER_IDENTITY";
          try {
            request=ReadRequest(pipe);
            // RunAsClient verifies the token of the user on this pipe connection.
            // If impersonation is disallowed, FAIL CLOSED (never use payload SID).
            pipe.RunAsClient(delegate() {
              using(var identity=WindowsIdentity.GetCurrent()) {
                if(identity.User!=null)actualSid=identity.User.Value;
              }
            });
            if(actualSid==expectedReaderSid) {
              var tokens=request.Split(' ');
              if(tokens.Length==4 && tokens[0]=="RESERVE" &&
                 Regex.IsMatch(tokens[1],"^[0-9a-f]{64}$") &&
                 Regex.IsMatch(tokens[2],"^[0-9a-f]{64}$")) {
                 result=Journal(python,script,dir,tokens[1],tokens[2]);
              } else result="HOLD_BAD_REQUEST";
              accepted++;
            } else refused++;
          } catch(Exception ex) {
            refused++;
            result="HOLD_PEER_TOKEN_UNAVAILABLE";
            log.WriteLine("ERROR_"+i+"="+ex.GetType().Name);
          }
          log.WriteLine("CLIENT_"+i+"_SID="+actualSid);
          log.WriteLine("CLIENT_"+i+"_RESPONSE="+result);
          log.Flush();
          try{WriteReply(pipe,result);}catch(IOException){}
        }
      }
      log.WriteLine("SERVER_PID="+Process.GetCurrentProcess().Id);
      log.WriteLine("SERVER_SID="+serverSid);
      log.WriteLine("ALLOW_COUNT="+accepted);
      log.WriteLine("DENY_COUNT="+refused);
      log.Flush();
    }
    return "G4_PIPE_GATE_COMPLETED";
  }
  public static string Request(string pipeName,string nonce,string id,string claim,string expectedClientSid) {
    Need(WindowsIdentity.GetCurrent().User.Value==expectedClientSid,"WRONG_CLIENT_OS_TOKEN");
    Need(Regex.IsMatch(claim,"^S-1-5-[0-9-]+$"),"BAD_CLIENT_CLAIM");
    using(var client=new NamedPipeClientStream(".",pipeName,PipeDirection.InOut,
            PipeOptions.None,TokenImpersonationLevel.Impersonation)) {
      client.Connect(15000);
      var bytes=Encoding.ASCII.GetBytes("RESERVE "+nonce+" "+id+" "+claim+"\n");
      client.Write(bytes,0,bytes.Length);client.Flush();
      return ReadRequest(client);
    }
  }
}
