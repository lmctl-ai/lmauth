"""Offline release regression controls. No network, actual tokens or release mutation."""
import hashlib,json,os,runpy,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

def text(file):return (ROOT/file).read_text()

def job_blocks():
 data={}
 for file in ['.github/workflows/qualify-private-draft.yml','.github/workflows/qualify-platforms.yml']:
  if not (ROOT/file).exists():continue
  current=None
  for line in text(file).split('\njobs:\n',1)[1].splitlines():
   if line.startswith('  ') and not line.startswith('   ') and line.endswith(':'):
    current=line.strip()[:-1];data[current]=[]
   elif current:data[current].append(line)
 return {key:'\n'.join(value) for key,value in data.items()}

class CredentialBoundary(unittest.TestCase):
 def test_only_final_promoter_has_contents_write(self):
  jobs=job_blocks();writers={name for name,body in jobs.items() if 'contents: write' in body}
  self.assertEqual(writers,{'promote'})
 def test_candidate_execution_has_no_token_environment(self):
  action=text('.github/actions/qualify-platform/action.yml')
  self.assertNotIn('GH_TOKEN:',action);self.assertNotIn('GITHUB_TOKEN:',action)
  self.assertIn('persist-credentials: false',text('.github/workflows/qualify-private-draft.yml'))
 def test_installed_candidate_cannot_see_parent_token(self):
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);candidate=d/'assets';candidate.mkdir();tools=d/'tools';tools.mkdir();record=d/'observed.json'
   host=("#!"+sys.executable+"\nimport os,json,pathlib\npathlib.Path("+repr(str(record))+").write_text(json.dumps({'credential':bool(os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN'))}))\nprint('lmauth 1.2.3')\n").encode()
   (candidate/'lmauth-linux-x64').write_bytes(host)
   (candidate/'SHA256SUMS').write_text(hashlib.sha256(host).hexdigest()+'  lmauth-linux-x64\n')
   (candidate/'RELEASE-MANIFEST.json').write_text(json.dumps({'tag':'v1.2.3','version':'1.2.3'}))
   compiler=tools/'compiler';compiler.write_text('#!'+sys.executable+"\nimport os,pathlib\nprint('source: PATH')\nprint('path: '+str(pathlib.Path(os.environ['RUNNER_TEMP'])/'lmauth-draft-bin/lmauth'))\n");compiler.chmod(0o755)
   env={'PATH':'/usr/bin:/bin','RUNNER_TEMP':str(d),'GITHUB_ENV':str(d/'env'),'GITHUB_PATH':str(d/'path'),'GH_TOKEN':'SYNTHETIC_ONLY','GITHUB_TOKEN':'SYNTHETIC_ONLY'}
   r=subprocess.run([sys.executable,str(ROOT/'scripts/install-draft-host.py'),'--compiler',str(compiler),'--tag','v1.2.3','--asset','lmauth-linux-x64','--candidate',str(candidate)],env=env,capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(json.loads(record.read_text())['credential'])
 def test_documented_permissions_match_workflow(self):
  doc=text('docs/release-pipeline.md');declared={}
  for line in doc.splitlines():
   if not line.startswith('|'):continue
   cells=[x.strip().strip('`') for x in line.strip('|').split('|')]
   if len(cells)>=2 and cells[0] in job_blocks():declared[cells[0]]=cells[1]
  actual={name:('contents:write' if 'contents: write' in body else 'contents:read')+('; actions:read' if 'actions: read' in body else '') for name,body in job_blocks().items()}
  self.assertEqual(declared,actual)
 def test_cross_run_artifacts_are_flattened(self):
  for file in ['.github/workflows/qualify-platforms.yml','.github/actions/qualify-platform/action.yml']:
   source=text(file)
   self.assertIn('artifact-ids:',source)
   self.assertIn('merge-multiple: true',source,file)
 def test_native_terminal_coverage_keeps_linux_integration_and_macos_pty_control(self):
  action=text('.github/actions/qualify-platform/action.yml')
  self.assertIn("if: runner.os == 'Linux'",action)
  self.assertIn("if: runner.os == 'macOS'",action)
  self.assertIn('tests/lmmock-terminal-e2e.py',action)
  self.assertIn('tests/terminal-pty-denial.py',action)
 def test_signal_gate_keeps_stdin_open_until_the_process_handles_termination(self):
  source=text('tests/session-signal.py')
  self.assertIn('proc.send_signal(signal.SIGTERM);proc.wait()',source)
  self.assertNotIn('proc.send_signal(signal.SIGTERM);out,err=proc.communicate()',source)
 def test_actions_pinned(self):
  for f in ['.github/workflows/qualify-private-draft.yml','.github/workflows/public-ci.yml','.github/workflows/qualify-platforms.yml','.github/actions/qualify-platform/action.yml']:
   for line in text(f).splitlines():
    if 'uses:' not in line:continue
    ref=line.split('uses:',1)[1].split('#',1)[0].strip()
    if ref.startswith('./'):continue
    pin=ref.rsplit('@',1)[-1]
    self.assertEqual(len(pin),40,(f,ref));self.assertTrue(all(c in '0123456789abcdef' for c in pin))
 def test_cancel_guard(self):
  body=job_blocks()['promote'];line=next(l for l in body.splitlines() if l.strip().startswith('if:'))
  self.assertIn('!cancelled()',line)
 def test_candidate_queue_does_not_drop_other_versions(self):
  workflow=text('.github/workflows/qualify-private-draft.yml')
  group=next(l for l in workflow.splitlines() if l.strip().startswith('group:'))
  self.assertIn('client_payload.tag',group)
  self.assertIn('queue: max',job_blocks()['promote'])

class SealedPolicy(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=ROOT/'scripts/release_policy.py'
  cls.module=runpy.run_path(str(cls.path)) if cls.path.exists() else {}
 def required(self,name):
  self.assertIn(name,self.module,'missing reusable release policy '+name)
  return self.module[name]
 def test_provenance_required(self):
  validate=self.required('validate_manifest')
  with self.assertRaises(ValueError):validate({'format':'lmauth-release-candidate/1','repository':'lmctl-ai/lmauth','source_sha':'0'*40})
 def test_older_and_revoked_refused(self):
  check=self.required('allow_promotion')
  with self.assertRaises(ValueError):check('v0.1.20','v0.1.58',[])
  with self.assertRaises(ValueError):check('v0.1.59','v0.1.58',['v0.1.59'])
 def test_cleanup_requires_sealed_throwaway(self):
  check=self.required('allow_cleanup')
  with self.assertRaises(ValueError):check({'deliberate_failure':False})
 def test_changed_asset_identity_refused(self):
  check=self.required('same_assets')
  with self.assertRaises(ValueError):check([{'id':1,'name':'a','digest':'sha256:aa','size':2}],[{'id':2,'name':'a','digest':'sha256:aa','size':2}])
 def test_private_attestation_verifier_is_required(self):
  verify=text('scripts/verify-draft-candidate.py')
  self.assertIn('verify_attestation',verify)

 def test_public_broker_retries_transient_actions_api_failure_without_a_deadline(self):
  broker=runpy.run_path(str(ROOT/'scripts/qualification_broker.py'))
  transient=broker['TransientGitHubError']
  class FlakyAPI:
   attempts=0
   def request(self,path):
    self.attempts+=1
    if self.attempts==1:raise transient('synthetic 502')
    return {'path':broker['WORKFLOW'],'head_branch':'main','head_sha':'a'*40,'event':'repository_dispatch','status':'completed','conclusion':'success'}
  api=FlakyAPI();pauses=[]
  good=[{'name':'candidate','status':'completed','conclusion':'success'}]
  good += [{'name':name,'status':'completed','conclusion':'success'} for name in broker['PLATFORMS']]
  good += [{'name':'deliberate-failure-test','status':'completed','conclusion':'skipped'}]
  broker['wait_for_qualification'](api,42,'a'*40,False,lambda seconds:pauses.append(seconds),lambda client,run_id:good)
  self.assertEqual(api.attempts,2);self.assertEqual(pauses,[3])
 def test_public_broker_retains_the_trusted_release_manager_boundary(self):
  source=text('scripts/qualification_broker.py')
  self.assertIn('import json,os,subprocess,time',source)
  self.assertIn("subprocess.run(['python3','scripts/manage-qualified-draft.py',mode",source)
 def test_api_errors_report_status_without_echoing_response_urls(self):
  policy=runpy.run_path(str(ROOT/'scripts/release_policy.py'))
  class Result:
   returncode=1;stdout=b'';stderr=b'gh: HTTP 422: Validation Failed (https://api.github.com/repos/example/release)\n'
  with patch.object(policy['subprocess'],'run',return_value=Result):
   try:policy['API']().request('releases',method='POST',data={})
   except ValueError as error:
    self.assertIn('HTTP 422: Validation Failed',str(error));self.assertNotIn('https://',str(error))
   else:self.fail('HTTP failure was accepted')

if __name__=='__main__':unittest.main()
