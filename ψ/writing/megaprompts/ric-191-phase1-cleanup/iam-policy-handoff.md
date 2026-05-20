# IAM policy handoff — riceguard prod operator

**For:** AWS admin
**From:** Fiez
**Purpose:** Grant a deploy/operator IAM user (e.g. `riceguard-prod-cicd` or my personal `ittipol-aws`) the minimum permissions needed to manage the 4 RiceGuard prod EC2 instances over SSM. No SSH ingress is exposed on these hosts; SSM is the only path.

**Policy file:** [`iam-policy-riceguard-prod.json`](iam-policy-riceguard-prod.json)

## Account + region

- **AWS account:** `654654475577`
- **Region:** `ap-southeast-7` (Bangkok)

## Target EC2s — scoped via tags

The policy uses tag conditions `Project=riceguard` AND `Env=prod`, which matches exactly these four instances (verified 2026-05-20):

| Instance ID | Name | Private IP |
|---|---|---|
| `i-0aa46f0468a9fd61e` | Rice Guard Prod API | 10.40.10.212 |
| `i-0f21012ac6240d468` | Rice Guard Prod DB | 10.40.10.155 |
| `i-084f4caaf4716f9d9` | Rice Guard Prod Broker | 10.40.10.242 |
| `i-01357f7c65795b7fc` | Rice Guard Prod Static | 10.40.10.200 |

Any future EC2 with the same two tags will automatically inherit access. Staging EC2s (no `Env=prod` tag) and unrelated instances are excluded by the condition.

## What each statement allows

| Sid | Why it's needed |
|---|---|
| `SsmSessionOnRiceguardProdEC2s` | Open an interactive shell session via `aws ssm start-session --target <instance-id>` — needed for editing `/opt/riceguard/env/.env`, restarting docker containers, ad-hoc diagnostics. **Tag-scoped.** |
| `SsmSessionDocuments` | Permission on the AWS-managed session documents that Session Manager invokes under the hood. No tag-scoping possible — these are AWS-owned. |
| `SsmSendCommandOnRiceguardProdEC2s` | Send a one-shot shell command via `aws ssm send-command` — useful for scripted operations like the env-file probe we did during the credential audit. **Tag-scoped.** |
| `SsmSendCommandShellDocument` | Permission on the `AWS-RunShellScript` document used by `send-command`. AWS-owned, no tag-scoping. |
| `SsmReadCommandAndSessionResults` | Read back the output of `send-command` and list active sessions. Read-only metadata; required by every Session Manager / RunCommand workflow. |
| `Ec2DescribeForInstanceLookup` | List instances + their tags so the operator can find the right `i-xxx` to target. These APIs don't support resource-level scoping, so `Resource: "*"` is the only option (this is the AWS-recommended pattern). |
| `SsmParameterStoreRiceguardProd` | Read `/riceguard/prod/*` Parameter Store entries. Currently only used by the `riceguard-sysinfo` service (`/riceguard/prod/sysinfo/*` per `07-security-and-iam.md` line 105), but worth including for future ops without needing a second policy update. |

## What the policy explicitly does NOT grant

- ❌ Any write to EC2 / EBS (no terminate, no stop, no reboot, no AMI ops)
- ❌ IAM modifications
- ❌ Any access to non-prod (no staging, no tooling, no other VPCs)
- ❌ Any access to RDS, S3, or other AWS services beyond the SSM/EC2 scope above
- ❌ SSM Parameter Store **write** — only read
- ❌ Session Manager port-forwarding to arbitrary ports — only allowed via the AWS-StartPortForwardingSession document, still tag-scoped to riceguard prod instances

## Attach to a new IAM user (recommended)

Per the [`README-CICD.md`](https://github.com/Mobile-AI-Co-Ltd-0105567015509/Rice-Guard-API/blob/develop/.github/workflows/README-CICD.md) the CI/CD flow expects an IAM user named `riceguard-prod-cicd`. Recommended setup:

```
1. Create IAM user `riceguard-prod-cicd` (no console access, programmatic only)
2. Attach a managed inline policy with the JSON in `iam-policy-riceguard-prod.json`
3. Generate access keys for the user
4. Hand the access keys to Fiez to add to GitHub Secrets as:
     - AWS_CICD_ACCESS_KEY_ID
     - AWS_CICD_SECRET_ACCESS_KEY
```

(Per `README-CICD.md` lines 52-54 — these are the secret names the prod deploy workflow already expects.)

## Or attach to an existing IAM user

If you'd prefer to grant my personal user `ittipol-aws` the same permissions directly:

```
1. Attach the same JSON as an inline policy on user `ittipol-aws`
2. No new access keys needed — I'll use my existing ones
```

This is what was used during the 2026-05-20 credential audit to confirm prod's `.env` state. Less ideal long-term (operations should run as a service user, not a person), but workable for short-term cleanup.

## Verification after attach

Once attached, this should succeed:

```bash
aws sts get-caller-identity                           # confirms identity
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=riceguard" \
            "Name=tag:Env,Values=prod" \
  --query 'Reservations[].Instances[].[InstanceId,Tags[?Key==`Name`]|[0].Value]' \
  --output table                                       # lists the 4 prod EC2s
aws ssm start-session --target i-0aa46f0468a9fd61e    # opens shell on prod API
```

And this should be denied (verifying scope tightness):

```bash
aws ssm start-session --target <a-non-riceguard-instance-id>
# Expected: AccessDeniedException
```
