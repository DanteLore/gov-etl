#!/usr/bin/env bash
set -e

echo "Terraform time!"
(
  cd terraform
  terraform apply -auto-approve
)
