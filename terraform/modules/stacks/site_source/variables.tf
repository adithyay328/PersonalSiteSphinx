# Declaring input variables that we
# need

# Each usage of this module creates a "siteSource",
# which is a combination of:
# An S3 bucket with static assets
# A Cloudfront Distribution in front of that bucket
# Route 53 Rules pointing to that distribution
# And an ACM Certificate for that distribution

# Defining all input variables for this module
# up here
variable "bucket_name" {
  type = string
  nullable = false
}

variable "cloudfront_aliases" {
  type = list(string)
  nullable = false
}

variable "cloudfront_path_prefix" {
  type = string
  nullable = true
}

variable "cloudfront_default_root_object" {
  type = string
  default = "index.html"
}

variable "domain_name" {
  type = string
  nullable = false
}

variable "viewer_request_function_arn_list" {
  type = list(string)
}

variable "route53_zone_id" {
  type = string
}

# Getting access to user ID
data "aws_caller_identity" "current" {}

# Storing account ID in locals to make it easier to access
locals {
    account_id = data.aws_caller_identity.current.account_id
}