# Create backend state for GCS
remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
  config = {
    bucket         = "sphinx-template-site-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "us-west-1"
    encrypt        = true
    dynamodb_table = "sphinx-template-site-table"
  }
}

locals {
  root_deployments_dir       = get_parent_terragrunt_dir()
  relative_deployment_path   = path_relative_to_include()
  deployment_path_components = compact(split("/", local.relative_deployment_path))

  stack = local.deployment_path_components[0]
}

# Importing config files and defining default
# to launch the corresponding stack
terraform {
  source = "${local.root_deployments_dir}/..//modules/stacks/${local.stack}"

  extra_arguments "extra_args" {
    required_var_files = [
      "${local.root_deployments_dir}/../infra_config.tfvars.json"
    ]

    commands = [
      "apply",
      "plan",
      "import",
      "push",
      "refresh",
      "destroy"
    ]
  }
}