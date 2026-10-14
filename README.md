# Semak Dulu

WhatsApp bot that helps seniors check a payment QR code before paying.
Design: [docs/SDD.md](docs/SDD.md) · Requirements: [docs/SRS.md](docs/SRS.md) · Today's plan: [docs/sprint-plan.md](docs/sprint-plan.md)

## What is already in this repo

| Ready to use | To build (see your task card) |
|---|---|
| `src/core/types.py` — the shared contracts (do not change without telling the team) | `core/emv.py`, `decode.py`, `classify.py`, `verdict.py` (Owner A) |
| `src/core/store.py` — `InMemoryStore` and `DynamoStore`, both tested | `core/flows.py`, `escalation.py`, `reports.py` (Owner C) |
| `src/core/messages.py` + `src/messages/ms.yaml`, `en.yaml` (drafts, need BM review) | `channels/whatsapp.py`, `telegram.py` (Owner B) |
| `src/handlers/ingest.py`, `worker.py`, `config.py` — Lambda glue, tested with moto | deployment, Meta setup, demo video (Owner B) |
| `template.yaml` — SAM stack, **no Docker needed** | |
| `scripts/build_layer.sh` / `.ps1` — builds QR libraries for Lambda | |
| `scripts/chat_sim.py` — chat with the bot locally, no AWS | |
| `tests/` — 110 passing tests (contracts, store, messages, handlers) | more tests (each owner) |

## Fasa 0 setup (everyone, about 20 minutes)

You need **Python 3.12** and **Git**. Check with `python3.12 --version` (macOS/Linux) or `py -3.12 --version` (Windows).

```bash
git clone https://github.com/<your-org>/semak-dulu.git
cd semak-dulu

# macOS / Linux / WSL
python3.12 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
pytest                     # expect: 110 passed
python scripts/chat_sim.py # type: @anak Daftar   (says "not built yet" until Owner C starts)
```

## Daily rules

1. Work only in the files on your task card. `src/core/types.py` is shared: announce in the group chat before changing it, and only one person edits it at a time.
2. Commit small and often: `git pull --rebase` → `pytest` → `git push`.
3. Never commit: `.env`, tokens, `layer/build/`, real QR images, real names or account numbers.
4. `pytest` must pass before every push.

## Deploy (Owner B)

```bash
bash scripts/build_layer.sh      # Windows: powershell -ExecutionPolicy Bypass -File scripts\build_layer.ps1
sam build                        # run inside the Python 3.12 venv; NEVER add --use-container
sam deploy --guided              # first time only; afterwards: sam build && sam deploy
```

Secrets (once per stage):

```bash
aws ssm put-parameter --type SecureString --name /semak/dev/wa_token           --value "<token>"
aws ssm put-parameter --type SecureString --name /semak/dev/wa_phone_number_id --value "<id>"
aws ssm put-parameter --type SecureString --name /semak/dev/wa_app_secret      --value "<secret>"
aws ssm put-parameter --type SecureString --name /semak/dev/wa_verify_token    --value "<any random text>"
aws ssm put-parameter --type SecureString --name /semak/dev/report_pepper      --value "$(python -c 'import secrets;print(secrets.token_hex(32))')"
# later: tg_token, tg_secret.   Update a value: add --overwrite
```

Lambda reads secrets at cold start. After changing one, redeploy or wait for new containers.
