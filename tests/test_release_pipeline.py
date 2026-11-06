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
 def test_every_always_step_stops_when_cancelled(self):
  files=['.github/actions/qualify-platform/action.yml','.github/workflows/qualify-private-draft.yml','.github/workflows/qualify-platforms.yml','.github/workflows/public-ci.yml']
  for file in files:
   for line in text(file).splitlines():
    if 'always()' in line:
     self.assertIn('!cancelled()',line,file+': '+line)
 def test_each_platform_leg_receives_the_verified_lmauth_tag(self):
  jobs=job_blocks()
  expected='LMAUTH_QUALIFY_TAG: ${{ needs.candidate.outputs.tag }}'
  self.assertIn(expected,jobs['qualify-macos-arm64'])
  self.assertIn(expected,jobs['integration'])
  self.assertIn('env.LMAUTH_QUALIFY_TAG',text('.github/actions/qualify-platform/action.yml'))
 def test_throwaway_gate_waits_for_macos_arm64_directly(self):
  body=job_blocks()['deliberate-failure-test']
  self.assertIn('needs: [candidate, qualify-macos-arm64, integration]',body)
  self.assertIn("needs.qualify-macos-arm64.result == 'success'",body)
 def test_runbook_has_redrive_replay_rollback_and_stale_draft_note(self):
  doc=text('docs/release-pipeline.md')
  self.assertIn('gh run rerun --repo lmctlhq/lmauth --job PUBLISH_DRAFT_JOB_ID',doc)
  self.assertIn('gh workflow run qualify-private-draft.yml --repo lmctl-ai/lmauth --ref main -f tag=UNRECORDED_TAG',doc)
  self.assertIn('git add REVOKED',doc)
  self.assertLess(doc.index('git add REVOKED'),doc.index('gh release edit "$BAD_TAG"'))
  self.assertIn('The public `v0.1.6` draft came from private run `42049931375`',doc)
  self.assertIn('It is not an eligible sealed throwaway cleanup.',doc)
 def test_readme_and_quickstart_pin_latest_published_lmauth(self):
  state=json.loads(text('release-state.json'))
  published=[tag for tag,item in state['candidates'].items() if item['outcome']=='published']
  latest=max(published,key=lambda tag:tuple(int(part) for part in tag[1:].split('.')))
  pin='github:lmctl-ai/lmauth@'+latest
  self.assertIn(pin,text('README.md'))
  self.assertIn(pin,text('docs/operator-quickstart.md'))
 def test_lmauth_tool_dependencies_are_explicitly_pinned(self):
  setup=text('tests/prepare-integration.sh')
  self.assertIn('LMMOCK_TAG=v0.1.105',setup)
  self.assertIn('LMMOCK_COMMIT=e9d6d7ffe8bf68f42bbfa8438130f2f2aa538542',setup)
  self.assertIn('sha256sum -c -',setup)
  self.assertIn('LMCONN_COMMIT=83cdec653e336167b55d5c1b4e5cd91f9572fce9',setup)
  self.assertIn('LMCTL_VERSION=0.2.462',setup)
  self.assertIn('@lmctl-ai/lmctl@0.2.462',text('.github/actions/qualify-platform/action.yml'))
 def test_public_release_state_has_no_foreign_pilot_records(self):
  state=json.loads(text('release-state.json'))
  self.assertEqual(state['format'],'native-release-state/2')
  for tag,record in state['candidates'].items():
   self.assertEqual(record['request']['tag'],tag)
   self.assertIn('github.com/lmctlhq/lmauth/actions/',record['private_run'])
   self.assertIn('github.com/lmctl-ai/lmauth/actions/',record['public_run'])
  self.assertNotIn('lmoffice',text('REVOKED')+text('release-state.json'))
 def test_candidate_shell_inputs_are_passed_through_environment(self):
  for file in ['.github/workflows/qualify-private-draft.yml','.github/workflows/qualify-platforms.yml','.github/actions/qualify-platform/action.yml']:
   in_run=False
   for line in text(file).splitlines():
    stripped=line.lstrip()
    if stripped.startswith('run:'):
     in_run=True
    elif in_run and stripped.startswith('- name:'):
     in_run=False
    if in_run:
     self.assertNotIn('${{ inputs.',line,file+': '+line)
 def test_broker_correlation_title_matches_worker_run_name(self):
  broker=text('scripts/qualification_broker.py')
  workflow=text('.github/workflows/qualify-platforms.yml')
  title=next(line for line in workflow.splitlines() if line.startswith('run-name: ')).split(': ',1)[1]
  title=title.replace('${{ github.event.client_payload.parent_run_id }}','PARENT_RUN_ID')
  title=title.replace('${{ github.event.client_payload.parent_attempt }}','PARENT_ATTEMPT')
  title=title.replace('${{ github.event.client_payload.tag }}','TAG')
  self.assertEqual(title,'Qualify artifact PARENT_RUN_ID.PARENT_ATTEMPT TAG')
  self.assertIn("title=f'Qualify artifact {parent}.{attempt} {tag}'",broker)
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
