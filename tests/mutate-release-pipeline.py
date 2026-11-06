#!/usr/bin/env python3
"""Mutate an isolated source snapshot; the normal offline suite must go red."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
state=json.loads((ROOT/'release-state.json').read_text())
published=[tag for tag,candidate in state['candidates'].items() if candidate['outcome']=='published']
latest_tag=max(published,key=lambda tag:tuple(int(part) for part in tag[1:].split('.')))
mutations=[
 ('credential-inheritance','scripts/release_policy.py',"return {k:v for k,v in env.items() if k not in {'GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN','ACTIONS_ID_TOKEN_REQUEST_URL'}}",'return dict(env)'),
 ('producer-identity','scripts/release_policy.py',"m.get('private_repository')!=PRIVATE","False"),
 ('certificate-run','scripts/release_policy.py',"if parts[4]==str(m['run_id']) and positive(parts[6])>=positive(m['run_attempt']):","if True:"),
 ('selected-tag','scripts/verify-private-build.py',"if m.get('tag')!=os.environ['EXPECTED_TAG']:","if False:"),
 ('selected-purpose','scripts/verify-private-build.py'," or m['deliberate_failure']!=(purpose=='true')",""),
 ('sealed-cleanup','scripts/release_policy.py',"if manifest.get('deliberate_failure') is not True:","if False:"),
 ('older-candidate','scripts/release_policy.py',"if latest and key<version(latest):","if False:"),
 ('revoked-candidate','scripts/release_policy.py',"if tag in revoked:","if False:"),
 ('asset-id','scripts/release_policy.py',"'id':positive(asset['id'])","'id':1"),
 ('late-recheck','scripts/manage-qualified-draft.py',"policy(api,tag);release,etag=recheck(api,root,seal,request,False)","policy(api,tag)"),
 ('frozen-repair','scripts/stage-frozen-draft.py',"if any(a['name'] in {SEAL,BUNDLE} for a in release.get('assets',[])) and name!=BUNDLE:","if False:"),
 ('stage-run-number','scripts/stage-frozen-draft.py',"'run_id','run_number','run_attempt'","'run_id','run_attempt'"),
 ('native-api-gate','scripts/qualification_broker.py',"for name in {'candidate'}|PLATFORMS:","for name in {'candidate'}:"),
 ('cancel',' .github/workflows/qualify-private-draft.yml'.strip(),"!cancelled() && ",""),
 ('queue-candidate','.github/workflows/qualify-private-draft.yml',"group: lmauth-qualification-${{ inputs.tag || github.event.client_payload.tag }}","group: one-shared-pending-slot"),
 ('queue-writer','.github/workflows/qualify-private-draft.yml',"      queue: max\n",""),
 ('artifact-layout','.github/actions/qualify-platform/action.yml','merge-multiple: true','merge-multiple: false'),
 ('action-pin','.github/workflows/qualify-private-draft.yml','actions/checkout@11d5960a326750d5838078e36cf38b85af677262','actions/checkout@v4'),
 ('doc-permissions','docs/release-pipeline.md','| promote | contents:write; actions:read |','| promote | contents:read; actions:read |'),
 ('throwaway-control-status','scripts/qualification_broker.py',"control[0].get('status')!='completed'",'False'),
 ('action-cancel','.github/actions/qualify-platform/action.yml','if: always() && !cancelled()','if: always()'),
 ('qualify-tag','.github/workflows/qualify-platforms.yml','LMAUTH_QUALIFY_TAG: ${{ needs.candidate.outputs.tag }}',"LMAUTH_QUALIFY_TAG: ''"),
 ('deliberate-macos-arm64','.github/workflows/qualify-platforms.yml','needs: [candidate, qualify-macos-arm64, integration]','needs: [candidate, integration]'),
 ('runbook-redrive','docs/release-pipeline.md','gh run rerun --repo lmctlhq/lmauth --job PUBLISH_DRAFT_JOB_ID','gh run rerun --repo lmctlhq/lmauth --job WRONG_JOB_ID'),
 ('runbook-revocation-first','docs/release-pipeline.md','git add REVOKED','git add docs/release-pipeline.md'),
 ('unsealed-v016-note','docs/release-pipeline.md','The public `v0.1.6` draft came from','The public partial draft came from'),
 ('copied-pilot-state','release-state.json','https://github.com/lmctlhq/lmauth/actions/','https://github.com/lmctlhq/lmoffice/actions/'),
 ('copied-pilot-revoked','REVOKED','v0.1.7 sealed throwaway qualification failure','v0.1.60 copied lmoffice pilot'),
 ('stale-readme-pin','README.md',f'github:lmctl-ai/lmauth@{latest_tag}','github:lmctl-ai/lmauth@v0.0.0'),
 ('worker-run-name','.github/workflows/qualify-platforms.yml','run-name: Qualify artifact','run-name: Qualify lmauth artifact'),
]
with tempfile.TemporaryDirectory(prefix='release-mutations-') as temporary:
 root=Path(temporary)
 for name in ['scripts','tests','.github','docs']:
  shutil.copytree(ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copy2(ROOT/'release-policy.json',root/'release-policy.json')
 shutil.copy2(ROOT/'REVOKED',root/'REVOKED')
 shutil.copy2(ROOT/'release-state.json',root/'release-state.json')
 shutil.copy2(ROOT/'README.md',root/'README.md')
 command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_release*.py']
 baseline=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if baseline.returncode:sys.stdout.buffer.write(baseline.stdout);raise SystemExit('mutation baseline is not green')
 for name,file,old,new in mutations:
  p=root/file;source=p.read_text()
  if old not in source:raise SystemExit('mutation target not found: '+name)
  try:
   p.write_text(source.replace(old,new,1));r=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   if r.returncode==0:raise SystemExit('SURVIVED '+name)
   if b'ModuleNotFoundError' in r.stdout or b'SyntaxError' in r.stdout:sys.stdout.buffer.write(r.stdout);raise SystemExit('invalid control '+name)
   print('CAUGHT '+name,flush=True)
  finally:p.write_text(source)
print('PASS '+str(len(mutations))+' release mutations')
