#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Bootstrap: check tools and AWS login, create the Python venv and initialise Terraform,
# so a fresh clone can build and deploy with nothing set up by hand.
export AWS_PROFILE="${AWS_PROFILE:-dantelore}"

for tool in python3 terraform aws; do
    command -v "$tool" > /dev/null || { echo "Missing $tool (Terraform: brew install hashicorp/tap/terraform)"; exit 1; }
done
aws sts get-caller-identity > /dev/null || { echo "AWS login expired: aws sso login --profile $AWS_PROFILE"; exit 1; }

if [ ! -d .venv ]; then
    echo "Creating Python venv..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install requirements on first run, and again whenever a requirements file changes
if [ ! -f .venv/.installed ] || [ -n "$(find requirements*.txt -newer .venv/.installed)" ]; then
    echo "Installing Python requirements..."
    pip install --quiet -r requirements.txt
    touch .venv/.installed
fi

echo "Initialising Terraform..."
terraform -chdir=terraform init -input=false -reconfigure > /dev/null

echo "Terraform time!"
(
  cd terraform
  terraform apply -auto-approve
)
