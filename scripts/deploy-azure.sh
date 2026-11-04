#!/usr/bin/env bash
# Preview by default. Resource creation requires --apply and an explicit target.
set -euo pipefail
umask 077
mode=plan
for argument in "$@"; do
  case "$argument" in --plan) mode=plan ;; --apply) mode=apply ;; *) echo 'Usage: deploy-azure.sh [--plan|--apply]' >&2; exit 2 ;; esac
done
: "${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID}"
: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${AZURE_LOCATION:?Set AZURE_LOCATION, for example westeurope}"
: "${DVT_PREFIX:?Set a unique lowercase prefix (3-20 characters)}"
: "${DVT_IMAGE:?Set a GitHub Container Registry image with release tag or digest}"
: "${AZURE_SQL_PASSWORD_FILE:?Set the path to the existing Azure SQL password file}"
: "${AZURE_VNET_ID:?Set the existing VNet resource ID}"
: "${AZURE_INFRASTRUCTURE_SUBNET_ID:?Set the existing Container Apps subnet resource ID}"
command -v az >/dev/null || { echo 'Azure CLI is required.' >&2; exit 2; }
command -v python >/dev/null || { echo 'Python 3.12+ is required.' >&2; exit 2; }
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
parameter_dir="$(mktemp -d)"
trap 'rm -rf -- "$parameter_dir"' EXIT
python - "$parameter_dir/parameters.json" <<'PY'
import json, os, re, sys
from pathlib import Path
prefix=os.environ['DVT_PREFIX']
if not re.fullmatch(r'[a-z][a-z0-9-]{1,18}[a-z0-9]',prefix):raise SystemExit('DVT_PREFIX: use 3-20 lowercase letters/digits/hyphens.')
image=os.environ['DVT_IMAGE']
if not image.startswith('ghcr.io/') or (':' not in image.rsplit('/',1)[-1] and '@sha256:' not in image):raise SystemExit('DVT_IMAGE requires namespace and explicit release tag or digest.')
def secret(name):
    path=os.environ.get(name)
    value=Path(path).read_text().rstrip('\r\n') if path else ''
    if not value:raise SystemExit(name+' must contain a non-empty secret.')
    return value
parameters={
    'prefix':{'value':prefix},'location':{'value':os.environ['AZURE_LOCATION']},
    'containerImage':{'value':image},
    'sqlServerFqdn':{'value':os.environ.get('AZURE_SQL_SERVER','dbservertil.database.windows.net')},
    'sqlDatabase':{'value':os.environ.get('AZURE_SQL_DATABASE','data-visualization-tool-db')},
    'sqlUser':{'value':os.environ.get('AZURE_SQL_USER','fuddos')},
    'sqlSchema':{'value':os.environ.get('AZURE_SQL_SCHEMA','dbo')},
    'sqlPassword':{'value':secret('AZURE_SQL_PASSWORD_FILE')},
    'virtualNetworkId':{'value':os.environ['AZURE_VNET_ID']},
    'infrastructureSubnetResourceId':{'value':os.environ['AZURE_INFRASTRUCTURE_SUBNET_ID']},
}
username=os.environ.get('GHCR_USERNAME','')
if username:
    parameters['registryUsername']={'value':username}
    parameters['registryToken']={'value':secret('GHCR_TOKEN_FILE')}
Path(sys.argv[1]).write_text(json.dumps({'parameters':parameters}))
PY
current_subscription="$(az account show --query id --output tsv)"
if [[ "${current_subscription,,}" != "${AZURE_SUBSCRIPTION_ID,,}" ]]; then
  echo 'The active Azure account does not match AZURE_SUBSCRIPTION_ID. Select the intended subscription first.' >&2
  exit 2
fi
if [[ "$mode" == apply ]]; then
  az group create --subscription "$AZURE_SUBSCRIPTION_ID" --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --output none
else
  az group show --subscription "$AZURE_SUBSCRIPTION_ID" --name "$AZURE_RESOURCE_GROUP" --output none
fi
operation=what-if
if [[ "$mode" == apply ]]; then operation=create; fi
az deployment group "$operation" --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$AZURE_RESOURCE_GROUP" --name "${DVT_PREFIX}-deployment" \
  --template-file "$repo_dir/infra/azure/main.bicep" --parameters "@$parameter_dir/parameters.json"
